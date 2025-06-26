import json
from flask import Flask
import uuid
from dashboard.nbsapi.data_definitions import (
    ProjectSettings,
    BasicProjectDetail,
    MapSettings,
    ClimateTargets,
    CostTargets,
    WaterQualityTargets,
    ProjectTargetsOutput,
    EnhancedImpactBaseInput,
    ClimateImpact,
    MeasureTypeCreate,
)
from dashboard.nbsapi.data_definitions import TargetValue as TargetValueDataDefinition
from dashboard.extension import db
from dashboard.nbsapi.models.naturebasedsolution import (
    NatureBasedSolution,
    TreeLocation,
)
from dashboard.nbsapi.models.impact import Impact
from dashboard.nbsapi.models.impact_intensity import ImpactIntensity
from dashboard.nbsapi.models.specialized_impact import SpecializedImpact
from dashboard.nbsapi.models.measure_type import MeasureType
from dashboard.nbsapi.models.apiversion import ApiVersion
from dashboard.nbsapi.models.impact_unit import ImpactUnit
from dashboard.nbsapi.models.project import Project, TargetValue
from geoalchemy2.shape import from_shape
from geojson import Point, FeatureCollection, Feature
from dashboard.nbsapi.data_definitions import (
    NatureBasedSolutionReadInput as NatureBasedSolutionRead,
)
from dacite import from_dict
from shapely import Point as ShapelyPoint
import os
from dataclasses import asdict


