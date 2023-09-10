from __future__ import annotations

import random
from typing import Any

import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException

from .functions import find_all, find_one, get_batting, get_bowling, parse_url
from .random_agents import AGENTS

app = FastAPI()


@app.get("/")
async def root():
    return {"success": True}


@app.get("/cricket_api")
async def cricket_api(url: str | None = None) -> dict[str, Any] | None:
    return await _cricket_api(url)


async def _cricket_api(url: str | None = None) -> dict[str, Any] | None:
    if not url:
        raise HTTPException(status_code=400, detail="URL not provided")

    if not url.startswith("https://m.cricbuzz.com/cricket-commentary/"):
        raise HTTPException(status_code=400, detail="Invalid URL")

    async with aiohttp.ClientSession() as session:
        response = await session.get(url, headers={"User-Agent": random.choice(AGENTS)})
        if response.status != 200:
            raise HTTPException(status_code=400, detail=f"Invalid URL - Status Code: {response.status}")

        html = await response.text()

    soup = await parse_url(html)

    return {
        "success": True,
        "title": await find_one(soup, "h4", **{"class": "cb-list-item"}),
        "status": await find_one(soup, "div", **{"class": "cbz-ui-status"}),
        "team_one": await find_one(soup, "span", **{"class": "ui-bowl-team-scores"}),
        "team_two": await find_one(soup, "span", **{"class": "ui-bat-team-scores"}),
        "crr": await find_all(soup, "span", **{"class": "crr"}),
        "extra": list(
            zip(
                await find_all(soup, "span", **{"style": "color:#777;"}),
                await find_all(soup, "span", **{"style": "color:#333"}),
            ),
        ),
        "commentry": await find_all(soup, "p", **{"class": "commtext"}),
        "batting": await get_batting(soup),
        "bowling": await get_bowling(soup),
    }


def runner() -> None:
    uvicorn.run(app, port=1729)
