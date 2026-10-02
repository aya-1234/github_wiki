from fastapi import APIRouter

from backend.app.services.system import get_system

router = APIRouter()


@router.get("/system")
def system():
    return get_system()
