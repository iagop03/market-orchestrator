from .generic_saas import GenericSaaSValidator


class SecurityValidator(GenericSaaSValidator):
    """Security tools face a higher trust barrier to adoption than typical SaaS —
    enterprises rarely switch security vendors, so an existing competitor is a bigger
    moat here than in a generic niche, and competitor density is weighted more heavily.
    Security work also carries a minimum rigor floor (threat modeling, audits) regardless
    of how small the described scope sounds."""

    MIN_EFFORT_WEEKS = 3

    def _estimate_effort(self, niche_description: str, category: str = "security") -> int:
        return max(super()._estimate_effort(niche_description, category), self.MIN_EFFORT_WEEKS)

    def _score(self, competitors_count: int, effort_weeks: int) -> float:
        competition_penalty = min(competitors_count / 10, 7)  # steeper than generic's /20, cap 5
        score = 10 - competition_penalty - effort_weeks
        return round(max(0.0, min(10.0, score)), 1)
