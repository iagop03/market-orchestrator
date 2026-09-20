from abc import ABC, abstractmethod


class BaseValidator(ABC):
    """A validator scores one candidate niche and returns viability metadata.

    No independent lifecycle: instantiated and called only by the orchestrator's
    decision engine, one call per opportunity awaiting validation.
    """

    @abstractmethod
    def validate(self, niche_title: str, niche_description: str, category: str = "other") -> dict:
        ...
