"""CRUD operations for measure types."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nbsapi.models.measure_type import MeasureType
from nbsapi.models.naturebasedsolution import NatureBasedSolution
from nbsapi.schemas.measure_type import MeasureTypeCreate, MeasureTypeUpdate


async def get_measure_type(db: AsyncSession, measure_id: str) -> MeasureType | None:
    """Get a measure type by ID."""
    result = await db.execute(select(MeasureType).where(MeasureType.id == measure_id))
    return result.scalar_one_or_none()


async def get_measure_types(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[MeasureType]:
    """Get all measure types."""
    result = await db.execute(select(MeasureType).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_measure_type(
    db: AsyncSession, measure_type: MeasureTypeCreate
) -> MeasureType:
    """Create a new measure type."""
    db_measure_type = MeasureType(**measure_type.model_dump())
    db.add(db_measure_type)
    await db.commit()
    await db.refresh(db_measure_type)
    return db_measure_type


async def update_measure_type(
    db: AsyncSession, measure_id: str, measure_type_update: MeasureTypeUpdate
) -> MeasureType | None:
    """Update a measure type."""
    db_measure_type = await get_measure_type(db, measure_id)
    if db_measure_type is None:
        return None

    update_data = measure_type_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_measure_type, field, value)

    await db.commit()
    await db.refresh(db_measure_type)
    return db_measure_type


async def delete_measure_type(db: AsyncSession, measure_id: str) -> bool:
    """Delete a measure type."""
    db_measure_type = await get_measure_type(db, measure_id)
    if db_measure_type is None:
        return False

    # Check if any nature-based solutions reference this measure type
    result = await db.execute(
        select(NatureBasedSolution).where(NatureBasedSolution.measure_id == measure_id)
    )
    referenced_solutions = result.scalars().first()

    if referenced_solutions:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete measure type {measure_id}: it is referenced by existing nature-based solutions",
        )

    try:
        await db.delete(db_measure_type)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete measure type {measure_id}: it is referenced by other resources",
        )
    else:
        return True
