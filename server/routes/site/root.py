from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...app import templates

root_router = APIRouter()


@root_router.get("/", response_class=HTMLResponse)
@root_router.get("/index.html", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")
