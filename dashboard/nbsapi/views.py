from operator import ge
from flask import jsonify
from sqlalchemy import desc
from dashboard.nbsapi.models.apiversion import ApiVersion
from dashboard.nbsapi.models.impact_intensity import ImpactIntensity
from dashboard.nbsapi.models.impact import Impact
from dashboard.nbsapi.models.impact_unit import ImpactUnit

from dashboard.nbsapi.models.measure_type import MeasureType
from dashboard.nbsapi.models.project import Project
from dashboard.nbsapi.models.naturebasedsolution import (
    NatureBasedSolution,
    TreeLocation,
)

from flask import Blueprint
from dashboard import db
from dataclasses import asdict
from dacite import from_dict

import json
import geojson
from .data_definitions import APIVersion as ApiVersionResponse, SolutionRequestV2
from .data_definitions import (
    Contact,
    ImpactBase,
    
)
from .data_definitions import EnhancedImpactBaseInput, SpecializedImpacts, ClimateImpact
from .data_definitions import MeasureTypeRead
from .data_definitions import TargetValue as TargetValueRead
from .data_definitions import ImpactIntensity as ImpactIntensityResponse
from .data_definitions import ImpactUnit as ImpactUnitResponse
from .data_definitions import (
    NatureBasedSolutionReadOutput as NatureBasedSolutionResponse,
    NatureBasedSolutionFeatureCollection,
    ProjectReadOutput,
    MapSettings,

    ProjectSettings
)
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
from flask import request
from shapely import wkb
from shapely.geometry import mapping
from geojson import Feature, FeatureCollection


nbsapi_blueprint = Blueprint("nbsapi", __name__, url_prefix="/nbsapi")


@nbsapi_blueprint.route("/contact", methods=["GET"])
def get_contact():
    return jsonify(Contact(website="https://community.geodesignhub.com"))


@nbsapi_blueprint.route("/currentversion", methods=["GET"])
def get_apiversion():
    versions = ApiVersion.query.all()
    return jsonify(
        [asdict(ApiVersionResponse(version=version.version)) for version in versions]
    )


@nbsapi_blueprint.route("/v2/measure_types/", methods=["GET"])
def get_measure_types():
    measure_types = MeasureType.query.all()
    all_measure_types: list[MeasureTypeRead] = []
    for measure_type in measure_types:
        cur_measure_type = MeasureTypeRead(
            id=measure_type.id,
            name=measure_type.name,
            description=measure_type.description,
            default_color=measure_type.default_color,
            default_inflow=measure_type.default_inflow,
            default_depth=measure_type.default_depth,
            default_width=measure_type.default_width,
            default_radius=measure_type.default_radius,
        )
        all_measure_types.append(cur_measure_type)

    return jsonify([asdict(measure_type) for measure_type in all_measure_types])


@nbsapi_blueprint.route("/v2/api/impacts/impacts", methods=["GET"])
def get_impacts():
    impacts = Impact.query.all()
    all_impacts: list[ImpactBase] = []
    for impact in impacts:
        impact_base = ImpactBase(
            magnitude=impact.magnitude,
            unit=ImpactUnitResponse(
                unit=impact.unit.unit, description=impact.unit.description
            ),
            intensity=ImpactIntensityResponse(intensity=impact.intensity.intensity),
        )
        all_impacts.append(impact_base)

    return jsonify([asdict(impact) for impact in all_impacts])


@nbsapi_blueprint.route("/v2/api/impacts/intensities", methods=["GET"])
def get_impacts_intensities():
    impact_intentities = ImpactIntensity.query.all()
    return jsonify(
        [
            asdict(ImpactIntensityResponse(intensity=impact_intensity.intensity))
            for impact_intensity in impact_intentities
        ]
    )


@nbsapi_blueprint.route("/v2/api/impacts/units", methods=["GET"])
def get_impacts_units():
    impact_units = ImpactUnit.query.all()
    return jsonify(
        [
            asdict(
                ImpactUnitResponse(
                    unit=impact_unit.unit, description=impact_unit.description
                )
            )
            for impact_unit in impact_units
        ]
    )


@nbsapi_blueprint.route(
    "/v2/api/solutions/solutions/<solution_id>/impacts", methods=["GET"]
)
def get_solution_impacts(solution_id: int):
    solutions = NatureBasedSolution.query.filter_by(id=solution_id).all()

    locations = TreeLocation.query.distinct(TreeLocation.location).all()

    all_solutions = []
    for location in locations:
        for solution in solutions:
            print(solution.impacts)
            all_solutions.append(
                asdict(
                    from_dict(
                        data_class=NatureBasedSolutionResponse,
                        data={
                            "name": solution.name,
                            "definition": solution.definition,
                            "cobenefits": solution.cobenefits,
                            "specificdetails": solution.specificdetails,
                            "location": location.location,
                            "geometry": location.geometry,
                            "id": solution.id,
                            "styling": solution.styling,
                            "physical_properties": solution.physical_properties,
                            "measure_id": solution.measure_id,
                            "area": solution.area,
                            "length": solution.length,
                            "measure_type": solution.measure_type,
                            "impacts": [asdict(impact) for impact in solution.impacts],
                        },
                    )
                )
            )
    return jsonify(all_solutions)


@nbsapi_blueprint.route("/v2/api/solutions/solutions", methods=["POST"])
@csrf.exempt
def filter_tree_locations():

    bbox = request.json.get("bbox", None)
    if bbox:
        minx, miny, maxx, maxy = bbox
        locations = TreeLocation.query.filter(
            TreeLocation.location.ST_Within(
                f"SRID=4326;POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
            )
        ).all()
    else:
        locations = TreeLocation.query.distinct(TreeLocation.location).all()
    adaptation_target = request.json.get("adaptation", None)
    if adaptation_target:

        adaptation_target = from_dict(
            data_class=AdapatationTargetResponse, data=adaptation_target
        )
        solutions = NatureBasedSolution.query.filter(
            NatureBasedSolution.solution_targets.any(
                adaptation=adaptation_target.adaptation,
                value=adaptation_target.value,
            )
        ).all()

    all_solutions = []
    for location in locations:
        for solution in solutions.copy():
            all_solutions.append(
                asdict(
                    from_dict(
                        data_class=NatureBasedSolutionResponse,
                        data={
                            "name": solution.name,
                            "definition": solution.definition,
                            "cobenefits": solution.cobenefits,
                            "specificdetails": solution.specificdetails,
                            "location": location,
                            "geometry": solution.geometry,
                            "id": solution.id,
                            "styling": solution.styling,
                            "physical_properties": solution.physical_properties,
                            "measure_id": solution.measure_id,
                            "area": solution.area,
                            "length": solution.length,
                            "measure_type": solution.measure_type,
                            "impacts": [asdict(impact) for impact in solution.impacts],
                        },
                    )
                )
            )
    return jsonify(all_solutions)


@nbsapi_blueprint.route(
    "/v2/api/impacts/solutions/<solution_id>/impacts", methods=["GET"]
)
def get_stored_solution_impacts(solution_id: int):
    solutions = NatureBasedSolution.query.filter_by(id=solution_id).all()

    all_impact_objs = []
    for solution in solutions:
        all_impacts = solution.impacts
        for impact in all_impacts:

            cur_impact = EnhancedImpactBaseInput(
                magnitude=impact.magnitude,
                unit=ImpactUnitResponse(
                    unit=impact.unit.unit, description=impact.unit.description
                ),
                intensity=ImpactIntensityResponse(intensity=impact.intensity.intensity),
            )
            if impact.specialized:
                _climate_data = impact.specialized.climate_data

                cur_impact.specialized = SpecializedImpacts(
                    climate=ClimateImpact(
                        temp_reduction=_climate_data.get("temp_reduction", None),
                        cool_spot=_climate_data.get("cool_spot", None),
                        evapotranspiration=_climate_data.get(
                            "evapotranspiration", None
                        ),
                        groundwater_recharge=_climate_data.get(
                            "groundwater_recharge", None
                        ),
                        storage_capacity=_climate_data.get("storage_capacity", None),
                    )
                )
        all_impact_objs.append(cur_impact)

    return jsonify(all_impact_objs)


@nbsapi_blueprint.route(
    "/v2/api/solutions/solutions/<solution_id>/geojson", methods=["GET"]
)
def get_stored_solution_geojson(solution_id: int):
    solutions = NatureBasedSolution.query.filter_by(id=solution_id).all()

    locations = TreeLocation.query.distinct(TreeLocation.location).all()

    all_features = []
    solution_properties = {}
    for solution in solutions:
        all_impacts = solution.impacts
        all_impact_objs = []
        for impact in all_impacts:

            cur_impact = EnhancedImpactBaseInput(
                magnitude=impact.magnitude,
                unit=ImpactUnitResponse(
                    unit=impact.unit.unit, description=impact.unit.description
                ),
                intensity=ImpactIntensityResponse(intensity=impact.intensity.intensity),
            )
            if impact.specialized:
                _climate_data = impact.specialized.climate_data

                cur_impact.specialized = SpecializedImpacts(
                    climate=ClimateImpact(
                        temp_reduction=_climate_data.get("temp_reduction", None),
                        cool_spot=_climate_data.get("cool_spot", None),
                        evapotranspiration=_climate_data.get(
                            "evapotranspiration", None
                        ),
                        groundwater_recharge=_climate_data.get(
                            "groundwater_recharge", None
                        ),
                        storage_capacity=_climate_data.get("storage_capacity", None),
                    )
                )
        all_impact_objs.append(cur_impact)
        # Convert solution.geometry (WKB) to GeoJSON Feature
        if solution.geometry:
            geom = wkb.loads(bytes(solution.geometry.data))
            geojson_feature = Feature(geometry=mapping(geom), properties={})
            solution_geojson = FeatureCollection([geojson_feature])
            solution_geojson = json.loads(geojson.dumps(solution_geojson))
        else:
            solution_geojson = None
        solution_properties = asdict(
            from_dict(
                data_class=NatureBasedSolutionResponse,
                data={
                    "name": solution.name,
                    "definition": solution.definition,
                    "cobenefits": solution.cobenefits,
                    "location": solution.location,
                    "specificdetails": solution.specificdetails,
                    "geometry": solution_geojson,
                    "id": solution.id,
                    "styling": solution.styling,
                    "physical_properties": solution.physical_properties,
                    "measure_id": solution.measure_id,
                    "area": solution.area,
                    "length": solution.length,
                    "measure_type": solution.measure_type,
                    "impacts": [asdict(impact_obj) for impact_obj in all_impact_objs],
                },
            )
        )
    all_location_features = []
    for location in locations:
        # Convert WKB to GeoJSON FeatureCollection
        if location.geometry:
            geom = wkb.loads(bytes(location.geometry.data))

            geojson_feature = Feature(
                geometry=mapping(geom), properties=solution_properties
            )
        else:
            geojson_feature = None

        if geojson_feature:
            all_location_features.append(geojson_feature)

    all_location_features = [
        json.loads(geojson.dumps(feature)) for feature in all_location_features
    ]
    all_features = NatureBasedSolutionFeatureCollection(
        features=all_location_features, type="FeatureCollection"
    )

    return jsonify(asdict(all_features))



