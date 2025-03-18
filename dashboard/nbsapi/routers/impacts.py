from flask import Blueprint, request, jsonify
from functools import wraps

from nbsapi.api.dependencies.auth import validate_is_authenticated
from nbsapi.api.dependencies.core import get_db_session
from nbsapi.crud.impact import (
    create_impact_intensity,
    create_impact_unit,
    get_impact_intensities,
    get_impact_units,
    get_impacts,
)
from nbsapi.schemas.impact import ImpactBase, ImpactIntensity, ImpactUnit

impacts_bp = Blueprint('impacts', __name__, url_prefix='/api/impacts')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_is_authenticated():
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

@impacts_bp.route('/impacts', methods=['GET'])
def read_impacts():
    """Retrieve all available adaptation impacts"""
    db_session = get_db_session()
    targets = get_impacts(db_session)
    return jsonify([target.to_dict() for target in targets])

@impacts_bp.route('/impact_intensities', methods=['GET'])
def read_impact_intensity():
    """Retrieve all available adaptation impact intensities"""
    db_session = get_db_session()
    targets = get_impact_intensities(db_session)
    return jsonify([target.to_dict() for target in targets])

@impacts_bp.route('/impact_intensities', methods=['POST'])
@login_required
def write_impact_intensity():
    """Create a new impact intensity measure"""
    db_session = get_db_session()
    intensity_data = request.get_json()
    intensity = ImpactIntensity(**intensity_data)
    target = create_impact_intensity(db_session, intensity)
    return jsonify(target.to_dict())

@impacts_bp.route('/impact_units', methods=['GET'])
def read_impact_unit():
    """Retrieve all available adaptation impact units"""
    db_session = get_db_session()
    targets = get_impact_units(db_session)
    return jsonify([target.to_dict() for target in targets])

@impacts_bp.route('/impact_units', methods=['POST'])
@login_required
def write_impact_unit():
    """Create a new impact intensity unit"""
    db_session = get_db_session()
    unit_data = request.get_json()
    unit = ImpactUnit(**unit_data)
    target = create_impact_unit(db_session, unit)
    return jsonify(target.to_dict())
