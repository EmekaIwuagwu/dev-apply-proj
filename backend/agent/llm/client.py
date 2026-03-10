import asyncio
import json
import logging

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Thin async wrapper around the Google Gemini API.
    Uses gemini-2.5-flash — the most capable model available on the
    free-tier API key, perfect for answering job application questions
    fully in the user's voice.
    """

    def __init__(self, system_instruction: str = None):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set — LLM calls will fail.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.system_instruction = system_instruction
        self._model_name = "gemini-2.5-flash"
        self.model = genai.GenerativeModel(
            self._model_name,
            system_instruction=system_instruction,
        )

    # ------------------------------------------------------------------
    # Core completion
    # ------------------------------------------------------------------

    async def complete(self, prompt: str, system_prompt: str = None) -> str:
        """Plain-text completion."""
        try:
            model = self.model
            if system_prompt:
                model = genai.GenerativeModel(
                    self._model_name,
                    system_instruction=system_prompt,
                )
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            raise

    # ------------------------------------------------------------------
    # JSON completion
    # ------------------------------------------------------------------

    async def complete_json(
        self, prompt: str, system_prompt: str = None
    ) -> dict | list:
        """
        Completion that expects the model to respond with valid JSON.
        Handles both dict `{}` and list `[]` top-level responses.
        Performs two rounds of cleanup before giving up.
        """
        text = await self.complete(prompt, system_prompt)

        # ---- Round 1: strip markdown fences and try direct parse ----
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

        # ---- Round 2: find the outermost JSON object or array ----
        try:
            obj_start = text.find("{")
            arr_start = text.find("[")

            # Prefer whichever opening delimiter appears first
            use_array = (
                arr_start != -1
                and (obj_start == -1 or arr_start < obj_start)
            )

            if use_array:
                end = text.rfind("]") + 1
                if end > arr_start:
                    return json.loads(text[arr_start:end])
            else:
                end = text.rfind("}") + 1
                if obj_start != -1 and end > obj_start:
                    return json.loads(text[obj_start:end])

        except (ValueError, json.JSONDecodeError):
            pass

        logger.error(f"Could not parse LLM JSON response:\n{text[:500]}")
        raise ValueError("Invalid JSON returned by LLM.")
