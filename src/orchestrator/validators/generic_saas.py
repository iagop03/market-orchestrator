import logging
import os

from github import Github

from .base import BaseValidator

logger = logging.getLogger(__name__)


class GenericSaaSValidator(BaseValidator):
    """Rule-based viability check: GitHub competitor density + a scope heuristic on effort."""

    def __init__(self, github_token: str | None = None):
        token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.github = Github(token) if token else Github()

    def validate(self, niche_title: str, niche_description: str) -> dict:
        competitors_count = self._count_competitors(niche_title)
        effort_weeks = self._estimate_effort(niche_description)
        return {
            "viability_score": self._score(competitors_count, effort_weeks),
            "market_size_estimate": self._estimate_market_size(competitors_count),
            "effort_estimate": f"{effort_weeks} weeks",
            "competitors_count": competitors_count,
        }

    def _count_competitors(self, niche_title: str) -> int:
        try:
            query = " ".join(niche_title.split()[:6])
            result = self.github.search_repositories(query=query)
            return min(result.totalCount, 999)
        except Exception:
            logger.warning("GitHub search failed for %r", niche_title, exc_info=True)
            return 0

    def _estimate_effort(self, niche_description: str) -> int:
        words = len(niche_description.split())
        if words < 20:
            return 1
        if words < 60:
            return 2
        return 4

    def _estimate_market_size(self, competitors_count: int) -> str:
        if competitors_count == 0:
            return "unknown - unvalidated demand"
        if competitors_count < 5:
            return "niche - low competition"
        if competitors_count < 50:
            return "medium - established category"
        return "large - crowded category"

    def _score(self, competitors_count: int, effort_weeks: int) -> float:
        competition_penalty = min(competitors_count / 20, 5)
        score = 10 - competition_penalty - effort_weeks
        return round(max(0.0, min(10.0, score)), 1)
