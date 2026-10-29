from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ....utils import ipc_request

router = APIRouter()


async def _read_ipc(op: str) -> dict[str, Any]:
    try:
        reply = await ipc_request(op, {})
    except Exception:
        return {"ok": False, "error": "Bot IPC is unavailable"}
    if not reply.get("ok"):
        return {"ok": False, "error": "Bot IPC request failed"}
    return {"ok": True, **reply.get("data", {})}


@router.get("/info")
async def api_public_info() -> JSONResponse:
    """Public, read-only snapshot used by the Parrot information page."""
    telemetry, commands, cogs = await asyncio.gather(
        _read_ipc("GET_TELEMETRY"),
        _read_ipc("GET_COMMANDS"),
        _read_ipc("GET_COGS"),
    )
    return JSONResponse(
        {
            "bot": {
                "connected": telemetry.get("ok", False),
                "telemetry": {key: value for key, value in telemetry.items() if key != "ok"},
            },
            "commands": {
                "ok": commands.get("ok", False),
                "prefix": commands.get("prefix", []),
                "slash": commands.get("slash", []),
                "default_prefix": commands.get("default_prefix", "$"),
                "error": commands.get("error"),
            },
            "cogs": cogs.get("cogs", []),
            "extensions": cogs.get("extensions", []),
            "ipc": {
                "connected": all((telemetry.get("ok"), commands.get("ok"), cogs.get("ok"))),
                "error": next((result["error"] for result in (telemetry, commands, cogs) if result.get("error")), None),
            },
        }
    )
