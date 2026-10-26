from fastapi import APIRouter
from fastapi import APIRouter, HTTPException

from backend.app.services.users import get_user
from backend.app.services.users import get_users


router = APIRouter()


@router.get("/users")
def users():
    return get_users()

@router.get("/users/{username}")
def user(username: str):
    result = get_user(username)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"User '{username}' not found",
        )

    return result
