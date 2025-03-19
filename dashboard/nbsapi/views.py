from flask import jsonify
from dashboard.nbsapi.models.apiversion import ApiVersion
from dashboard.nbsapi.models.impact_intensity import ImpactIntensity
from dashboard.nbsapi.models.impact import Impact
from dashboard.nbsapi.models.impact_unit import ImpactUnit
from dashboard.nbsapi.models.adaptation_target import AdaptationTarget
from dashboard.nbsapi.models.naturebasedsolution import TreeLocation

from flask import Blueprint
from dashboard import db
from dataclasses import asdict
from dacite import from_dict

from .data_definitions import APIVersion as ApiVersionResponse
from .data_definitions import Contact
from .data_definitions import ImpactIntensity as ImpactIntensityResponse
from .data_definitions import ImpactUnit as ImpactUnitResponse
from .data_definitions import AdaptationTargetRead as AdaptationTargetResponse
from .data_definitions import NatureBasedSolution as NatureBasedSolutionResponse
from .data_definitions import AdaptationTargetRead
from flask import request


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


@nbsapi_blueprint.route("/v1/api/impacts/impact_intensities/", methods=["GET"])
def get_impacts_intensities():
    impact_intentities = ImpactIntensity.query.all()
    return jsonify(
        [
            asdict(ImpactIntensityResponse(intensity=impact_intensity.intensity))
            for impact_intensity in impact_intentities
        ]
    )


@nbsapi_blueprint.route("/v1/api/impacts/impact_units/", methods=["GET"])
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


@nbsapi_blueprint.route("/v1/adaptation_targets/adaptation_target", methods=["GET"])
def get_adaptation_targets():
    adaptation_targets = AdaptationTarget.query.all()
    all_adapatation_targets = []
    for adaptation_target in adaptation_targets:
        all_adapatation_targets.append(
            asdict(
                from_dict(
                    data_class=AdaptationTargetResponse,
                    data={
                        "adaptation": adaptation_target.adaptation,
                        "value": adaptation_target.value,
                    },
                )
            )
        )
    return jsonify(all_adapatation_targets)


@nbsapi_blueprint.route("/v1/solutions/solutions/<solution_id>", methods=["GET"])
def get_stored_solutions(solution_id: int):
    solutions = NatureBasedSolution.query.filter_by(id=solution_id).all()
    locations = TreeLocation.query.distinct(TreeLocation.location).all()

    all_solutions = []
    for location in locations:
        for solution in solutions:
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
                        },
                    )
                )
            )
    return jsonify(all_solutions)


@nbsapi_blueprint.route("/v1/solutions/solutions", methods=["POST"])
def get_tree_locations():
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
        try:
            adaptation_target = from_dict(
                data_class=AdaptationTargetRead, data=adaptation_target
            )
        except:
            return jsonify({"error": "Invalid adaptation target"}), 400

    if adaptation_target:
        solutions = NatureBasedSolution.query.filter(
            NatureBasedSolution.solution_targets.any(
                adaptation=adaptation_target.adaptation,
                value=adaptation_target.value,
            )
        ).all()

    all_solutions = []
    for location in locations:
        for solution in solutions:
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
                        },
                    )
                )
            )
    return jsonify(all_solutions)