@nbsapi_blueprint.route("/v2/api/projects", methods=["GET"])
def get_stored_projects():
    
    projects = Project.query.all()
    all_projects = []
    for cur_project in projects: 

        _project_settings = from_dict(data_class=ProjectSettings, 
                                        data=cur_project.settings)
        _map_settings = from_dict(data_class=MapSettings,
                                    data=cur_project.map_settings)
        
        targets = cur_project.targets
        _targets = []
        for target in targets:
            _target = from_dict(data_class=TargetValueRead, data=asdict(target))
            _targets.append(_target)
        solutions = cur_project.solutions
        _solutions = []
        for solution in solutions:
            all_impacts = solution.impacts
            all_impact_objs = []
            for impact in all_impacts:

                cur_impact = EnhancedImpactBaseInput(
                    magnitude=impact.magnitude,
                    unit=ImpactUnitResponse(
                        unit=impact.unit.unit, description=impact.unit.description
                    ),
                    intensity=ImpactIntensityResponse(
                        intensity=impact.intensity.intensity
                    ),
                )
                if impact.specialized:
                    _climate_data = impact.specialized.climate_data

                    cur_impact.specialized = SpecializedImpacts(
                        climate=ClimateImpact(
                            temp_reduction=_climate_data.get("temp_reduction", None),
                            cool_spot=_climate_data.get("cool_spot", None),
                            evapotranspiration=_climate_data.get(
                                "evapotranspiration", None
                            ),
                            groundwater_recharge=_climate_data.get(
                                "groundwater_recharge", None
                            ),
                            storage_capacity=_climate_data.get(
                                "storage_capacity", None
                            ),
                        )
                    )
                all_impact_objs.append(cur_impact)
            _solutions.append(
                asdict(
                    from_dict(
                        data_class=NatureBasedSolutionResponse,
                        data={
                            "name": solution.name,
                            "definition": solution.definition,
                            "cobenefits": solution.cobenefits,
                            "specificdetails": solution.specificdetails,
                            "location": solution.location,
                            "geometry": solution.geometry,
                            "id": solution.id,
                            "styling": solution.styling,
                            "physical_properties": solution.physical_properties,
                            "measure_id": solution.measure_id,
                            "area": solution.area,
                            "length": solution.length,
                            "measure_type": solution.measure_type,
                            "impacts": [
                                asdict(impact_obj) for impact_obj in all_impact_objs
                            ],
                        },
                    )
                )   
            )
        _project = ProjectReadOutput(id =str(cur_project.id),
                                     name=cur_project.name,
                                     description=cur_project.description,
                                     settings = _project_settings,
                                     map = _map_settings,
                                     targets=_targets,
                                     solutions=_solutions,
                                     )

        all_projects.append(_project)





    return jsonify(asdict(all_projects))

@nbsapi_blueprint.route("/v2/api/solutions/solutions/<solution_id>", methods=["GET"])
def get_stored_solutions(solution_id: int):
    solutions = NatureBasedSolution.query.filter_by(id=solution_id).all()

    locations = TreeLocation.query.distinct(TreeLocation.location).all()

    all_solutions = []
    for location in locations:
        for solution in solutions:
            all_impacts = solution.impacts
            all_impact_objs = []
            for impact in all_impacts:

                cur_impact = EnhancedImpactBaseInput(
                    magnitude=impact.magnitude,
                    unit=ImpactUnitResponse(
                        unit=impact.unit.unit, description=impact.unit.description
                    ),
                    intensity=ImpactIntensityResponse(
                        intensity=impact.intensity.intensity
                    ),
                )
                if impact.specialized:
                    _climate_data = impact.specialized.climate_data

                    cur_impact.specialized = SpecializedImpacts(
                        climate=ClimateImpact(
                            temp_reduction=_climate_data.get("temp_reduction", None),
                            cool_spot=_climate_data.get("cool_spot", None),
                            evapotranspiration=_climate_data.get(
                                "evapotranspiration", None
                            ),
                            groundwater_recharge=_climate_data.get(
                                "groundwater_recharge", None
                            ),
                            storage_capacity=_climate_data.get(
                                "storage_capacity", None
                            ),
                        )
                    )
            # Convert WKB to GeoJSON FeatureCollection
            if location.geometry:
                geom = wkb.loads(bytes(location.geometry.data))

                geojson_feature = Feature(geometry=mapping(geom), properties={})
                location_geojson = FeatureCollection([geojson_feature])
                location_geojson = json.loads(geojson.dumps(location_geojson))
            else:
                location_geojson = None
            all_impact_objs.append(cur_impact)
            all_solutions.append(
                asdict(
                    from_dict(
                        data_class=NatureBasedSolutionResponse,
                        data={
                            "name": solution.name,
                            "definition": solution.definition,
                            "cobenefits": solution.cobenefits,
                            "specificdetails": solution.specificdetails,
                            "location": location.location,
                            "geometry": location_geojson,
                            "id": solution.id,
                            "styling": solution.styling,
                            "physical_properties": solution.physical_properties,
                            "measure_id": solution.measure_id,
                            "area": solution.area,
                            "length": solution.length,
                            "measure_type": solution.measure_type,
                            "impacts": [
                                asdict(impact_obj) for impact_obj in all_impact_objs
                            ],
                        },
                    )
                )
            )
    return jsonify(all_solutions)
