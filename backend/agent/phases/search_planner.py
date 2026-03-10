import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from agent.llm.client import LLMClient

logger = logging.getLogger(__name__)

@dataclass
class SearchStrategy:
    query: str
    target_platforms: List[str]  # e.g., ["DDG", "Google", "LinkedIn"]
    niche: str                  # e.g., "Startups", "Fintech", "Enterprise"
    reasoning: str              # Internal use to track why this query exists

class SearchPlanner:
    def __init__(self, user: Any, preferences: Any):
        self.user = user
        self.preferences = preferences
        self.llm = LLMClient()

    async def generate_strategies(self) -> List[SearchStrategy]:
        """
        Analyzes user profile and generates a set of 3-5 high-impact search strategies.
        """
        logger.info(f"Planning search strategy for user {self.user.id}...")
        
        system_prompt = "You are a senior job search strategist and expert in technical search optimization (Boolean Search)."
        
        prompt = f"""
        Analyze the following candidate's profile and preferences to generate an optimized set of job search queries.
        
        CANDIDATE PROFILE:
        Name: {self.user.full_name}
        Bio: {self.user.bio}
        Skills: {self.preferences.skills}
        Preferred Titles: {self.preferences.job_titles}
        Experience: {self.preferences.experience_level}
        
        GOAL:
        Create a set of 4-5 diverse search strategies that:
        1. Mix broad job titles with specific tech stack combinations (e.g., Python + AWS).
        2. Identify "Niches" based on the candidate's background (e.g., Blockchain if bio suggests it, or Fintech).
        3. Optimize for finding DIRECT job boards (Lever, Greenhouse, Ashby).
        
        Rules:
        - The queries will be used with site: operators like "site:lever.co OR site:ashbyhq.com".
        - Do NOT include the site: operators in the "query" field, just the keywords.
        - The "query" should be a well-formed Boolean string if helpful.
        
        Return ONLY valid JSON:
        {{
            "strategies": [
                {{
                    "query": "Fullstack Engineer Python React",
                    "target_platforms": ["DDG", "Google"],
                    "niche": "General Fullstack",
                    "reasoning": "Standard broad search for main titles"
                }},
                ...
            ]
        }}
        """
        
        try:
            result = await self.llm.complete_json(prompt, system_prompt)
            strategies = []
            for s in result.get("strategies", []):
                strategies.append(SearchStrategy(
                    query=s.get("query", ""),
                    target_platforms=s.get("target_platforms", []),
                    niche=s.get("niche", "General"),
                    reasoning=s.get("reasoning", "")
                ))
            return strategies
        except Exception as e:
            logger.error(f"Failed to generate search strategies via LLM: {e}")
            # Fallback to naive strategy if LLM fails
            return [SearchStrategy(
                query=f"{self.preferences.job_titles[0]} {' '.join(self.preferences.skills[:2])}",
                target_platforms=["DDG", "Google"],
                niche="Fallback",
                reasoning="LLM failure fallback"
            )]
