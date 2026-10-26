from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.disk import router as disk_router
from backend.app.api.network import router as network_router
from backend.app.api.processes import router as processes_router
from backend.app.api.services import router as services_router
from backend.app.api.system import router as system_router
from backend.app.api.users import router as users_router


app = FastAPI(title="Unicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(processes_router)
app.include_router(services_router)
app.include_router(network_router)
app.include_router(disk_router)
app.include_router(users_router)
app.include_router(network_router)
