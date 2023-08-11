from __future__ import annotations

from quart import Response, jsonify

from ..quart_app import app, ipc


@app.route("/get/users")
async def get_users() -> Response:
    ipc_response = await ipc.request("users")
    if not ipc_response:
        return jsonify({"status": "error", "message": "No users found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/users/<user>")
async def get_user(user: str) -> Response:
    kw = {}
    if user.isdigit():
        kw["id"] = int(user)
    else:
        kw["name"] = user
    ipc_response = await ipc.request("users", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "User not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore
