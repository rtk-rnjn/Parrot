from __future__ import annotations

import asyncio
import contextlib
import random
from typing import Any

import discord
from core import Context, Parrot
from discord.ext import commands

cd_mapping = commands.CooldownMapping.from_cooldown(5, 5, commands.BucketType.channel)


async def telephone_update(ctx: Context, *, guild_id: int, event: str, value: Any) -> None:
    await ctx.bot.guild_configurations.update_one({"_id": guild_id}, {"$set": {f"telephone.{event}": value}}, upsert=True)


async def get_guild(ctx: Context, guild_id: int) -> dict:
    if ctx.bot.guild_configurations_cache.get(guild_id):
        return ctx.bot.guild_configurations_cache.get(guild_id)

    return await ctx.bot.guild_configurations.find_one({"_id": guild_id})


def outer_check_pickup_hangup(channel: discord.abc.MessageableChannel, target_channel: discord.abc.Messageable):
    def check_pickup_hangup(m: discord.Message) -> bool:
        return (
            (m.content.lower() in ("pickup", "hangup")) and (m.channel in (channel, target_channel)) and (not m.author.bot)
        )

    return check_pickup_hangup


async def dial(bot: Parrot, ctx: Context, server: discord.Guild, reverse: bool = False):
    if server.id == ctx.guild.id:
        return await ctx.send("Can't make a self call")

    number = server.id
    channel = ctx.channel
    self_guild = await get_guild(ctx, ctx.guild.id)
    if not self_guild:
        return await ctx.send(
            f"{ctx.author.mention} no telephone line channel is set for this server, ask your Server Manager to fix this."
        )
    target_guild = await get_guild(ctx, number)
    target_guild_obj = bot.get_guild(target_guild["_id"])
    if not target_guild_obj:
        return await ctx.send(
            f"{ctx.author.mention} no telephone line channel is set for the **{number}** server,"
            f" or the number you entered do not match with any other server!"
        )

    if not target_guild:
        return await ctx.send(
            f"{ctx.author.mention} no telephone line channel is set for the **{number}** server,"
            f" or the number you entered do not match with any other server!"
        )

    if target_guild.get("is_line_busy"):
        return await ctx.send(f"Can not make a connection to **{number} ({target_guild_obj.name})**. Line busy!")

    target_channel = bot.get_channel(target_guild.get("channel", 0))
    if not target_channel:
        return await ctx.send("Calling failed! Possible reasons: `Channel deleted`, missing `View Channels` permission.")
    assert isinstance(target_channel, discord.abc.Messageable)

    if (target_guild["_id"] in self_guild.get("blocked", [])) or (self_guild["_id"] in target_guild.get("blocked", [])):
        return await ctx.send("Calling failed! Possible reasons: They blocked You, You blocked Them.")

    await ctx.send(f"Calling to **{number} ({target_guild_obj.name})** ... Waiting for the response ...")

    await target_channel.send(
        f"**Incoming call from {ctx.guild.id}. {ctx.guild.name} ...**\n`pickup` to pickup | `hangup` to reject"
    )
    await telephone_update(ctx, guild_id=ctx.guild.id, event="is_line_busy", value=True)
    await telephone_update(ctx, guild_id=number, event="is_line_busy", value=True)
    with contextlib.suppress(AttributeError, KeyError):
        temp_message: discord.Message = target_channel.send(  # type: ignore
            f'<@&{target_guild["pingrole"]}> <@{target_guild["memberping"]}>',
            delete_after=1,
        )
        await temp_message.delete(delay=0)

    try:
        _talk: discord.Message = await bot.wait_for(
            "message",
            check=outer_check_pickup_hangup(channel, target_channel),
            timeout=60,
        )
    except asyncio.TimeoutError:
        await asyncio.sleep(0.5)
        await target_channel.send(
            f"Line disconnected from **{ctx.guild.id} ({ctx.guild.name})**. Reason: Line Inactive for more than 60 seconds"
        )
        await ctx.send(
            f"Line disconnected from **{number} ({target_guild_obj.name})**. Reason: Line Inactive for more than 60 seconds"
        )
        await telephone_update(ctx, guild_id=ctx.guild.id, event="is_line_busy", value=False)
        await telephone_update(ctx, guild_id=number, event="is_line_busy", value=False)
        return

    assert isinstance(_talk, discord.Message) and isinstance(_talk.author, discord.Member)
    if _talk.content.lower() == "hangup":
        await ctx.send(f"Disconnected. From **{_talk.author.guild.name} ({_talk.author.guild.id})**")
        await target_channel.send(f"Disconnected. From **{_talk.author.guild.name} ({_talk.author.guild.id})**")

    elif _talk.content.lower() == "pickup":
        await telephone_update(ctx, guild_id=ctx.guild.id, event="is_line_busy", value=True)
        await telephone_update(ctx, guild_id=number, event="is_line_busy", value=True)
        await ctx.send(f"**Connected. Say {random.choice(['hi', 'hello', 'heya'])}**")
        await target_channel.send(f"**Connected. Say {random.choice(['hi', 'hello', 'heya'])}**")

        ini = discord.utils.utcnow().timestamp() + 120
        while ini > discord.utils.utcnow().timestamp():

            def check_in_channel(m: discord.Message) -> bool:
                return False if m.author.bot else m.channel in (target_channel, channel)

            try:
                talk_message = await bot.wait_for("message", check=check_in_channel, timeout=60.0)
            except asyncio.TimeoutError:
                await asyncio.sleep(0.5)
                await target_channel.send(
                    f"Line disconnected from **{ctx.guild.id} ({ctx.guild.name})**. Reason: Line Inactive for more than 60 seconds"
                )
                await ctx.send(
                    f"Line disconnected from **{number} ({target_guild_obj.name})**."
                    f"Reason: Line Inactive for more than 60 seconds"
                )
                break

            bucket = cd_mapping.get_bucket(talk_message)
            retry_after = bucket.update_rate_limit()
            if retry_after:
                await target_channel.send("Disconnect due to channel spam")
                await ctx.send("Disconnect due to channel spam")
                break

            if talk_message.content.lower() == "hangup":
                await ctx.send("Disconnected")
                await target_channel.send("Disconnected")
                break

            TALK = discord.utils.escape_mentions(talk_message.content[:1000:])
            if reverse:
                TALK = discord.utils.escape_mentions(
                    "".join(reversed(talk_message.content[:1000:]))
                )  # this is imp, cause people can bypass so i added discord.utils

            if talk_message.channel == target_channel:
                await channel.send(f"**{talk_message.author}** {TALK}")

            elif talk_message.channel == channel:
                await target_channel.send(f"**{talk_message.author}** {TALK}")

        await channel.send("Disconnected. Call duration reached its maximum limit")
        await target_channel.send("Disconnected. Call duration reached its maximum limit")

    await telephone_update(ctx, guild_id=ctx.guild.id, event="is_line_busy", value=False)
    await telephone_update(ctx, guild_id=number, event="is_line_busy", value=False)
