from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


project_nbs_table = Table(
    "project_nbs",
    Base.metadata,
    Column("project_id", ForeignKey("project.id"), primary_key=True),
    Column("nbs_id", ForeignKey("naturebasedsolution.id"), primary_key=True),
)


class Project(Base):
    __tablename__ = "project"
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(index=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    map_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    targets: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    areas = relationship(
        "NatureBasedSolution",
        secondary=project_nbs_table,
        lazy="selectin",
    )
