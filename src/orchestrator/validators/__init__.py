from .base import BaseValidator
from .cobol_automation import CobolAutomationValidator
from .generic_saas import GenericSaaSValidator

_CACHE: dict[str, BaseValidator] = {}


def get_validator(niche_title: str) -> BaseValidator:
    title_lower = niche_title.lower()
    key = "cobol_automation" if ("cobol" in title_lower or "legacy" in title_lower) else "generic_saas"

    if key not in _CACHE:
        _CACHE[key] = CobolAutomationValidator() if key == "cobol_automation" else GenericSaaSValidator()
    return _CACHE[key]


__all__ = ["BaseValidator", "CobolAutomationValidator", "GenericSaaSValidator", "get_validator"]
