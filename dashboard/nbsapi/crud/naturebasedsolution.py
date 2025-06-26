from fastapi import HTTPException
from geoalchemy2 import Geography
from geoalchemy2 import functions as geo_func
from sqlalchemy import cast, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.sql import distinct

from nbsapi.utils.geometry import (
    wkb_to_geometry_model,
    geometry_to_wkb,
    calculate_area,
    calculate_length,
)

from nbsapi.models import (
    AdaptationTarget,
    Association,
    ImpactUnit,
    MeasureType,
)
from nbsapi.models import (
    Impact as Imp,
)
from nbsapi.models import (
    ImpactIntensity as ImpInt,
)
from nbsapi.models import NatureBasedSolution as NbsDBModel
from nbsapi.schemas.adaptationtarget import TargetBase
from nbsapi.schemas.impact import ImpactIntensity
from nbsapi.schemas.adaptationtarget import AdaptationTargetRead
from nbsapi.schemas.naturebasedsolution import (
    NatureBasedSolutionCreate,
    NatureBasedSolutionRead,
    NatureBasedSolutionUpdate,
)


async def get_intersecting_geometries(
    db_session: AsyncSession, bbox: list[float] | None
):
    MAX_BBOX_AREA = 1_000_000.0  # noqa: N806
    polygon_geom = geo_func.ST_MakeEnvelope(bbox[0], bbox[1], bbox[2], bbox[3], 4326)
    geodesic_area = (
        await db_session.execute(geo_func.ST_Area(cast(polygon_geom, Geography)))
    ).scalar()
    if geodesic_area > MAX_BBOX_AREA:
        raise HTTPException(
            status_code=400,
            detail="GeoJSON input area exceeds the maximum limit of 1 square kilometer.",
        )

    # Query to find intersecting geometries
    query = select(NbsDBModel).where(
        geo_func.ST_Intersects(NbsDBModel.geometry, polygon_geom)
    )
    return query


async def build_nbs_schema_from_model(db_solution: NbsDBModel):
    """FastAPI seems to struggle with automatic serialisation of the the db model to the schema
    so we're doing it manually for now
    """
    # Convert WKBElement geometry to GeoJSON if present
    geometry = None
    if db_solution.geometry:
        geometry = wkb_to_geometry_model(db_solution.geometry)

    # Get styling properties if present
    styling = None
    if hasattr(db_solution, "styling") and db_solution.styling:
        styling = db_solution.styling

    # Get physical properties if present
    physical_properties = None
    if hasattr(db_solution, "physical_properties") and db_solution.physical_properties:
        physical_properties = db_solution.physical_properties

    # Use stored area/length if available, otherwise calculate from geometry
    area = db_solution.area
    length = db_solution.length

    if geometry and area is None:
        area = calculate_area(geometry)

    # Calculate length for LineString geometries if not stored
    if geometry and length is None and geometry.type == "LineString":
        length = calculate_length(geometry)

    solution_read = NatureBasedSolutionRead(
        id=db_solution.id,
        name=db_solution.name,
        definition=db_solution.definition,
        cobenefits=db_solution.cobenefits,
        specificdetails=db_solution.specificdetails,
        location=db_solution.location,
        geometry=geometry,
        styling=styling,
        physical_properties=physical_properties,
        area=area,
        length=length,
        measure_id=db_solution.measure_id,
        adaptations=[
            AdaptationTargetRead(
                adaptation=TargetBase(id=assoc.tg.id, type=assoc.tg.target),
                value=assoc.value,
            )
            for assoc in db_solution.solution_targets
        ],
        impacts=[],  # Impacts are handled separately in v2 API
    )
    return solution_read


async def get_solution(db_session: AsyncSession, solution_id: int):
    solution = (
        await db_session.scalars(
            select(NbsDBModel)
            .options(joinedload(NbsDBModel.solution_targets).joinedload(Association.tg))
            .where(NbsDBModel.id == solution_id)
        )
    ).first()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    return await build_nbs_schema_from_model(solution)


def build_cte(target, assoc_alias, target_alias):
    """
    Build an aliased CTE for Association and AdaptationTarget
    """
    return (
        select(distinct(assoc_alias.nbs_id).label("nbs_id"))
        .join(target_alias, assoc_alias.target_id == target_alias.id)
        .where(
            (target_alias.target == target.adaptation.type)
            & (assoc_alias.value >= target.value)
        )
        .cte()
    )


async def get_filtered_solutions(
    db_session: AsyncSession,
    targets: list[AdaptationTargetRead] | None,
    bbox: list[float] | None,
    intensities: list[ImpactIntensity] | None,
):
    query = select(NbsDBModel)
    if bbox:
        query = await get_intersecting_geometries(db_session, bbox)
    if targets:
        # generate CTEs for each Target and adaptation value in the incoming API query
        condition_sets = [
            build_cte(target, aliased(Association), aliased(AdaptationTarget))
            for target in targets
        ]

        for cset in condition_sets:
            # dynamically add WHERE clauses from the generated CTEs
            query = query.where(NbsDBModel.id.in_(select(cset.c.nbs_id)))
    if intensities:
        # join solution -> intensity -> impact
        query = query.join(Imp)
        query = query.join(Imp.intensity)
        query = query.where(
            ImpInt.intensity.in_(impact.intensity for impact in intensities)
        )
    res = (await db_session.scalars(query)).unique()
    if res:
        res = [await build_nbs_schema_from_model(model) for model in res]
    return res


