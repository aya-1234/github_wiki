from fastapi import APIRouter

from backend.app.services.network import get_connections

router = APIRouter(
    prefix="/network",
    tags=["network"],
)

@router.get("/connections")
def connections():
    return get_connections()
