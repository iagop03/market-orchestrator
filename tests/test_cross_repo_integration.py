"""Real end-to-end tests across the two repos: a live market-discovery API server
(actual subprocess, actual HTTP over a real socket) and a real orchestrator DB.

No mocked httpx/subprocess here — only orchestrator's own antcrew_client is faked,
since invoking the real `antcrew quick` CLI is out of scope for a test run (it's an
external tool this repo deliberately doesn't install as a dependency). Everything
else — the claim/ack protocol over the network, both real SQLite databases, and the
GenericSaaSValidator's real (unauthenticated) GitHub competitor search — is real.

Opt-in: `pytest -m integration`. Skipped by default (see pyproject.toml's addopts)
since it's slower and depends on network/sibling-checkout state that a fast unit
test run shouldn't require.
"""
import os
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from orchestrator.config import Settings
from orchestrator.database import get_session, init_db
from orchestrator.integrations.discovery_client import DiscoveryClient
from orchestrator.main import MarketDrivenOrchestrator
from orchestrator.state_machine import Opportunity, OpportunityState

pytestmark = pytest.mark.integration

DISCOVERY_REPO = Path(__file__).resolve().parents[2] / "market-discovery"
DISCOVERY_VENV_PYTHON = DISCOVERY_REPO / ".venv" / "Scripts" / "python.exe"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _seed_opportunity(db_path: Path, niche_title: str, source: str, category: str = "other") -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO opportunities
                (niche_title, niche_description, source, category, status, exported,
                 claimed_at, confidence, created_at)
            VALUES (?, ?, ?, ?, 'discovered', 0, NULL, 0.8, ?)
            """,
            (niche_title, "a real description", source, category, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def _wait_for_server(base_url: str, proc: subprocess.Popen, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"discovery server exited early (code {proc.returncode}):\n{output}")
        try:
            httpx.get(f"{base_url}/opportunities", timeout=1.0)
            return
        except httpx.HTTPError:
            time.sleep(0.3)
    proc.kill()
    raise TimeoutError(f"discovery server at {base_url} did not start within {timeout}s")


@pytest.fixture
def discovery_server(tmp_path):
    if not DISCOVERY_VENV_PYTHON.exists():
        pytest.skip(
            "market-discovery not found as a sibling checkout with its own .venv "
            f"(expected {DISCOVERY_VENV_PYTHON}) — run `pip install -e \".[dev,api]\"` "
            "there first, or skip this opt-in integration test."
        )

    db_path = tmp_path / "discovery_integration.db"
    # Alembic (not create_all) is the schema authority for a real deploy — apply it
    # exactly the way scripts/init_db.py does, so this test exercises the real path.
    subprocess.run(
        [str(DISCOVERY_VENV_PYTHON), "scripts/init_db.py"],
        cwd=str(DISCOVERY_REPO),
        env={**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"},
        check=True,
        capture_output=True,
        text=True,
    )

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            str(DISCOVERY_VENV_PYTHON), "-m", "uvicorn",
            "market_discovery.api.app:app", "--host", "127.0.0.1", "--port", str(port),
        ],
        cwd=str(DISCOVERY_REPO),
        env={**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_server(base_url, proc)
        yield base_url, db_path
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


async def test_discovery_client_round_trips_against_a_real_server(discovery_server):
    base_url, db_path = discovery_server
    _seed_opportunity(db_path, niche_title="Real HTTP niche", source="reddit")

    client = DiscoveryClient(base_url)

    first_fetch = await client.get_new_opportunities()
    assert [o["niche_title"] for o in first_fetch] == ["Real HTTP niche"]

    # claimed but unacked: a second real HTTP fetch must not return it again
    assert await client.get_new_opportunities() == []

    await client.ack_opportunities([first_fetch[0]["id"]])

    # acked: still not returned, i.e. retired for good, confirmed over a real round trip
    assert await client.get_new_opportunities() == []


async def test_full_orchestration_cycle_against_a_real_discovery_server(discovery_server, tmp_path):
    base_url, discovery_db_path = discovery_server
    _seed_opportunity(discovery_db_path, niche_title="End to end niche", source="hackernews", category="devops")

    orchestrator_db_path = tmp_path / "orchestrator_integration.db"
    init_db(f"sqlite:///{orchestrator_db_path}")

    settings = Settings(discovery_api_url=base_url, database_url=f"sqlite:///{orchestrator_db_path}")
    orchestrator = MarketDrivenOrchestrator(settings)

    async def fake_generate_project(niche_title, niche_description, validation):
        return {
            "niche": niche_title,
            "status": "generated",
            "antcrew_result": {"repo_url": "https://example.test/repo"},
        }

    # Only fake: the real antcrew CLI is an external tool this repo doesn't install.
    orchestrator.antcrew_client.generate_project = fake_generate_project

    await orchestrator.orchestration_cycle()

    session = get_session()
    try:
        opp = session.query(Opportunity).filter_by(niche_title="End to end niche").one()
        # GenericSaaSValidator hits the real (unauthenticated) GitHub search API here,
        # so the exact score is non-deterministic — assert the wiring reached a real
        # terminal decision, not a specific outcome.
        assert opp.state in (OpportunityState.SHIPPED.value, OpportunityState.REJECTED.value)
        assert opp.source == "hackernews"
        assert opp.category == "devops"
        if opp.state == OpportunityState.SHIPPED.value:
            assert opp.build_result["antcrew_result"]["repo_url"] == "https://example.test/repo"
    finally:
        session.close()

    # The synced opportunity must have been acked too, over the real HTTP round trip.
    client = DiscoveryClient(base_url)
    assert await client.get_new_opportunities() == []
