from __future__ import annotations

from hypercorn.asyncio import serve
from hypercorn.config import Config

from .quart_app import app

config = Config()
config.bind = ["0.0.0.0:5000"]
config.loglevel = "INFO"
config.accesslog = "-"
config.errorlog = "-"
config.use_reloader = True


def runner():
    return serve(app, config)
