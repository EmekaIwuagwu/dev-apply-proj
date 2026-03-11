"""
Form filler — scans visible form fields, maps them to user data via LLM,
then fills each field using human-like behaviour.
"""
import base64
import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from agent.brain import Brain
from agent.llm import LLMClient

logger = logging.getLogger(__name__)


class FormFiller:
    def __init__(self, page: Page, user: Any, brain: Brain, preferences: Any = None):
        self.page = page
        self.user = user
        self.brain = brain
        self.preferences = preferences
        self.llm = LLMClient()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def fill(self, job: Any) -> None:
        """
        Scan the page, map every visible form field to a value,
        then fill each field.
        """
        elements = await self._scan()
        if not elements:
            logger.warning("No visible form fields found — nothing to fill")
            return

        logger.info(f"Mapping {len(elements)} form fields via LLM …")
        mapping = await self._map_fields(elements, job)

        for item in mapping:
            selector: str = item.get("selector", "")
            value: Optional[str] = item.get("value")
            ftype: str = item.get("type", "text")
            label: str = item.get("label", selector)
            needs_gen: bool = bool(item.get("needs_generated_answer", False))

            if not selector:
                continue

            # Generate answer for open-ended questions
            if needs_gen and not value:
                logger.info(f"Generating answer for: {label!r}")
                value = await self._generate_answer(label, job)

            await self.brain.between_fields()

            try:
                if ftype == "file":
                    await self._upload_resume(selector)
                elif ftype == "select":
                    if value:
                        await self.page.select_option(selector, value, timeout=5000)
                elif ftype in ("checkbox", "radio"):
                    if str(value).lower() in ("true", "yes", "1"):
                        await self.page.check(selector, timeout=5000)
                else:
                    if value:
                        await self.brain.type_text(self.page, selector, str(value))
            except Exception as e:
                logger.warning(f"Fill failed for {selector!r}: {e}")
                # Fallback: direct fill
                try:
                    if ftype not in ("file", "checkbox", "radio", "select") and value:
                        await self.page.fill(selector, str(value), timeout=5000)
                except Exception:
                    pass

        await self.brain.sleep(1, 2)

    # ------------------------------------------------------------------
    # DOM scanner
    # ------------------------------------------------------------------

    async def _scan(self) -> List[Dict]:
        """Return visible interactive elements as JSON descriptors."""
        return await self.page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll('input, textarea, select'))
                    .filter(el => {
                        const s = window.getComputedStyle(el);
                        const b = el.getBoundingClientRect();
                        return (
                            s.display !== 'none' &&
                            s.visibility !== 'hidden' &&
                            el.type !== 'hidden' &&
                            b.width > 0 && b.height > 0
                        );
                    })
                    .map(el => {
                        const labelEl =
                            document.querySelector(`label[for="${el.id}"]`) ||
                            el.closest('label') ||
                            el.closest('[class*="field"],[class*="form-group"],[class*="input-wrap"]')
                               ?.querySelector('label,[class*="label"]');

                        const label = (
                            labelEl?.innerText?.trim() ||
                            el.placeholder?.trim() ||
                            el.ariaLabel?.trim() ||
                            el.getAttribute('data-label')?.trim() ||
                            el.name?.replace(/[_-]/g, ' ') ||
                            ''
                        );

                        return {
                            selector: el.id ? `#${el.id}`
                                    : el.name ? `[name="${el.name}"]`
                                    : el.tagName.toLowerCase(),
                            id      : el.id,
                            name    : el.name,
                            type    : el.type || el.tagName.toLowerCase(),
                            label,
                            placeholder: el.placeholder || '',
                        };
                    });
            }
        """) or []

    # ------------------------------------------------------------------
    # LLM field mapping
    # ------------------------------------------------------------------

    async def _map_fields(self, elements: List[Dict], job: Any) -> List[Dict]:
        ctx = self._user_context()
        system = (
            f"You are a job application assistant helping "
            f"{getattr(self.user, 'full_name', 'the applicant')} fill out a form. "
            "Map every element to the correct value from the user profile."
        )

        prompt = f"""
USER PROFILE:
{ctx}

JOB:
  Title  : {getattr(job, 'title', '')}
  Company: {getattr(job, 'company', '')}
  Desc   : {getattr(job, 'description', '')[:500]}

FORM ELEMENTS:
{json.dumps(elements, indent=2)}

RULES:
1. Map standard fields (name, email, phone, LinkedIn, etc.) directly from profile.
2. Open-ended / essay questions → set needs_generated_answer=true, value=null.
3. File inputs (resume/CV) → type="file", value=null.
4. SELECT dropdowns → pick best matching option string from profile.
5. CHECKBOX for consent/agreement → value="true".
6. Skip CSRF tokens, hidden, honeypot fields.

Return ONLY a valid JSON array (no markdown):
[
  {{
    "selector": "#field-id",
    "label": "human label",
    "value": "filled value or null",
    "type": "text|textarea|email|tel|url|file|select|checkbox|radio",
    "needs_generated_answer": false
  }}
]
"""
        try:
            result = await self.llm.complete_json(prompt, system)
            if isinstance(result, list):
                return result
            # Unwrap if LLM wrapped in a dict
            for key in ("fields", "mapping", "items", "form"):
                if isinstance(result, dict) and isinstance(result.get(key), list):
                    return result[key]
        except Exception as e:
            logger.error(f"LLM mapping error: {e}")

        return self._fallback_map(elements)

    # ------------------------------------------------------------------
    # Persona-based answer generation
    # ------------------------------------------------------------------

    async def _generate_answer(self, question: str, job: Any) -> str:
        name = getattr(self.user, "full_name", "the applicant")
        system = (
            f"You ARE {name}. Write a natural, professional, first-person answer "
            "to the application question below. 2-5 sentences, specific and authentic. "
            "Never say 'As an AI'."
        )
        prompt = (
            f"Applying for {getattr(job, 'title', 'this role')} at "
            f"{getattr(job, 'company', 'this company')}.\n\n"
            f"MY PROFILE:\n{self._user_context()}\n\n"
            f"QUESTION: {question}"
        )
        try:
            answer = (await self.llm.complete(prompt, system)).strip()
            if answer.startswith('"') and answer.endswith('"'):
                answer = answer[1:-1]
            return answer
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return getattr(self.user, "bio", "")[:400] or "I am a strong candidate for this role."

    # ------------------------------------------------------------------
    # Resume upload
    # ------------------------------------------------------------------

    async def _upload_resume(self, selector: str) -> None:
        b64 = getattr(self.user, "resume_base64", "") or ""
        if not b64:
            logger.warning("No resume on user profile — skipping upload")
            return
        filename = getattr(self.user, "resume_filename", None) or f"resume_{self.user.id}.pdf"
        tmp = os.path.join(tempfile.gettempdir(), filename)
        try:
            with open(tmp, "wb") as fh:
                fh.write(base64.b64decode(b64))
            await self.page.set_input_files(selector, tmp, timeout=10000)
            logger.info(f"Resume uploaded: {filename}")
        except Exception as e:
            logger.error(f"Resume upload failed: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _user_context(self) -> str:
        skills = list(getattr(self.preferences, "skills", []) or []) if self.preferences else []
        exp = (getattr(self.preferences, "experience_level", "") or "") if self.preferences else ""
        titles = list(getattr(self.preferences, "job_titles", []) or []) if self.preferences else []
        return (
            f"  Full Name  : {getattr(self.user, 'full_name', '')}\n"
            f"  Email      : {getattr(self.user, 'email', '')}\n"
            f"  Phone      : {getattr(self.user, 'telephone', '')}\n"
            f"  LinkedIn   : {getattr(self.user, 'linkedin_url', '')}\n"
            f"  Bio        : {getattr(self.user, 'bio', '')[:300]}\n"
            f"  Skills     : {', '.join(skills)}\n"
            f"  Experience : {exp}\n"
            f"  Titles     : {', '.join(titles)}"
        )

    def _fallback_map(self, elements: List[Dict]) -> List[Dict]:
        """Rule-based mapping used when LLM call fails."""
        full = getattr(self.user, "full_name", "") or ""
        parts = full.split(" ", 1)
        first, last = parts[0], (parts[1] if len(parts) > 1 else "")

        lookup = {
            "name": full, "full_name": full, "fullname": full,
            "first_name": first, "firstname": first, "first": first,
            "last_name": last, "lastname": last, "last": last,
            "email": getattr(self.user, "email", "") or "",
            "phone": getattr(self.user, "telephone", "") or "",
            "telephone": getattr(self.user, "telephone", "") or "",
            "mobile": getattr(self.user, "telephone", "") or "",
            "linkedin": getattr(self.user, "linkedin_url", "") or "",
            "linkedin_url": getattr(self.user, "linkedin_url", "") or "",
        }

        result = []
        for el in elements:
            sel = el.get("selector", "")
            if not sel:
                continue
            ftype = (el.get("type") or "text").lower()
            name_k = (el.get("name") or "").lower().replace("-", "_")
            label_k = (el.get("label") or "").lower()

            if ftype == "file":
                result.append({"selector": sel, "label": el.get("label", ""),
                                "value": None, "type": "file",
                                "needs_generated_answer": False})
                continue

            val = None
            for key, v in lookup.items():
                if key in name_k or key in label_k:
                    val = v
                    break

            if val is not None:
                result.append({"selector": sel, "label": el.get("label", ""),
                                "value": val, "type": ftype,
                                "needs_generated_answer": False})
        return result
