"""
ai_eye.py — Gemini Vision: the agent's "eyes" on the screen.

Every time the agent needs to understand WHAT IS ON SCREEN it calls this
module.  We feed a live screenshot (PIL Image) to Gemini Vision and ask
structured questions.  The results drive every subsequent action.

Key capabilities:
  find_element()        → locate a UI element by natural-language description
  read_page_content()   → extract all readable text from the screenshot
  analyze_form()        → list every visible form field with position + label
  should_apply()        → evaluate a job page and decide yes/no
  has_captcha()         → detect CAPTCHA / bot challenge screens
"""
import asyncio
import io
import json
import logging
import re
from typing import Any, List, Optional

import google.generativeai as genai
from PIL import Image

from config import settings
from agent.vision.screen import VIEWPORT_W, VIEWPORT_H

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"


class AIEye:
    """
    The agent's visual intelligence layer.
    One shared instance per user run to avoid re-configuring the API repeatedly.
    """

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set — AI Eye cannot function")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(_MODEL)

    # ------------------------------------------------------------------
    # Element location
    # ------------------------------------------------------------------

    async def find_element(
        self,
        pil_image: Image.Image,
        description: str,
    ) -> Optional[dict]:
        """
        Ask Gemini Vision where a described element is on screen.

        Returns:
            {"x": pixel_x, "y": pixel_y, "found": True, "confidence": "high"}
            or None if not found / low confidence.

        description examples:
          "the blue Apply button"
          "the email address input field"
          "the Submit Application button"
          "any CAPTCHA or bot-verification challenge"
        """
        prompt = f"""You are analysing a screenshot of a webpage (browser window).

Task: Locate this element — "{description}"

Rules:
- x_pct and y_pct are the CENTER of the element expressed as a decimal
  fraction of the image dimensions (0.0 = left/top, 1.0 = right/bottom).
- confidence: "high" if clearly visible, "medium" if partially visible,
  "low" if guessing.
- If the element does not exist on this page set found=false.

Respond with ONLY valid JSON, no markdown:
{{"found": true,  "x_pct": 0.72, "y_pct": 0.45, "confidence": "high"}}
or
{{"found": false}}
"""
        raw = await self._call(prompt, pil_image)
        data = self._parse_json(raw)
        if not data or not data.get("found"):
            return None
        x = int(data["x_pct"] * VIEWPORT_W)
        y = int(data["y_pct"] * VIEWPORT_H)
        return {"x": x, "y": y, "found": True, "confidence": data.get("confidence", "medium")}

    async def find_all_links(
        self,
        pil_image: Image.Image,
        filter_hint: str = "",
    ) -> List[dict]:
        """
        Return a list of all visible link-like items on the page.
        Used by the searcher to identify job result links on the DDG results page.

        Returns:
            [{"text": "Job Title at Company", "x_pct": 0.3, "y_pct": 0.25}, ...]
        """
        hint = f' Focus on links related to: "{filter_hint}".' if filter_hint else ""
        prompt = f"""You are analysing a search-results page screenshot.{hint}

List every visible clickable link / result title you can see, with its
approximate center position as a fraction of image width/height.

Return ONLY valid JSON array, no markdown:
[
  {{"text": "Python Developer – Acme Corp", "x_pct": 0.35, "y_pct": 0.22}},
  {{"text": "Backend Engineer – StartupXYZ",  "x_pct": 0.35, "y_pct": 0.31}}
]

If there are no relevant links return an empty array: []
"""
        raw = await self._call(prompt, pil_image)
        data = self._parse_json(raw)
        if isinstance(data, list):
            return data
        return []

    # ------------------------------------------------------------------
    # Page content reading
    # ------------------------------------------------------------------

    async def read_page_content(self, pil_image: Image.Image) -> str:
        """
        Extract all meaningful text from the page as seen visually.
        Used to read the full job description before deciding to apply.
        """
        prompt = """You are reading a job listing page screenshot.

Extract ALL visible text content from this page — job title, company name,
location, description, requirements, responsibilities, salary, and any other
relevant information.

Return the extracted text as plain text only, preserving structure with
newlines. Do not add commentary.
"""
        return (await self._call(prompt, pil_image)).strip()

    async def analyze_form(self, pil_image: Image.Image) -> List[dict]:
        """
        Identify every visible form field on the application form page.

        Returns a list of field descriptors:
        [
          {
            "label"   : "Full Name",
            "type"    : "text|email|tel|url|textarea|file|select|checkbox",
            "x_pct"   : 0.45,
            "y_pct"   : 0.30,
            "required": true
          },
          ...
        ]
        """
        prompt = """You are analysing a job application form screenshot.

List EVERY visible form field you can see (text inputs, textareas, dropdowns,
file upload buttons, checkboxes).

For each field return:
- label    : the visible label text (e.g. "First Name", "Resume/CV", "Phone")
- type     : one of text | email | tel | url | textarea | file | select | checkbox
- x_pct    : horizontal center of the INPUT FIELD (not its label) as fraction 0-1
- y_pct    : vertical center of the INPUT FIELD as fraction 0-1
- required : true if marked as required (has * or "required"), else false

Return ONLY valid JSON array, no markdown:
[
  {"label": "Full Name",  "type": "text",     "x_pct": 0.50, "y_pct": 0.22, "required": true},
  {"label": "Email",      "type": "email",    "x_pct": 0.50, "y_pct": 0.32, "required": true},
  {"label": "Resume/CV",  "type": "file",     "x_pct": 0.50, "y_pct": 0.55, "required": true},
  {"label": "Cover Note", "type": "textarea", "x_pct": 0.50, "y_pct": 0.70, "required": false}
]

If no form fields are visible return: []
"""
        raw = await self._call(prompt, pil_image)
        data = self._parse_json(raw)
        if isinstance(data, list):
            return data
        return []

    # ------------------------------------------------------------------
    # Job evaluation
    # ------------------------------------------------------------------

    async def should_apply(
        self,
        pil_image: Image.Image,
        user_profile: str,
        job_page_text: str,
    ) -> dict:
        """
        Read the job page screenshot + extracted text and decide:
          - Should the agent apply?
          - What is the match score (0–100)?
          - What personalised cover note should be submitted?

        Returns:
        {
          "apply"     : True,
          "score"     : 87,
          "title"     : "Senior Python Engineer",
          "company"   : "Acme Corp",
          "reasoning" : "...",
          "cover_note": "..."
        }
        """
        prompt = f"""You are a senior career advisor AI acting on behalf of this candidate:

CANDIDATE PROFILE:
{user_profile}

JOB PAGE TEXT (extracted):
{job_page_text[:3000]}

Evaluate this job for the candidate:
1. Does the candidate's skills match the job requirements?
2. Is this a genuine job listing (not a redirect / error page)?
3. Is the company NOT on the excluded list?

Scoring: 0–100 (70+ = strong match, apply)

Return ONLY valid JSON, no markdown:
{{
  "apply"      : true,
  "score"      : 85,
  "title"      : "Job title as shown",
  "company"    : "Company name",
  "reasoning"  : "2-3 sentences explaining the match",
  "cover_note" : "3-4 sentence first-person cover note specific to this role",
  "skip_reason": null
}}

If the page is not a valid job listing or score < 70:
{{
  "apply"      : false,
  "score"      : 0,
  "title"      : "",
  "company"    : "",
  "reasoning"  : "",
  "cover_note" : "",
  "skip_reason": "reason for skipping"
}}
"""
        raw = await self._call(prompt, pil_image)
        data = self._parse_json(raw)
        if isinstance(data, dict):
            return data
        return {"apply": False, "score": 0, "skip_reason": "AI Eye parse error"}

    # ------------------------------------------------------------------
    # Safety checks
    # ------------------------------------------------------------------

    async def has_captcha(self, pil_image: Image.Image) -> bool:
        """
        Detect any CAPTCHA, OTP challenge, or bot-detection wall on screen.
        """
        prompt = """Look at this screenshot. Is there ANY of the following:
- A CAPTCHA (reCAPTCHA, hCaptcha, Cloudflare Turnstile, etc.)
- An OTP / verification code entry
- A "Verify you are human" challenge
- A Cloudflare bot challenge page

Reply with ONLY "YES" or "NO".
"""
        answer = (await self._call(prompt, pil_image)).strip().upper()
        return answer.startswith("Y")

    async def is_success_page(self, pil_image: Image.Image) -> bool:
        """Check whether the current page confirms a successful submission."""
        prompt = """Look at this screenshot. Does the page show a confirmation
that a job application was successfully submitted?

Look for text like "Thank you", "Application received", "Application submitted",
"We'll be in touch", or similar success indicators.

Reply with ONLY "YES" or "NO".
"""
        answer = (await self._call(prompt, pil_image)).strip().upper()
        return answer.startswith("Y")

    async def generate_answer(
        self,
        pil_image: Image.Image,
        question_label: str,
        user_profile: str,
        job_title: str,
        company: str,
    ) -> str:
        """
        Generate a first-person answer to an open-ended application question
        in the user's voice.
        """
        prompt = f"""You are acting AS this candidate (write in first person "I"):

CANDIDATE PROFILE:
{user_profile}

They are applying for: {job_title} at {company}

Application question visible on screen:
"{question_label}"

Write a natural, professional, specific 2-5 sentence answer in first person.
Do NOT start with "As an AI". Do NOT say "I am an AI".
Return ONLY the answer text — no labels, no JSON, no quotes.
"""
        answer = (await self._call(prompt, pil_image)).strip()
        # Strip wrapping quotes if present
        if answer.startswith('"') and answer.endswith('"'):
            answer = answer[1:-1]
        return answer

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call(self, prompt: str, image: Image.Image) -> str:
        """Send a text+image request to Gemini Vision and return the raw text."""
        try:
            response = await asyncio.to_thread(
                self._model.generate_content,
                [prompt, image],
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini Vision call failed: {e}")
            return ""

    @staticmethod
    def _parse_json(text: str) -> Any:
        """Parse JSON from model output, stripping markdown fences if present."""
        clean = text.strip()
        # Strip ```json ... ``` fences
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
        clean = clean.strip()

        try:
            return json.loads(clean)
        except (ValueError, json.JSONDecodeError):
            pass

        # Try finding first JSON object or array
        for start, end in [(clean.find("{"), clean.rfind("}")),
                           (clean.find("["), clean.rfind("]"))]:
            if start != -1 and end > start:
                try:
                    return json.loads(clean[start : end + 1])
                except (ValueError, json.JSONDecodeError):
                    pass

        logger.warning(f"AI Eye: could not parse JSON from: {text[:200]}")
        return None
