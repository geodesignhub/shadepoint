from typing import List

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from . import Base


class ImpactUnit(Base):
    __tablename__ = "impact_unit"
    id: Mapped[int] = mapped_column(primary_key=True)
    unit: Mapped[str] = mapped_column(index=True, unique=True)
    description: Mapped[str] = mapped_column(index=True)
    impacts: Mapped[List["Impact"]] = relationship(
        back_populates="unit",
    )
