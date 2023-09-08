from __future__ import annotations

from datetime import timedelta
from os import environ

from discord.ext.ipc.client import Client
from quart import Quart
from quart_rate_limiter import RateLimit, RateLimiter

from core.Parrot import IPC_PORT

IPC_SECRET_KEY = environ.get("IPC_KEY")

app = Quart("discord_bot_ipc_api")
rate_limiter = RateLimiter(default_limits=[RateLimit(10, timedelta(seconds=1))])
rate_limiter.init_app(app)

ipc = Client(standard_port=IPC_PORT, secret_key=IPC_SECRET_KEY)


from . import routes  # noqa: E402, F401
