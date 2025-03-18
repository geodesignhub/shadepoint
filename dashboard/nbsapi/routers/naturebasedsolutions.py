# from nbsapi.api.dependencies.auth import validate_is_authenticated
from nbsapi.api.dependencies.core import DBSessionDep
from nbsapi.crud.naturebasedsolution import (
    create_nature_based_solution,
    get_filtered_solutions,
    get_solution,
)
from nbsapi.schemas.adaptationtarget import AdaptationTargetRead
from nbsapi.schemas.impact import ImpactIntensity
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from nbsapi.schemas.naturebasedsolution import (
    NatureBasedSolutionCreate,
    NatureBasedSolutionRead,
)
router = Blueprint('solutions', __name__, url_prefix='/api/solutions')

@router.route('/solutions/<int:solution_id>', methods=['GET'])
def read_nature_based_solution(solution_id):
    """Retrieve a nature-based solution using its ID"""
    db_session = DBSessionDep()
    solution = get_solution(db_session, solution_id)
    return jsonify(solution)

@router.route('/solutions', methods=['POST'])
def get_solutions():
    """
    Return a list of nature-based solutions using _optional_ filter criteria:
    """
    db_session = DBSessionDep()
    request_body = request.get_json()
    targets = request_body.get('targets') if request_body else None
    bbox = request_body.get('bbox') if request_body else None
    intensities = request_body.get('intensities') if request_body else None
    solutions = get_filtered_solutions(db_session, targets, bbox, intensities)
    return jsonify(solutions)

@router.route('/add_solution/', methods=['POST'])
@jwt_required()
def write_nature_based_solution():
    """
    Add a nature-based solution. The payload must be a `NatureBasedSolutionRead` object.
    Its `adaptations` array must contain one or more valid `AdaptationTargetRead` objects
    """
    db_session = DBSessionDep()
    solution_data = request.get_json()
    solution = NatureBasedSolutionCreate(**solution_data)
    solution = create_nature_based_solution(db_session, solution)
    return jsonify(solution)