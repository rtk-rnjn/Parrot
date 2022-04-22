from __future__ import annotations
from typing import List, Literal, Union

from core import Parrot, Context

import discord
import asyncio
import aiohttp
import datetime

from utilities.time import ShortTime


async def _add_roles_bot(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    operator: Literal["+", "add", "give", "-", "remove", "take"],
    role: discord.Role,
    reason: str,
):
    if ctx.author.top_role.position < role.position:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit the role which is above you"
        )
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit admin role."
        )
    is_mod = await ctx.modrole()

    if is_mod and (is_mod.id == role.id):
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit mod role"
        )
    for member in guild.members:
        try:
            if not member.bot:
                pass
            else:
                if operator.lower() in ["+", "add", "give"]:
                    await member.add_roles(role, reason=reason)
                elif operator.lower() in ["-", "remove", "take"]:
                    await member.remove_roles(role, reason=reason)
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False


async def _add_roles_humans(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    operator: Literal["+", "add", "give", "-", "remove", "take"],
    role: discord.Role,
    reason: str,
):
    if ctx.author.top_role.position < role.position:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit the role which is above you"
        )
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit admin role."
        )
    is_mod = await ctx.modrole()
    if is_mod and (is_mod.id == role.id):
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit mod role"
        )
    for member in guild.members:
        try:
            if member.bot:
                pass
            else:
                if operator.lower() in ["+", "add", "give"]:
                    await member.add_roles(role, reason=reason)
                elif operator.lower() in ["-", "remove", "take"]:
                    await member.remove_roles(role, reason=reason)
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False


async def _add_roles(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    role: discord.Role,
    reason: str,
):
    if ctx.author.top_role.position < role.position:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit the role which is above you"
        )
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit admin role."
        )
    is_mod = await ctx.modrole()
    if is_mod and (is_mod.id == role.id):
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit mod role"
        )
    try:
        await member.add_roles(
            role,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(
            f"{ctx.author.mention} given **{role.name} ({role.id})** to **{member.name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _remove_roles(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    role: discord.Role,
    reason: str,
):
    if ctx.author.top_role.position < role.position:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit the role which is above you"
        )
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit admin role."
        )
    is_mod = await ctx.modrole()
    if is_mod and (is_mod.id == role.id):
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit mod role"
        )
    try:
        await member.remove_roles(
            role,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(
            f"{ctx.author.mention} removed **{role.name} ({role.id})** from **{member.name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _role_hoist(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    role: discord.Role,
    _bool: bool,
    reason: str,
):
    if ctx.author.top_role.position < role.position:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit the role which is above you"
        )
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit admin role."
        )
    is_mod = await ctx.modrole()
    if is_mod and (is_mod.id == role.id):
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit mod role"
        )
    try:
        await role.edit(
            hoist=_bool,
            reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(
            f"{ctx.author.mention} **{role.name} ({role.id})** is now hoisted"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )
        return False


async def _change_role_name(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    role: discord.Role,
    text: str,
    reason: str,
):
    if ctx.author.top_role.position < role.position:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit the role which is above you"
        )
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit admin role."
        )
    is_mod = await ctx.modrole()
    if is_mod and (is_mod.id == role.id):
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit mod role"
        )
    try:
        await role.edit(
            name=text,
            reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(
            f"{ctx.author.mention} role name changed to **{text} ({role.id})**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )
        return False


async def _change_role_color(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    role: discord.Role,
    int_: int,
    reason: str,
):
    if ctx.author.top_role.position < role.position:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit the role which is above you"
        )
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit admin role."
        )
    is_mod = await ctx.modrole()
    if is_mod and (is_mod.id == role.id):
        return await destination.send(
            f"{ctx.author.mention} can not assign/remove/edit mod role"
        )
    try:
        await role.edit(
            color=discord.Color.value(int(int_)),
            reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(
            f"{ctx.author.mention} **{role.name} ({role.id})** color changed successfully"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )
        return False


# BAN


async def _ban(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    days: int,
    reason: str,
    silent=False,
):
    if (
        isinstance(member, discord.Member)
        and ctx.author.top_role.position < member.top_role.position
    ) and not silent:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        if member.id in (ctx.author.id, guild.me.id) and not silent:
            await destination.send(
                f"{ctx.author.mention} don't do that, Bot is only trying to help"
            )
            return
        await guild.ban(
            discord.Object(member if isinstance(member, int) else member.id),
            reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}",
            delete_message_days=days,
        )
        if not silent:
            await destination.send(f"{ctx.author.mention} **{member}** is banned!")
    except Exception as e:
        if not silent:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False


