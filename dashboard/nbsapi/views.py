
from flask import jsonify
from dashboard.nbsapi.models.apiversion import ApiVersion
from flask import Blueprint
from dashboard import db
from dataclasses import asdict

from .data_definitions import APIVersionResponse as APV



nbsapi_blueprint = Blueprint('nbsapi', __name__)


@nbsapi_blueprint.route('/nbsapi/currentversion', methods=['GET'])
def get_apiversion():
    versions = ApiVersion.query.all()
    return jsonify([asdict(APV(version=version.version)) for version in versions])

