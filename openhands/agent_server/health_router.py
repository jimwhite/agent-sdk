import time

from fastapi import APIRouter
from pydantic import BaseModel


health_router = APIRouter(prefix="/")
_start_time = time.time()
_last_execution_time = time.time()


class ServerInfo(BaseModel):
    uptime: float
    idle_time: float


@health_router.get("/alive")
async def alive():
    return {"status": "ok"}


@health_router.get("/health")
async def health() -> str:
    return "OK"


@health_router.get("/server_info")
async def get_server_info() -> ServerInfo:
    return ServerInfo(
        uptime=time.time() - _start_time,
        idle_time=_last_execution_time - _start_time,
    )
