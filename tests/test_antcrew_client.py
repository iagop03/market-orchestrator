import subprocess

import pytest

from orchestrator.integrations.antcrew_client import AntCrewClient


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


async def test_generate_project_builds_goal_and_specs_and_parses_json(monkeypatch):
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return FakeCompletedProcess(returncode=0, stdout='{"repo_url": "https://github.com/iagop03/thing"}')

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = AntCrewClient(antcrew_path="antcrew", model="claude")
    result = await client.generate_project(
        niche_title="COBOL to Python translator",
        niche_description="Banks need this",
        validation={"viability_score": 8.5, "market_size_estimate": "niche", "effort_estimate": "2 weeks"},
    )

    assert result["niche"] == "COBOL to Python translator"
    assert result["status"] == "generated"
    assert result["antcrew_result"] == {"repo_url": "https://github.com/iagop03/thing"}

    cmd = captured["cmd"]
    assert cmd[0] == "antcrew"
    assert cmd[1] == "quick"
    assert "COBOL to Python translator" in cmd[2]
    assert "8.5/10" in cmd[2]
    assert cmd[cmd.index("--model") + 1] == "claude"
    assert cmd[-1] == "--json"


async def test_generate_project_raises_on_nonzero_exit(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        return FakeCompletedProcess(returncode=1, stdout="", stderr="antcrew blew up")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = AntCrewClient()
    with pytest.raises(RuntimeError, match="antcrew blew up"):
        await client.generate_project(niche_title="x", niche_description="y", validation={})


async def test_generate_project_falls_back_to_raw_output_on_invalid_json(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        return FakeCompletedProcess(returncode=0, stdout="not json")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = AntCrewClient()
    result = await client.generate_project(niche_title="x", niche_description="y", validation={})

    assert result["antcrew_result"] == {"raw_output": "not json"}
