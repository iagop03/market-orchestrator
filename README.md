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
python scripts/init_db.py  # applies Alembic migrations
```

`antcrew` must be installed and on `PATH` (`pip install antcrew`) for the build stage to run.

## Database migrations

Schema changes go through Alembic (`alembic/versions/`), not `Base.metadata.create_all()` directly —
`create_all()` only creates missing tables, so an existing deployed DB would silently miss any new
column added to a model. After changing a model:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

`scripts/init_db.py` (`alembic upgrade head`) is the one command to run on a fresh or an existing DB.

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

## Docker (full local pipeline)

`docker-compose.yml` in this repo runs the whole pipeline — both services, each with its own
Postgres — for local smoke testing. It assumes `market-discovery` is checked out as a sibling
directory:

```
projects/
├── market-discovery/
└── market-orchestrator/   <- docker-compose.yml lives here
```

```bash
docker compose up --build
```

Reddit/GitHub/Slack credentials are optional — everything degrades gracefully without them (see
each source/validator's own resilience handling). `antcrew` itself is not installed in the image
(it's a subprocess CLI dependency, not a Python import); without it, discovery/validation still run
normally and only the final build step fails-and-retries next cycle. See the comment block at the
top of `docker-compose.yml` for details, including how to add `antcrew` to the image if you want
builds to actually complete inside compose.

## Adding a validator

Add a module under `src/orchestrator/validators/`, subclass `BaseValidator`, and register it in `validators/__init__.py`'s `get_validator()`. See `generic_saas.py` for the default and `cobol_automation.py` for an example of tuning it per category.

## Tests

```bash
pytest
```
