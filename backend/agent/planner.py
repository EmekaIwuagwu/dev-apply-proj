"""
Scores each discovered job against the user's profile with Gemini.
Only jobs scoring >= 0.70 proceed to application.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, List

from agent.llm import LLMClient
from agent.search import DiscoveredJob

logger = logging.getLogger(__name__)

_THRESHOLD = 0.70


@dataclass
class PlannedJob:
    title: str
    company: str
    url: str
    description: str
    platform: str
    match_score: float       # 0-100
    reasoning: str
    cover_note: str
    key_skills: List[str] = field(default_factory=list)


async def plan_jobs(
    user: Any,
    raw_jobs: List[DiscoveredJob],
    preferences: Any,
) -> List[PlannedJob]:
    """Score every raw job; return only those that pass the threshold."""
    llm = LLMClient()
    planned: List[PlannedJob] = []

    for job in raw_jobs:
        try:
            result = await _score_job(llm, user, job, preferences)
            score = float(result.get("match_score", 0))
            if result.get("should_apply") and score >= _THRESHOLD:
                planned.append(PlannedJob(
                    title=job.title,
                    company=job.company,
                    url=job.url,
                    description=job.description,
                    platform=job.platform,
                    match_score=round(score * 100, 1),
                    reasoning=result.get("reasoning", ""),
                    cover_note=result.get("cover_note", ""),
                    key_skills=result.get("key_skills", []),
                ))
                logger.info(f"Accepted: {job.title} @ {job.company} [{score:.2f}]")
            else:
                logger.debug(
                    f"Skipped: {job.title} @ {job.company} "
                    f"[score={score:.2f} reason={result.get('skip_reason')}]"
                )
        except Exception as e:
            logger.error(f"Scoring error for {job.title}: {e}")

    return planned


async def _score_job(llm: LLMClient, user, job: DiscoveredJob, prefs) -> dict:
    skills = list(getattr(prefs, "skills", []) or [])
    exp = getattr(prefs, "experience_level", "Mid") or "Mid"
    titles = list(getattr(prefs, "job_titles", []) or [])
    job_type = getattr(prefs, "job_type", "") or ""
    locations = list(getattr(prefs, "preferred_locations", []) or [])
    excluded = list(getattr(prefs, "excluded_companies", []) or [])

    system = (
        "You are a precise career advisor AI. "
        "Evaluate job-candidate compatibility rigorously and honestly."
    )

    prompt = f"""
Evaluate this job against the candidate profile and return ONLY valid JSON.

CANDIDATE:
  Name               : {getattr(user, 'full_name', '')}
  Bio                : {getattr(user, 'bio', '')[:400]}
  Skills             : {skills}
  Experience Level   : {exp}
  Target Titles      : {titles}
  Job Type Preference: {job_type}
  Preferred Locations: {locations}
  Excluded Companies : {excluded}

JOB:
  Title      : {job.title}
  Company    : {job.company}
  Platform   : {job.platform}
  Description: {job.description[:2000]}

RULES:
- If the company is in excluded_companies, set should_apply=false.
- match_score is 0.0–1.0 (0.70+ = strong match).
- cover_note is 3–4 sentences, first person, specific to this role.

Return ONLY this JSON (no markdown):
{{
  "match_score"  : 0.85,
  "should_apply" : true,
  "skip_reason"  : null,
  "reasoning"    : "2-3 sentences explaining the match",
  "cover_note"   : "personalised cover note",
  "key_skills"   : ["skill1", "skill2"]
}}
"""
    return await llm.complete_json(prompt, system)
