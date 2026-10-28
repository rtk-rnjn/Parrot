from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ....app import app
from ....config import DISCORD_CLIENT_ID, IPC_REQUEST_CHANNEL, TELEMETRY_KEY
from ....utils import ipc_request

if TYPE_CHECKING:
    from redis.asyncio import Redis

router = APIRouter()


@router.get("/me")
async def api_me(request: Request) -> JSONResponse:
    user = request.session.get("user")
    oauth_guilds = request.session.get("oauth_guilds", [])
    if not user:
        return JSONResponse({"authenticated": False}, status_code=401)

    guild_ids = [str(g["id"]) for g in oauth_guilds]
    ipc_data = {}
    ipc_meta = {"ok": False, "channel": IPC_REQUEST_CHANNEL}

    try:
        reply = await ipc_request(
            "GET_MUTUAL_GUILDS",
            {"user_id": str(user["id"]), "guild_ids": guild_ids},
        )
        ipc_data = reply.get("data", {}).get("guilds", {})
        ipc_meta = {
            "ok": reply.get("ok", False),
            "corr_id": reply.get("corr_id"),
            "rtt_ms": reply.get("rtt_ms"),
            "channel": IPC_REQUEST_CHANNEL,
        }
    except Exception as exc:
        ipc_meta["error"] = str(exc)

    merged_guilds = []
    for g in oauth_guilds:
        gid = str(g["id"])
        perms = int(g.get("permissions", 0))
        can_manage = bool((perms & 0x20) or (perms & 0x8) or g.get("owner"))
        bot_info = ipc_data.get(gid, {"bot_present": False})
        merged_guilds.append(
            {
                "id": gid,
                "name": g["name"],
                "icon": g.get("icon"),
                "owner": bool(g.get("owner", False)),
                "permissions": perms,
                "can_manage": can_manage,
                "bot_present": bool(bot_info.get("bot_present", False)),
                "member_count": bot_info.get("member_count"),
                "text_channels": bot_info.get("text_channels"),
                "voice_channels": bot_info.get("voice_channels"),
                "roles_count": bot_info.get("roles_count"),
                "user_top_role": bot_info.get("user_top_role"),
                "active_cogs": bot_info.get("active_cogs", []),
            }
        )

    telemetry = None
    redis_client: Redis = app.state.redis_client
    raw_telemetry = await redis_client.get(TELEMETRY_KEY)
    if raw_telemetry:
        telemetry = json.loads(raw_telemetry)

    return JSONResponse(
        {
            "authenticated": True,
            "user": user,
            "guilds": merged_guilds,
            "ipc": ipc_meta,
            "telemetry": telemetry,
            "bot_invite_client_id": DISCORD_CLIENT_ID,
        }
    )
