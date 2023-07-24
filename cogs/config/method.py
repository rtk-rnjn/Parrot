from __future__ import annotations

from typing import Any, Literal, Optional, Union

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
    target: Optional[Union[discord.Role, discord.abc.GuildChannel]],
    tp: Literal["enable", "disable"],
) -> str:
    is_are = "commands are" if cmd_cog == "all" else "is"
    initial_str = f"{ctx.author.mention} **{cmd_cog}** {is_are} now {tp}"
    if not target:
        return f"{initial_str} **server** wide"
    elif isinstance(target, discord.abc.GuildChannel):
        return f"{initial_str} for **{target.mention}**"
    elif isinstance(target, discord.Role):
        return f"{initial_str} for **{target.name} ({target.id})**"


async def _enable(
    ctx: Context,
    cmd_cog: str,
    target: Union[discord.abc.GuildChannel, discord.Role, None],
) -> None:
    assert ctx.guild
    if not target:
        await update_db(ctx=ctx, key="CMD_GLOBAL_ENABLE", cmd=cmd_cog, value=True, op="$set")

    elif isinstance(target, discord.abc.GuildChannel):
        await update_db(ctx=ctx, key="CMD_CHANNEL_ENABLE", cmd=cmd_cog, value=ctx.channel.id, op="$addToSet")
        await update_db(ctx=ctx, key="CMD_CHANNEL_DISABLE", cmd=cmd_cog, value=ctx.channel.id, op="$pull")

    elif isinstance(target, discord.Role):
        await update_db(ctx=ctx, key="CMD_ROLE_ENABLE", cmd=cmd_cog, value=target.id, op="$addToSet")
        await update_db(ctx=ctx, key="CMD_ROLE_DISABLE", cmd=cmd_cog, value=target.id, op="$pull")

    await ctx.send(get_text(ctx=ctx, cmd_cog=cmd_cog, target=target, tp="enable"))


async def _disable(
    ctx: Context,
    cmd_cog: str,
    target: Union[discord.abc.GuildChannel, discord.Role],
) -> None:
    assert ctx.guild
    if not target:
        await update_db(ctx=ctx, key="CMD_GLOBAL_ENABLE", cmd=cmd_cog, value=False, op="$set")

    elif isinstance(target, discord.abc.GuildChannel):
        await update_db(ctx=ctx, key="CMD_CHANNEL_DISABLE", cmd=cmd_cog, value=ctx.channel.id, op="$addToSet")
        await update_db(ctx=ctx, key="CMD_CHANNEL_ENABLE", cmd=cmd_cog, value=ctx.channel.id, op="$pull")

    elif isinstance(target, discord.Role):
        await update_db(ctx=ctx, key="CMD_ROLE_DISABLE", cmd=cmd_cog, value=target.id, op="$addToSet")
        await update_db(ctx=ctx, key="CMD_ROLE_ENABLE", cmd=cmd_cog, value=target.id, op="$pull")

    await ctx.send(get_text(ctx=ctx, cmd_cog=cmd_cog, target=target, tp="disable"))
