"""
Thin async wrapper around the Google Gemini API.
All agent modules import from here — one place to swap providers.
"""
import asyncio
import json
import logging

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"


class LLMClient:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set — LLM calls will fail")
        genai.configure(api_key=settings.GEMINI_API_KEY)

    def _model(self, system: str = None) -> genai.GenerativeModel:
        return genai.GenerativeModel(_MODEL, system_instruction=system)

    async def complete(self, prompt: str, system: str = None) -> str:
        """Return raw text from the model."""
        response = await asyncio.to_thread(
            self._model(system).generate_content, prompt
        )
        return response.text

    async def complete_json(self, prompt: str, system: str = None) -> dict | list:
        """
        Return a parsed JSON object/array.
        Two cleanup passes before giving up.
        """
        text = await self.complete(prompt, system)

        # Pass 1 — strip markdown fences
        clean = text.strip()
        for fence in ("```json", "```"):
            if clean.startswith(fence):
                clean = clean[len(fence):]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        try:
            return json.loads(clean)
        except (ValueError, json.JSONDecodeError):
            pass

        # Pass 2 — find outermost { } or [ ]
        obj_s, arr_s = text.find("{"), text.find("[")
        use_arr = arr_s != -1 and (obj_s == -1 or arr_s < obj_s)
        try:
            if use_arr:
                return json.loads(text[arr_s : text.rfind("]") + 1])
            else:
                return json.loads(text[obj_s : text.rfind("}") + 1])
        except (ValueError, json.JSONDecodeError):
            pass

        raise ValueError(f"LLM did not return valid JSON.\nRaw:\n{text[:400]}")
