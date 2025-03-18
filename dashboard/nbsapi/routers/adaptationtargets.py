from typing import List
from flask import Blueprint, request, jsonify
from nbsapi.api.dependencies.auth import validate_is_authenticated
from nbsapi.api.dependencies.core import get_db_session
from nbsapi.crud.adaptationtarget import create_target, get_targets
from nbsapi.schemas.adaptationtarget import TargetBase

router = Blueprint('adaptation_targets', __name__, url_prefix='/api/adaptation_targets')

@router.route('/adaptation_target', methods=['GET'])
def read_targets():
    """Retrieve all available adaptation targets"""
    db_session = get_db_session()
    targets = get_targets(db_session)
    return jsonify([target.dict() for target in targets])

@router.route('/adaptation_target', methods=['POST'])
def write_target():
    """Create a new adaptation target"""
    validate_is_authenticated()
    db_session = get_db_session()
    itarget = TargetBase(**request.json)
    wtarget = create_target(db_session, itarget=itarget)
    return jsonify(wtarget.dict())
