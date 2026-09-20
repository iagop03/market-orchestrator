import logging

from orchestrator.state_machine import Opportunity, OpportunityState

logger = logging.getLogger(__name__)

VIABILITY_THRESHOLD = 7.0
MAX_EFFORT_WEEKS = 4


class DecisionEngine:
    """Turns validator output into a build/reject decision."""

    def should_validate(self, opp: Opportunity) -> bool:
        return opp.state not in {
            OpportunityState.VALIDATED.value,
            OpportunityState.REJECTED.value,
            OpportunityState.BUILDING.value,
            OpportunityState.SHIPPED.value,
        }

    def should_build(self, opp: Opportunity) -> bool:
        if opp.viability_score is None or opp.viability_score < VIABILITY_THRESHOLD:
            return False

        weeks = self._parse_weeks(opp.effort)
        if weeks is not None and weeks > MAX_EFFORT_WEEKS:
            logger.info("Effort %s weeks exceeds cap of %s", weeks, MAX_EFFORT_WEEKS)
            return False

        return True

    def _parse_weeks(self, effort: str | None) -> int | None:
        if not effort or "week" not in effort.lower():
            return None
        try:
            return int(effort.split()[0])
        except (ValueError, IndexError):
            return None
