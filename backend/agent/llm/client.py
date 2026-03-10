import google.generativeai as genai
import asyncio
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, system_instruction: str = None):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set in configuration")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.system_instruction = system_instruction
        self.model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=system_instruction
        )

    async def complete(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generic completion method.
        """
        try:
            model = self.model
            if system_prompt:
                model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_prompt)
            
            response = await asyncio.to_thread(
                model.generate_content, prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"LLM completion error: {str(e)}")
            raise

    async def complete_json(self, prompt: str, system_prompt: str = None) -> dict:
        """
        Expects a JSON response and parses it.
        """
        text = await self.complete(prompt, system_prompt)
        try:
            # Basic cleanup of markdown markers
            clean = text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()
            return json.loads(clean)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse LLM JSON response: {text}")
            # Try a second pass to find JSON in the text
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end != -1:
                    return json.loads(text[start:end])
            except:
                pass
            raise ValueError(f"Invalid JSON from LLM: {str(e)}")
