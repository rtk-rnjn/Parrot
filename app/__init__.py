from __future__ import annotations

import os

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart

from discord.ext.ipc.client import Client

app = Quart(__name__)
ipc = Client(secret_key=os.environ["IPC_KEY"], standard_port=1730)

__all__ = ("runner", "ipc", "app")

@app.route("/")
async def main():
    return {"message": "Hello World!"}


config = Config()
config.bind = ["0.0.0.0:5000"]


def runner():
    return serve(app, config)
