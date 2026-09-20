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

Runs the unit/wiring suite (mocked network, in-memory DB). Real cross-repo integration
tests are opt-in and excluded by default:

```bash
pytest -m integration
```

`test_cross_repo_integration.py` spins up a real market-discovery API server (an actual
`uvicorn` subprocess, real HTTP over a real socket, real SQLite migrated via Alembic) and
runs the full sync → validate → build cycle against it — only `antcrew_client` is faked,
since the real `antcrew` CLI is an external tool this repo doesn't install. It needs
market-discovery checked out as a sibling directory with its own `.venv` set up
(`pip install -e ".[dev,api]"` there); otherwise it skips itself with a clear message.

## Deploy to Railway

`railway.json` points Railway at `docker/Dockerfile` and runs migrations before the
orchestrator loop on every deploy (`python scripts/init_db.py && market-orchestrator`).

1. Add a Postgres database in the Railway project — it auto-injects `DATABASE_URL`
   (make sure `psycopg2-binary` is available: the Dockerfile installs the `postgres` extra).
2. Set `DISCOVERY_API_URL` (pointing at your deployed market-discovery service),
   `GITHUB_TOKEN`, `SLACK_WEBHOOK_URL`, `ANTCREW_MODEL` as needed (see `.env.example`).
3. **`antcrew` must be added to the image for the build step to do anything in production** —
   it's deliberately not installed by default (see "Why validators live here" above for the
   subprocess-CLI-not-a-dependency reasoning). Add `RUN pip install antcrew` to
   `docker/Dockerfile` before deploying if you want builds to actually run.
4. Deploy from this GitHub repo — Railway picks up `railway.json` automatically.
5. To also expose the read-only API, add a second Railway service from the same repo and
   override its start command to
   `python scripts/init_db.py && uvicorn orchestrator.api.app:app --host 0.0.0.0 --port $PORT`.
