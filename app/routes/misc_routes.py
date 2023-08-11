from __future__ import annotations

from quart import Response, jsonify

from ..quart_app import app, ipc


@app.route("/")
async def index() -> Response:
    return jsonify({"status": "running"})


@app.route("/echo")
async def echo(msg: str) -> Response:
    return jsonify({"status": "running", "message": msg})


@app.route("/get/guilds")
async def get_guilds() -> Response:
    ipc_response = await ipc.request("guilds")
    if not ipc_response:
        return jsonify({"status": "error", "message": "No guilds found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore
