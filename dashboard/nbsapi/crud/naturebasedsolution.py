from typing import List, Optional

from fastapi import HTTPException
from geoalchemy2 import Geography
from geoalchemy2 import functions as geo_func
from sqlalchemy import cast, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.sql import distinct

from nbsapi.models import (
    AdaptationTarget,
    Association,
    ImpactUnit,
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
from nbsapi.schemas.naturebasedsolution import (
    AdaptationTargetRead,
    NatureBasedSolutionCreate,
    NatureBasedSolutionRead,
)


async def get_intersecting_geometries(
    db_session: AsyncSession, bbox: Optional[List[float]]
):
    MAX_BBOX_AREA = 1_000_000.0
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
    solution_read = NatureBasedSolutionRead(
        id=db_solution.id,
        name=db_solution.name,
        definition=db_solution.definition,
        cobenefits=db_solution.cobenefits,
        specificdetails=db_solution.specificdetails,
        location=db_solution.location,
        adaptations=[
            AdaptationTargetRead(
                adaptation=TargetBase(id=assoc.tg.id, type=assoc.tg.target),
                value=assoc.value,
            )
            for assoc in db_solution.solution_targets
        ],
        impacts=db_solution.impacts,
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
    targets: Optional[List[AdaptationTargetRead]],
    bbox: Optional[List[float]],
    intensities: Optional[List[ImpactIntensity]],
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
        db_solution = NbsDBModel(
            name=solution.name,
            definition=solution.definition,
            cobenefits=solution.cobenefits,
            specificdetails=solution.specificdetails,
            location=solution.location,
        )
        for adaptation in solution.adaptations:
            target_type = adaptation.adaptation.type
            value = adaptation.value
            # Properly execute the select statement
            result = await db_session.execute(
                select(AdaptationTarget).where(AdaptationTarget.target == target_type)
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
        for impact in solution.impacts:
            magnitude = impact.magnitude
            intensity = impact.intensity
            unit = impact.unit
            db_intensity = await db_session.execute(
                select(ImpactIntensity).where(
                    ImpactIntensity.intensity == intensity.intensity
                )
            )
            intensity_res = db_intensity.unique().scalar_one_or_none()
            db_unit = await db_session.execute(
                select(ImpactUnit).where(ImpactUnit.unit == unit.unit)
            )
            unit_res = db_unit.unique().scalar_one_or_none()
            if intensity_res and unit_res:
                db_impact = Impact(
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
        db_session.rollback()
        raise HTTPException(
            status_code=403,
            detail=f"Solution '{solution.name}' already exists",
        )
    return await build_nbs_schema_from_model(db_solution)
