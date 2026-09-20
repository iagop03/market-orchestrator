from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OpportunityState(str, Enum):
    DISCOVERED = "discovered"
    VALIDATING = "validating"
    VALIDATED = "validated"
    BUILDING = "building"
    SHIPPED = "shipped"
    REJECTED = "rejected"


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(100), default="")
    niche_title: Mapped[str] = mapped_column(String(255))
    niche_description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50), default="other")

    state: Mapped[str] = mapped_column(String(20), default=OpportunityState.DISCOVERED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    viability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_size: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effort: Mapped[str | None] = mapped_column(String(50), nullable=True)

    validation_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    build_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "niche_title": self.niche_title,
            "state": self.state,
            "viability_score": self.viability_score,
            "market_size": self.market_size,
            "effort": self.effort,
        }

    @staticmethod
    def from_discovery_api(api_response: dict) -> "Opportunity":
        return Opportunity(
            source_id=str(api_response.get("id", "")),
            niche_title=api_response["niche_title"],
            niche_description=api_response.get("niche_description", ""),
            source=api_response["source"],
            category=api_response.get("category", "other"),
        )