async def _mass_ban(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    members: List[discord.Member],
    days: int,
    reason: str,
):

    for member in members:
        if ctx.author.top_role.position < member.top_role.position:
            return await destination.send(
                f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
            )
        try:
            if member.id in (ctx.author.id, guild.me.id):
                await destination.send(
                    f"{ctx.author.mention} don't do that, Bot is only trying to help"
                )
                return
            await guild.ban(
                member,
                reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}",
                delete_message_days=days,
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False

    await destination.send(
        f"{ctx.author.mention} **{', '.join([str(member) for member in members])}** are banned!"
    )


async def _softban(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    members: List[discord.Member],
    reason: str,
):
    for member in members:
        if ctx.author.top_role.position < member.top_role.position:
            return await destination.send(
                f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
            )
        try:
            if member.id in (ctx.author.id, guild.me.id):
                await destination.send(
                    f"{ctx.author.mention} don't do that, Bot is only trying to help"
                )
                return
            await member.ban(
                reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}"
            )

            banned_users = await guild.bans()
            member_n, member_d = member.name, member.discriminator
            for ban_entry in banned_users:
                user = ban_entry.user
                if (user.name, user.discriminator) == (member_n, member_d):
                    await guild.unban(user)

            await destination.send(f"{ctx.author.mention} **{member}** is soft banned!")
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False


async def _temp_ban(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    members: List[discord.Member],
    duration: ShortTime,
    reason: str,
    silent=True,
    *,
    bot: Parrot = None,
):
    for member in members:
        if ctx.author.top_role.position < member.top_role.position and not silent:
            return await destination.send(
                f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
            )
        try:
            if member.id in (ctx.author.id, guild.me.id) and not silent:
                await destination.send(
                    f"{ctx.author.mention} don't do that, Bot is only trying to help"
                )
                return
            await member.ban(
                reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}"
            )
            mod_action = {
                "action": "UNBAN",
                "member": member.id,
                "reason": f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: Automatic tempban action",
                "guild": guild.id,
            }
            cog = bot.get_cog("Utils")
            await cog.create_timer(
                expires_at=duration.dt.timestamp(),
                created_at=discord.utils.utcnow().timestamp(),
                message=ctx.message,
                mod_action=mod_action,
            )
        except Exception as e:
            if not silent:
                await destination.send(
                    f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
                )
                return False


