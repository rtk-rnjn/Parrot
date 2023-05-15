from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pymongo import ReturnDocument
from pymongo.collection import Collection
from pymongo.results import DeleteResult
from tabulate import tabulate

import discord
from core import Context
from utilities.time import ShortTime


async def get_warn_count(ctx: Context, guild: discord.Guild) -> Optional[int]:
    data = await ctx.bot.guild_configurations.find_one_and_update(
        {"_id": guild.id},
        {"$inc": {"warn_count": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return data["warn_count"]


def get_warn_expiry(ctx: Context):
    try:
        duration = ctx.bot.guild_configurations[ctx.guild.id]["warn_expiry"]
    except KeyError:
        return None
    else:
        return ShortTime(duration).dt.timestamp()


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
        "expires_at": expires_at or get_warn_expiry(ctx),
        "message_link": message.jump_url if message else None,
        "channel": message.channel.id if message else None,
        "message": message.id if message else None,
        "messageUrl": message.jump_url,
        "at": at,
    }
    collection: Collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    await collection.insert_one(post)

    if expires_at:
        await ctx.bot.create_timer(  # type: ignore
            expires_at=expires_at,
            created_at=discord.utils.utcnow(),
            message=message,
            extra={
                "name": "DB_EXECUTE",
                "main": {
                    "database": "warn_db",
                    "collection": f"{guild.id}",
                    "action": "delete_one",
                    "filter": {"warn_id": count},
                },
            },
        )
    return post


async def custom_delete_warn(
    ctx: Context, guild: discord.Guild, **kwargs
) -> DeleteResult:
    collection: Collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    return await collection.delete_one(kwargs)


async def delete_warn_by_message_id(
    ctx: Context, guild: discord.Guild, *, messageID: int
) -> None:
    collection: Collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    await collection.delete_one({"message": messageID})


async def delete_many_warn(ctx: Context, guild: discord.Guild, **kw) -> None:
    collection: Collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    await collection.delete_many(kw)


async def edit_warn(ctx: Context, guild: discord.Guild, **kw) -> None:
    collection: Collection = ctx.bot.mongo.warn_db[f"{guild.id}"]
    await collection.update_one(kw)


async def show_warn(ctx: Context, guild: discord.Guild, **kw) -> List[str]:
    collection: Collection = ctx.bot.mongo.warn_db[f"{guild.id}"]

    temp = {"ID": [], "User": [], "Reason": [], "At": []}
    entries: List[str] = []
    i = 1
    async for data in collection.find({**kw}):
        temp["User"].append(f'{data["target"]} ({ctx.bot.get_user(data["target"])})')
        temp["ID"].append(data["warn_id"])
        temp["Reason"].append(data["reason"])
        temp["At"].append(f"{datetime.fromtimestamp(data['at'])}")
        i += 1
        if i % 10 == 0:
            entries.append(tabulate(temp, headers="keys", tablefmt="pretty"))
            temp = {"ID": [], "User": [], "Reason": [], "At": []}

    return entries
