from __future__ import annotations

from quart import Response, jsonify, request

from ..quart_app import app, ipc


@app.route("/")
async def index() -> Response:
    return jsonify({"status": "running"})


@app.route("/echo/<msg>", methods=["GET", "POST"])
async def echo(msg: str) -> Response:
    get_raw_data = dict(request.args)
    return jsonify({"status": "running", "message": msg, "GET": get_raw_data, "POST": await request.get_json()})


@app.route("/get/guilds")
async def get_guilds() -> Response:
    ipc_response = await ipc.request("guilds")
    if not ipc_response:
        return jsonify({"status": "error", "message": "No guilds found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/routes")
async def routes() -> Response:
    rules = app.url_map.iter_rules()
    ls = [{"methods": rule.methods, "path": str(rule)} for rule in rules]
    return jsonify({"status": "success", "routes": ls})
