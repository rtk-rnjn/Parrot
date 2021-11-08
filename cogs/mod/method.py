from __future__ import annotations

from utilities.database import parrot_db
import discord, asyncio, aiohttp, time

from datetime import datetime

from utilities.infraction import Infraction

collection = parrot_db['server_config']
mute_collection = parrot_db['mute']


async def create_mute_task(guild_id: int, author_id: int, role_id: int, timestamp: float):
    post = {
        'guild_id': guild_id,
        'author_id': author_id,
        'role_id': role_id,
        'timestamp': timestamp
    }
    await mute_collection.insert_one(post)

async def is_role_mod(guild, role) -> bool:
    data = await collection.find_one({'_id': guild.id})
    if not data: return False
    r = guild.get_role(data['mod_role'])
    if not r: return False
    if role.id == r.id: return True


async def _add_roles_bot(guild, command_name, ctx_author, destination,
                         operator, role, reason):
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit admin role.")
    is_mod = await is_role_mod(guild, role)
    if is_mod:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit mod role")
    for member in guild.members:
        try:
            if not member.bot: pass
            else:
                if operator.lower() in ['+', 'add', 'give']:
                    await member.add_roles(role, reason=reason)
                elif operator.lower() in ['-', 'remove', 'take']:
                    await member.remove_roles(role, reason=reason)
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


async def _add_roles_humans(guild, command_name, ctx_author, destination,
                            operator, role, reason):
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit admin role.")
    is_mod = await is_role_mod(guild, role)
    if is_mod:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit mod role")
    for member in guild.members:
        try:
            if member.bot: pass
            else:
                if operator.lower() in ['+', 'add', 'give']:
                    await member.add_roles(role, reason=reason)
                elif operator.lower() in ['-', 'remove', 'take']:
                    await member.remove_roles(role, reason=reason)
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


async def _add_roles(guild, command_name, ctx_author, destination, member,
                     role, reason):
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit admin role.")
    is_mod = await is_role_mod(guild, role)
    if is_mod:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit mod role")
    try:
        await member.add_roles(
            role,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} given **{role.name} ({role.id})** to **{member.name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _remove_roles(guild, command_name, ctx_author, destination, member,
                        role, reason):
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit admin role.")
    is_mod = await is_role_mod(guild, role)
    if is_mod:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit mod role")
    try:
        await member.remove_roles(
            role,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} removed **{role.name} ({role.id})** from **{member.name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _role_hoist(guild, command_name, ctx_author, destination, role,
                      _bool, reason):
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit admin role.")
    is_mod = await is_role_mod(guild, role)
    if is_mod:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit mod role")
    try:
        await role.edit(
            hoist=_bool,
            reason=
            f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}'
        )
        await destination.send(f"{ctx_author.mention} **{role.name} ({role.id})** is now hoisted")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )


async def _change_role_name(guild, command_name, ctx_author, destination, role,
                            text, reason):
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit admin role.")
    is_mod = await is_role_mod(guild, role)
    if is_mod:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit mod role")
    try:
        await role.edit(
            name=text,
            reason=
            f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}'
        )
        await destination.send(f"{ctx_author.mention} role name changed to **{text} ({role.id})**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )


async def _change_role_color(guild, command_name, ctx_author, destination,
                             role, int_, reason):
    if role.permissions.administrator:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit admin role.")
    is_mod = await is_role_mod(guild, role)
    if is_mod:
        return await destination.send(
            f"{ctx_author.mention} can not assign/remove/edit mod role")
    try:
        await role.edit(
            color=discord.Color.value(int(int_)),
            reason=
            f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}'
        )
        await destination.send(f"{ctx_author.mention} **{role.name} ({role.id})** color changed successfully")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{role.name} ({role.id})**. Error raised: **{e}**"
        )


# BAN


async def _ban(guild, command_name, ctx_author, destination, member, days,
               reason):
    try:
        if member.id == ctx_author.id or member.id == 800780974274248764:
            await destination.send(
                f"{ctx_author.mention} don't do that, Bot is only trying to help"
            )
        else:
            await guild.ban(
                member,
                reason=
                f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}',
                delete_message_days=days)
            await destination.send(
                f"{ctx_author.mention} **`{member}`** is banned!"
            )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _mass_ban(guild, command_name, ctx_author, destination, members,
                    days, reason):
    _list = members
    for member in members:
        try:
            if member.id == ctx_author.id or member.id == 800780974274248764:
                await destination.send(
                    f"{ctx_author.mention} don't do that, Bot is only trying to help"
                )
            else:
                await guild.ban(
                    member,
                    reason=
                    f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}',
                    delete_message_days=days)
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
            _list.remove(member)
    await destination.send(
        f"{ctx_author.mention} **{', '.join([str(member) for member in members])}** are banned!"
    )


