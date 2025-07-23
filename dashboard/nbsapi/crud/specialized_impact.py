from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nbsapi.models import SpecializedImpact
from nbsapi.schemas.specialized_impacts import (
    ClimateImpact,
    WaterQualityImpact,
    CostImpact,
    SpecializedImpacts,
)


async def create_specialized_impact(
    db_session: AsyncSession, impact_id: int, specialized_data: SpecializedImpacts
):
    """
    Create a new specialized impact entry linked to an existing impact
    """
    # Extract individual impact data
    climate_data = None
    water_quality_data = None
    cost_data = None

    if specialized_data.climate:
        climate_data = specialized_data.climate.model_dump(exclude_none=True)

    if specialized_data.water_quality:
        water_quality_data = specialized_data.water_quality.model_dump(
            exclude_none=True
        )

    if specialized_data.cost:
        cost_data = specialized_data.cost.model_dump(exclude_none=True)

    # Create the specialized impact object
    specialized_impact = SpecializedImpact(
        impact_id=impact_id,
        climate_data=climate_data,
        water_quality_data=water_quality_data,
        cost_data=cost_data,
    )

    db_session.add(specialized_impact)
    return specialized_impact


async def get_specialized_impact(
    db_session: AsyncSession, impact_id: int
) -> SpecializedImpacts:
    """
    Get specialized impact data for a specific impact ID
    Returns a SpecializedImpacts object or None if not found
    """
    specialized_impact = await db_session.scalar(
        select(SpecializedImpact).where(SpecializedImpact.impact_id == impact_id)
    )

    if not specialized_impact:
        return None

    # Convert from db model to schema
    climate = None
    water_quality = None
    cost = None

    if specialized_impact.climate_data:
        climate = ClimateImpact(**specialized_impact.climate_data)

    if specialized_impact.water_quality_data:
        water_quality = WaterQualityImpact(**specialized_impact.water_quality_data)

    if specialized_impact.cost_data:
        cost = CostImpact(**specialized_impact.cost_data)

    return SpecializedImpacts(climate=climate, water_quality=water_quality, cost=cost)


async def update_specialized_impact(
    db_session: AsyncSession, impact_id: int, specialized_data: SpecializedImpacts
):
    """
    Update an existing specialized impact entry
    """
    specialized_impact = await db_session.scalar(
        select(SpecializedImpact).where(SpecializedImpact.impact_id == impact_id)
    )

    if not specialized_impact:
        # Create new if it doesn't exist
        return await create_specialized_impact(db_session, impact_id, specialized_data)

    # Update existing record
    if specialized_data.climate:
        specialized_impact.climate_data = specialized_data.climate.model_dump(
            exclude_none=True
        )

    if specialized_data.water_quality:
        specialized_impact.water_quality_data = (
            specialized_data.water_quality.model_dump(exclude_none=True)
        )

    if specialized_data.cost:
        specialized_impact.cost_data = specialized_data.cost.model_dump(
            exclude_none=True
        )

    db_session.add(specialized_impact)
    return specialized_impact


async def delete_specialized_impact(db_session: AsyncSession, impact_id: int):
    """
    Delete a specialized impact entry
    """
    specialized_impact = await db_session.scalar(
        select(SpecializedImpact).where(SpecializedImpact.impact_id == impact_id)
    )

    if specialized_impact:
        await db_session.delete(specialized_impact)

    return True
