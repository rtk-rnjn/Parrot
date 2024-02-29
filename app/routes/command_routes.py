from __future__ import annotations

from quart import Response, jsonify

from ..quart_app import app, ipc


@app.route("/get/commands")
async def get_commands() -> Response:
    ipc_response = await ipc.request("commands")
    if not ipc_response:
        return jsonify({"status": "error", "message": "No commands found"})
    return jsonify({"status": "success", **ipc_response.response})


@app.route("/get/commands/<command>")
async def get_command(command: str) -> Response:
    ipc_response = await ipc.request("commands", name=command)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Command not found"})
    return jsonify({"status": "success", **ipc_response.response})


@app.route("/get/commands/cog/<cog>")
async def get_commands_cog(cog: str) -> Response:
    ipc_response = await ipc.request("commands", cog=cog)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Cog not found"})
    return jsonify({"status": "success", **ipc_response.response})
