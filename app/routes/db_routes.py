from __future__ import annotations

from quart import Response, jsonify, request

from ..quart_app import app, ipc


@app.route("/db/mongo/find_one", methods=["POST", "GET"])
async def db_find_one() -> Response:
    if request.method == "GET":
        return jsonify({"status": "error", "message": "GET not allowed"})

    data = await request.get_json()
    ipc_response = await ipc.request("db_exec_find_one", **data)
    return jsonify({"status": "success", **ipc_response.response})


@app.route("/db/mongo/update_one", methods=["POST", "GET"])
async def db_update_one() -> Response:
    if request.method == "GET":
        return jsonify({"status": "error", "message": "GET not allowed"})

    data = await request.get_json()
    ipc_response = await ipc.request("db_exec_update_one", **data)
    return jsonify({"status": "success", **ipc_response.response})


@app.route("/db/sql/execute/<query>")
async def db_sql_execute(query: str) -> Response:
    ipc_response = await ipc.request("sql_execute", query=query)
    return jsonify({"status": "success", **ipc_response.response})
