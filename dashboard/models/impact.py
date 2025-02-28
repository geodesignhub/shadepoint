from __future__ import annotations

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class Impact(Base):
    __tablename__ = "impact"
    id: Mapped[int] = mapped_column(primary_key=True)
    magnitude: Mapped[float] = mapped_column(index=True, unique=False)
    intensity_id: Mapped[int] = mapped_column(ForeignKey("impact_intensity.id"))
    intensity: Mapped["ImpactIntensity"] = relationship(
        back_populates="impacts", lazy="joined"
    )
    unit_id: Mapped[int] = mapped_column(ForeignKey("impact_unit.id"))
    unit: Mapped["ImpactUnit"] = relationship(back_populates="impacts", lazy="joined")
    solution_id: Mapped[int] = mapped_column(
        ForeignKey("naturebasedsolution.id"), nullable=False
    )
    solution: Mapped["NatureBasedSolution"] = relationship(
        back_populates="impacts",
    )
