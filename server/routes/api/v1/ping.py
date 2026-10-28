from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ....utils import ipc_request

router = APIRouter()


@router.post("/ipc/ping")
async def api_ipc_ping() -> JSONResponse:
    reply = await ipc_request("PING", {})
    return JSONResponse(reply)
