from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nbsapi.models import User as UserDBModel
from nbsapi.schemas.user import UserWrite
from nbsapi.utils.auth import create_user


async def get_user(db_session: AsyncSession, user_id: int):
    user = (
        await db_session.scalars(select(UserDBModel).where(UserDBModel.id == user_id))
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_user_by_username(db_session: AsyncSession, username: str):
    return (
        await db_session.scalars(
            select(UserDBModel).where(UserDBModel.username == username)
        )
    ).first()


async def make_user(db_session: AsyncSession, newuser: UserWrite):
    db_user = (
        await db_session.scalars(
            select(UserDBModel).where(UserDBModel.username == newuser.username)
        )
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Could not create user")
    return await create_user(db_session=db_session, user=newuser)
