from dataclasses import asdict

from flask import Blueprint, jsonify, request

from dashboard import db
from dashboard.nbsapi.models.apiversion import ApiVersion
from dashboard.nbsapi.models.impact_intensity import ImpactIntensity
from dashboard.nbsapi.models.impact import Impact
from dashboard.nbsapi.models.impact_unit import ImpactUnit
from dashboard.nbsapi.models.naturebasedsolution import NatureBasedSolution
from dashboard.nbsapi.models.measure_type import MeasureType
from dashboard.nbsapi.models.project import Project

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from shapely.geometry import Polygon, LineString

from .data_definitions import (
    APIVersion as ApiVersionResponse,
    Contact,
    ImpactBase,
    ImpactIntensity as ImpactIntensityResponse,
    ImpactUnit as ImpactUnitResponse,
    EnhancedImpactBase,
    NatureBasedSolutionV2Read,
    NatureBasedSolutionFeature,
    StylingProperties,
    PhysicalProperties,
    MeasureTypeRead,
    MapSettingsRead,
    ProjectRead,
)


nbsapi_blueprint = Blueprint("nbsapi", __name__, url_prefix="/nbsapi")


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _geometry_dict(solution):
    """WKBElement on NatureBasedSolution → GeoJSON dict or None."""
    if solution.geometry is None:
        return None
    return mapping(to_shape(solution.geometry))


def _area(solution):
    if solution.geometry is None:
        return None
    shape = to_shape(solution.geometry)
    return shape.area if isinstance(shape, Polygon) else None


def _length(solution):
    if solution.geometry is None:
        return None
    shape = to_shape(solution.geometry)
    return shape.length if isinstance(shape, LineString) else None


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _build_nbs_v2(solution):
    impacts = [
        ImpactBase(
            magnitude=imp.magnitude,
            unit=ImpactUnitResponse(unit=imp.unit.unit, description=imp.unit.description),
            intensity=ImpactIntensityResponse(intensity=imp.intensity.intensity),
        )
        for imp in solution.impacts
    ]
    styling = StylingProperties(**(solution.styling or {})) if solution.styling else None
    physical = PhysicalProperties(**(solution.physical_properties or {})) if solution.physical_properties else None
    return NatureBasedSolutionV2Read(
        id=solution.id,
        name=solution.name,
        definition=solution.definition,
        cobenefits=solution.cobenefits,
        specificdetails=solution.specificdetails,
        geometry=_geometry_dict(solution),
        styling=styling,
        physical_properties=physical,
        area=_area(solution),
        length=_length(solution),
        measure_id=solution.measure_id,
        impacts=impacts or None,
    )


def _build_project_read(project):
    areas = [asdict(_build_nbs_v2(nbs)) for nbs in project.areas]
    map_s = MapSettingsRead(**(project.map_settings or {})) if project.map_settings else None
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        settings=project.settings,
        map=map_s,
        targets=project.targets,
        areas=areas or None,
    )


# ---------------------------------------------------------------------------
# Non-versioned endpoints (kept from v1)
# ---------------------------------------------------------------------------

@nbsapi_blueprint.route("/contact", methods=["GET"])
def get_contact():
    return jsonify(asdict(Contact(website="https://community.geodesignhub.com")))


@nbsapi_blueprint.route("/currentversion", methods=["GET"])
def get_apiversion():
    versions = ApiVersion.query.all()
    return jsonify(
        [asdict(ApiVersionResponse(version=v.version)) for v in versions]
    )


# ---------------------------------------------------------------------------
# v2 — Solutions
# ---------------------------------------------------------------------------

@nbsapi_blueprint.route("/v2/api/solutions/solutions/<int:solution_id>", methods=["GET"])
def v2_get_solution(solution_id):
    solution = db.get_or_404(NatureBasedSolution, solution_id)
    return jsonify(asdict(_build_nbs_v2(solution)))


@nbsapi_blueprint.route("/v2/api/solutions/solutions/<int:solution_id>/geojson", methods=["GET"])
def v2_get_solution_geojson(solution_id):
    solution = db.get_or_404(NatureBasedSolution, solution_id)
    nbs = _build_nbs_v2(solution)
    feature = NatureBasedSolutionFeature(
        geometry=nbs.geometry,
        properties={k: v for k, v in asdict(nbs).items() if k != "geometry"},
    )
    return jsonify(asdict(feature))


