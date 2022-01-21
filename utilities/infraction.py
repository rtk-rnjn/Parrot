from __future__ import annotations
import discord

from typing import Optional, Union

from datetime import datetime
from tabulate import tabulate

from utilities.database import warn_db, parrot_db

collection_config = parrot_db["server_config"]


async def get_warn_count(guild: discord.Guild) -> Optional[int]:
    if data := await collection_config.find_one(
        {"_id": guild.id, "warn_count": {"exists": True}}
    ):
        return data["warn_count"]
    await collection_config.update_one({"_id": guild.id}, {"$set": {"warn_count": 1}})
    return 1


async def warn(
    guild: discord.Guild,
    user: Union[discord.Member, discord.User],
    reason: str,
    *,
    moderator: discord.Member,
    expires_at: Optional[float] = None,
    message: Optional[discord.Message] = None,
    at: Optional[float] = None,
) -> dict:
    post = {
        "warn_id": await get_warn_count(guild),
        "target": user.id,
        "moderator": moderator.id,
        "reason": reason,
        "expires_at": expires_at,
        "message_link": message.jump_url if message else None,
        "channel": message.channel.id if message else None,
        "message": message.id if message else None,
        "at": at,
    }
    collection = warn_db[f"{guild.id}"]
    await collection.insert_one(post)
    return post


async def custom_delete_warn(guild: discord.Guild, **kwargs) -> None:
    collection = warn_db[f"{guild.id}"]
    await collection.delete_one(kwargs)


async def delete_warn_by_message_id(guild: discord.Guild, *, messageID: int) -> None:
    collection = warn_db[f"{guild.id}"]
    await collection.delete_one({"message": messageID})


async def delete_many_warn(guild: discord.Guild, **kw) -> None:
    collection = warn_db[f"{guild.id}"]
    await collection.delete_many(kw)


async def edit_warn(guild: discord.Guild, **kw):
    collection = warn_db[f"{guild.id}"]
    await collection.update_one(kw)


async def show_warn(guild: discord.Guild, **kw):
    collection = warn_db[f"{guild.id}"]
    temp = {"User": [], "Reason": [], "At": []}
    async for data in collection.find({**kw}):
        temp["User"].append(data["target"])
        # temp["Moderator"].append(data["moderator"])
        temp["Reason"].append(data["reason"])
        temp["At"].append(f"{datetime.fromtimestamp(data['at'])}")
    return str(tabulate(temp, headers="keys", tablefmt="pretty"))