async def _softban(guild, command_name, ctx_author, destination, member,
                   reason):
    for member in member:
        try:
            if member.id == ctx_author.id or member.id == 800780974274248764:
                await destination.send(
                    f"{ctx_author.mention} don't do that, Bot is only trying to help"
                )
            else:
                await member.ban(
                    reason=
                    f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}'
                )

                banned_users = await guild.bans()
                member_n, member_d = member.name, member.discriminator
                for ban_entry in banned_users:
                    user = ban_entry.user
                    if (user.name, user.discriminator) == (member_n, member_d):
                        await guild.unban(user)

                await destination.send(
                    f'{ctx_author.mention} **{member}** is soft banned!'
                )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


async def _unban(guild, command_name, ctx_author, destination, member, reason):
    try:
        await guild.unban(
            member,
            reason=
            f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}'
        )
        await destination.send(
            f"{ctx_author.mention} **`{member}`** is unbanned!"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


# MUTE


async def _mute(guild, command_name, ctx_author, destination, member, seconds,
                reason):
    if member.id == ctx_author.id or member.id == 800780974274248764:
        await destination.send(
            f"{ctx_author.mention} don't do that, Bot is only trying to help"
        )
    data = await collection.find_one({'_id': guild.id})
    if not data:
        post = {
            '_id': guild.id,
            'prefix': '$',
            'mod_role': None,
            'action_log': None,
            'mute_role': None,
        }
        await collection.insert_one(post)

    data = await collection.find_one({'_id': guild.id})

    muted = guild.get_role(data['mute_role']) or discord.utils.get(
        guild.roles, name="Muted")

    if not muted:
        muted = await guild.create_role(
            name="Muted",
            reason=
            f"Setting up mute role. it's first command is execution, by {ctx_author.name} ({ctx_author.id})"
        )
        for channel in guild.channels:
            try:
                await channel.set_permissions(muted,
                                              send_messages=False,
                                              read_message_history=False)
            except Exception:
                pass
        await collection.update_one({'_id': guild.id},
                                    {'$set': {
                                        'mute_role': muted.id
                                    }})
    if seconds is None:
        try:
            await member.add_roles(
                muted,
                reason=
                f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
            )
            await destination.send(f"{ctx_author.mention} **{member}** is muted till death")
            return
        except Exception as e:
            await destination.send(f"Can not able to {command_name} **{member}**. Error raised: **{e}**")
    else:
        try:
            await member.add_roles(
                muted,
                reason=
                f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
            )
            await create_mute_task(guild.id, member.id, muted.id, seconds)
            await destination.send(f"{ctx_author.mention} **{member}** is muted till **<t:{int(seconds)}>**")
            return
        except Exception as e:
            await destination.send(f"Can not able to {command_name} **{member}**. Error raised: **{e}**")
        

async def _unmute(guild, command_name, ctx_author, destination, member,
                  reason):
    data = await collection.find_one({'_id': guild.id})
    if not data:
        post = {
            '_id': guild.id,
            'prefix': '$',
            'mod_role': None,
            'action_log': None,
            'mute_role': None,
        }
        await collection.insert_one(post)
    data = await collection.find_one({'_id': guild.id})

    muted = guild.get_role(data['mute_role']) or discord.utils.get(
        guild.roles, name="Muted")
    try:
        if muted in member.roles:
            await destination.send(
                f'{ctx_author.mention} **{member}** has been unmuted now!'
            )
            await member.remove_roles(
                muted,
                reason=
                f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}'
            )
        else:
            await destination.send(
                f"{ctx_author.mention} **{member.name}** already unmuted :')")
        await mute_collection.delete_one({'author_id': member.id, 'guild_id': guild.id})
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _kick(guild, command_name, ctx_author, destination, member, reason):
    try:
        if member.id == ctx_author.id or member.id == 800780974274248764:
            await destination.send(
                f"{ctx_author.mention} don't do that, Bot is only trying to help"
            )
        else:
            await member.kick(
                reason=
                f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}'
            )
            await destination.send(
                f'{ctx_author.mention} **`{member}`** is kicked from the server!'
            )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _mass_kick(guild, command_name, ctx_author, destination, members,
                     reason):
    _list = members
    for member in members:
        try:
            if member.id == ctx_author.id or member.id == 800780974274248764:
                await destination.send(
                    f"{ctx_author.mention} don't do that, Bot is only trying to help"
                )
            else:
                await member.kick(
                    reason=
                    f'Action requested by: {ctx_author.name} ({ctx_author.id}) | Reason: {reason}'
                )
        except Exception as e:
            _list.remove(member)
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )
        await asyncio.sleep(0.25)
    await destination.send(
        f"{ctx_author.mention} **{', '.join([str(member) for member in members])}** are kicked from the server!"
    )


