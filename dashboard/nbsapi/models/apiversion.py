from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from . import Base


class ApiVersion(Base):
    __tablename__ = "apiversion"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(index=True, unique=True)
