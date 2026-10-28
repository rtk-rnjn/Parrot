from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis.asyncio import Redis
from starlette.middleware.sessions import SessionMiddleware

from .config import SESSION_SECRET

__all__ = ("app",)

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Bot")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=86400 * 7)
app.state.redis_client = Redis()

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.filters["commas"] = lambda n: f"{n:,}" if isinstance(n, int) else "-"


from .routes import router  # noqa: E402

app.include_router(router)
