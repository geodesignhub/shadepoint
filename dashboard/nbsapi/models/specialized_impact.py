from __future__ import annotations

from typing import Any, TYPE_CHECKING
from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base

if TYPE_CHECKING:
    from .impact import Impact


class SpecializedImpact(Base):
    """
    Specialized impact metrics model that stores structured JSON data
    for different impact categories (climate, water quality, cost)
    """

    __tablename__ = "specialized_impact"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key to the Impact table
    impact_id: Mapped[int] = mapped_column(
        ForeignKey("impact.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    impact: Mapped[Impact] = relationship(
        back_populates="specialized", single_parent=True
    )

    # JSON columns for each specialized impact type
    climate_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Climate-related impact metrics (temp_reduction, cool_spot, etc.)",
    )

    water_quality_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Water quality impact metrics (capture_unit, filtering_unit, etc.)",
    )

    cost_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Cost-related metrics (construction_cost, maintenance_cost, etc.)",
    )
