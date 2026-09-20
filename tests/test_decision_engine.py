from orchestrator.decision_engine import DecisionEngine
from orchestrator.state_machine import Opportunity, OpportunityState


def make_opportunity(**kwargs):
    defaults = dict(niche_title="test", source="reddit")
    defaults.update(kwargs)
    return Opportunity(**defaults)


def test_should_build_true_for_high_score_low_effort():
    engine = DecisionEngine()
    opp = make_opportunity(viability_score=8.5, effort="2 weeks")
    assert engine.should_build(opp) is True


def test_should_build_false_for_low_score():
    engine = DecisionEngine()
    opp = make_opportunity(viability_score=5.0, effort="1 week")
    assert engine.should_build(opp) is False


def test_should_build_false_for_high_effort():
    engine = DecisionEngine()
    opp = make_opportunity(viability_score=9.0, effort="6 weeks")
    assert engine.should_build(opp) is False


def test_should_validate_skips_terminal_states():
    engine = DecisionEngine()
    opp = make_opportunity(state=OpportunityState.SHIPPED.value)
    assert engine.should_validate(opp) is False


def test_should_build_false_for_unparseable_effort():
    """Fails closed: an effort estimate we can't parse must not silently bypass the cap."""
    engine = DecisionEngine()
    opp = make_opportunity(viability_score=9.0, effort="N/A")
    assert engine.should_build(opp) is False
