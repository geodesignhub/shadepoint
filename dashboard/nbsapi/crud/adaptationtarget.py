from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nbsapi.models.adaptation_target import AdaptationTarget
from nbsapi.schemas.adaptationtarget import TargetBase


async def get_target(db_session: AsyncSession, target_id: int):
    """Retrieve an individual adaptation target"""
    target = (
        await db_session.scalars(
            select(AdaptationTarget).where(AdaptationTarget.id == target_id)
        )
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Adaptation target not found")
    actual = TargetBase(id=target.id, type=target.target)
    return actual


async def get_targets(db_session: AsyncSession):
    """Retrieve all available adaptation targets"""
    targets = (await db_session.scalars(select(AdaptationTarget))).unique()
    actual = [TargetBase(id=target.id, type=target.target) for target in targets]
    return actual


async def create_target(db_session: AsyncSession, itarget: TargetBase):
    db_target = AdaptationTarget(
        target=itarget.type,
    )
    db_session.add(db_target)
    try:
        await db_session.commit()
        await db_session.refresh(db_target)
    except IntegrityError:
        await db_session.rollback()
        raise HTTPException(
            status_code=409, detail=f"Target '{itarget.type}' already exists"
        )
    return itarget
