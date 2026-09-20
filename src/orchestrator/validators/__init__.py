from .base import BaseValidator
from .cobol_automation import CobolAutomationValidator
from .data_science import DataScienceValidator
from .generic_saas import GenericSaaSValidator
from .mobile import MobileValidator
from .security import SecurityValidator

_VALIDATOR_CLASSES: dict[str, type[BaseValidator]] = {
    "cobol_automation": CobolAutomationValidator,
    "security": SecurityValidator,
    "data_science": DataScienceValidator,
    "mobile": MobileValidator,
    "generic_saas": GenericSaaSValidator,
}
_CACHE: dict[str, BaseValidator] = {}


def get_validator(niche_title: str, category: str = "other") -> BaseValidator:
    """Routes to a specialized validator.

    A title-level legacy/COBOL signal takes priority over category — it's a more
    specific match than the discovery-assigned category, which was itself derived from
    keyword matching and can miss. Otherwise routing follows category directly.
    """
    title_lower = niche_title.lower()
    if "cobol" in title_lower or "legacy" in title_lower:
        key = "cobol_automation"
    elif category == "security":
        key = "security"
    elif category == "data":
        key = "data_science"
    elif category == "mobile":
        key = "mobile"
    else:
        key = "generic_saas"

    if key not in _CACHE:
        _CACHE[key] = _VALIDATOR_CLASSES[key]()
    return _CACHE[key]


__all__ = [
    "BaseValidator",
    "CobolAutomationValidator",
    "DataScienceValidator",
    "GenericSaaSValidator",
    "MobileValidator",
    "SecurityValidator",
    "get_validator",
]
