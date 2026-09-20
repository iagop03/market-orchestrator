import pytest

from orchestrator.config import Settings
from orchestrator.main import MarketDrivenOrchestrator
from orchestrator.state_machine import Opportunity, OpportunityState


@pytest.fixture
def orchestrator():
    return MarketDrivenOrchestrator(Settings())


class FakeValidator:
    def __init__(self, result):
        self.result = result

    def validate(self, niche_title, niche_description, category="other"):
        return self.result


async def test_sync_from_discovery_dedupes_within_same_batch(orchestrator, db_session, monkeypatch):
    async def fake_get_new_opportunities():
        return [
            {"niche_title": "COBOL to Python", "source": "github", "niche_description": "a"},
            {"niche_title": "COBOL to Python", "source": "github", "niche_description": "a again"},
        ]

    monkeypatch.setattr(orchestrator.discovery_client, "get_new_opportunities", fake_get_new_opportunities)

    await orchestrator._sync_from_discovery(db_session)
    db_session.commit()

    stored = db_session.query(Opportunity).filter_by(niche_title="COBOL to Python", source="github").all()
    assert len(stored) == 1


async def test_sync_from_discovery_returns_ids_for_acking(orchestrator, db_session, monkeypatch):
    async def fake_get_new_opportunities():
        return [{"id": 101, "niche_title": "A niche", "source": "reddit", "niche_description": "x"}]

    monkeypatch.setattr(orchestrator.discovery_client, "get_new_opportunities", fake_get_new_opportunities)

    synced_ids = await orchestrator._sync_from_discovery(db_session)
    db_session.commit()

    assert synced_ids == [101]


async def test_sync_from_discovery_returns_ids_even_for_duplicates(orchestrator, db_session, monkeypatch):
    """A niche already stored still needs acking — the orchestrator handled it, just via dedup."""
    db_session.add(Opportunity(niche_title="Already known", source="reddit"))
    db_session.commit()

    async def fake_get_new_opportunities():
        return [{"id": 55, "niche_title": "Already known", "source": "reddit", "niche_description": "x"}]

    monkeypatch.setattr(orchestrator.discovery_client, "get_new_opportunities", fake_get_new_opportunities)

    synced_ids = await orchestrator._sync_from_discovery(db_session)

    assert synced_ids == [55]


async def test_orchestration_cycle_acks_synced_opportunities_after_commit(orchestrator, db_session, monkeypatch):
    async def fake_get_new_opportunities():
        return [{"id": 7, "niche_title": "Ackable niche", "source": "reddit", "niche_description": "x"}]

    monkeypatch.setattr(orchestrator.discovery_client, "get_new_opportunities", fake_get_new_opportunities)

    acked = {}

    async def fake_ack(ids):
        acked["ids"] = ids

    monkeypatch.setattr(orchestrator.discovery_client, "ack_opportunities", fake_ack)

    await orchestrator.orchestration_cycle()

    assert acked["ids"] == [7]


async def test_sync_from_discovery_dedupes_against_existing_rows(orchestrator, db_session, monkeypatch):
    async def first_batch():
        return [{"niche_title": "A niche", "source": "reddit", "niche_description": "x"}]

    monkeypatch.setattr(orchestrator.discovery_client, "get_new_opportunities", first_batch)
    await orchestrator._sync_from_discovery(db_session)
    db_session.commit()

    async def second_batch():
        return [{"niche_title": "A niche", "source": "reddit", "niche_description": "x"}]

    monkeypatch.setattr(orchestrator.discovery_client, "get_new_opportunities", second_batch)
    await orchestrator._sync_from_discovery(db_session)
    db_session.commit()

    assert db_session.query(Opportunity).count() == 1


async def test_validate_pending_moves_high_score_low_effort_to_validated(orchestrator, db_session, monkeypatch):
    opp = Opportunity(niche_title="A niche", source="reddit", state=OpportunityState.DISCOVERED.value)
    db_session.add(opp)
    db_session.commit()

    monkeypatch.setattr(
        "orchestrator.main.get_validator",
        lambda niche_title, category: FakeValidator(
            {"viability_score": 8.5, "market_size_estimate": "niche", "effort_estimate": "2 weeks"}
        ),
    )

    await orchestrator._validate_pending(db_session)
    db_session.commit()

    refreshed = db_session.query(Opportunity).filter_by(niche_title="A niche").one()
    assert refreshed.state == OpportunityState.VALIDATED.value
    assert refreshed.viability_score == 8.5


async def test_validate_pending_rejects_low_score(orchestrator, db_session, monkeypatch):
    opp = Opportunity(niche_title="Another niche", source="reddit", state=OpportunityState.DISCOVERED.value)
    db_session.add(opp)
    db_session.commit()

    monkeypatch.setattr(
        "orchestrator.main.get_validator",
        lambda niche_title, category: FakeValidator(
            {"viability_score": 2.0, "market_size_estimate": "large", "effort_estimate": "1 weeks"}
        ),
    )

    await orchestrator._validate_pending(db_session)
    db_session.commit()

    refreshed = db_session.query(Opportunity).filter_by(niche_title="Another niche").one()
    assert refreshed.state == OpportunityState.REJECTED.value


async def test_validate_pending_reverts_to_discovered_on_validator_error(orchestrator, db_session, monkeypatch):
    opp = Opportunity(niche_title="Flaky niche", source="reddit", state=OpportunityState.DISCOVERED.value)
    db_session.add(opp)
    db_session.commit()

    class BoomValidator:
        def validate(self, *args, **kwargs):
            raise RuntimeError("GitHub is down")

    monkeypatch.setattr("orchestrator.main.get_validator", lambda niche_title, category: BoomValidator())

    await orchestrator._validate_pending(db_session)
    db_session.commit()

    refreshed = db_session.query(Opportunity).filter_by(niche_title="Flaky niche").one()
    assert refreshed.state == OpportunityState.DISCOVERED.value


async def test_build_viable_ships_on_success(orchestrator, db_session, monkeypatch):
    opp = Opportunity(
        niche_title="Buildable niche",
        source="reddit",
        state=OpportunityState.VALIDATED.value,
        validation_result={"viability_score": 8.0},
    )
    db_session.add(opp)
    db_session.commit()

    async def fake_generate_project(niche_title, niche_description, validation):
        return {"niche": niche_title, "status": "generated", "antcrew_result": {"repo_url": "https://x"}}

    monkeypatch.setattr(orchestrator.antcrew_client, "generate_project", fake_generate_project)

    await orchestrator._build_viable(db_session)
    db_session.commit()

    refreshed = db_session.query(Opportunity).filter_by(niche_title="Buildable niche").one()
    assert refreshed.state == OpportunityState.SHIPPED.value
    assert refreshed.build_result["antcrew_result"]["repo_url"] == "https://x"


async def test_build_viable_reverts_to_validated_on_failure(orchestrator, db_session, monkeypatch):
    opp = Opportunity(
        niche_title="Unbuildable niche",
        source="reddit",
        state=OpportunityState.VALIDATED.value,
        validation_result={"viability_score": 8.0},
    )
    db_session.add(opp)
    db_session.commit()

    async def failing_generate_project(niche_title, niche_description, validation):
        raise RuntimeError("antcrew quick failed")

    monkeypatch.setattr(orchestrator.antcrew_client, "generate_project", failing_generate_project)

    await orchestrator._build_viable(db_session)
    db_session.commit()

    refreshed = db_session.query(Opportunity).filter_by(niche_title="Unbuildable niche").one()
    assert refreshed.state == OpportunityState.VALIDATED.value
