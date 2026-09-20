FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
COPY scripts/ scripts/
COPY alembic.ini .
COPY alembic/ alembic/

RUN pip install --no-cache-dir ".[api,postgres]"

CMD ["market-orchestrator"]