async def create_nature_based_solution(
    db_session: AsyncSession, solution: NatureBasedSolutionCreate
):
    try:
        # Convert GeoJSON geometry to WKBElement if provided
        geometry_wkb = None
        calculated_area = None
        calculated_length = None

        if solution.geometry:
            geometry_wkb = geometry_to_wkb(solution.geometry)
            # Calculate area and length from geometry
            calculated_area = calculate_area(solution.geometry)
            if solution.geometry.type == "LineString":
                calculated_length = calculate_length(solution.geometry)

        # Get styling properties if present
        styling_data = None
        if solution.styling:
            styling_data = solution.styling.model_dump()

        # Get physical properties if present
        physical_properties_data = None
        if solution.physical_properties:
            physical_properties_data = solution.physical_properties.model_dump(
                exclude_none=True
            )

        # Validate measure_id if provided
        if solution.measure_id:
            measure_result = await db_session.execute(
                select(MeasureType).where(MeasureType.id == solution.measure_id)
            )
            measure_type = measure_result.scalars().first()
            if not measure_type:
                raise HTTPException(
                    status_code=404,
                    detail=f"MeasureType {solution.measure_id} not found",
                )

        db_solution = NbsDBModel(
            name=solution.name,
            definition=solution.definition,
            cobenefits=solution.cobenefits,
            specificdetails=solution.specificdetails,
            location=solution.location,
            geometry=geometry_wkb,
            styling=styling_data,
            physical_properties=physical_properties_data,
            measure_id=solution.measure_id,
            area=solution.area or calculated_area,  # Use provided area or calculated
            length=solution.length
            or calculated_length,  # Use provided length or calculated
        )
        # Handle adaptations if they exist (for backwards compatibility)
        if hasattr(solution, "adaptations") and solution.adaptations:
            for adaptation in solution.adaptations:
                target_type = adaptation.adaptation.type
                value = adaptation.value
                # Properly execute the select statement
                result = await db_session.execute(
                    select(AdaptationTarget).where(
                        AdaptationTarget.target == target_type
                    )
                )
                target = result.scalars().first()
                if not target:
                    raise HTTPException(
                        status_code=404,
                        detail=f"AdaptationTarget {target_type} not found",
                    )
                association = Association(tg=target, value=value)
                db_solution.solution_targets.append(association)
                db_session.add(association)
        # Handle impacts if they exist
        if hasattr(solution, "impacts") and solution.impacts:
            for impact in solution.impacts:
                magnitude = impact.magnitude
                intensity = impact.intensity
                unit = impact.unit
                db_intensity = await db_session.execute(
                    select(ImpInt).where(ImpInt.intensity == intensity.intensity)
                )
                intensity_res = db_intensity.unique().scalar_one_or_none()
                db_unit = await db_session.execute(
                    select(ImpactUnit).where(ImpactUnit.unit == unit.unit)
                )
                unit_res = db_unit.unique().scalar_one_or_none()
                if intensity_res and unit_res:
                    db_impact = Imp(
                        magnitude=magnitude,
                        unit=unit_res,
                        intensity=intensity_res,
                        solution=db_solution,
                    )
                    db_session.add(db_impact)
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="Missing Impact",
                    )
        db_session.add(db_solution)
        await db_session.commit()
        await db_session.refresh(db_solution)
    except IntegrityError:
        await db_session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Solution '{solution.name}' already exists",
        )
    return await build_nbs_schema_from_model(db_solution)


async def update_nature_based_solution(
    db_session: AsyncSession, solution_id: int, update_data: NatureBasedSolutionUpdate
):
    """Update an existing nature-based solution with partial data."""
    try:
        # Get the existing solution
        result = await db_session.execute(
            select(NbsDBModel)
            .options(joinedload(NbsDBModel.solution_targets).joinedload(Association.tg))
            .where(NbsDBModel.id == solution_id)
        )
        db_solution = result.scalars().first()

        if not db_solution:
            raise HTTPException(status_code=404, detail="Solution not found")

        # Update only the fields that are provided
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if field == "geometry" and value is not None:
                # Convert GeoJSON geometry to WKBElement if provided
                geometry_wkb = geometry_to_wkb(value)
                setattr(db_solution, "geometry", geometry_wkb)

                # Recalculate area and length from new geometry
                calculated_area = calculate_area(value)
                setattr(db_solution, "area", calculated_area)

                if value.get("type") == "LineString":
                    calculated_length = calculate_length(value)
                    setattr(db_solution, "length", calculated_length)
                else:
                    setattr(db_solution, "length", None)

            elif field == "styling" and value is not None:
                # Convert styling to dict for storage
                styling_data = (
                    value.model_dump() if hasattr(value, "model_dump") else value
                )
                setattr(db_solution, field, styling_data)

            elif field == "physical_properties" and value is not None:
                # Convert physical properties to dict for storage
                props_data = (
                    value.model_dump(exclude_none=True)
                    if hasattr(value, "model_dump")
                    else value
                )
                setattr(db_solution, field, props_data)

            else:
                # Update regular fields
                setattr(db_solution, field, value)

        await db_session.commit()
        await db_session.refresh(db_solution)

        return await build_nbs_schema_from_model(db_solution)

    except IntegrityError:
        await db_session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Update failed due to constraint violation",
        )
