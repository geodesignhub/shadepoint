
from flask import jsonify
from dashboard.nbsapi.models.apiversion import ApiVersion
from flask import Blueprint
from dashboard import db

apiversion = ApiVersion()

nbsapi_blueprint = Blueprint('nbsapi', __name__)


@nbsapi_blueprint.route('/nbsapi/apiversion', methods=['GET'])
def get_apiversion():
    versions = db.session.execute(db.select(ApiVersion)).scalars()
    return jsonify(versions)
