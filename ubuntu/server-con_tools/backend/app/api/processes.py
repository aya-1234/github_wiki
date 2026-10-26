from fastapi import APIRouter, HTTPException

from backend.app.services.processes import get_process
from backend.app.services.processes import get_process_children
from backend.app.services.processes import get_processes
from backend.app.services.processes import get_process_tree
from backend.app.services.processes import terminate_process

router = APIRouter()


@router.get("/processes")
def processes():
    return get_processes()

@router.get("/processes/{pid}")
def process(pid: int):
    result = get_process(pid)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Process {pid} not found",
        )

    return result


@router.get("/processes/{pid}/children")
def process_children(pid: int):
    result = get_process_children(pid)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Process {pid} not found",
        )

    return result

@router.get("/processes/tree")
def process_tree():
    return get_process_tree()

@router.post("/processes/{pid}/terminate")
def terminate(pid: int):
    try:
        result = terminate_process(pid)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Process {pid} not found",
            )

        return result

    except PermissionError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        )
