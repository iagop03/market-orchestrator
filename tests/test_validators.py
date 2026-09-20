from orchestrator.validators import get_validator
from orchestrator.validators.cobol_automation import CobolAutomationValidator
from orchestrator.validators.data_science import DataScienceValidator
from orchestrator.validators.generic_saas import GenericSaaSValidator
from orchestrator.validators.mobile import MobileValidator
from orchestrator.validators.security import SecurityValidator


def test_get_validator_routes_cobol_keyword():
    assert isinstance(get_validator("COBOL modernization for banks"), CobolAutomationValidator)


def test_get_validator_defaults_to_generic():
    assert isinstance(get_validator("A tool for scheduling social posts"), GenericSaaSValidator)


def test_get_validator_routes_by_category():
    assert isinstance(get_validator("A niche title", category="security"), SecurityValidator)
    assert isinstance(get_validator("A niche title", category="data"), DataScienceValidator)
    assert isinstance(get_validator("A niche title", category="mobile"), MobileValidator)
    assert isinstance(get_validator("A niche title", category="frontend"), GenericSaaSValidator)


def test_get_validator_cobol_keyword_overrides_category():
    """A title-level legacy/COBOL signal is more specific than the discovery-assigned
    category and must win even if category was (mis)assigned to something else."""
    assert isinstance(
        get_validator("Legacy COBOL system audit", category="security"), CobolAutomationValidator
    )


def test_score_bounds():
    validator = GenericSaaSValidator()
    assert 0.0 <= validator._score(competitors_count=0, effort_weeks=1) <= 10.0
    assert 0.0 <= validator._score(competitors_count=500, effort_weeks=10) <= 10.0


def test_devops_and_security_categories_get_higher_effort_estimate():
    validator = GenericSaaSValidator()
    description = "a short description"
    assert validator._estimate_effort(description, category="other") == 1
    assert validator._estimate_effort(description, category="devops") == 2
    assert validator._estimate_effort(description, category="security") == 2


def test_count_competitors_retries_transient_github_failures(monkeypatch):
    monkeypatch.setattr("orchestrator.retry.time.sleep", lambda _seconds: None)

    class FakeResult:
        totalCount = 3

    calls = {"n": 0}

    def fake_search_repositories(query):
        calls["n"] += 1
        if calls["n"] < 2:
            raise ConnectionError("transient")
        return FakeResult()

    validator = GenericSaaSValidator()
    monkeypatch.setattr(validator.github, "search_repositories", fake_search_repositories)

    assert validator._count_competitors("some niche") == 3
    assert calls["n"] == 2


def test_count_competitors_falls_back_to_zero_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("orchestrator.retry.time.sleep", lambda _seconds: None)

    def always_fails(query):
        raise ConnectionError("permanent")

    validator = GenericSaaSValidator()
    monkeypatch.setattr(validator.github, "search_repositories", always_fails)

    assert validator._count_competitors("some niche") == 0


def test_security_validator_enforces_minimum_effort_floor():
    validator = SecurityValidator()
    # 1 word -> base 1 week, +1 for the shared security bump = 2, floored up to 3
    assert validator._estimate_effort("short", category="security") == 3
    # 100 words -> base 4 weeks, +1 for the shared security bump = 5, already above the floor
    assert validator._estimate_effort("word " * 100, category="security") == 5


def test_security_validator_penalizes_competitors_more_steeply_than_generic():
    security_score = SecurityValidator()._score(competitors_count=100, effort_weeks=1)
    generic_score = GenericSaaSValidator()._score(competitors_count=100, effort_weeks=1)
    assert security_score < generic_score


def test_data_science_validator_adds_extra_effort():
    validator = DataScienceValidator()
    assert validator._estimate_effort("short", category="data") == 1 + 2
    assert validator._estimate_effort("word " * 100, category="data") == 4 + 2


def test_data_science_validator_penalizes_competitors_less_steeply_than_generic():
    data_score = DataScienceValidator()._score(competitors_count=100, effort_weeks=1)
    generic_score = GenericSaaSValidator()._score(competitors_count=100, effort_weeks=1)
    assert data_score > generic_score


def test_mobile_validator_adds_extra_effort_and_enforces_floor():
    validator = MobileValidator()
    assert validator._estimate_effort("short", category="mobile") == 2  # 1 base + 1 extra, floor 2
    assert validator._estimate_effort("word " * 100, category="mobile") == 4 + 1
