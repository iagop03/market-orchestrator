from orchestrator.validators import get_validator
from orchestrator.validators.cobol_automation import CobolAutomationValidator
from orchestrator.validators.generic_saas import GenericSaaSValidator


def test_get_validator_routes_cobol_keyword():
    assert isinstance(get_validator("COBOL modernization for banks"), CobolAutomationValidator)


def test_get_validator_defaults_to_generic():
    assert isinstance(get_validator("A tool for scheduling social posts"), GenericSaaSValidator)


def test_score_bounds():
    validator = GenericSaaSValidator()
    assert 0.0 <= validator._score(competitors_count=0, effort_weeks=1) <= 10.0
    assert 0.0 <= validator._score(competitors_count=500, effort_weeks=10) <= 10.0
