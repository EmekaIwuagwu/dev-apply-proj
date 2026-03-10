import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from agent.brain.human_brain import HumanBrain
from agent.llm.client import LLMClient

logger = logging.getLogger(__name__)


class FormFiller:
    """
    Intelligent form filler that:
      1. Maps standard fields (name, email, phone, LinkedIn …) directly from
         the user's saved profile.
      2. Generates persona-based answers for ANY unexpected / open-ended
         questions — completely as the individual, using Gemini.
    """

    def __init__(
        self,
        page: Page,
        user: Any,
        brain: HumanBrain,
        preferences: Any = None,
    ):
        self.page = page
        self.user = user
        self.brain = brain
        self.preferences = preferences
        self.llm = LLMClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fill_all_fields(self, job_details: Any) -> None:
        """
        Two-phase fill:
          Phase 1 — LLM maps all elements to values (standard + custom).
          Phase 2 — For any field flagged needs_generated_answer, Gemini
                    writes the answer completely as the user persona.
        """
        logger.info("Scanning page for form elements …")
        form_elements = await self._scan_form()
        if not form_elements:
            logger.warning("No interactive elements found on page.")
            return

        logger.info(
            f"Requesting LLM mapping for {len(form_elements)} elements …"
        )
        mapping = await self._get_field_mapping(form_elements, job_details)

        for item in mapping:
            selector: str = item.get("selector", "")
            value: Optional[str] = item.get("value")
            field_type: str = item.get("type", "text")
            needs_answer: bool = bool(item.get("needs_generated_answer", False))
            label: str = item.get("label", selector)

            if not selector:
                continue

            # For open-ended / unexpected questions, generate a full answer
            if needs_answer and not value:
                logger.info(f"Generating persona answer for: {label!r}")
                value = await self._generate_persona_answer(label, job_details)

            if not value and field_type != "file":
                continue

            await self.brain.pause_between_fields()

            try:
                if field_type == "file":
                    await self._upload_resume(selector)
                elif field_type == "select":
                    await self.page.select_option(selector, value)
                elif field_type in ("checkbox", "radio"):
                    if str(value).lower() in ("true", "yes", "1"):
                        await self.page.check(selector)
                else:
                    # textarea, text, email, tel, url — type like a human
                    await self.brain.type_text(self.page, selector, str(value))
            except Exception as e:
                logger.warning(f"Primary fill failed for {selector!r}: {e}")
                # Playwright direct fill as fallback
                try:
                    if field_type not in ("file", "checkbox", "radio", "select"):
                        await self.page.fill(selector, str(value))
                except Exception as fe:
                    logger.debug(f"Fallback fill also failed: {fe}")

        await self.brain.human_delay(2, 4)

    # ------------------------------------------------------------------
    # DOM scanning
    # ------------------------------------------------------------------

    async def _scan_form(self) -> List[Dict[str, str]]:
        """Return simplified DOM descriptors for all visible interactive elements."""
        elements = await self.page.evaluate("""
            () => {
                const inputs = Array.from(
                    document.querySelectorAll('input, textarea, select')
                );
                return inputs
                    .filter(el => {
                        const s = window.getComputedStyle(el);
                        return (
                            s.display !== 'none' &&
                            s.visibility !== 'hidden' &&
                            el.getBoundingClientRect().width > 0
                        );
                    })
                    .map(el => {
                        // Try several strategies to find a human-readable label
                        const labelEl =
                            document.querySelector(`label[for="${el.id}"]`) ||
                            el.closest('label') ||
                            el.closest(
                                '[class*="field"],[class*="form-group"],[class*="input-wrapper"]'
                            )?.querySelector('label,[class*="label"]');

                        const label = (
                            labelEl?.innerText?.trim() ||
                            el.placeholder?.trim() ||
                            el.ariaLabel?.trim() ||
                            el.getAttribute('data-label')?.trim() ||
                            el.name?.replace(/[_-]/g, ' ') ||
                            ''
                        );

                        return {
                            id          : el.id,
                            name        : el.name,
                            type        : el.type || el.tagName.toLowerCase(),
                            tagName     : el.tagName.toLowerCase(),
                            label       : label,
                            placeholder : el.placeholder || '',
                            css_selector: el.id
                                ? `#${el.id}`
                                : el.name
                                    ? `[name="${el.name}"]`
                                    : el.tagName.toLowerCase()
                        };
                    });
            }
        """)
        return elements or []

    # ------------------------------------------------------------------
    # LLM field mapping
    # ------------------------------------------------------------------

    async def _get_field_mapping(
        self, elements: List[Dict[str, str]], job: Any
    ) -> List[Dict[str, Any]]:
        """
        Ask Gemini to map every form element to a value drawn from the
        user's full profile.  Open-ended questions are flagged for
        persona-based answer generation.
        """
        user_ctx = self._build_user_context()
        full_name = getattr(self.user, "full_name", "the applicant")
        job_title = getattr(job, "title", "")
        job_company = getattr(job, "company", "")
        job_desc = getattr(job, "description", "")[:600]
        cover_note = getattr(job, "cover_note", "")

        system_prompt = f"""You are a job application assistant helping {full_name} \
apply for a position. Your task is to map every form element to a value from \
the user's profile, or flag it for persona-based generation.

USER PROFILE (use ONLY this data — do not invent facts):
{user_ctx}

JOB BEING APPLIED TO:
  Role        : {job_title}
  Company     : {job_company}
  Description : {job_desc}
  Cover Note  : {cover_note}

MAPPING RULES:
1. STANDARD fields (full name, first name, last name, email, phone, address,
   LinkedIn URL, portfolio URL, website, etc.):
   → Map directly from the user profile above.
   → Set "needs_generated_answer": false.

2. OPEN-ENDED / CUSTOM QUESTIONS — any field whose label asks something like
   "Why do you want to work here?", "Tell us about yourself",
   "What's your greatest strength?", "Describe your experience with X",
   "What motivates you?", or any textarea whose label is a question:
   → Set "needs_generated_answer": true and "value": null.
   → Gemini will generate the answer separately, fully in the user's voice.

3. FILE upload fields (resume / CV):
   → Set type to "file" and value to null.

4. SELECT / DROPDOWN:
   → Choose the best option from the user profile (e.g. experience_level
     for seniority dropdowns, preferred job_type for work-type dropdowns).

5. CHECKBOX / RADIO (e.g. "I agree to terms"):
   → Set value to "true" if it represents consent / agreement.

6. Skip hidden fields, honeypot fields, and CSRF tokens.

Respond with ONLY a valid JSON array — no markdown, no explanation:
[
  {{
    "selector"              : "#field-id or [name=fieldname]",
    "label"                 : "human-readable label",
    "value"                 : "the value to fill, or null",
    "type"                  : "text|textarea|file|select|checkbox|radio|email|tel|url",
    "needs_generated_answer": false
  }},
  ...
]"""

        user_prompt = (
            f"FORM ELEMENTS TO MAP:\n{json.dumps(elements, indent=2)}"
        )

        try:
            response = await self.llm.complete_json(user_prompt, system_prompt)
            if isinstance(response, list):
                return response
            # LLM may wrap the list in a dict
            if isinstance(response, dict):
                for key in ("fields", "mapping", "form", "result", "data", "items"):
                    if key in response and isinstance(response[key], list):
                        return response[key]
            logger.warning("Unexpected LLM response shape; falling back.")
            return self._fallback_direct_map(elements)
        except Exception as e:
            logger.error(f"LLM field mapping error: {e}")
            return self._fallback_direct_map(elements)

    # ------------------------------------------------------------------
    # Persona-based answer generator
    # ------------------------------------------------------------------

    async def _generate_persona_answer(
        self, question_label: str, job: Any
    ) -> str:
        """
        Uses Gemini to answer an unexpected / open-ended question
        COMPLETELY AS the user — in first person, drawing on their full
        profile, and showing genuine enthusiasm for the specific role.
        """
        user_ctx = self._build_user_context()
        full_name = getattr(self.user, "full_name", "the applicant")
        job_title = getattr(job, "title", "this role")
        job_company = getattr(job, "company", "the company")
        job_desc = getattr(job, "description", "")[:400]

        system_prompt = f"""You ARE {full_name}. You are personally filling \
out a job application for the role of {job_title} at {job_company}.

Answer the question below COMPLETELY AS {full_name} — in first person, \
naturally, professionally, and authentically.

YOUR PROFILE AS {full_name}:
{user_ctx}

ROLE CONTEXT:
  Job Title   : {job_title}
  Company     : {job_company}
  Description : {job_desc}

ANSWER GUIDELINES:
  • Write in first person ("I have …", "My experience …", "I am passionate …").
  • Be professional yet personable — sound like a real thoughtful human.
  • Keep responses concise (2–5 sentences) unless the question clearly
    demands more detail.
  • Draw specific, authentic details from the profile (skills, bio, etc.).
  • Show genuine enthusiasm for THIS specific role and company.
  • Do NOT use hollow phrases like "I am a hard worker" without evidence.
  • Do NOT reveal that this application is automated.
  • Do NOT start with "As an AI" or any similar disclaimer."""

        prompt = (
            f'I am applying for {job_title} at {job_company}.\n\n'
            f'Question on the application form: "{question_label}"\n\n'
            f'Answer this question as {full_name}, drawing from the profile.'
        )

        try:
            answer = (await self.llm.complete(prompt, system_prompt)).strip()
            # Strip surrounding quotes if LLM added them
            if len(answer) >= 2 and answer[0] == '"' and answer[-1] == '"':
                answer = answer[1:-1]
            return answer
        except Exception as e:
            logger.error(
                f"Persona answer generation failed for {question_label!r}: {e}"
            )
            bio = getattr(self.user, "bio", "")
            return (
                bio[:400]
                if bio
                else f"I am a strong candidate for this {job_title} position."
            )

    # ------------------------------------------------------------------
    # User context builder
    # ------------------------------------------------------------------

    def _build_user_context(self) -> str:
        """Assemble a comprehensive, human-readable profile block for LLM prompts."""
        skills: List[str] = []
        experience_level: str = ""
        job_titles: List[str] = []
        job_type: str = ""
        preferred_locations: List[str] = []

        if self.preferences:
            skills = list(getattr(self.preferences, "skills", []) or [])
            experience_level = (
                getattr(self.preferences, "experience_level", "") or ""
            )
            job_titles = list(getattr(self.preferences, "job_titles", []) or [])
            job_type = getattr(self.preferences, "job_type", "") or ""
            preferred_locations = list(
                getattr(self.preferences, "preferred_locations", []) or []
            )

        return (
            f"  Full Name          : {getattr(self.user, 'full_name', '')}\n"
            f"  Salutation         : {getattr(self.user, 'salutation', '')}\n"
            f"  Email              : {getattr(self.user, 'email', '')}\n"
            f"  Phone              : {getattr(self.user, 'telephone', '')}\n"
            f"  LinkedIn           : {getattr(self.user, 'linkedin_url', '')}\n"
            f"  Professional Bio   : {getattr(self.user, 'bio', '')}\n"
            f"  Technical Skills   : {', '.join(skills) if skills else 'Not specified'}\n"
            f"  Experience Level   : {experience_level or 'Not specified'}\n"
            f"  Target Job Titles  : {', '.join(job_titles) if job_titles else 'Not specified'}\n"
            f"  Preferred Locations: {', '.join(preferred_locations) if preferred_locations else 'Remote / Flexible'}\n"
            f"  Job Type           : {job_type or 'Not specified'}"
        )

    # ------------------------------------------------------------------
    # Fallback direct mapper (no LLM)
    # ------------------------------------------------------------------

    def _fallback_direct_map(
        self, elements: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Rule-based field mapping used when the LLM call fails.
        Covers the most common standard fields by name / label patterns.
        """
        full_name: str = getattr(self.user, "full_name", "") or ""
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        standard_map: Dict[str, str] = {
            "name"        : full_name,
            "full_name"   : full_name,
            "fullname"    : full_name,
            "first_name"  : first_name,
            "firstname"   : first_name,
            "last_name"   : last_name,
            "lastname"    : last_name,
            "email"       : getattr(self.user, "email", "") or "",
            "phone"       : getattr(self.user, "telephone", "") or "",
            "telephone"   : getattr(self.user, "telephone", "") or "",
            "mobile"      : getattr(self.user, "telephone", "") or "",
            "linkedin"    : getattr(self.user, "linkedin_url", "") or "",
            "linkedin_url": getattr(self.user, "linkedin_url", "") or "",
        }

        mapping: List[Dict[str, Any]] = []
        for el in elements:
            selector = el.get("css_selector", "")
            if not selector:
                continue

            el_type = (el.get("type") or "text").lower()
            name_key = (el.get("name") or "").lower().replace("-", "_")
            label_key = (el.get("label") or "").lower()

            if el_type == "file":
                mapping.append(
                    {
                        "selector": selector,
                        "label": el.get("label", ""),
                        "value": None,
                        "type": "file",
                        "needs_generated_answer": False,
                    }
                )
                continue

            matched_value: Optional[str] = None
            for pattern, value in standard_map.items():
                if pattern in name_key or pattern in label_key:
                    matched_value = value
                    break

            if matched_value is not None:
                mapping.append(
                    {
                        "selector": selector,
                        "label": el.get("label", ""),
                        "value": matched_value,
                        "type": el_type,
                        "needs_generated_answer": False,
                    }
                )

        return mapping

    # ------------------------------------------------------------------
    # Resume upload
    # ------------------------------------------------------------------

    async def _upload_resume(self, file_input_selector: str) -> None:
        """Decode the base64 resume and upload it via the file input."""
        try:
            resume_b64: str = getattr(self.user, "resume_base64", "") or ""
            if not resume_b64:
                logger.warning("No resume data on user profile — skipping upload.")
                return

            resume_data = base64.b64decode(resume_b64)
            filename = (
                getattr(self.user, "resume_filename", None)
                or f"resume_{self.user.id}.pdf"
            )
            temp_path = os.path.abspath(filename)

            with open(temp_path, "wb") as fh:
                fh.write(resume_data)

            await self.page.set_input_files(file_input_selector, temp_path)
            logger.info(f"Resume uploaded from {temp_path}")
        except Exception as e:
            logger.error(f"Resume upload failed: {e}")
