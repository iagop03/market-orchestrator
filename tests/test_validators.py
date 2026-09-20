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