async def _unban(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
):
    try:
        await guild.unban(
            member,
            reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(f"{ctx.author.mention} **`{member}`** is unbanned!")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


# MUTE
async def _timeout(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    _datetime: datetime.datetime,
    reason: str,
    silent=False,
):
    if ctx.author.top_role.position < member.top_role.position and not silent:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    if member.id in (ctx.author.id, guild.me.id) and not silent:
        await destination.send(
            f"{ctx.author.mention} don't do that, Bot is only trying to help"
        )
        return
    if member.timed_out_until:
        return await destination.send(
            f"{ctx.author.mention} **{member}** is already on timeout **{discord.utils.format_dt(member.timed_out_until, 'R')}>**"
        )
    try:
        await member.edit(
            timed_out_until=_datetime,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        if not silent:
            await destination.send(
                f"{ctx.author.mention} **{member}** is on timeout **{discord.utils.format_dt(_datetime, 'R')}>**"
            )
    except Exception as e:
        if not silent:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False


async def _mute(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    silent=False,
):
    if ctx.author.top_role.position < member.top_role.position and not silent:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    if member.id in (ctx.author.id, guild.me.id) and not silent:
        await destination.send(
            f"{ctx.author.mention} don't do that, Bot is only trying to help"
        )
        return

    muted = await ctx.muterole()

    if not muted:
        muted = await guild.create_role(
            name="Muted",
            reason=f"Setting up mute role. it's first command is execution, by {ctx.author} ({ctx.author.id})",
        )
        for channel in guild.channels:
            try:
                await channel.set_permissions(
                    muted, send_messages=False, add_reactions=False
                )
            except discord.Forbidden:
                pass
    try:
        await member.add_roles(
            muted,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        if not silent:
            await destination.send(f"{ctx.author.mention} **{member}** is muted!")
        return
    except Exception as e:
        if not silent:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False


async def _unmute(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
):
    if member.timed_out_until:
        try:
            await member.edit(
                timed_out_until=None,
                reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}",
            )
            await destination.send(
                f"{ctx.author.mention} removed timeout from **{member}**"
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False
        return
    muted = await ctx.muterole()
    if not muted:
        await destination.send(
            f"{ctx.author.mention} can not find Mute role in the server"
        )
        return False
    try:
        if muted in member.roles:
            await member.remove_roles(
                muted,
                reason=f"Action requested by: {ctx.author.name} ({ctx.author.id}) | Reason: {reason}",
            )
            return await destination.send(
                f"{ctx.author.mention} **{member}** has been unmuted now!"
            )
        await destination.send(
            f"{ctx.author.mention} **{member.name}** already unmuted"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _kick(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    silent=False,
):
    try:
        if ctx.author.top_role.position < member.top_role.position and not silent:
            return await destination.send(
                f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
            )
        if member.id in (ctx.author.id, guild.me.id) and not silent:
            await destination.send(
                f"{ctx.author.mention} don't do that, Bot is only trying to help"
            )
            return
        await member.kick(
            reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}"
        )
        if not silent:
            await destination.send(
                f"{ctx.author.mention} **{member}** is kicked from the server!"
            )
    except Exception as e:
        if not silent:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False


async def _mass_kick(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    members: List[discord.Member],
    reason: str,
):
    for member in members:
        if ctx.author.top_role.position < member.top_role.position:
            return await destination.send(
                f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
            )
        try:
            if member.id in (ctx.author.id, guild.me.id):
                await destination.send(
                    f"{ctx.author.mention} don't do that, Bot is only trying to help"
                )
                return
            await member.kick(
                reason=f"Action requested by: {ctx.author} ({ctx.author.id}) | Reason: {reason}"
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False
        await asyncio.sleep(0.25)
    await destination.send(
        f"{ctx.author.mention} **{', '.join([str(member) for member in members])}** are kicked from the server!"
    )


# BLOCK


async def _block(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    members: List[discord.Member],
    reason: str,
    silent=False,
):
    for member in members:
        if ctx.author.top_role.position < member.top_role.position and not silent:
            return await destination.send(
                f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
            )
        try:
            if member.id in (ctx.author.id, guild.me.id) and not silent:
                await destination.send(
                    f"{ctx.author.mention} don't do that, Bot is only trying to help"
                )
                return
            await channel.set_permissions(
                member,
                send_messages=False,
                view_channel=False,
                reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
            )
            if not silent:
                await destination.send(
                    f"{ctx.author.mention} overwrite permission(s) for **{member}** has been created! **View Channel, and Send Messages** is denied!"
                )
        except Exception as e:
            if not silent:
                await destination.send(
                    f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
                )
                return False


async def _unblock(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    members: List[discord.Member],
    reason: str,
):
    for member in members:
        try:
            if channel.permissions_for(member).send_messages:
                await destination.send(
                    f"{ctx.author.mention} {member.name} is already unblocked. They can send message"
                )
            else:
                await channel.set_permissions(
                    member,
                    send_messages=None,
                    view_channel=None,
                    reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
                )
            await destination.send(
                f"{ctx.author.mention} overwrite permission(s) for **{member}** has been deleted!"
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            return False


# LOCK


async def _text_lock(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
):
    try:
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx.author} ({ctx.author.id})",
            send_messages=False,
        )
        await destination.send(f"{ctx.author.mention} channel locked.")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )
        return False


async def _vc_lock(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: Union[discord.VoiceChannel, discord.StageChannel],
):
    if not channel:
        return
    try:
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx.author} ({ctx.author.id})",
            connect=False,
        )
        await destination.send(f"{ctx.author.mention} channel locked.")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )
        return False


# UNLOCK


async def _text_unlock(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
):
    try:
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx.author} ({ctx.author.id})",
            send_messages=None,
        )
        await destination.send(f"{ctx.author.mention} channel unlocked.")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )
        return False


async def _vc_unlock(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: Union[discord.VoiceChannel, discord.StageChannel],
):
    if not channel:
        return
    try:
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx.author} ({ctx.author.id})",
            connect=None,
        )
        await destination.send(f"{ctx.author.mention} channel unlocked.")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )
        return False


# EXTRA


async def _change_nickname(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    name: str,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        await member.edit(
            nick=name, reason=f"Action Requested by {ctx.author} ({ctx.author.id})"
        )
        await destination.send(
            f"{ctx.author.mention} **{member}** nickname changed to **{name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _change_channel_topic(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    text: str,
):
    try:
        await channel.edit(
            topic=text,
            reason=f"Action Requested by {ctx.author} ({ctx.author.id})",
        )
        await destination.send(
            f"{ctx.author.mention} **{channel.name}** topic changed to **{text}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )
        return False


async def _change_channel_name(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    text: str,
):
    try:
        await channel.edit(
            name=text, reason=f"Action Requested by {ctx.author} ({ctx.author.id})"
        )
        await destination.send(
            f"{ctx.author.mention} **{channel}** name changed to **{text}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )
        return False


async def _slowmode(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    seconds: int,
    channel: discord.TextChannel,
    reason: str,
):
    if seconds:
        try:
            if 21600 >= seconds > 0:  # discord limit
                await channel.edit(
                    slowmode_delay=seconds,
                    reason=f"Action Requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
                )
                return await destination.send(
                    f"{ctx.author.mention} {channel} is now in slowmode of **{seconds}**, to reverse type [p]slowmode 0"
                )
            if seconds == 0 or (seconds.lower() in ("off", "disable")):
                await channel.edit(
                    slowmode_delay=seconds,
                    reason=f"Action Requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
                )
                return await destination.send(
                    f"{ctx.author.mention} **{channel}** is now not in slowmode."
                )
            if (seconds >= 21600) or (seconds < 0):
                return await destination.send(
                    f"{ctx.author.mention} you can't set slowmode in negative numbers or more than 21600 seconds"
                )

        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
            )
            return False


async def _clone(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    reason: str,
):
    try:
        new_channel = await channel.clone(
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}"
        )
        await channel.delete(
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}"
        )
        await new_channel.send(f"{ctx.author.mention}", delete_after=5)
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )
        return False


