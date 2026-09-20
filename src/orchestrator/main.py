import asyncio
import logging

from orchestrator.config import Settings
from orchestrator.database import get_session, init_db
from orchestrator.decision_engine import DecisionEngine
from orchestrator.integrations.antcrew_client import AntCrewClient
from orchestrator.integrations.discovery_client import DiscoveryClient
from orchestrator.integrations.slack import SlackNotifier
from orchestrator.state_machine import Opportunity, OpportunityState
from orchestrator.validators import get_validator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

CYCLE_INTERVAL_SECONDS = 3600


class MarketDrivenOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.discovery_client = DiscoveryClient(settings.discovery_api_url)
        self.antcrew_client = AntCrewClient(settings.antcrew_path, settings.antcrew_model)
        self.slack = SlackNotifier(settings.slack_webhook_url) if settings.slack_webhook_url else None
        self.decision_engine = DecisionEngine()

    async def run(self) -> None:
        logger.info("Starting market-orchestrator")
        while True:
            try:
                await self.orchestration_cycle()
            except Exception:
                logger.exception("Orchestration cycle failed")
            await asyncio.sleep(CYCLE_INTERVAL_SECONDS)

    async def orchestration_cycle(self) -> None:
        session = get_session()
        try:
            await self._sync_from_discovery(session)
            await self._validate_pending(session)
            await self._build_viable(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def _sync_from_discovery(self, session) -> None:
        new_opps = await self.discovery_client.get_new_opportunities()
        logger.info("Got %d new opportunities from discovery", len(new_opps))

        for data in new_opps:
            existing = (
                session.query(Opportunity)
                .filter_by(niche_title=data["niche_title"], source=data["source"])
                .first()
            )
            if existing:
                continue
            session.add(Opportunity.from_discovery_api(data))

    async def _validate_pending(self, session) -> None:
        pending = session.query(Opportunity).filter_by(state=OpportunityState.DISCOVERED.value).all()
        logger.info("Validating %d pending opportunities", len(pending))

        for opp in pending:
            if not self.decision_engine.should_validate(opp):
                continue

            opp.state = OpportunityState.VALIDATING.value
            try:
                validator = get_validator(opp.niche_title)
                validation = await asyncio.to_thread(
                    validator.validate, opp.niche_title, opp.niche_description
                )

                opp.viability_score = validation.get("viability_score", 0)
                opp.market_size = validation.get("market_size_estimate")
                opp.effort = validation.get("effort_estimate")
                opp.validation_result = validation

                if self.decision_engine.should_build(opp):
                    opp.state = OpportunityState.VALIDATED.value
                    await self._notify(
                        f":white_check_mark: Validated: {opp.niche_title} "
                        f"(score {opp.viability_score}/10, {opp.effort})"
                    )
                else:
                    opp.state = OpportunityState.REJECTED.value
                    await self._notify(
                        f":x: Rejected: {opp.niche_title} (score {opp.viability_score}/10)"
                    )
            except Exception:
                logger.exception("Validation failed for %s", opp.niche_title)
                opp.state = OpportunityState.DISCOVERED.value

    async def _build_viable(self, session) -> None:
        viable = session.query(Opportunity).filter_by(state=OpportunityState.VALIDATED.value).all()
        logger.info("Building %d viable opportunities", len(viable))

        for opp in viable:
            opp.state = OpportunityState.BUILDING.value
            try:
                build_result = await self.antcrew_client.generate_project(
                    niche_title=opp.niche_title,
                    niche_description=opp.niche_description,
                    validation=opp.validation_result or {},
                )
                opp.build_result = build_result
                opp.state = OpportunityState.SHIPPED.value
                await self._notify(f":rocket: Shipped: {opp.niche_title}")
            except Exception:
                logger.exception("Build failed for %s", opp.niche_title)
                opp.state = OpportunityState.VALIDATED.value

    async def _notify(self, text: str) -> None:
        if self.slack:
            await self.slack.notify(text)


async def _main() -> None:
    settings = Settings()
    init_db(settings.database_url)
    await MarketDrivenOrchestrator(settings).run()


def cli() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    cli()
