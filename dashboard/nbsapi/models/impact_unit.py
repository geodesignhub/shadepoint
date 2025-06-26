from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from . import Base

if TYPE_CHECKING:
    from .impact import Impact


class ImpactUnit(Base):
    __tablename__ = "impact_unit"
    id: Mapped[int] = mapped_column(primary_key=True)
    unit: Mapped[str] = mapped_column(index=True, unique=True)
    description: Mapped[str] = mapped_column(index=True)
    impacts: Mapped[list[Impact]] = relationship(
        back_populates="unit",
    )
