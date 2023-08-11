from __future__ import annotations

from ..quart_app import app, ipc

from quart import Response, jsonify


@app.route("/get/messages/<channel>/<message>")
async def messages(channel: str, message: str) -> Response:
    try:
        channel = int(channel)  # type: ignore
        message = int(message)  # type: ignore
    except ValueError:
        return jsonify({"status": "error", "message": "Channel or message not found"})

    ipc_response = await ipc.request("messages", channel_id=channel, message_id=message)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Channel or message not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore
