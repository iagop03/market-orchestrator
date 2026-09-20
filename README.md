# market-orchestrator

State machine that pulls candidate niches from `market-discovery`, scores their viability with rule-based validators, and — for anything that clears the bar — invokes `antcrew` to generate the shipped project.

```
discovered -> validating -> validated -> building -> shipped
                        \-> rejected
```

## Why validators live here, not in their own repo

Validators (`src/orchestrator/validators/`) have no lifecycle of their own — they're short scoring functions invoked only by this orchestrator's decision engine, never installed or run standalone. Giving them a third repo would add packaging/versioning overhead for something that's never a standalone artifact.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
python scripts/init_db.py
```

`antcrew` must be installed and on `PATH` (`pip install antcrew`) for the build stage to run.

## Run

```bash
market-orchestrator
```

Runs sync → validate → build once an hour:

1. **Sync** — pulls new opportunities from `market-discovery`'s `GET /opportunities/new`.
2. **Validate** — scores each pending opportunity with the matching validator in `validators/` (competitor density, effort estimate, viability score 0–10). Score ≥ 7 and effort ≤ 4 weeks → validated; otherwise rejected.
3. **Build** — for each validated opportunity, shells out to `antcrew quick` with the niche + validation context as the goal, and stores antcrew's result on the opportunity.

Set `SLACK_WEBHOOK_URL` in `.env` to get a notification at each validate/build outcome.

## Expose state over HTTP (optional)

```bash
pip install -e ".[api]"
uvicorn orchestrator.api.app:app --reload
```

- `GET /health` — liveness check.
- `GET /stats` — opportunity counts per state.
- `GET /opportunities?state=&limit=` — list opportunities, optionally filtered by state.
- `GET /opportunities/{id}` — full detail for one opportunity, including its validation and build result.

Read-only: this is for observability into the orchestrator's own state, not a control surface — it doesn't trigger cycles or mutate anything.

## Adding a validator

Add a module under `src/orchestrator/validators/`, subclass `BaseValidator`, and register it in `validators/__init__.py`'s `get_validator()`. See `generic_saas.py` for the default and `cobol_automation.py` for an example of tuning it per category.

## Tests

```bash
pytest
```
