import json
import uuid
import os

from flask import Flask
from geoalchemy2.shape import from_shape
from shapely.geometry import shape as shapely_shape
from shapely import Point as ShapelyPoint

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
from dashboard.nbsapi.models.measure_type import MeasureType


def register_cli(app: Flask):
    @app.cli.command(
        "initialize_db", help="Initialize the database with the fixture data"
    )
    def initialize_db():
        with app.app_context():
            fixture_file_path = os.path.join(
                os.path.dirname(__file__), "nbs_definitions.json"
            )

            apiversion = ApiVersion(version=2)
            db.session.add(apiversion)

            with open(fixture_file_path, "r", encoding="utf-8") as f:
                fixture = json.load(f)

            for mt in fixture.get("measure_types", []):
                measure_type = MeasureType(
                    id=mt["id"],
                    name=mt["name"],
                    description=mt.get("description"),
                    default_color=mt.get("default_color"),
                    default_inflow=mt.get("default_inflow"),
                    default_depth=mt.get("default_depth"),
                    default_width=mt.get("default_width"),
                    default_radius=mt.get("default_radius"),
                )
                db.session.add(measure_type)

            db.session.flush()

            for nbs in fixture.get("solutions", []):
                all_db_impacts = []
                for impact_data in nbs.get("impacts", []):
                    impact = Impact(magnitude=impact_data["magnitude"])
                    impact_intensity = ImpactIntensity(
                        intensity=impact_data["intensity"]["intensity"],
                        impacts=[impact],
                    )
                    impact_unit = ImpactUnit(
                        unit=impact_data["unit"]["unit"],
                        description=impact_data["unit"]["description"],
                        impacts=[impact],
                    )
                    db.session.add(impact)
                    db.session.add(impact_intensity)
                    db.session.add(impact_unit)
                    all_db_impacts.append(impact)

                all_db_associations = []
                for target_data in nbs.get("solution_targets", []):
                    adaptation_target = AdaptationTarget(
                        target=target_data["adaptation"]["type"]
                    )
                    association = Association(
                        tg=adaptation_target, value=target_data["value"]
                    )
                    all_db_associations.append(association)
                    db.session.add(adaptation_target)
                    db.session.add(association)

                nbs_geometry = None
                if nbs.get("geometry"):
                    nbs_geometry = from_shape(
                        shapely_shape(nbs["geometry"]), srid=4326
                    )

                nature_based_solution = NatureBasedSolution(
                    name=nbs["name"],
                    definition=nbs["definition"],
                    cobenefits=nbs["cobenefits"],
                    specificdetails=nbs["specificdetails"],
                    geometry=nbs_geometry,
                    measure_id=nbs.get("measure_id"),
                    styling=nbs.get("styling"),
                    physical_properties=nbs.get("physical_properties"),
                    solution_targets=all_db_associations,
                    impacts=all_db_impacts,
                )
                db.session.add(nature_based_solution)

                session_id = uuid.uuid4()
                for coords in nbs.get("tree_locations", []):
                    shapely_point = ShapelyPoint(coords)
                    tree_location = TreeLocation(
                        location=nbs.get("location", ""),
                        geometry=from_shape(shapely_point, srid=4326),
                        session_id=session_id,
                    )
                    db.session.add(tree_location)

            db.session.commit()


if __name__ == "__main__":
    initialize_db()
