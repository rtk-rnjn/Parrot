from database.server_config import collection, guild_join, guild_update
import discord, asyncio
from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["parrot_db"]

# ROLES
async def _add_roles_bot(guild, command_name, destination, operator, role,
                         reason):
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
                f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
            )


async def _add_roles_humans(guild, command_name, destination, operator, role,
                            reason):
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
                f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
            )


async def _add_roles(guild, command_name, ctx_author, destination, member,
                     role, reason):

    if guild.me.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx_author.mention} can't give the role to {member.name} as it's role is above the bot"
        )

    try:
        await member.add_roles(
            role,
            reason=
            f"Action requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} given {role.name}({role.id}) to {member.name}"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _remove_roles(guild, command_name, ctx_author, destination, member,
                        role, reason):

    if guild.me.top_role.position < member.top_role.position:
        return await destination.send(
            f"{ctx_author.mention} can't give the role to {member.name} as it's role is above the bot"
        )
    try:
        await member.remove_roles(
            role,
            reason=
            f"Action requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
        )
        await destination.send(
            f"{ctx_author.mention} removed {role.name}({role.id}) from {member.name}"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _role_hoist(guild, command_name, ctx_author, destination, role,
                      _bool, reason):
    if guild.me.top_role.position < role.position:
        return await destination.send(
            f"{ctx_author.mention} can't edit {role.name} as it's role is above the bot"
        )
    try:
        await role.edit(
            hoist=_bool,
            reason=
            f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {role.name}({role.id}). Error raised: {e}"
        )


async def _change_role_name(guild, command_name, ctx_author, destination, role,
                            text, reason):
    if guild.me.top_role.position < role.position:
        return await destination.send(
            f"{ctx_author.mention} can't edit {role.name} as it's role is above the bot"
        )
    try:
        await role.edit(
            name=text,
            reason=
            f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {role.name}({role.id}). Error raised: {e}"
        )


async def _change_role_color(guild, command_name, ctx_author, destination,
                             role, int_, reason):
    if guild.me.top_role.position < role.position:
        return await destination.send(
            f"{ctx_author.mention} can't edit {role.name} as it's role is above the bot"
        )
    try:
        await role.edit(
            color=discord.Color.value(int(int_)),
            reason=
            f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {role.name}({role.id}). Error raised: {e}"
        )


# BAN


async def _ban(guild, command_name, ctx_author, destination, member, days,
               reason):
    try:
        if member.id == ctx_author.id or member.id == 800780974274248764:
            pass
        else:
            await guild.ban(
                member,
                reason=
                f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}',
                delete_message_days=days)
            await destination.send(
                f"**`{member.name}#{member.discriminator}`** is banned! Responsible moderator: **`{ctx_author.name}#{ctx_author.discriminator}`**! Reason: **{reason}**"
            )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _mass_ban(guild, command_name, ctx_author, destination, members,
                    days, reason):
    _list = members
    for member in members:
        try:
            if member.id == ctx_author.id or member.id == 800780974274248764:
                pass
            else:
                await guild.ban(
                    member,
                    reason=
                    f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}',
                    delete_message_days=days)
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
            )
            _list.remove(member)
    await destination.send(
        f"**{', '.join([member.name for member in members])}** are banned! Responsible moderator: **`{ctx_author.name}#{ctx_author.discriminator}`**! Total: **{len(members)}**! Reason: **{reason}**"
    )


async def _softban(guild, command_name, ctx_author, destination, member,
                   reason):
    for member in member:
        try:
            if member.id == ctx_author.id or member.id == 800780974274248764:
                pass
            else:
                await member.ban(
                    reason=
                    f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
                )

                banned_users = await guild.bans()
                member_n, member_d = member.name, member.discriminator
                for ban_entry in banned_users:
                    user = ban_entry.user
                    if (user.name, user.discriminator) == (member_n, member_d):
                        await guild.unban(user)

                await destination.send(
                    f'**`{member.name}#{member.discriminator}`** is banned then unbanned! Responsible moderator: **`{ctx_author.name}#{ctx_author.discriminator}`**! Reason: **{reason}**'
                )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
            )


