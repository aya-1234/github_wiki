from fastapi import APIRouter
from fastapi import APIRouter, HTTPException

from backend.app.services.services import get_services
from backend.app.services.services import get_service


router = APIRouter()


@router.get("/services")
def services():
    return get_services()


@router.get("/services/{name}")
def service(name: str):
    result = get_service(name)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{name}' not found",
        )

    return result
