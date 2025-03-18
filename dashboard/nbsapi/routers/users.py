from fastapi import APIRouter, Depends

from nbsapi.api.dependencies.auth import validate_is_authenticated
from nbsapi.api.dependencies.core import DBSessionDep
from nbsapi.crud.user import get_user, make_user
from nbsapi.schemas.user import User, UserWrite

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/{user_id}",
    response_model=User,
    dependencies=[Depends(validate_is_authenticated)],
)
async def user_details(
    user_id: int,
    db_session: DBSessionDep,
):
    """
    Get any user details
    """
    user = await get_user(db_session, user_id)
    return user


@router.post(
    "/user",
    response_model=User,
)
async def write_user(db_session: DBSessionDep, user: UserWrite):
    """Create a new user"""
    new_user = await make_user(db_session, newuser=user)
    return new_user
