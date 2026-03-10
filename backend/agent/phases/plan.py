import json
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from agent.llm.client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class PlannedJob:
    title: str
    company: str
    url: str
    description: str
    platform: str
    match_score: float
    reasoning: str
    cover_note: str
    key_skills_to_highlight: List[str]


class PlanPhase:
    def __init__(self, user: Any, raw_jobs: List[Any]):
        self.user = user
        self.raw_jobs = raw_jobs
        self.llm = LLMClient()

    async def execute(self) -> List[PlannedJob]:
        """Score and filter jobs using LLM."""
        planned_jobs = []
        logger.info(f"Planning applications for {len(self.raw_jobs)} jobs...")

        for job in self.raw_jobs:
            try:
                plan = await self._analyze_job(job)
                if plan.get('should_apply') and float(plan.get('match_score', 0)) >= 0.7:
                    planned_jobs.append(PlannedJob(
                        title=job.title,
                        company=job.company,
                        url=job.url,
                        description=job.description,
                        platform=job.platform,
                        match_score=float(plan.get('match_score', 0)) * 100,
                        reasoning=plan.get('reasoning', ''),
                        cover_note=plan.get('cover_note', ''),
                        key_skills_to_highlight=plan.get('key_skills_to_highlight', [])
                    ))
                    logger.info(f"Accepted job: {job.title} at {job.company} [Score: {plan.get('match_score')}]")
                else:
                    logger.debug(f"Skipped job: {job.title} [Reason: {plan.get('skip_reason', 'Low Score')}]")
            except Exception as e:
                logger.error(f"Failed to analyze job {getattr(job, 'title', '?')}: {e}")
                continue

        return planned_jobs

    async def _analyze_job(self, job: Any) -> Dict[str, Any]:
        """Prompt Gemini to analyze job compatibility."""
        system_prompt = "You are a professional career advisor AI specializing in technical recruitment."

        skills = []
        exp = "Mid"
        if hasattr(self.user, 'job_preferences') and self.user.job_preferences:
            skills = getattr(self.user.job_preferences, 'skills', [])
            exp = getattr(self.user.job_preferences, 'experience_level', 'Mid')

        prompt = f"""
Analyze the following job description against this candidate's profile and return a structured JSON object.

CANDIDATE PROFILE:
Name: {getattr(self.user, 'full_name', 'Operator')}
Bio: {getattr(self.user, 'bio', '')}
Skills: {skills}
Experience Level: {exp}

JOB POSTING:
Title: {job.title}
Company: {job.company}
Description: {job.description}

Return ONLY valid JSON with this exact structure:
{{
  "match_score": <float 0.0-1.0>,
  "should_apply": <boolean>,
  "skip_reason": "<string or null>",
  "reasoning": "<2-3 sentence explanation>",
  "cover_note": "<3-4 sentence personalized cover note for this specific role>",
  "key_skills_to_highlight": ["skill1", "skill2", "skill3"],
  "red_flags": []
}}
"""
        try:
            result = await self.llm.complete_json(prompt, system_prompt)
            return result
        except Exception as e:
            logger.error(f"LLM API error during job analysis: {e}")
            return {"should_apply": False, "skip_reason": "LLM_ERROR"}