async def _unban(guild, command_name, ctx_author, destination, member, reason):
    try:
        await guild.unban(
            member,
            reason=
            f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
        )
        await destination.send(
            f"**`{member.name}#{member.discriminator}`** is unbanned! Responsible moderator: **`{ctx_author.name}#{ctx_author.discriminator}`**! Reason: **{reason}**"
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


# MUTE


async def _mute(guild, command_name, ctx_author, destination, member, seconds,
                reason):
    if not collection.find_one({'_id': guild.id}):
        await guild_join(guild.id)

    data = collection.find_one({'_id': guild.id})

    muted = guild.get_role(data['mute_role']) or discord.utils.get(
        guild.roles, name="Muted")

    if not muted:
        muted = await guild.create_role(
            name="Muted",
            reason=
            f"Setting up mute role. it's first command is execution, by {ctx_author.name}({ctx_author.id})"
        )
        for channel in guild.channels:
            try:
                await channel.set_permissions(muted,
                                              send_messages=False,
                                              read_message_history=False)
            except Exception:
                pass
        await guild_update(guild.id, {'mute_role': muted.id})
    if seconds is None: seconds = 0
    try:
        if member.id == ctx_author.id or member.id == 800780974274248764:
            pass
        else:
            await member.add_roles(
                muted,
                reason=
                f"Action requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
            )
            await destination.send(
                f"{ctx_author.mention} **{member.name}** has been successfully muted {'for **' + str(seconds) + 's**' if (seconds > 0) and (type(seconds) is int) else ''}!"
            )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
        )

    if seconds > 0:
        await asyncio.sleep(seconds)
        try:
            await member.remove_roles(
                muted,
                reason=
                f"Action requested by {ctx_author.name}({ctx_author.id}) || Reason: Mute Duration Expired"
            )
        except Exception:
            pass


async def _unmute(guild, command_name, ctx_author, destination, member,
                  reason):
    if not collection.find_one({'_id': guild.id}):
        await guild_join(guild.id)

    data = collection.find_one({'_id': guild.id})

    muted = guild.get_role(data['mute_role']) or discord.utils.get(
        guild.roles, name="Muted")
    try:
        if muted in member.roles:
            await destination.send(
                f'{ctx_author.mention} **{member.name}** has been unmuted now!'
            )
            await member.remove_roles(
                muted,
                reason=
                f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
            )
        else:
            await destination.send(
                f"{ctx_author.mention} **{member.name}** already unmuted :')")
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _kick(guild, command_name, ctx_author, destination, member, reason):
    try:
        if member.id == ctx_author.id or member.id == 800780974274248764:
            pass
        else:
            await member.kick(
                reason=
                f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
            )
            await destination.send(
                f'**`{member.name}#{member.discriminator}`** is kicked! Responsible moderator: **`{ctx_author.name}#{ctx_author.discriminator}`**! Reason: **{reason}**'
            )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _mass_kick(guild, command_name, ctx_author, destination, members,
                     reason):
    _list = members
    for member in members:
        try:
            if member.id == ctx_author.id or member.id == 800780974274248764:
                pass
            else:
                await member.kick(
                    reason=
                    f'Action requested by: {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
                )
        except Exception as e:
            _list.remove(member)
            await destination.send(
                f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
            )
        await asyncio.sleep(0.25)
    await destination.send(
        f"**{', '.join([member.name for member in members])}** are kicked! Responsible moderator: **`{ctx_author.name}#{ctx_author.discriminator}`**! Total: **{len(members)}**! Reason: **{reason}**"
    )


# BLOCK


async def _block(guild, command_name, ctx_author, destination, channel, member,
                 reason):
    for member in member:
        try:
            if member.id == ctx_author.id or member.id == 800780974274248764:
                pass  # cant mod the calling author or the bot itself
            else:
                await channel.set_permissions(
                    member,
                    send_messages=False,
                    reason=
                    f"Action requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
                )
                await destination.send(
                    f'{ctx_author.mention} overwrite permission(s) for **{member.name}** has been created! **View Channel, and Send Messages** is denied!'
                )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
            )


async def _unblock(guild, command_name, ctx_author, destination, channel,
                   member, reason):
    for member in member:
        try:
            if member.permissions_in(channel).send_messages:
                await destination.send(
                    f"{ctx_author.mention} {member.name} is already unblocked. They can send message"
                )
            else:
                await channel.set_permissions(
                    member,
                    overwrite=None,
                    reason=
                    f"Action requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
                )
            await destination.send(
                f'{ctx_author.mention} overwrite permission(s) for **{member.name}** has been deleted!'
            )
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
            )


