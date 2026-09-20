import pytest
from fastapi import HTTPException

from orchestrator.api.app import get_opportunity, list_opportunities, stats
from orchestrator.state_machine import Opportunity, OpportunityState


def test_stats_counts_opportunities_per_state(db_session):
    db_session.add(Opportunity(niche_title="A", source="reddit", state=OpportunityState.DISCOVERED.value))
    db_session.add(Opportunity(niche_title="B", source="reddit", state=OpportunityState.DISCOVERED.value))
    db_session.add(Opportunity(niche_title="C", source="reddit", state=OpportunityState.SHIPPED.value))
    db_session.commit()

    result = stats()

    assert result[OpportunityState.DISCOVERED.value] == 2
    assert result[OpportunityState.SHIPPED.value] == 1
    assert result[OpportunityState.REJECTED.value] == 0


def test_list_opportunities_filters_by_state(db_session):
    db_session.add(Opportunity(niche_title="Pending", source="reddit", state=OpportunityState.DISCOVERED.value))
    db_session.add(Opportunity(niche_title="Done", source="reddit", state=OpportunityState.SHIPPED.value))
    db_session.commit()

    shipped = list_opportunities(state=OpportunityState.SHIPPED.value, limit=50)

    assert [o["niche_title"] for o in shipped] == ["Done"]


def test_list_opportunities_rejects_unknown_state(db_session):
    with pytest.raises(HTTPException) as exc_info:
        list_opportunities(state="not-a-real-state", limit=50)
    assert exc_info.value.status_code == 422


def test_get_opportunity_returns_detail_with_validation_and_build_result(db_session):
    opp = Opportunity(
        niche_title="Detailed niche",
        source="reddit",
        state=OpportunityState.SHIPPED.value,
        validation_result={"viability_score": 8.0},
        build_result={"antcrew_result": {"repo_url": "https://x"}},
    )
    db_session.add(opp)
    db_session.commit()

    result = get_opportunity(opp.id)

    assert result["niche_title"] == "Detailed niche"
    assert result["validation_result"] == {"viability_score": 8.0}
    assert result["build_result"]["antcrew_result"]["repo_url"] == "https://x"


def test_get_opportunity_404s_for_missing_id(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_opportunity(999999)
    assert exc_info.value.status_code == 404
