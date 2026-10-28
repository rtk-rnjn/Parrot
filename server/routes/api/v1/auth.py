from __future__ import annotations

import asyncio
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ....config import DISCORD_API_BASE, DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI

router = APIRouter(prefix="/auth")


@router.get("/login")
async def auth_login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
        "state": state,
        "prompt": "none",
    }
    return RedirectResponse(f"{DISCORD_API_BASE}/oauth2/authorize?{urlencode(params)}")


@router.get("/callback")
async def auth_callback(request: Request, code: str, state: str | None = None) -> RedirectResponse:
    expected_state = request.session.get("oauth_state")
    if expected_state and state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth2 state parameter")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            f"{DISCORD_API_BASE}/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange Discord OAuth2 code")
        tokens = token_resp.json()
        access_token = tokens["access_token"]

        auth_headers = {"Authorization": f"Bearer {access_token}"}
        user_resp, guilds_resp = await asyncio.gather(
            client.get(f"{DISCORD_API_BASE}/users/@me", headers=auth_headers),
            client.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=auth_headers),
        )
        user_resp.raise_for_status()
        guilds_resp.raise_for_status()

    request.session["user"] = user_resp.json()
    request.session["oauth_guilds"] = guilds_resp.json()
    return RedirectResponse("/")


@router.post("/logout")
async def auth_logout(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"ok": True})