# VOICE MOD


async def _voice_mute(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        await member.edit(
            mute=True,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(f"{ctx.author.mention} voice muted **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _voice_unmute(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
):
    try:
        await member.edit(
            mute=False,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(f"{ctx.author.mention} voice unmuted **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _voice_deafen(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        await member.edit(
            deafen=True,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(f"{ctx.author.mention} voice deafened **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _voice_undeafen(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
):
    try:
        await member.edit(
            deafen=False,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(f"{ctx.author.mention} voice undeafened **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _voice_kick(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        await member.edit(
            voice_channel=None,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(f"{ctx.author.mention} voice kicked **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _voice_ban(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    channel: Union[discord.VoiceChannel, discord.StageChannel],
    reason: str,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        await channel.set_permissions(
            member,
            connect=False,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(f"{ctx.author.mention} voice banned **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _voice_unban(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    channel: Union[discord.VoiceChannel, discord.StageChannel],
    reason: str,
):
    try:
        await channel.set_permissions(
            member,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
            connect=None,
        )
        await destination.send(f"{ctx.author.mention} voice unbanned **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )
        return False


async def _emoji_delete(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    emojis: List[Union[discord.Emoji, discord.PartialEmoji]],
    reason: str,
):
    for emoji in emojis:
        try:
            if emoji.guild.id == guild.id:
                await emoji.delete(
                    reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}"
                )
                await destination.send(f"{ctx.author.mention} **{emoji}** deleted!")
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{emoji.name} ({emoji.id})**. Error raised: **{e}**"
            )
            return False


async def _emoji_add(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    emojis: List[Union[discord.Emoji, discord.PartialEmoji]],
    reason: str,
):
    for emoji in emojis:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji.url) as res:
                    raw = await res.read()
            ej = await guild.create_custom_emoji(
                name=emoji.name,
                image=raw,
                reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
            )
            await destination.send(f"{ctx.author.mention} emoji created {ej}")
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{emoji.name} ({emoji.id})**. Error raised: **{e}**"
            )
            return False


async def _emoji_addurl(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    url: str,
    name: str,
    reason: str,
):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as res:
                raw = await res.read()
        emoji = await guild.create_custom_emoji(
            name=name,
            image=raw,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(f"{ctx.author.mention} emoji created {emoji}")
    except Exception as e:
        await destination.send(f"Can not able to {command_name}. Error raised: **{e}**")
        return False


async def _emoji_rename(
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    emoji: Union[discord.Emoji, discord.PartialEmoji],
    name: str,
    reason: str,
):
    try:
        await emoji.edit(
            name=name,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        await destination.send(
            f"{ctx.author.mention} {emoji} name edited to **{name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{emoji.name} ({emoji.id})**. Error raised: **{e}**"
        )
        return False


MEMBER_REACTION = [
    "\N{HAMMER}",
    "\N{WOMANS BOOTS}",
    "\N{ZIPPER-MOUTH FACE}",
    "\N{GRINNING FACE WITH SMILING EYES}",
    "\N{CROSS MARK}",
    "\N{HEAVY LARGE CIRCLE}",
    "\N{UPWARDS BLACK ARROW}",
    "\N{DOWNWARDS BLACK ARROW}",
    "\N{LOWER LEFT FOUNTAIN PEN}",
]
TEXT_REACTION = ["\N{LOCK}", "\N{OPEN LOCK}", "\N{MEMO}", "\N{LOWER LEFT FOUNTAIN PEN}"]
VC_REACTION = ["\N{LOCK}", "\N{OPEN LOCK}", "\N{LOWER LEFT FOUNTAIN PEN}"]
ROLE_REACTION = [
    "\N{LOCK}",
    "\N{OPEN LOCK}",
    "\N{RAINBOW}",
    "\N{LOWER LEFT FOUNTAIN PEN}",
]
