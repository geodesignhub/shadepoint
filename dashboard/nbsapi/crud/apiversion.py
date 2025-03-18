from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nbsapi.models.apiversion import ApiVersion as DbApiVersion
from nbsapi.schemas.apiversion import ApiVersion as SchemaApiVersion


async def get_current_version(db_session: AsyncSession):
    """Retrieve an individual adaptation target"""
    version = await db_session.scalar(select(func.max(DbApiVersion.version)))
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    actual = SchemaApiVersion(version=version)
    return actual
