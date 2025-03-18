from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nbsapi.models.impact import Impact
from nbsapi.models.impact_intensity import ImpactIntensity as IIM
from nbsapi.models.impact_unit import ImpactUnit as IIU
from nbsapi.schemas.impact import ImpactBase, ImpactIntensity, ImpactUnit


async def get_impacts(db_session: AsyncSession):
    """Retrieve all available adaptation impacts"""
    impacts = (await db_session.scalars(select(Impact))).unique()
    actual = [
        ImpactBase(
            magnitude=impact.magnitude, unit=impact.unit, intensity=impact.intensity
        )
        for impact in impacts
    ]
    return actual


async def get_impact_intensities(db_session: AsyncSession):
    """Retrieve all available impact intensities"""
    intensities = (await db_session.scalars(select(IIM))).unique()
    actual = [
        ImpactIntensity(intensity=intensity.intensity) for intensity in intensities
    ]
    return actual


async def get_impact_units(db_session: AsyncSession):
    """Retrieve all available impact units"""
    units = (await db_session.scalars(select(IIU))).unique()
    actual = [
        ImpactUnit(unit=unit.unit, description=unit.description) for unit in units
    ]
    return actual


async def create_impact_intensity(
    db_session: AsyncSession, i_intensity: ImpactIntensity
):
    """Create a new impact intensity"""
    db_target = IIM(
        intensity=i_intensity.intensity,
    )
    db_session.add(db_target)
    try:
        await db_session.commit()
        await db_session.refresh(db_target)
    except IntegrityError:
        db_session.rollback()
        raise HTTPException(status_code=403, detail="Intensity already exists")
    return i_intensity


async def create_impact_unit(db_session: AsyncSession, i_unit: ImpactUnit):
    """Create a new impact unit"""
    db_target = IIU(unit=i_unit.unit, description=i_unit.description)
    db_session.add(db_target)
    try:
        await db_session.commit()
        await db_session.refresh(db_target)
    except IntegrityError:
        db_session.rollback()
        raise HTTPException(status_code=403, detail="Unit already exists")
    return i_unit
