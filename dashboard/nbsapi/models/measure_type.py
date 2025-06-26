"""Measure Type model for predefined Nature-Based Solution types."""

from sqlalchemy import Column, Float, String, Text

from . import Base


class MeasureType(Base):
    """Database model for measure types."""

    __tablename__ = "measure_types"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    default_color = Column(String, nullable=True)
    default_inflow = Column(Float, nullable=True)
    default_depth = Column(Float, nullable=True)
    default_width = Column(Float, nullable=True)
    default_radius = Column(Float, nullable=True)
