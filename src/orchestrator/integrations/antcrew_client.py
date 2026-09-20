import asyncio
import json
import logging
import subprocess

logger = logging.getLogger(__name__)


class AntCrewClient:
    """Generates a shipped project for a validated niche via antcrew's `quick` pipeline.

    Uses `antcrew quick` (role/goal specs as plain strings — see antcrew's docs) rather
    than the full EngineLoop API, since that needs no platform account or API key: the
    right fit for a fully local build step.
    """

    def __init__(self, antcrew_path: str = "antcrew", model: str = "claude"):
        self.antcrew_path = antcrew_path
        self.model = model

    async def generate_project(self, niche_title: str, niche_description: str, validation: dict) -> dict:
        goal = (
            f"Build a production-ready project for: {niche_title}. {niche_description} "
            f"Market validation: viability {validation.get('viability_score')}/10, "
            f"market size {validation.get('market_size_estimate')}, "
            f"estimated effort {validation.get('effort_estimate')}."
        )
        specs = [
            "Architect: Design the project structure and pick the tech stack for the goal",
            "Developer: Implement the core functionality end to end, including a README",
            "QA: Write tests covering the core functionality and report any gaps",
        ]

        result = await asyncio.to_thread(self._run_antcrew, goal, specs)
        return {"niche": niche_title, "status": "generated", "antcrew_result": result}

    def _run_antcrew(self, goal: str, specs: list[str]) -> dict:
        proc = subprocess.run(
            [self.antcrew_path, "quick", goal, *specs, "--model", self.model, "--json"],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"antcrew quick failed: {proc.stderr.strip()}")

        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            logger.warning("antcrew did not return valid JSON; keeping raw stdout")
            return {"raw_output": proc.stdout}