# BLOCK


async def _block(guild, command_name, ctx_author, destination, channel, member,
                 reason):
    for member in member:
        try:
            if member.id == ctx_author.id or member.id == 800780974274248764:
                await destination.send(
                    f"{ctx_author.mention} don't do that, Bot is only trying to help"
                )
            else:
                await channel.set_permissions(
                    member,
                    send_messages=False,
                    view_channel=False,
                    reason=
                    f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
                )
                await destination.send(
                    f'{ctx_author.mention} overwrite permission(s) for **{member}** has been created! **View Channel, and Send Messages** is denied!'
                )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


async def _unblock(guild, command_name, ctx_author, destination, channel,
                   member, reason):
    for member in member:
        try:
            if channel.permissions_for(member).send_messages:
                await destination.send(
                    f"{ctx_author.mention} {member.name} is already unblocked. They can send message"
                )
            else:
                await channel.set_permissions(
                    member,
                    send_messages=None,
                    view_channel=None,
                    reason=
                    f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
                )
            await destination.send(
                f'{ctx_author.mention} overwrite permission(s) for **{member}** has been deleted!'
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
            )


# LOCK


async def _text_lock(guild, command_name, ctx_author, destination, channel):
    try:

        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx_author.name} ({ctx_author.id})",
            overwrite=overwrite)
        await destination.send(f'{ctx_author.mention} channel locked.')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


async def _vc_lock(guild, command_name, ctx_author, destination, channel):
    if not channel: return
    try:
        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.connect = False
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx_author.name} ({ctx_author.id})",
            overwrite=overwrite)
        await destination.send(f'{ctx_author.mention} channel locked.')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


# UNLOCK


async def _text_unlock(guild, command_name, ctx_author, destination, channel):

    try:
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx_author.name} ({ctx_author.id})",
            send_messages=None)
        await destination.send(f'{ctx_author.mention} channel unlocked.')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


async def _vc_unlock(guild, command_name, ctx_author, destination, channel):
    if not channel: return
    try:
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx_author.name} ({ctx_author.id})",
            connect=None)
        await destination.send(f'{ctx_author.mention} channel unlocked.')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


# EXTRA


async def _change_nickname(guild, command_name, ctx_author, destination,
                           member, name):
    try:
        await member.edit(
            nick=name,
            reason=f'Action Requested by {ctx_author.name} ({ctx_author.id})')
        await destination.send(
            f"{ctx_author.mention} **{member}** nickname changed to **{name}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _change_channel_topic(guild, command_name, ctx_author, destination,
                                channel, text):
    try:
        await channel.edit(
            topic=text,
            reason=f'Action Requested by {ctx_author.name} ({ctx_author.id})')
        await destination.send(
            f"{ctx_author.mention} **{channel.name}** topic changed to **{text}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


async def _change_channel_name(guild, command_name, ctx_author, destination,
                               channel, text):
    try:
        await channel.edit(
            name=text,
            reason=f'Action Requested by {ctx_author.name} ({ctx_author.id})')
        await destination.send(
            f"{ctx_author.mention} **{channel}** name changed to **{text}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


async def _slowmode(guild, command_name, ctx_author, destination, seconds,
                    channel, reason):
    if seconds:
        try:
            if (seconds <= 21600) and (seconds > 0):
                await channel.edit(
                    slowmode_delay=seconds,
                    reason=
                    f"Action Requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
                )
                await destination.send(
                    f"{ctx_author.mention} {channel} is now in slowmode of **{seconds}**, to reverse type [p]slowmode 0"
                )
            elif seconds == 0 or seconds.lower() == 'off':
                await channel.edit(
                    slowmode_delay=seconds,
                    reason=
                    f"Action Requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
                )
                await destination.send(
                    f"{ctx_author.mention} **{channel}** is now not in slowmode.")
            elif (seconds >= 21600) or (seconds < 0):
                await destination.send(
                    f"{ctx_author.mention} you can't set slowmode in negative numbers or more than 21600 seconds"
                )
            else:
                return
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
            )


async def _clone(guild, command_name, ctx_author, destination, channel,
                 reason):
    try:
        new_channel = await channel.clone(
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await channel.delete(
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await new_channel.send(f"{ctx_author.mention}", delete_after=5)
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{channel.name}**. Error raised: **{e}**"
        )


# VOICE MOD


async def _voice_mute(guild, command_name, ctx_author, destination, member,
                      reason):
    try:
        await member.edit(
            mute=True,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} voice muted **{member}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_unmute(guild, command_name, ctx_author, destination, member,
                        reason):
    try:
        await member.edit(
            mute=False,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} voice unmuted **{member}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_deafen(guild, command_name, ctx_author, destination, member,
                        reason):
    try:
        await member.edit(
            deafen=True,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} voice deafened **{member}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_undeafen(guild, command_name, ctx_author, destination, member,
                          reason):
    try:
        await member.edit(
            deafen=False,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} voice undeafened **{member}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_kick(guild, command_name, ctx_author, destination, member,
                      reason):
    try:
        await member.edit(
            voice_channel=None,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} voice kicked **{member}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_ban(guild, command_name, ctx_author, destination, member,
                     channel, reason):
    try:
        await channel.set_permissions(
            member,
            connect=False,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} voice banned **{member}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _voice_unban(guild, command_name, ctx_author, destination, member,
                       channel, reason):
    try:
        await channel.set_permissions(
            member,
            overwrite=None,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} voice unbanned **{member}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{member}**. Error raised: **{e}**"
        )


async def _emoji_delete(guild, command_name, ctx_author, destination, emoji,
                        reason):
    for emoji in emoji:
        try:
            if emoji.guild.id == guild.id:
                await emoji.delete(
                    reason=
                    f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
                )
                await destination.send(f"{ctx_author.mention} **{emoji}** deleted!")
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{emoji.name} ({emoji.id})**. Error raised: **{e}**"
            )


