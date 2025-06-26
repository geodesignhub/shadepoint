from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nbsapi.models.impact import Impact
from nbsapi.models.impact_intensity import ImpactIntensity as IIM  # noqa: N814
from nbsapi.models.impact_unit import ImpactUnit as IIU  # noqa: N814
from nbsapi.models.naturebasedsolution import NatureBasedSolution
from nbsapi.schemas.impact import ImpactBase
from nbsapi.schemas.specialized_impacts import (
    EnhancedImpactBase,
    SpecializedImpacts,
    ClimateImpact,
    WaterQualityImpact,
    CostImpact,
)
from nbsapi.crud.specialized_impact import (
    create_specialized_impact,
    get_specialized_impact,
)


async def create_enhanced_impact(
    db_session: AsyncSession, solution_id: int, impact: EnhancedImpactBase
):
    """
    Create a new impact with optional specialized impact data
    """
    # Get the solution
    solution = await db_session.get(NatureBasedSolution, solution_id)
    if not solution:
        raise HTTPException(
            status_code=404, detail=f"Solution with ID {solution_id} not found"
        )

    # Get or create the intensity
    intensity_result = await db_session.scalars(
        select(IIM).where(IIM.intensity == impact.intensity.intensity)
    )
    intensity = intensity_result.first()
    if not intensity:
        # Create the intensity if it doesn't exist
        intensity = IIM(intensity=impact.intensity.intensity)
        db_session.add(intensity)
        await db_session.flush()  # Get the ID without committing

    # Get or create the unit
    unit_result = await db_session.scalars(
        select(IIU).where(IIU.unit == impact.unit.unit)
    )
    unit = unit_result.first()
    if not unit:
        # Create the unit if it doesn't exist
        unit = IIU(unit=impact.unit.unit, description=impact.unit.description)
        db_session.add(unit)
        await db_session.flush()  # Get the ID without committing

    # Create the basic impact
    db_impact = Impact(
        magnitude=impact.magnitude, intensity=intensity, unit=unit, solution=solution
    )
    db_session.add(db_impact)
    await db_session.flush()  # Get the impact ID without committing transaction

    # Add specialized impact data if provided
    if impact.specialized:
        await create_specialized_impact(db_session, db_impact.id, impact.specialized)

    return db_impact


async def get_enhanced_impact(
    db_session: AsyncSession, impact_id: int
) -> EnhancedImpactBase:
    """
    Get an impact with its specialized data
    """
    # Get the basic impact
    impact_result = await db_session.get(Impact, impact_id)
    if not impact_result:
        return None

    # Create the basic impact schema
    basic_impact = ImpactBase(
        magnitude=impact_result.magnitude,
        unit=impact_result.unit,
        intensity=impact_result.intensity,
    )

    # Get specialized impact data if it exists
    specialized = await get_specialized_impact(db_session, impact_id)

    # Create the enhanced impact
    return EnhancedImpactBase(
        magnitude=basic_impact.magnitude,
        unit=basic_impact.unit,
        intensity=basic_impact.intensity,
        specialized=specialized,
    )


async def get_enhanced_impacts_for_solution(
    db_session: AsyncSession, solution_id: int
) -> list[EnhancedImpactBase]:
    """
    Get all impacts with specialized data for a solution
    """
    # Get all impacts for the solution
    impacts_result = await db_session.scalars(
        select(Impact).where(Impact.solution_id == solution_id)
    )

    impacts = impacts_result.all()
    if not impacts:
        return []

    # Create enhanced impacts
    enhanced_impacts = []
    for impact in impacts:
        # Create the basic impact schema
        basic_impact = ImpactBase(
            magnitude=impact.magnitude, unit=impact.unit, intensity=impact.intensity
        )

        # Get specialized impact data if it exists
        specialized = None
        if hasattr(impact, "specialized") and impact.specialized:
            # Convert from database model to schema
            climate = None
            water_quality = None
            cost = None

            if impact.specialized.climate_data:
                climate = ClimateImpact(**impact.specialized.climate_data)

            if impact.specialized.water_quality_data:
                water_quality = WaterQualityImpact(
                    **impact.specialized.water_quality_data
                )

            if impact.specialized.cost_data:
                cost = CostImpact(**impact.specialized.cost_data)

            specialized = SpecializedImpacts(
                climate=climate, water_quality=water_quality, cost=cost
            )

        # Create the enhanced impact
        enhanced_impact = EnhancedImpactBase(
            magnitude=basic_impact.magnitude,
            unit=basic_impact.unit,
            intensity=basic_impact.intensity,
            specialized=specialized,
        )

        enhanced_impacts.append(enhanced_impact)

    return enhanced_impacts
