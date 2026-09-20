from .generic_saas import GenericSaaSValidator


class MobileValidator(GenericSaaSValidator):
    """Mobile ships slower than web SaaS: cross-platform (or dual iOS+Android) work plus
    app store review adds real time before a first release is even possible, regardless
    of how small the description's raw scope sounds."""

    EXTRA_EFFORT_WEEKS = 1
    MIN_EFFORT_WEEKS = 2

    def _estimate_effort(self, niche_description: str, category: str = "mobile") -> int:
        base = super()._estimate_effort(niche_description, category) + self.EXTRA_EFFORT_WEEKS
        return max(base, self.MIN_EFFORT_WEEKS)
