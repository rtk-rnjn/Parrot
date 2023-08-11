from __future__ import annotations

from quart import Response, jsonify, request

from ..quart_app import app, ipc


@app.route("/db/find_one", methods=["POST", "GET"])
async def db_find_one() -> Response:
    if request.method == "GET":
        return jsonify({"status": "error", "message": "GET not allowed"})

    data = await request.get_json()
    ipc_response = await ipc.request("db_exec_find_one", **data)
    return jsonify(ipc_response)


@app.route("/db/update_one", methods=["POST", "GET"])
async def db_update_one() -> Response:
    if request.method == "GET":
        return jsonify({"status": "error", "message": "GET not allowed"})

    data = await request.get_json()
    ipc_response = await ipc.request("db_exec_update_one", **data)
    return jsonify(ipc_response)