# ---------------------------------------------------------------------------
# v2 — Impacts
# ---------------------------------------------------------------------------

@nbsapi_blueprint.route("/v2/api/impacts/intensities", methods=["GET"])
def v2_get_intensities():
    rows = ImpactIntensity.query.all()
    return jsonify([asdict(ImpactIntensityResponse(intensity=r.intensity)) for r in rows])


@nbsapi_blueprint.route("/v2/api/impacts/units", methods=["GET"])
def v2_get_units():
    rows = ImpactUnit.query.all()
    return jsonify([asdict(ImpactUnitResponse(unit=r.unit, description=r.description)) for r in rows])


@nbsapi_blueprint.route("/v2/api/impacts/solutions/<int:solution_id>/impacts", methods=["GET"])
def v2_get_solution_impacts(solution_id):
    db.get_or_404(NatureBasedSolution, solution_id)
    impacts = Impact.query.filter_by(solution_id=solution_id).all()
    result = [
        asdict(EnhancedImpactBase(
            magnitude=imp.magnitude,
            unit=ImpactUnitResponse(unit=imp.unit.unit, description=imp.unit.description),
            intensity=ImpactIntensityResponse(intensity=imp.intensity.intensity),
        ))
        for imp in impacts
    ]
    return jsonify(result)


@nbsapi_blueprint.route("/v2/api/impacts/impacts/<int:impact_id>", methods=["GET"])
def v2_get_impact(impact_id):
    imp = db.get_or_404(Impact, impact_id)
    return jsonify(asdict(EnhancedImpactBase(
        magnitude=imp.magnitude,
        unit=ImpactUnitResponse(unit=imp.unit.unit, description=imp.unit.description),
        intensity=ImpactIntensityResponse(intensity=imp.intensity.intensity),
    )))


# ---------------------------------------------------------------------------
# v2 — Projects
# ---------------------------------------------------------------------------

@nbsapi_blueprint.route("/v2/api/projects", methods=["GET"])
def v2_get_projects():
    projects = Project.query.all()
    return jsonify([asdict(_build_project_read(p)) for p in projects])


@nbsapi_blueprint.route("/v2/api/projects/<project_id>", methods=["GET"])
def v2_get_project(project_id):
    project = db.get_or_404(Project, project_id)
    return jsonify(asdict(_build_project_read(project)))


@nbsapi_blueprint.route("/v2/api/projects/<project_id>/export", methods=["GET"])
def v2_export_project(project_id):
    project = db.get_or_404(Project, project_id)
    return jsonify(asdict(_build_project_read(project)))


@nbsapi_blueprint.route("/v2/api/projects/<project_id>/export/deltares", methods=["GET"])
def v2_export_project_deltares(project_id):
    project = db.get_or_404(Project, project_id)
    areas = []
    for nbs in project.areas:
        areas.append({
            "id": str(nbs.id),
            "type": "Feature",
            "geometry": _geometry_dict(nbs),
            "properties": asdict(_build_nbs_v2(nbs)),
        })
    settings = project.settings or {}
    export = {
        "areas": areas,
        "legalAccepted": True,
        "displayMap": True,
        "map": project.map_settings or {},
        "settings": settings,
        "savedInWorkspace": None,
    }
    return jsonify(export)


# ---------------------------------------------------------------------------
# v2 — Measure Types
# ---------------------------------------------------------------------------

@nbsapi_blueprint.route("/v2/measure_types/", methods=["GET"])
def v2_get_measure_types():
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 100, type=int)
    rows = MeasureType.query.offset(skip).limit(limit).all()
    return jsonify([
        asdict(MeasureTypeRead(
            id=r.id,
            name=r.name,
            description=r.description,
            default_color=r.default_color,
            default_inflow=r.default_inflow,
            default_depth=r.default_depth,
            default_width=r.default_width,
            default_radius=r.default_radius,
        ))
        for r in rows
    ])


@nbsapi_blueprint.route("/v2/measure_types/<measure_id>", methods=["GET"])
def v2_get_measure_type(measure_id):
    mt = db.get_or_404(MeasureType, measure_id)
    return jsonify(asdict(MeasureTypeRead(
        id=mt.id,
        name=mt.name,
        description=mt.description,
        default_color=mt.default_color,
        default_inflow=mt.default_inflow,
        default_depth=mt.default_depth,
        default_width=mt.default_width,
        default_radius=mt.default_radius,
    )))
