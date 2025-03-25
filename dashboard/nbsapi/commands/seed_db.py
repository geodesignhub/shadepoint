import json
from flask import Flask
import uuid
from dashboard.nbsapi.data_definitions import NatureBasedSolutionRead
from dashboard.extension import db
from dashboard.nbsapi.models.naturebasedsolution import (
    NatureBasedSolution,
    Association,
    TreeLocation,
)
from dashboard.nbsapi.models.adaptation_target import AdaptationTarget
from dashboard.nbsapi.models.impact import Impact
from dashboard.nbsapi.models.impact_intensity import ImpactIntensity
from dashboard.nbsapi.models.apiversion import ApiVersion
from dashboard.nbsapi.models.impact_unit import ImpactUnit
from geoalchemy2.shape import from_shape
from geojson import Point, FeatureCollection, Feature
from dashboard.nbsapi.data_definitions import NatureBasedSolutionRead
from dacite import from_dict
from shapely import Point as ShapelyPoint
import os


def register_cli(app: Flask):
    @app.cli.command(
        "initialize_db", help="Initialize the database with the fixture data"
    )
    def initialize_db():
        with app.app_context():
            fixture_file_path = os.path.join(
                os.path.dirname(__file__), "nbs_definitions.json"
            )

            apiversion = ApiVersion(version=1)
            db.session.add(apiversion)

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
                all_db_impact_targets =[]
                for impact in impacts:
                    _impact_intensity = impact.intensity.intensity
                    _impact_unit = impact.unit
                    impact = Impact(magnitude=impact.magnitude)
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

                solution_targets = nbs_data.solution_targets
                all_db_adapation_targets = []
                
                for solution_target in solution_targets:
                    adaptation_target = AdaptationTarget(
                        target=solution_target.adaptation.type
                    )

                    association = Association(tg=adaptation_target, value=solution_target.value)
                    
                    all_db_adapation_targets.append(association)
                    db.session.add(adaptation_target)
                    db.session.add(association)
                nature_based_solution = NatureBasedSolution(
                    name=nbs_data.name,
                    definition=nbs_data.definition,
                    cobenefits=nbs_data.cobenefits,      
                    specificdetails=nbs_data.specificdetails,  
                    
                    solution_targets=all_db_adapation_targets,            
                    impacts=all_db_impact_targets,
                )
                
                db.session.add(nature_based_solution)
                session_id = uuid.uuid4()
                for feature in nbs_data.geometry.features:
                    shapely_point = ShapelyPoint(feature.geometry.coordinates)
                    my_tree_location = from_shape(shapely_point)
                    tree_location = TreeLocation(
                        location=nbs_data.location, geometry=my_tree_location,
                        session_id=session_id
                    )
                    db.session.add(tree_location)

            db.session.commit()


if __name__ == "__main__":
    initialize_db()
