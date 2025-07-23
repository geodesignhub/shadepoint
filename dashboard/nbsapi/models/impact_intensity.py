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


class ImpactIntensity(Base):
    __tablename__ = "impact_intensity"
    id: Mapped[int] = mapped_column(primary_key=True)
    intensity: Mapped[str] = mapped_column(index=True, unique=True)
    impacts: Mapped[list[Impact]] = relationship(
        back_populates="intensity",
    )
