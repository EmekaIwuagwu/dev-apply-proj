import logging
from typing import List, Any, Optional
from dataclasses import dataclass
from agent.llm.client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class SearchStrategy:
    query: str
    target_platforms: List[str]  # e.g., ["DDG", "Google"]
    niche: str                   # e.g., "Backend Engineer – Fintech"
    reasoning: str               # Why this strategy exists


class SearchPlanner:
    def __init__(self, user: Any, preferences: Any):
        self.user = user
        self.preferences = preferences
        self.llm = LLMClient()

    async def generate_strategies(self) -> List[SearchStrategy]:
        """
        Builds job search strategies directly anchored to the user's saved
        job_titles and skills from the database.  Each job title becomes at
        least one search query combined with the user's skills.  Gemini then
        adds 1-2 creative niche variants on top.
        """
        job_titles: List[str] = list(getattr(self.preferences, 'job_titles', []) or [])
        skills: List[str] = list(getattr(self.preferences, 'skills', []) or [])
        experience_level: str = getattr(self.preferences, 'experience_level', '') or ''

        if not job_titles:
            logger.warning(
                f"User {self.user.id} has no job titles configured — "
                "skipping strategy generation."
            )
            return []

        logger.info(
            f"Building strategies for user {self.user.id} | "
            f"Titles: {job_titles} | Skills: {skills[:6]} | "
            f"Experience: {experience_level}"
        )

        # ---------------------------------------------------------------
        # BASE STRATEGIES — built directly from DB values (no LLM risk)
        # ---------------------------------------------------------------
        base_strategies: List[SearchStrategy] = []
        top_skills = skills[:5]

        for title in job_titles[:4]:          # cap at 4 titles
            # Strategy A: title + first 3 skills
            primary_skill_str = " ".join(top_skills[:3])
            query_a = f'"{title}" {primary_skill_str}'.strip()
            base_strategies.append(SearchStrategy(
                query=query_a,
                target_platforms=["DDG"],
                niche=title,
                reasoning=f"Primary anchor search for '{title}' using core skills"
            ))

            # Strategy B: title + remaining skills (for diversity)
            if len(top_skills) > 3:
                alt_skills = " ".join(top_skills[3:])
                query_b = f'"{title}" {alt_skills}'.strip()
                base_strategies.append(SearchStrategy(
                    query=query_b,
                    target_platforms=["DDG", "Google"],
                    niche=f"{title} – alt skills",
                    reasoning=f"Alt-skill variation for '{title}'"
                ))

        # ---------------------------------------------------------------
        # LLM ENRICHMENT — 1-2 creative niche strategies on top
        # ---------------------------------------------------------------
        try:
            niche_strategies = await self._llm_niche_strategies(
                job_titles, skills, experience_level
            )
            base_strategies.extend(niche_strategies)
        except Exception as e:
            logger.warning(
                f"LLM niche strategy enrichment failed (using base strategies only): {e}"
            )

        # De-duplicate by normalised query text
        seen: set = set()
        unique: List[SearchStrategy] = []
        for s in base_strategies:
            key = s.query.lower().strip()
            if key and key not in seen:
                unique.append(s)
                seen.add(key)

        logger.info(f"Final strategy count for user {self.user.id}: {len(unique)}")
        return unique[:6]   # Hard cap — prevents excessively long runs

    # ------------------------------------------------------------------

    async def _llm_niche_strategies(
        self,
        job_titles: List[str],
        skills: List[str],
        experience_level: str
    ) -> List[SearchStrategy]:
        """Ask Gemini to generate 1-2 creative niche search queries."""

        system_prompt = (
            "You are a senior job search strategist specialising in "
            "Boolean search optimisation for software engineers."
        )

        prompt = f"""
A candidate is searching for jobs with these parameters:
- Target Job Titles: {job_titles}
- Skills: {skills}
- Experience Level: {experience_level}

Generate exactly 2 NICHE search strategies that go BEYOND a plain title + skills query.
Think about:
  • Industry verticals relevant to their skills (e.g. Fintech, HealthTech, SaaS, Web3)
  • Alternative job titles companies use for the same role
  • Specific tech-stack combinations that signal the right type of company

These queries will be appended with:
  (site:lever.co OR site:ashbyhq.com OR site:boards.greenhouse.io OR site:workable.com)
so do NOT include site: operators in the "query" field — only the search keywords.

Return ONLY valid JSON, no markdown fences:
{{
    "strategies": [
        {{
            "query": "Backend Engineer Python Fintech remote",
            "target_platforms": ["DDG"],
            "niche": "Fintech Backend",
            "reasoning": "Targets fintech startups hiring Python backend engineers"
        }}
    ]
}}
"""
        result = await self.llm.complete_json(prompt, system_prompt)
        strategies: List[SearchStrategy] = []
        for s in result.get("strategies", [])[:2]:
            q = (s.get("query") or "").strip()
            if q:
                strategies.append(SearchStrategy(
                    query=q,
                    target_platforms=s.get("target_platforms", ["DDG"]),
                    niche=s.get("niche", "Niche"),
                    reasoning=s.get("reasoning", "LLM-generated niche strategy")
                ))
        return strategies
