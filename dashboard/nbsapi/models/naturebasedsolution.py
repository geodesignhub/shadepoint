from __future__ import annotations

from typing import Any
import uuid
from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import ForeignKey, JSON, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import UUID
from . import Base


class NatureBasedSolution(Base):
    __tablename__ = "naturebasedsolution"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True, unique=True)
    definition: Mapped[str] = mapped_column(index=True)
    cobenefits: Mapped[str] = mapped_column(index=True)
    specificdetails: Mapped[str] = mapped_column(index=True)
    location: Mapped[str] = mapped_column(index=True)
    geometry: Mapped[WKBElement] = mapped_column(
        Geometry("GEOMETRY", srid=4326), spatial_index=True, nullable=True
    )
    styling: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    physical_properties: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Physical dimensions and properties"
    )
    measure_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("measure_types.id"),
        nullable=True,
        comment="Reference to measure type",
    )
    area: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Calculated area in square meters"
    )
    length: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Calculated length in meters (for LineString)"
    )

    # Relationships
    measure_type = relationship("MeasureType", lazy="joined")


    impacts = relationship(
        "Impact",
        back_populates="solution",
        collection_class=list,
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class TreeLocation(Base):
    __tablename__ = "treelocation"
    id: Mapped[int] = mapped_column(primary_key=True)
    location: Mapped[str] = mapped_column(index=True)
    geometry: Mapped[WKBElement] = mapped_column(
        Geometry("POINT", srid=4326), spatial_index=False, nullable=True
    )
    session_id =mapped_column(UUID(as_uuid=True), default=uuid.uuid4)

    __table_args__ = (Index("idx_geo_data_geometry", geometry, postgresql_using="gist"),)