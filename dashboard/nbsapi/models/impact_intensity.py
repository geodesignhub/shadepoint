from typing import List

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from . import Base


class ImpactIntensity(Base):
    __tablename__ = "impact_intensity"
    id: Mapped[int] = mapped_column(primary_key=True)
    intensity: Mapped[str] = mapped_column(index=True, unique=True)
    impacts: Mapped[List["Impact"]] = relationship(
        back_populates="intensity",
    )
