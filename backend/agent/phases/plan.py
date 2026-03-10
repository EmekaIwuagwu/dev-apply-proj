import logging
from dataclasses import dataclass
from typing import Any, Dict, List

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
    def __init__(self, user: Any, raw_jobs: List[Any], preferences: Any = None):
        self.user = user
        self.raw_jobs = raw_jobs
        self.preferences = preferences   # Passed directly — avoids async lazy-load
        self.llm = LLMClient()

    async def execute(self) -> List[PlannedJob]:
        """Score and filter jobs using Gemini. Only jobs ≥ 0.7 proceed."""
        planned_jobs: List[PlannedJob] = []
        logger.info(f"Planning applications for {len(self.raw_jobs)} jobs...")

        for job in self.raw_jobs:
            try:
                plan = await self._analyze_job(job)
                score = float(plan.get("match_score", 0))
                if plan.get("should_apply") and score >= 0.7:
                    planned_jobs.append(
                        PlannedJob(
                            title=job.title,
                            company=job.company,
                            url=job.url,
                            description=job.description,
                            platform=job.platform,
                            match_score=score * 100,
                            reasoning=plan.get("reasoning", ""),
                            cover_note=plan.get("cover_note", ""),
                            key_skills_to_highlight=plan.get(
                                "key_skills_to_highlight", []
                            ),
                        )
                    )
                    logger.info(
                        f"Accepted: {job.title} @ {job.company} "
                        f"[score={score:.2f}]"
                    )
                else:
                    logger.debug(
                        f"Skipped: {job.title} "
                        f"[reason={plan.get('skip_reason', 'Low score')}]"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to analyse job {getattr(job, 'title', '?')}: {e}"
                )

        return planned_jobs

    async def _analyze_job(self, job: Any) -> Dict[str, Any]:
        """Prompt Gemini to analyse job compatibility against the full user profile."""
        # Pull profile data — prefer the explicit preferences object
        skills: List[str] = []
        experience_level: str = "Mid"
        job_titles: List[str] = []
        job_type: str = ""
        preferred_locations: List[str] = []

        if self.preferences:
            skills = list(getattr(self.preferences, "skills", []) or [])
            experience_level = (
                getattr(self.preferences, "experience_level", "Mid") or "Mid"
            )
            job_titles = list(getattr(self.preferences, "job_titles", []) or [])
            job_type = getattr(self.preferences, "job_type", "") or ""
            preferred_locations = list(
                getattr(self.preferences, "preferred_locations", []) or []
            )

        full_name = getattr(self.user, "full_name", "Candidate")
        bio = getattr(self.user, "bio", "")

        system_prompt = (
            "You are a professional career advisor AI specialising in "
            "technical recruitment. Evaluate job-candidate fit rigorously."
        )

        prompt = f"""
Analyse the following job description against this candidate's profile and
return a structured JSON object.

CANDIDATE PROFILE:
  Name              : {full_name}
  Bio               : {bio}
  Skills            : {skills}
  Experience Level  : {experience_level}
  Target Job Titles : {job_titles}
  Preferred Locations: {preferred_locations}
  Job Type          : {job_type}

JOB POSTING:
  Title       : {job.title}
  Company     : {job.company}
  Description : {job.description[:2000]}

Return ONLY valid JSON (no markdown fences) with this exact structure:
{{
  "match_score"              : <float 0.0–1.0>,
  "should_apply"             : <boolean>,
  "skip_reason"              : "<string or null>",
  "reasoning"                : "<2-3 sentences explaining the match or mismatch>",
  "cover_note"               : "<3-4 sentence personalised cover note for this specific role>",
  "key_skills_to_highlight"  : ["skill1", "skill2", "skill3"],
  "red_flags"                : []
}}
"""
        try:
            return await self.llm.complete_json(prompt, system_prompt)
        except Exception as e:
            logger.error(f"LLM API error during job analysis: {e}")
            return {"should_apply": False, "skip_reason": "LLM_ERROR"}
