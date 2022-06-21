from __future__ import annotations
from core import Context
import discord

from typing import Any, Dict, Optional, Union

from datetime import datetime
from tabulate import tabulate
from pymongo import ReturnDocument


async def get_warn_count(ctx: Context, guild: discord.Guild) -> Optional[int]:
    data = await ctx.bot.mongo.parrot_db.server_config.find_one_and_update(
        {"_id": guild.id},
        {"$inc": {"warn_count": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return data["warn_count"]


async def warn(
    guild: discord.Guild,
    user: Union[discord.Member, discord.User],
    reason: str,
    *,
    moderator: discord.Member,
    ctx: Context,
    expires_at: Optional[float] = None,
    message: Optional[discord.Message] = None,
    at: Optional[float] = None,
) -> Dict[str, Any]:
    """|coro|

    To warn the user.

    Parameters
    -----------
    guild: discord.Guild
        Guild instance, in which the Member in
    user: Union[discord.Member, discord.User]
        User who is getting warned
    reason: str
        Reason for warning user
    moderator: discord.Member
        The moderator who is issuing warn
    expires_at: Optional[float]
        Time at which the warning will be deleted
    message: Optional[discord.Message]
        Message object (ctx.message)
    at: Optional[float]
        Time ate which the warning is issued
    """
    count = await get_warn_count(ctx, guild)
    post = {
        "warn_id": count,
        "target": user.id,
        "moderator": moderator.id,
        "reason": reason,
        "expires_at": expires_at,
        "message_link": message.jump_url if message else None,
        "channel": message.channel.id if message else None,
        "message": message.id if message else None,
        "messageUrl": message.jump_url,
        "at": at,
    }
    collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    await collection.insert_one(post)
    return post


async def custom_delete_warn(ctx, guild: discord.Guild, **kwargs):
    collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    return await collection.delete_one(kwargs)


async def delete_warn_by_message_id(
    ctx, guild: discord.Guild, *, messageID: int
) -> None:
    collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    await collection.delete_one({"message": messageID})


async def delete_many_warn(ctx, guild: discord.Guild, **kw) -> None:
    collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    await collection.delete_many(kw)


async def edit_warn(ctx, guild: discord.Guild, **kw) -> None:
    collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    await collection.update_one(kw)


async def show_warn(ctx, guild: discord.Guild, **kw) -> str:
    collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    temp = {"User": [], "Reason": [], "At": []}
    async for data in collection.find({**kw}):
        temp["User"].append(data["target"])
        # temp["Moderator"].append(data["moderator"])
        temp["Reason"].append(data["reason"])
        temp["At"].append(f"{datetime.fromtimestamp(data['at'])}")
    return str(tabulate(temp, headers="keys", tablefmt="pretty"))
