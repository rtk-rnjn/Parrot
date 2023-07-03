from __future__ import annotations

from typing import Any, Literal, Optional, Union

import discord
from core import Context, Parrot


async def update_db(*, ctx: Context, key: str, cmd: str, value: Any, op: str) -> None:
    assert ctx.guild

    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id},
        {
            op: {
                f"cmd_config.{key}_{cmd.upper().replace(' ', '_')}": value,
            }
        },
        upsert=True,
    )


def get_text(
    *,
    ctx: Context,
    cmd_cog: str,
    force: Optional[bool],
    target: Optional[Union[discord.Role, discord.abc.GuildChannel]],
    tp: Literal['enable', 'disable'],
) -> str:
    is_are = "commands are" if cmd_cog == "all" else "is"
    force_text = ", forcely" if force else ""
    initial_str = f"{ctx.author.mention} **{cmd_cog}** {is_are} now {tp}"
    if not target:
        return f"{initial_str} **server** wide{force_text}"
    elif isinstance(target, discord.abc.GuildChannel):
        return f"{initial_str} for **{target.mention}**{force_text}"
    elif isinstance(target, discord.Role):
        return f"{initial_str} for **{target.name} ({target.id})**{force_text}"


async def _enable(
    bot: Parrot,
    ctx: Context,
    cmd_cog: str,
    target: Union[discord.abc.GuildChannel, discord.Role, None],
    force: Optional[bool] = None,
) -> None:
    assert ctx.guild
    if not target:
        if force:
            await update_db(ctx=ctx, key="CMD_GLOBAL_ENABLE", cmd=cmd_cog, value=True, op="$set")
        else:
            await update_db(ctx=ctx, key="CMD_ENABLE", cmd=cmd_cog, value=False, op="$set")

    elif isinstance(target, discord.abc.GuildChannel):
        if force:
            await update_db(ctx=ctx, key="CMD_CHANNEL_ENABLE", cmd=cmd_cog, value=ctx.channel.id, op="$addToSet")
        else:
            await update_db(ctx=ctx, key="CMD_CHANNEL_DISABLE", cmd=cmd_cog, value=ctx.channel.id, op="$pull")

    elif isinstance(target, discord.Role):
        if force:
            await update_db(ctx=ctx, key="CMD_ROLE_ENABLE", cmd=cmd_cog, value=target.id, op="$addToSet")
        else:
            await update_db(ctx=ctx, key="CMD_ROLE_DISABLE", cmd=cmd_cog, value=target.id, op="$pull")

    await ctx.send(get_text(ctx=ctx, cmd_cog=cmd_cog, force=force, target=target, tp='enable'))


async def _disable(
    bot: Parrot,
    ctx: Context,
    cmd_cog: str,
    target: Union[discord.abc.GuildChannel, discord.Role],
    force: Optional[bool] = None,
) -> None:
    assert ctx.guild
    if not target:
        if force:
            await update_db(ctx=ctx, key="CMD_GLOBAL_ENABLE", cmd=cmd_cog, value=False, op="$set")

    elif isinstance(target, discord.abc.GuildChannel):
        if force:
            await update_db(ctx=ctx, key="CMD_CHANNEL_DISABLE", cmd=cmd_cog, value=ctx.channel.id, op="$addToSet")
        else:
            await update_db(ctx=ctx, key="CMD_CHANNEL_ENABLE", cmd=cmd_cog, value=ctx.channel.id, op="$pull")

    elif isinstance(target, discord.Role):
        if force:
            await update_db(ctx=ctx, key="CMD_ROLE_DISABLE", cmd=cmd_cog, value=target.id, op="$addToSet")
        else:
            await update_db(ctx=ctx, key="CMD_ROLE_ENABLE", cmd=cmd_cog, value=target.id, op="$pull")

    await ctx.send(get_text(ctx=ctx, cmd_cog=cmd_cog, force=force, target=target, tp='disable'))
