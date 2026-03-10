import logging
import base64
import os
import json
from typing import List, Dict, Any

from playwright.async_api import Page
from agent.llm.client import LLMClient
from agent.brain.human_brain import HumanBrain

logger = logging.getLogger(__name__)


class FormFiller:
    def __init__(self, page: Page, user: Any, brain: HumanBrain):
        self.page = page
        self.user = user
        self.brain = brain
        self.llm = LLMClient()

    async def fill_all_fields(self, job_details: Any):
        """
        Intelligently detect, map, and fill all fields on the current page.
        """
        logger.info("Scanning page for form elements...")
        form_elements = await self._scan_form()
        if not form_elements:
            logger.warning("No interactive elements found on page.")
            return

        logger.info(f"Generating field mapping for {len(form_elements)} elements via LLM...")
        mapping = await self._get_field_mapping(form_elements, job_details)

        for item in mapping:
            selector = item.get("selector")
            value = item.get("value")
            field_type = item.get("type", "text")

            if not selector or not value:
                continue

            await self.brain.pause_between_fields()

            try:
                if field_type == "file":
                    await self._upload_resume(selector)
                elif field_type == "select":
                    await self.page.select_option(selector, value)
                elif field_type in ("checkbox", "radio"):
                    if str(value).lower() == "true":
                        await self.page.check(selector)
                else:
                    await self.brain.type_text(self.page, selector, value)
            except Exception as e:
                logger.error(f"Failed to fill field {selector}: {e}")

        await self.brain.human_delay(2, 4)

    async def _scan_form(self) -> List[Dict[str, str]]:
        """Extract simplified DOM info for all visible interactive elements."""
        elements = await self.page.evaluate("""
            () => {
                const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
                return inputs.filter(el => {
                    // Check visibility
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           el.getBoundingClientRect().width > 0;
                }).map(el => {
                    const label = document.querySelector(`label[for="${el.id}"]`)?.innerText ||
                                  el.closest('label')?.innerText ||
                                  el.placeholder ||
                                  el.ariaLabel || "";
                    return {
                        id: el.id,
                        name: el.name,
                        type: el.type,
                        tagName: el.tagName,
                        label: label.trim(),
                        placeholder: el.placeholder,
                        css_selector: el.id ? `#${el.id}` : `[name="${el.name}"]`
                    };
                });
            }
        """)
        return elements

    async def _get_field_mapping(self, elements: List[Dict[str, str]], job: Any) -> List[Dict[str, Any]]:
        """Asks LLM to map DOM elements to user profile data."""
        system_prompt = f"""
        You are a job application assistant. Map these form elements on a job portal to the user's data.
        USER PROFILE:
        - Name: {getattr(self.user, 'full_name', '')}
        - Email: {getattr(self.user, 'email', '')}
        - Phone: {getattr(self.user, 'telephone', '')}
        - LinkedIn: {getattr(self.user, 'linkedin_url', '')}
        - Bio: {getattr(self.user, 'bio', '')}

        JOB DETAILS:
        - Role: {getattr(job, 'title', '')}
        - Company: {getattr(job, 'company', '')}

        Respond ONLY with a JSON list of objects: [{{"selector": "...", "value": "...", "type": "text|file|select|checkbox"}}]
        """
        user_prompt = f"FORM ELEMENTS:\n{json.dumps(elements, indent=2)}"
        try:
            response = await self.llm.complete_json(user_prompt, system_prompt)
            return response if isinstance(response, list) else []
        except Exception as e:
            logger.error(f"LLM Mapping error: {e}")
            return []

    async def _upload_resume(self, file_input_selector: str):
        """Decode base64 resume and upload to the file input."""
        try:
            resume_b64 = getattr(self.user, 'resume_base64', '')
            if not resume_b64:
                logger.warning("No resume data found on user.")
                return
            resume_data = base64.b64decode(resume_b64)
            temp_filename = f"resume_{self.user.id}.pdf"
            with open(temp_filename, "wb") as f:
                f.write(resume_data)
            await self.page.set_input_files(file_input_selector, os.path.abspath(temp_filename))
        except Exception as e:
            logger.error(f"Resume upload failed: {e}")
