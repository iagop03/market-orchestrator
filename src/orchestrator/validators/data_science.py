from .generic_saas import GenericSaaSValidator


class DataScienceValidator(GenericSaaSValidator):
    """Data/ML tooling ecosystems tend to have many coexisting specialized tools rather
    than a generic SaaS's winner-take-all dynamics, so competitor density penalizes the
    score less. Data pipelines and model training/evaluation add real scope beyond what
    the description implies, though, so effort gets a bigger bump than the shared
    devops/security baseline."""

    EXTRA_EFFORT_WEEKS = 2

    def _estimate_effort(self, niche_description: str, category: str = "data") -> int:
        return super()._estimate_effort(niche_description, category) + self.EXTRA_EFFORT_WEEKS

    def _score(self, competitors_count: int, effort_weeks: int) -> float:
        competition_penalty = min(competitors_count / 40, 3)  # gentler than generic's /20, cap 5
        score = 10 - competition_penalty - effort_weeks
        return round(max(0.0, min(10.0, score)), 1)