def register_cli(app: Flask):
    @app.cli.command(
        "initialize_db", help="Initialize the database with the fixture data"
    )
    def initialize_db():
        with app.app_context():
            apiversion = ApiVersion(version=2)
            db.session.add(apiversion)
            fixture_file_path = os.path.join(
                os.path.dirname(__file__), "nbs_definitions.json"
            )
            with open(fixture_file_path, "r", encoding="utf-8") as f:
                all_nbs = json.load(f)

            for nbs in all_nbs:
                _all_features = []
                tree_geometry = nbs["geometry"]
                for _point_feature in tree_geometry["features"]:
                    _point_geometry = Point(
                        coordinates=_point_feature["geometry"]["coordinates"]
                    )
                    _feature = Feature(
                        geometry=_point_geometry,
                        properties=_point_feature["properties"],
                    )

                    _all_features.append(_feature)

                _diagram_feature_collection = FeatureCollection(features=_all_features)

                nbs["geometry"] = _diagram_feature_collection

                nbs_data = from_dict(data_class=NatureBasedSolutionRead, data=nbs)

                impacts = nbs_data.impacts

                all_db_impact_targets = []
                for _impact in impacts:
                    _impact_intensity = _impact.intensity.intensity
                    impact = Impact(magnitude=_impact.magnitude)
                    print(_impact.specialized)
                    _speciaized_climate_impact_db = SpecializedImpact(
                        impact=impact, climate_data=asdict(_impact.specialized.climate)
                    )

                    db.session.add(_speciaized_climate_impact_db)
                    impact.specialized = _speciaized_climate_impact_db
                    _impact_unit = _impact.unit

                    impact_intensity = ImpactIntensity(
                        intensity=_impact_intensity, impacts=[impact]
                    )

                    impact_unit = ImpactUnit(
                        unit=_impact_unit.unit,
                        description=_impact_unit.description,
                        impacts=[impact],
                    )

                    db.session.add(impact)
                    db.session.add(impact_intensity)

                    db.session.add(impact_unit)
                    all_db_impact_targets.append(impact)

                nature_based_solution = NatureBasedSolution(
                    name=nbs_data.name,
                    definition=nbs_data.definition,
                    cobenefits=nbs_data.cobenefits,
                    specificdetails=nbs_data.specificdetails,
                    impacts=all_db_impact_targets,
                    location=nbs_data.location,
                )

                db.session.add(nature_based_solution)
                session_id = uuid.uuid4()
                for feature in nbs_data.geometry.features:
                    shapely_point = ShapelyPoint(feature.geometry.coordinates)
                    my_tree_location = from_shape(shapely_point)
                    tree_location = TreeLocation(
                        location=nbs_data.location,
                        geometry=my_tree_location,
                        session_id=session_id,
                    )
                    db.session.add(tree_location)

            mesaure_type_fixture_path = os.path.join(
                os.path.dirname(__file__), "measure_type_definitions.json"
            )

            with open(mesaure_type_fixture_path, "r", encoding="utf-8") as f:
                measure_types = json.load(f)

            for measure_type in measure_types:
                _measure_type = from_dict(
                    data_class=MeasureTypeCreate, data=measure_type
                )
                measure_type_db = MeasureType(
                    id=str(uuid.uuid4()),
                    name=_measure_type.name,
                    description=_measure_type.description,
                    default_color= _measure_type.default_color,
                    default_inflow= _measure_type.default_inflow,
                    default_depth= _measure_type.default_depth,
                    default_width= _measure_type.default_width,
                    default_radius= _measure_type.default_radius,
                )
                db.session.add(measure_type_db)

            project_fixture_path = os.path.join(
                os.path.dirname(__file__), "project_definitions.json"
            )

            with open(project_fixture_path, "r", encoding="utf-8") as f:
                project_details = json.load(f)

            for project_detail in project_details:
                _project_settings = from_dict(
                    data_class=ProjectSettings, data=project_detail["settings"]
                )
                _basic_project_detail = from_dict(
                    data_class=BasicProjectDetail, data=project_detail
                )
                _map_settings = from_dict(
                    data_class=MapSettings, data=project_detail["map"]
                )
                _project_targets = []
                for climate_key in project_detail["targets"]["climate"]:
                    _climate_key_details = project_detail["targets"]["climate"][
                        climate_key
                    ]

                    _climate_target_value = TargetValueDataDefinition(
                        value=_climate_key_details["value"],
                        include=_climate_key_details["include"],
                        _type=climate_key,
                    )

                    _climate_target_value_db = TargetValue(
                        id=str(uuid.uuid4()),
                        value=_climate_target_value.value,
                        include=_climate_target_value.include,
                        type=_climate_target_value._type,
                    )
                    _project_targets.append(_climate_target_value_db)

                    db.session.add(_climate_target_value_db)

                for cost_key in project_detail["targets"]["cost"]:
                    _cost_key_details = project_detail["targets"]["cost"][cost_key]

                    _cost_target_value = TargetValueDataDefinition(
                        value=_cost_key_details["value"],
                        include=_cost_key_details["include"],
                        _type=cost_key,
                    )

                    _cost_target_value_db = TargetValue(
                        id=str(uuid.uuid4()),
                        value=_cost_target_value.value,
                        include=_cost_target_value.include,
                        type=_cost_target_value._type,
                    )
                    _project_targets.append(_cost_target_value_db)

                    db.session.add(_cost_target_value_db)

                for water_quaility_key in project_detail["targets"]["water_quality"]:
                    _water_quaility_key_details = project_detail["targets"][
                        "water_quality"
                    ][water_quaility_key]

                    _water_quality_target_value = TargetValueDataDefinition(
                        value=_water_quaility_key_details["value"],
                        include=_water_quaility_key_details["include"],
                        _type=water_quaility_key,
                    )

                    _water_quality_target_value_db = TargetValue(
                        id=str(uuid.uuid4()),
                        value=_water_quality_target_value.value,
                        include=_water_quality_target_value.include,
                        type=_water_quality_target_value._type,
                    )
                    _project_targets.append(_water_quality_target_value_db)

                    db.session.add(_water_quality_target_value_db)

                project = Project(
                    id=str(uuid.uuid4()),
                    title=_basic_project_detail.title,
                    description=_basic_project_detail.description,
                    settings=asdict(_project_settings),
                    map_settings=asdict(_map_settings),
                    targets=_project_targets,
                )
                db.session.add(project)

            db.session.commit()


if __name__ == "__main__":
    initialize_db()
