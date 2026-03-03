from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class MeasureType(Base):
    __tablename__ = "measuretype"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    default_color: Mapped[Optional[str]] = mapped_column(nullable=True)
    default_inflow: Mapped[Optional[float]] = mapped_column(nullable=True)
    default_depth: Mapped[Optional[float]] = mapped_column(nullable=True)
    default_width: Mapped[Optional[float]] = mapped_column(nullable=True)
    default_radius: Mapped[Optional[float]] = mapped_column(nullable=True)
    solutions = relationship("NatureBasedSolution", back_populates="measure_type")
