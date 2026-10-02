from fastapi import APIRouter

from backend.app.services.disk import get_disks

router = APIRouter()


@router.get("/disk")
def disks():
    return get_disks()
