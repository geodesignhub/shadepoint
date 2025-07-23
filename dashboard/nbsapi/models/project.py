from __future__ import annotations

from typing import Any, TYPE_CHECKING
from sqlalchemy import Column, ForeignKey, String, JSON, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base

if TYPE_CHECKING:
    from .naturebasedsolution import NatureBasedSolution


# Association table for many-to-many relationship between projects and NBS solutions
project_nbs_association = Table(
    "project_nbs_assoc",
    Base.metadata,
    Column(
        "project_id",
        String,
        ForeignKey("project.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "nbs_id",
        ForeignKey("naturebasedsolution.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# Association table for many-to-many relationship between projects and TargetValue
project_targetvalue_association = Table(
    "project_targetvalue_assoc",
    Base.metadata,
    Column(
        "project_id",
        String,
        ForeignKey("project.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "targetvalue_id",
        String,
        ForeignKey("target_value.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)



class Project(Base):
    """
    Project model that can contain multiple nature-based solutions
    """

    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # JSON fields for complex settings
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Project-level settings (scenario, capacity, etc.)"
    )

    map_settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Map display settings (center, zoom, base layer)"
    )

    targets: Mapped[list["TargetValue"]] = relationship(
        "TargetValue",
        secondary=lambda: project_targetvalue_association,
        lazy="selectin",
        backref="projects",
    )

    # Relationship to NBS solutions
    solutions: Mapped[list[NatureBasedSolution]] = relationship(
        "NatureBasedSolution",
        secondary=project_nbs_association,
        backref="projects",
        lazy="selectin",
    )

class TargetValue(Base):

    __tablename__ = "target_value"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of target value: storage_capacity, groundwater_recharge, evapotranspiration, temp_reduction, cool_spot, construction_cost, maintenance_cost, filtering_unit, capture_unit, settling_unit ",
    )
    value: Mapped[float | None] = mapped_column(nullable=True)

    include: Mapped[bool] = mapped_column(nullable=False, default=True)
