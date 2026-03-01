from __future__ import annotations

import uuid
from typing import Optional

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class Association(Base):
    __tablename__ = "nbs_target_assoc"
    nbs_id: Mapped[int] = mapped_column(
        ForeignKey("naturebasedsolution.id"), primary_key=True
    )
    target_id: Mapped[int] = mapped_column(
        ForeignKey("adaptationtarget.id"), primary_key=True
    )
    tg = relationship("AdaptationTarget", lazy="joined", back_populates="solutions")
    solution = relationship("NatureBasedSolution", back_populates="solution_targets")
    value: Mapped[int]

    @property
    def target_obj(self):
        return self.tg


class NatureBasedSolution(Base):
    __tablename__ = "naturebasedsolution"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True, unique=True)
    definition: Mapped[str] = mapped_column(index=True)
    cobenefits: Mapped[str] = mapped_column(index=True)
    specificdetails: Mapped[str] = mapped_column(index=True)

    # v2: solution boundary geometry (Point / LineString / Polygon)
    geometry: Mapped[WKBElement] = mapped_column(
        Geometry("GEOMETRY", srid=4326), spatial_index=False, nullable=True
    )
    # v2: reference to measure type
    measure_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("measuretype.id"), nullable=True
    )
    # v2: styling and physical properties stored as JSON blobs
    styling: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    physical_properties: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    measure_type = relationship("MeasureType", back_populates="solutions")
    tree_locations = relationship(
        "TreeLocation", back_populates="solution", lazy="selectin"
    )
    solution_targets = relationship(
        "Association",
        back_populates="solution",
        lazy="joined",
        collection_class=list,
        cascade="all, delete-orphan",
    )
    impacts = relationship(
        "Impact",
        back_populates="solution",
        collection_class=list,
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_nbs_geometry", geometry, postgresql_using="gist"),
    )


class TreeLocation(Base):
    __tablename__ = "treelocation"
    id: Mapped[int] = mapped_column(primary_key=True)
    location: Mapped[str] = mapped_column(index=True)
    geometry: Mapped[WKBElement] = mapped_column(
        Geometry("POINT", srid=4326), spatial_index=False, nullable=True
    )
    session_id = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    solution_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("naturebasedsolution.id"), nullable=True
    )
    solution = relationship("NatureBasedSolution", back_populates="tree_locations")

    __table_args__ = (
        Index("idx_geo_data_geometry", geometry, postgresql_using="gist"),
    )
