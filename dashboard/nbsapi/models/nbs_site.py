from __future__ import annotations

from typing import List
from sqlalchemy import Index
from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class NatureBasedSolutionSite(Base):
    __tablename__ = "naturebasedsolutionsite"
    id: Mapped[int] = mapped_column
    location: Mapped[str] = mapped_column(index=True, primary_key=True)
    geometry: Mapped[WKBElement] = mapped_column(
        Geometry("GEOMETRY", srid=4326), spatial_index=False, nullable=True
    )

    __table_args__ = (
        Index("idx_geo_data_geometry", geometry, postgresql_using="gist"),
    )
