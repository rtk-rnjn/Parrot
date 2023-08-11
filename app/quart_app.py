from __future__ import annotations

from os import environ

from discord.ext.ipc.client import Client
from quart import Quart

from core.Parrot import IPC_PORT

IPC_SECRET_KEY = environ.get("IPC_KEY")

app = Quart("discord_bot_ipc_api")
ipc = Client(standard_port=IPC_PORT, secret_key=IPC_SECRET_KEY)


from . import routes  # noqa: E402, F401
