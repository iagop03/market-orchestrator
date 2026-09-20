from .generic_saas import GenericSaaSValidator


class CobolAutomationValidator(GenericSaaSValidator):
    """Same heuristic as GenericSaaSValidator, tuned for legacy/COBOL niches: low competitor
    counts here reflect a genuinely underserved market, not low demand, so score gets a bump."""

    def _score(self, competitors_count: int, effort_weeks: int) -> float:
        return round(min(10.0, super()._score(competitors_count, effort_weeks) + 1.5), 1)
