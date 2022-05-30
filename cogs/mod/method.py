from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Dict, List, Literal, Optional, Union

from core import Parrot, Context

import discord
import asyncio
import aiohttp  # type: ignore
import datetime

from utilities.time import FutureTime


async def _add_roles_bot(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    operator: Literal["+", "add", "give", "-", "remove", "take"],
    role: discord.Role,
    reason: str,
    **kwargs: Any,
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


async def _add_roles_humans(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    operator: Literal["+", "add", "give", "-", "remove", "take"],
    role: discord.Role,
    reason: str,
    **kwargs: Any,
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


async def _add_roles(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    role: discord.Role,
    reason: str,
    **kwargs: Any,
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
            reason=reason,
        )
        await destination.send(
            f"{ctx.author.mention} given **{role.name} ({role.id})** to **{member.name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _remove_roles(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    role: discord.Role,
    reason: str,
    **kwargs: Any,
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
            reason=reason,
        )
        await destination.send(
            f"{ctx.author.mention} removed **{role.name} ({role.id})** from **{member.name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _role_hoist(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    role: discord.Role,
    _bool: bool,
    reason: str,
    **kwargs: Any,
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
            reason=reason,
        )
        await destination.send(
            f"{ctx.author.mention} **{role.name} ({role.id})** is now hoisted"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )


async def _change_role_name(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    role: discord.Role,
    text: str,
    reason: str,
    **kwargs: Any,
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
            reason=reason,
        )
        await destination.send(
            f"{ctx.author.mention} role name changed to **{text} ({role.id})**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )


async def _change_role_color(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    role: discord.Role,
    int_: int,
    reason: str,
    **kwargs: Any,
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
            reason=reason,
        )
        await destination.send(
            f"{ctx.author.mention} **{role.name} ({role.id})** color changed successfully"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )


# BAN


async def _ban(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    days: int = 0,
    reason: str,
    silent: bool = False,
    **kwargs: Any,
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
            reason=reason,
            delete_message_days=days,
        )
        if not silent:
            await destination.send(f"{ctx.author.mention} **{member}** is banned!")
    except Exception as e:
        if not silent:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


async def _mass_ban(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    members: Union[List[discord.Member], discord.Member],
    days: int = 0,
    reason: str,
    **kwargs: Any,
):
    members = [members] if not isinstance(members, list) else members
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
                reason=reason,
                delete_message_days=days,
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )

    await destination.send(
        f"{ctx.author.mention} **{', '.join([str(member) for member in members])}** are banned!"
    )


async def _softban(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    members: Union[List[discord.Member], discord.Member],
    reason: str,
    **kwargs: Any,
):
    members = [members] if not isinstance(members, list) else members
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
            await member.ban(reason=reason)

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


async def _temp_ban(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    members: Union[List[discord.Member], discord.Member],
    duration: Union[FutureTime, datetime.datetime],
    reason: str,
    silent: bool = True,
    bot: Parrot = None,
    **kwargs: Any,
):
    bot = bot or ctx.bot
    members = [members] if not isinstance(members, list) else members
    for member in members:
        try:
            if member.id in (ctx.author.id, guild.me.id) and not silent:
                await destination.send(
                    f"{ctx.author.mention} don't do that, Bot is only trying to help"
                )
                return
            await guild.ban(discord.Object(id=member.id), reason=reason)
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
            await destination.send(
                f"{ctx.author.mention} **{member}** will be unbanned {discord.utils.format_dt(duration.dt, 'R')}!"
            )

        except Exception as e:
            if not silent:
                await destination.send(
                    f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
                )


async def _unban(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    **kwargs: Any,
):
    try:
        await guild.unban(
            member,
            reason=reason,
        )
        await destination.send(f"{ctx.author.mention} **{member}** is unbanned!")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


# MUTE
async def _timeout(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    _datetime: datetime.datetime,
    reason: str,
    silent: bool = False,
    **kwargs: Any,
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
    if (
        member.timed_out_until is not None
        and member.timed_out_until > datetime.datetime.now(datetime.timezone.utc)
    ):
        return await destination.send(
            f"{ctx.author.mention} **{member}** is already on timeout. It will be removed **{discord.utils.format_dt(member.timed_out_until, 'R')}**"
        )
    try:
        await member.edit(
            timed_out_until=_datetime,
            reason=reason,
        )
        if not silent:
            await destination.send(
                f"{ctx.author.mention} **{member}** is on timeout and will be removed **{discord.utils.format_dt(_datetime, 'R')}**"
            )
    except Exception as e:
        if not silent:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


async def _mute(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    silent: bool = False,
    **kwargs: Any,
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
            reason=reason,
        )
        if not silent:
            await destination.send(f"{ctx.author.mention} **{member}** is muted!")
        return
    except Exception as e:
        if not silent:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


async def _unmute(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    **kwargs: Any,
):
    if member.timed_out_until:
        try:
            await member.edit(
                timed_out_until=None,
                reason=reason,
            )
            await destination.send(
                f"{ctx.author.mention} removed timeout from **{member}**"
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )

        return
    muted = await ctx.muterole()
    if not muted:
        await destination.send(
            f"{ctx.author.mention} can not find Mute role in the server"
        )

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


async def _kick(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    silent: bool = False,
    **kwargs: Any,
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
        await member.kick(reason=reason)
        if not silent:
            await destination.send(
                f"{ctx.author.mention} **{member}** is kicked from the server!"
            )
    except Exception as e:
        if not silent:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


async def _mass_kick(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    members: Union[List[discord.Member], discord.Member],
    reason: str,
    **kwargs: Any,
):
    members = [members] if not isinstance(members, list) else members
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
            await member.kick(reason=reason)
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )

        await asyncio.sleep(0.25)
    await destination.send(
        f"{ctx.author.mention} **{', '.join([str(member) for member in members])}** are kicked from the server!"
    )


# BLOCK


async def _block(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    members: Union[List[discord.Member], discord.Member],
    reason: str,
    silent: bool = False,
    **kwargs: Any,
):
    members = [members] if not isinstance(members, list) else members
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
            overwrite = channel.overwrites
            if member_overwrite := overwrite.get(member):
                member_overwrite.update(
                    send_messages=False,
                    view_channel=False,
                )
            else:
                overwrite[member] = discord.PermissionOverwrite(
                    send_messages=False,
                    view_channel=False,
                )
            await channel.edit(overwrites=overwrite, reason=reason)
            # await channel.set_permissions(
            #     member,
            #     send_messages=False,
            #     view_channel=False,
            #     reason=reason,
            # )
            if not silent:
                await destination.send(
                    f"{ctx.author.mention} overwrite permission(s) for **{member}** has been created! **View Channel, and Send Messages** is denied!"
                )
        except Exception as e:
            if not silent:
                await destination.send(
                    f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
                )


async def _unblock(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    members: Union[List[discord.Member], discord.Member],
    reason: str,
    **kwargs: Any,
):
    members = [members] if not isinstance(members, list) else members
    for member in members:
        try:
            if channel.permissions_for(member).send_messages:
                await destination.send(
                    f"{ctx.author.mention} {member.name} is already unblocked. They can send message"
                )
            else:
                overwrite = channel.overwrites
                if member_overwrite := overwrite.get(member):
                    member_overwrite.update(
                        send_messages=False,
                        view_channel=False,
                    )
                else:
                    overwrite[member] = discord.PermissionOverwrite(
                        send_messages=False,
                        view_channel=False,
                    )
                await channel.edit(overwrites=overwrite, reason=reason)
                # await channel.set_permissions(
                #     member,
                #     send_messages=None,
                #     view_channel=None,
                #     reason=reason,
                # )
            await destination.send(
                f"{ctx.author.mention} overwrite permission(s) for **{member}** has been deleted!"
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


# LOCK


async def _text_lock(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    reason: str = None,
    **kwargs: Any,
):
    try:
        overwrite = channel.overwrites
        if _overwrite := overwrite.get(guild.deafult_role):
            _overwrite.update(
                send_messages=False,
            )
        else:
            overwrite[guild.deafult_role] = discord.PermissionOverwrite(
                send_messages=False,
            )
        await channel.edit(overwrites=overwrite, reason=reason)
        # await channel.set_permissions(
        #     guild.default_role, send_messages=False, reason=reason
        # )
        await destination.send(f"{ctx.author.mention} channel locked.")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


async def _vc_lock(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: Union[discord.VoiceChannel, discord.StageChannel],
    reason: str = None,
    **kwargs: Any,
):
    if not channel:
        return
    try:
        overwrite = channel.overwrites
        if _overwrite := overwrite.get(guild.deafult_role):
            _overwrite.update(
                connect=False
            )
        else:
            overwrite[guild.deafult_role] = discord.PermissionOverwrite(
                connect=False
            )
        await channel.edit(overwrites=overwrite, reason=reason)
        # await channel.set_permissions(guild.default_role, connect=False, reason=reason)
        await destination.send(f"{ctx.author.mention} channel locked.")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


# UNLOCK


async def _text_unlock(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    reason: str = None,
    **kwargs: Any,
):
    try:
        overwrite = channel.overwrites
        if _overwrite := overwrite.get(guild.deafult_role):
            _overwrite.update(
                send_messages=None,
            )
        else:
            overwrite[guild.deafult_role] = discord.PermissionOverwrite(
                send_messages=None,
            )
        await channel.edit(overwrites=overwrite, reason=reason)
        # await channel.set_permissions(
        #     guild.default_role, send_messages=None, reason=reason
        # )
        await destination.send(f"{ctx.author.mention} channel unlocked.")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


async def _vc_unlock(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: Union[discord.VoiceChannel, discord.StageChannel],
    reason: str = None,
    **kwargs: Any,
):
    if not channel:
        return
    try:
        overwrite = channel.overwrites
        if _overwrite := overwrite.get(guild.deafult_role):
            _overwrite.update(
                connect=None
            )
        else:
            overwrite[guild.deafult_role] = discord.PermissionOverwrite(
                connect=None
            )
        await channel.edit(overwrites=overwrite, reason=reason)
        # await channel.set_permissions(guild.default_role, connect=None, reason=reason)
        await destination.send(f"{ctx.author.mention} channel unlocked.")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


# EXTRA


async def _change_nickname(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    name: str,
    **kwargs: Any,
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


async def _change_channel_topic(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    text: str,
    **kwargs: Any,
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


async def _change_channel_name(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    text: str,
    **kwargs: Any,
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


async def _slowmode(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    seconds: int,
    channel: discord.TextChannel,
    reason: str,
    **kwargs: Any,
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


async def _clone(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    channel: discord.TextChannel,
    reason: str,
    **kwargs: Any,
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


# VOICE MOD


async def _voice_mute(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    **kwargs: Any,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        await member.edit(
            mute=True,
            reason=reason,
        )
        await destination.send(f"{ctx.author.mention} voice muted **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_unmute(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    **kwargs: Any,
):
    try:
        await member.edit(
            mute=False,
            reason=reason,
        )
        await destination.send(f"{ctx.author.mention} voice unmuted **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_deafen(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    **kwargs: Any,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        await member.edit(
            deafen=True,
            reason=reason,
        )
        await destination.send(f"{ctx.author.mention} voice deafened **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_undeafen(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    **kwargs: Any,
):
    try:
        await member.edit(
            deafen=False,
            reason=reason,
        )
        await destination.send(f"{ctx.author.mention} voice undeafened **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_kick(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    reason: str,
    **kwargs: Any,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        await member.edit(
            voice_channel=None,
            reason=reason,
        )
        await destination.send(f"{ctx.author.mention} voice kicked **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_ban(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    channel: Union[discord.VoiceChannel, discord.StageChannel],
    reason: str,
    **kwargs: Any,
):
    if ctx.author.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx.author.mention} can not {command_name} the {member}, as the their's role is above you"
        )
    try:
        overwrite = channel.overwrites
        if member_overwrite := overwrite.get(member):
            member_overwrite.update(
                connect=False
            )
        else:
            overwrite[member] = discord.PermissionOverwrite(
                connect=False
            )
        await channel.edit(overwrites=overwrite, reason=reason)
        # await channel.set_permissions(
        #     member,
        #     connect=False,
        #     reason=reason,
        # )
        await destination.send(f"{ctx.author.mention} voice banned **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_unban(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    member: discord.Member,
    channel: Union[discord.VoiceChannel, discord.StageChannel],
    reason: str,
    **kwargs: Any,
):
    try:
        overwrite = channel.overwrites
        if member_overwrite := overwrite.get(member):
            member_overwrite.update(
                connect=False
            )
        else:
            overwrite[member] = discord.PermissionOverwrite(
                connect=False
            )
        await channel.edit(overwrites=overwrite, reason=reason)
        # await channel.set_permissions(
        #     member,
        #     reason=reason,
        #     connect=None,
        # )
        await destination.send(f"{ctx.author.mention} voice unbanned **{member}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _emoji_delete(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    emojis: List[Union[discord.Emoji, discord.PartialEmoji]],
    reason: str,
    **kwargs: Any,
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


async def _emoji_add(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    emojis: List[Union[discord.Emoji, discord.PartialEmoji]],
    reason: str,
    **kwargs: Any,
):
    for emoji in emojis:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji.url) as res:
                    raw = await res.read()
            ej = await guild.create_custom_emoji(
                name=emoji.name,
                image=raw,
                reason=reason,
            )
            await destination.send(f"{ctx.author.mention} emoji created {ej}")
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{emoji.name} ({emoji.id})**. Error raised: **{e}**"
            )


async def _emoji_addurl(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    url: str,
    name: str,
    reason: str,
    **kwargs: Any,
):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as res:
                raw = await res.read()
        emoji = await guild.create_custom_emoji(
            name=name,
            image=raw,
            reason=reason,
        )
        await destination.send(f"{ctx.author.mention} emoji created {emoji}")
    except Exception as e:
        await destination.send(f"Can not able to {command_name}. Error raised: **{e}**")


async def _emoji_rename(
    *,
    guild: discord.Guild,
    command_name: str,
    ctx: Context,
    destination: discord.TextChannel,
    emoji: Union[discord.Emoji, discord.PartialEmoji],
    name: str,
    reason: str,
    **kwargs: Any,
):
    try:
        await emoji.edit(
            name=name,
            reason=reason,
        )
        await destination.send(
            f"{ctx.author.mention} {emoji} name edited to **{name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{emoji.name} ({emoji.id})**. Error raised: **{e}**"
        )


async def do_removal(
    ctx: Context,
    limit: int,
    predicate: Callable[[discord.Message], Any],
    *,
    before: Optional[int] = None,
    after: Optional[int] = None,
):
    if limit > 2000:
        return await ctx.send(f"Too many messages to search given ({limit}/2000)")

    if before is None:
        passed_before = ctx.message
    else:
        passed_before = discord.Object(id=before)

    if after is not None:
        passed_after = discord.Object(id=after)
    else:
        passed_after = None

    try:
        deleted = await ctx.channel.purge(
            limit=limit, before=passed_before, after=passed_after, check=predicate
        )
    except discord.HTTPException as e:
        return await ctx.send(
            f"Can not able to {ctx.command.qualified_name}. Error raised: **{e}** (try a smaller search?)"
        )

    spammers = Counter(m.author.display_name for m in deleted)
    deleted = len(deleted)
    messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
    if deleted:
        messages.append("")
        spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
        messages.extend(f"**{name}**: {count}" for name, count in spammers)

    to_send = "\n".join(messages)

    if len(to_send) > 2000:
        await ctx.send(f"Successfully removed {deleted} messages.", delete_after=10)
    else:
        await ctx.send(to_send, delete_after=10)


MEMBER_REACTION: Dict[str, Callable] = {
    "\N{HAMMER}": _ban,
    "\N{WOMANS BOOTS}": _kick,
    "\N{ZIPPER-MOUTH FACE}": _mute,
    "\N{GRINNING FACE WITH SMILING EYES}": _unmute,
    "\N{CROSS MARK}": _block,
    "\N{HEAVY LARGE CIRCLE}": _unblock,
    "\N{UPWARDS BLACK ARROW}": _add_roles,
    "\N{DOWNWARDS BLACK ARROW}": _remove_roles,
    "\N{LOWER LEFT FOUNTAIN PEN}": _change_nickname,
}
TEXT_REACTION: Dict[str, Callable] = {
    "\N{LOCK}": _text_lock,
    "\N{OPEN LOCK}": _text_unlock,
    "\N{MEMO}": _change_channel_topic,
    "\N{LOWER LEFT FOUNTAIN PEN}": _change_channel_name,
}

VC_REACTION: Dict[str, Callable] = {
    "\N{LOCK}": _vc_lock,
    "\N{OPEN LOCK}": _vc_unlock,
    "\N{LOWER LEFT FOUNTAIN PEN}": _change_channel_name,
}
ROLE_REACTION: Dict[str, Callable] = {
    "\N{UPWARDS BLACK ARROW}": _role_hoist,
    "\N{DOWNWARDS BLACK ARROW}": _role_hoist,
    "\N{RAINBOW}": _change_role_color,
    "\N{LOWER LEFT FOUNTAIN PEN}": _change_role_name,
}
