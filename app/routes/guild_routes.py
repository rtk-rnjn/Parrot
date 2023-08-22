from __future__ import annotations

from quart import Response, jsonify

from ..quart_app import app, ipc


@app.route("/get/guilds/<guild>")
async def get_guild(guild: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/channels")
async def get_guild_channels(guild: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    kw["channels"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/channels/<channel>")
async def get_guild_channel(guild: str, channel: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    try:
        channel = int(channel)  # type: ignore
        kw["channel_id"] = channel
    except ValueError:
        return jsonify({"status": "error", "message": "Channel not found"})

    kw["channels"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild or channel not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/roles")
async def get_guild_roles(guild: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    kw["roles"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/roles/<role>")
async def get_guild_role(guild: str, role: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    try:
        role = int(role)  # type: ignore
        kw["role_id"] = role
    except ValueError:
        return jsonify({"status": "error", "message": "Role not found"})

    kw["roles"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild or role not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/members")
async def get_guild_members(guild: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    kw["members"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/members/<member>")
async def get_guild_member(guild: str, member: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    try:
        member = int(member)  # type: ignore
        kw["member_id"] = member
    except ValueError:
        return jsonify({"status": "error", "message": "Member not found"})

    kw["members"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild or member not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/emojis")
async def get_guild_emojis(guild: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    kw["emojis"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/emojis/<emoji>")
async def get_guild_emoji(guild: str, emoji: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    try:
        emoji = int(emoji)  # type: ignore
        kw["emoji_id"] = emoji
    except ValueError:
        return jsonify({"status": "error", "message": "Emoji not found"})

    kw["emojis"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild or emoji not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/threads")
async def get_guild_threads(guild: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    kw["threads"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/threads/<thread>")
async def get_guild_thread(guild: str, thread: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    try:
        thread = int(thread)  # type: ignore
        kw["thread_id"] = thread
    except ValueError:
        return jsonify({"status": "error", "message": "Thread not found"})

    kw["threads"] = True
    ipc_response = await ipc.request("guilds", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild or thread not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/exists")
async def guild_exists(guild: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild
    ipc_response = await ipc.request("guild_exists", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore


@app.route("/get/guilds/<guild>/config")
async def get_guild_config(guild: str) -> Response:
    kw = {}
    if guild.isdigit():
        kw["id"] = int(guild)
    else:
        kw["name"] = guild

    ipc_response = await ipc.request("guild_config", **kw)
    if not ipc_response:
        return jsonify({"status": "error", "message": "Guild not found"})
    return jsonify({"status": "success", **ipc_response.response})  # type: ignore
