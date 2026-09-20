from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from orchestrator.config import Settings
from orchestrator.database import get_session, init_db
from orchestrator.logging_config import configure_logging
from orchestrator.state_machine import Opportunity, OpportunityState

VALID_STATES = {s.value for s in OpportunityState}


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db(Settings().database_url)
    yield


app = FastAPI(title="market-orchestrator", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    """Opportunity counts per state — the cheapest useful observability signal."""
    session = get_session()
    try:
        return {
            state.value: session.query(Opportunity).filter_by(state=state.value).count()
            for state in OpportunityState
        }
    finally:
        session.close()


@app.get("/opportunities")
def list_opportunities(state: str | None = None, limit: int = 50):
    if state is not None and state not in VALID_STATES:
        raise HTTPException(status_code=422, detail=f"Unknown state {state!r}. Valid: {sorted(VALID_STATES)}")

    session = get_session()
    try:
        query = session.query(Opportunity)
        if state:
            query = query.filter_by(state=state)
        opportunities = query.order_by(Opportunity.created_at.desc()).limit(limit).all()
        return [opp.to_dict() for opp in opportunities]
    finally:
        session.close()


@app.get("/opportunities/{opportunity_id}")
def get_opportunity(opportunity_id: int):
    session = get_session()
    try:
        opp = session.get(Opportunity, opportunity_id)
        if opp is None:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        return opp.to_detail_dict()
    finally:
        session.close()