async def _emoji_add(guild, command_name, ctx_author, destination, emoji,
                     reason):
    ls = []
    for emoji in emoji:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji.url) as res:
                    raw = await res.read()
            ej = await guild.create_custom_emoji(
                name=emoji.name,
                image=raw,
                reason=
                f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
            )
            await destination.send(f"{ctx_author.mention} emoji created {ej}")
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} **{emoji.name} ({emoji.id})**. Error raised: **{e}**"
            )


async def _emoji_addurl(guild, command_name, ctx_author, destination, url,
                        name, reason):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as res:
                raw = await res.read()
        emoji = await guild.create_custom_emoji(
            name=name,
            image=raw,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(f"{ctx_author.mention} emoji created {emoji}")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name}. Error raised: **{e}**"
        )


async def _emoji_rename(guild, command_name, ctx_author, destination, emoji,
                        name, reason):
    try:
        await emoji.edit(
            name=name,
            reason=
            f"Action requested by {ctx_author.name} ({ctx_author.id}) | Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} {emoji} name edited to **{name}**")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} **{emoji.name} ({emoji.id})**. Error raised: **{e}**"
        )


MEMBER_REACTION = ['🔨', '👢', '🤐', '😁', '❌', '⭕', '⬆️', '⬇️', '🖋️']
TEXT_REACTION = ['🔒', '🔓', '📝', '🖋️']
VC_REACTION = ['🔒', '🔓', '🖋️']
ROLE_REACTION = ['🔒', '🔓', '🌈', '🖋️']


async def _warn(bot, guild, command_name, ctx_author, destination, target, reason):
    infrn = Infraction(
        bot, 
        guild_id=guild.id, 
        user_id=target.id, 
        reason=reason, 
        mod=ctx_author.id, 
        at=time.time(), 
        expires_at=None
    )
    if target.guild_permissions.administrator:
        await destination.send(f"{ctx_author.mention} can not warn Server Admin")
        return

    data = await infrn.add_warn()
    await destination.send(f"{ctx_author.mention} **{target}** warned.")
    try:
        await target.send(f"{target.mention} you are being warned from **{guild.name}** for: **{reason}**")
    except Exception:
        pass
    

async def _del_all_warn(bot, guild, command_name, ctx_author, destination, target, reason):
    infrn = Infraction(
        bot, 
        guild_id=guild.id,
        user_id=target.id,
        reason=reason,
        mod=ctx_author.id,
        at=time.time(),
        expires_at=None
    )
    if target.guild_permissions.administrator:
        await destination.send(f"{ctx_author.mention} can not warn Server Admin")
        return

    await destination.send(f"{ctx_author.mention} **{target}** warned")
    try:
        await target.send(f"{target.mention} you are being warned from **{guild.name}** for: **{reason}**")
    except Exception:
        pass
    
    await infrn.del_warn_all()

async def _del_warn(bot, guild, command_name, ctx_author, destination, target, reason):
    infrn = Infraction(
        bot, 
        guild_id=guild.id,
        user_id=target.id,
        reason=reason,
        mod=ctx_author.id,
        at=time.time(),
        expires_at=None
    )
    if target.guild_permissions.administrator:
        await destination.send(f"{ctx_author.mention} can not warn Server Admin")
        return