# LOCK


async def _text_lock(guild, command_name, ctx_author, destination, channel):
    try:

        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx_author.name}({ctx_author.id})",
            overwrite=overwrite)
        await destination.send(f'{ctx_author.mention} channel locked.')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {channel.name}. Error raised: {e}"
        )


async def _vc_lock(guild, command_name, ctx_author, destination, channel):
    if not channel: return
    try:
        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.connect = False
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx_author.name}({ctx_author.id})",
            overwrite=overwrite)
        await destination.send(f'{ctx_author.mention} channel locked.')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {channel.name}. Error raised: {e}"
        )


# UNLOCK


async def _text_unlock(guild, command_name, ctx_author, destination, channel):

    try:
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx_author.name}({ctx_author.id})",
            overwrite=None)
        await destination.send(f'{ctx_author.mention} channel unlocked.')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {channel.name}. Error raised: {e}"
        )


async def _vc_unlock(guild, command_name, ctx_author, destination, channel):
    if not channel: return
    try:
        await channel.set_permissions(
            guild.default_role,
            reason=f"Action requested by {ctx_author.name}({ctx_author.id})",
            overwrite=None)
        await destination.send(f'{ctx_author.mention} channel unlocked.')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {channel.name}. Error raised: {e}"
        )


# EXTRA


async def _change_nickname(guild, command_name, ctx_author, destination,
                           member, name, reason):
    try:
        await member.edit(
            nick=name,
            reason=
            f'Action Requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}'
        )
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _change_channel_topic(guild, command_name, ctx_author, destination,
                                channel, text):
    try:
        await channel.edit(
            topic=text,
            reason=f'Action Requested by {ctx_author.name}({ctx_author.id})')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {channel.name}. Error raised: {e}"
        )


async def _change_channel_name(guild, command_name, ctx_author, destination,
                               channel, text):
    try:
        await channel.edit(
            name=text,
            reason=f'Action Requested by {ctx_author.name}({ctx_author.id})')
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {channel.name}. Error raised: {e}"
        )


async def _slowmode(guild, command_name, ctx_author, destination, seconds,
                    channel, reason):
    if seconds:
        try:
            if (seconds <= 21600) and (seconds > 0):
                await channel.edit(
                    slowmode_delay=seconds,
                    reason=
                    f"Action Requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
                )
                await destination.send(
                    f"{ctx_author.mention} {channel} is now in slowmode of **{seconds}**, to reverse type [p]slowmode 0"
                )
            elif seconds == 0 or seconds.lower() == 'off':
                await channel.edit(
                    slowmode_delay=seconds,
                    reason=
                    f"Action Requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
                )
                await destination.send(
                    f"{ctx_author.mention} {channel} is now not in slowmode.")
            elif (seconds >= 21600) or (seconds < 0):
                await destination.send(
                    f"{ctx_author.mention} you can't set slowmode in negative numbers or more than 21600 seconds"
                )
            else:
                return
        except Exception as e:
            await destination.send(
                f"Can not able to {command_name} {channel.name}. Error raised: {e}"
            )


async def _clone(guild, command_name, ctx_author, destination, channel,
                 reason):
    try:
        new_channel = await channel.clone(
            reason=
            f"Action requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
        )
        await channel.delete(
            reason=
            f"Action requested by {ctx_author.name}({ctx_author.id}) || Reason: {reason}"
        )
        await new_channel.send(f"{ctx_author.mention}", delete_after=5)
    except Exception as e:
        await destination.send(
            f"Can not able to {command_name} {channel.name}. Error raised: {e}"
        )


async def _warn(guild, command_name, ctx_author, destination, target, reason):
    await destination.send(f"{target.name}#{target.discriminator} has being warned for: {reason}")


MEMBER_REACTION = ['🔨', '👢', '🤐', '😁', '❌', '⭕', '⬆️', '⬇️', '🖋️']
TEXT_REACTION = ['🔒', '🔓', '📝', '🖋️']
VC_REACTION = ['🔒', '🔓', '🖋️']
ROLE_REACTION = ['🔒', '🔓', '🌈', '🖋️']
