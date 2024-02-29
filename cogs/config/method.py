from __future__ import annotations

from typing import Any, Literal

import discord
from core import Context


async def update_db(*, ctx: Context, key: str, cmd: str, value: Any, op: str) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id},
        {
            op: {
                f"cmd_config.{key}_{cmd.upper().replace(' ', '_')}": value,
            },
        },
        upsert=True,
    )


def get_text(
    *,
    ctx: Context,
    cmd_cog: str,
    target: discord.Role | discord.abc.GuildChannel | None,
    tp: Literal["enable", "disable"],
) -> str:
    is_are = "commands are" if cmd_cog == "all" else "is"
    initial_str = f"{ctx.author.mention} **{cmd_cog}** {is_are} now {tp}"
    if not target:
        return f"{initial_str} **server** wide"
    if isinstance(target, discord.TextChannel):
        return f"{initial_str} for **{target.mention}**"
    if isinstance(target, discord.Role):
        return f"{initial_str} for **{target.name} ({target.id})**"


async def _enable(
    ctx: Context,
    cmd_cog: str,
    target: discord.abc.GuildChannel | discord.Role | None,
) -> None:
    if not target:
        await update_db(ctx=ctx, key="CMD_GLOBAL_ENABLE", cmd=cmd_cog, value=True, op="$set")

    elif isinstance(target, discord.TextChannel):
        await update_db(ctx=ctx, key="CMD_CHANNEL_DISABLE", cmd=cmd_cog, value=ctx.channel.id, op="$pull")

    elif isinstance(target, discord.Role):
        await update_db(ctx=ctx, key="CMD_ROLE_DISABLE", cmd=cmd_cog, value=target.id, op="$pull")

    await ctx.send(get_text(ctx=ctx, cmd_cog=cmd_cog, target=target, tp="enable"))


async def _disable(
    ctx: Context,
    cmd_cog: str,
    target: discord.abc.GuildChannel | discord.Role,
) -> None:
    if not target:
        await update_db(ctx=ctx, key="CMD_GLOBAL_ENABLE", cmd=cmd_cog, value=False, op="$set")

    elif isinstance(target, discord.TextChannel):
        await update_db(ctx=ctx, key="CMD_CHANNEL_DISABLE", cmd=cmd_cog, value=ctx.channel.id, op="$addToSet")

    elif isinstance(target, discord.Role):
        await update_db(ctx=ctx, key="CMD_ROLE_DISABLE", cmd=cmd_cog, value=target.id, op="$addToSet")

    await ctx.send(get_text(ctx=ctx, cmd_cog=cmd_cog, target=target, tp="disable"))
