from database.server_config import collection, guild_join, guild_update
import discord, asyncio


# ROLES
async def _add_roles_bot(ctx, operator, role, reason):
    for member in ctx.guild.members:
        try:
            if not member.bot: pass
            else:
                if operator.lower() in ['+', 'add', 'give']:
                    await member.add_roles(role, reason=reason)
                elif operator.lower() in ['-', 'remove', 'take']:
                    await member.remove_roles(role, reason=reason)
        except Exception as e:
            await ctx.reply(
                f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
            )


async def _add_roles_humans(ctx, operator, role, reason):
    for member in ctx.guild.members:
        try:
            if member.bot: pass
            else:
                if operator.lower() in ['+', 'add', 'give']:
                    await member.add_roles(role, reason=reason)
                elif operator.lower() in ['-', 'remove', 'take']:
                    await member.remove_roles(role, reason=reason)
        except Exception as e:
            await ctx.reply(
                f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
            )


async def _add_roles(ctx, member, role, reason):
    guild = ctx.guild

    if guild.me.top_role < member.top_role:
        await ctx.reply(
            f"{ctx.author.mention} can't give the role to {member.name} as it's role is above the bot"
        )

    try:
        await member.add_roles(
            role,
            reason=
            f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
        )
        await ctx.reply(
            f"{ctx.author.mention} given {role.name}({role.id}) to {member.name}"
        )
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _remove_roles(ctx, member, role, reason):
    guild = ctx.guild

    if guild.me.top_role < member.top_role:
        await ctx.reply(
            f"{ctx.author.mention} can't give the role to {member.name} as it's role is above the bot"
        )
    try:
        await member.remove_roles(
            role,
            reason=
            f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
        )
        await ctx.reply(
            f"{ctx.author.mention} removed {role.name}({role.id}) from {member.name}"
        )
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


# BAN


async def _ban(ctx, member, days, reason):
    try:
        if member.id == ctx.author.id or member.id == 800780974274248764:
            pass
        else:
            await ctx.guild.ban(
                member,
                reason=
                f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}',
                delete_message_days=days)
            await ctx.reply(
                f"**`{member.name}#{member.discriminator}`** is banned! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Reason: **{reason}**"
            )
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _mass_ban(ctx, members, days, reason):
    _list = members
    for member in members:
        try:
            if member.id == ctx.author.id or member.id == 800780974274248764:
                pass
            else:
                await ctx.guild.ban(
                    member,
                    reason=
                    f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}',
                    delete_message_days=days)
        except Exception as e:
            await ctx.reply(
                f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
            )
            _list.remove(member)
    await ctx.reply(
        f"**{', '.join([member.name for member in members])}** are banned! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Total: **{len(members)}**! Reason: **{reason}**"
    )


async def _softban(ctx, member, reason):
    for member in member:
        try:
            if member.id == ctx.author.id or member.id == 800780974274248764:
                pass
            else:
                await member.ban(
                    reason=
                    f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
                )

                banned_users = await ctx.guild.bans()
                member_n, member_d = member.name, member.discriminator
                for ban_entry in banned_users:
                    user = ban_entry.user
                    if (user.name, user.discriminator) == (member_n, member_d):
                        await ctx.guild.unban(user)

                await ctx.reply(
                    f'**`{member.name}#{member.discriminator}`** is banned then unbanned! Responsible moderator: **`{ctx.author.name}#{ctx.authoe.discriminator}`**! Reason: **{reason}**'
                )
        except Exception as e:
            await ctx.reply(
                f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
            )


async def _unban(ctx, member, reason):
    await ctx.guild.unban(
        member,
        reason=
        f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
    )
    await ctx.reply(
        f"**`{member.name}#{member.discriminator}`** is unbanned! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Reason: **{reason}**"
    )


# MUTE


async def _mute(ctx, member, seconds, reason):
    if not collection.find_one({'_id': ctx.guild.id}):
        await guild_join(ctx.guild.id)

    data = collection.find_one({'_id': ctx.guild.id})

    muted = ctx.guild.get_role(data['mute_role']) or discord.utils.get(
        ctx.guild.roles, name="Muted")

    if not muted:
        muted = await ctx.guild.create_role(
            name="Muted",
            reason=
            f"Setting up mute role. it's first command is execution, by {ctx.author.name}({ctx.author.id})"
        )
        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(muted,
                                              send_messages=False,
                                              read_message_history=False)
            except Exception:
                pass
        await guild_update(ctx.guild.id, {'mute_role': muted.id})
    if seconds is None: seconds = 0
    try:
        if member.id == ctx.author.id or member.id == 800780974274248764:
            pass
        else:
            await member.add_roles(
                muted,
                reason=
                f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
            )
            await ctx.reply(
                f"{ctx.author.mention} **{member.name}** has been successfully muted {'for **' + str(seconds) + 's**' if (seconds > 0) and (type(seconds) is int) else ''}!"
            )
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
        )

    if seconds > 0:
        await asyncio.sleep(seconds)
        try:
            await member.remove_roles(
                muted,
                reason=
                f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: Mute Duration Expired"
            )
        except Exception:
            pass


async def _unmute(ctx, member, reason):
    if not collection.find_one({'_id': ctx.guild.id}):
        await guild_join(ctx.guild.id)

    data = collection.find_one({'_id': ctx.guild.id})

    muted = ctx.guild.get_role(data['mute_role']) or discord.utils.get(
        ctx.guild.roles, name="Muted")
    try:
        if muted in member.roles:
            await ctx.reply(
                f'{ctx.author.mention} **{member.name}** has been unmuted now!'
            )
            await member.remove_roles(
                muted,
                reason=
                f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
            )
        else:
            await ctx.reply(
                f"{ctx.author.mention} **{member.name}** already unmuted :')")
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}\n\nMake sure that the bot role is above the target role"
        )


async def _kick(ctx, member, reason):
    try:
        if member.id == ctx.author.id or member.id == 800780974274248764:
            pass
        else:
            await member.kick(
                reason=
                f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
            )
            await ctx.reply(
                f'**`{member.name}#{member.discriminator}`** is kicked! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Reason: **{reason}**'
            )
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
        )


async def _mass_kick(ctx, members, reason):
    _list = members
    for member in members:
        try:
            if member.id == ctx.author.id or member.id == 800780974274248764:
                pass
            else:
                await member.kick(
                    reason=
                    f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
                )
        except Exception as e:
            _list.remove(member)
            await ctx.reply(
                f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
            )
        await asyncio.sleep(0.25)
    await ctx.reply(
        f"**{', '.join([member.name for member in members])}** are kicked! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Total: **{len(members)}**! Reason: **{reason}**"
    )


# BLOCK


async def _block(ctx, member, reason):
    for member in member:
        try:
            if member.id == ctx.author.id or member.id == 800780974274248764:
                pass  # cant mod the calling author or the bot itself
            else:
                await ctx.channel.set_permissions(
                    member,
                    send_messages=False,
                    reason=
                    f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
                )
                await ctx.reply(
                    f'{ctx.author.mention} overwrite permission(s) for **{member.name}** has been created! **View Channel, and Send Messages** is denied!'
                )
        except Exception as e:
            await ctx.reply(
                f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
            )
        await asyncio.sleep(0.25)


async def _unblock(ctx, member, reason):
    for member in member:
        try:
            if member.permissions_in(ctx.channel).send_messages:
                await ctx.reply(
                    f"{ctx.author.mention} {member.name} is already unblocked. They can send message"
                )
            else:
                await ctx.channel.set_permissions(
                    member,
                    overwrite=None,
                    reason=
                    f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
                )
            await ctx.reply(
                f'{ctx.author.mention} overwrite permission(s) for **{member.name}** has been deleted!'
            )
        except Exception as e:
            await ctx.reply(
                f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
            )
        await asyncio.sleep(0.25)


# LOCK


async def _text_lock(ctx, channel):
    channel = channel or ctx.channel
    try:

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(
            ctx.guild.default_role,
            reason=f"Action requested by {ctx.author.name}({ctx.author.id})",
            overwrite=overwrite)
        await ctx.reply(f'{ctx.author.mention} channel locked.')
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {channel.name}. Error raised: {e}"
        )


async def _vc_lock(ctx, channel):
    if not channel: channel = ctx.author.voice.channel
    if not channel: return
    try:
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.connect = False
        await channel.set_permissions(
            ctx.guild.default_role,
            reason=f"Action requested by {ctx.author.name}({ctx.author.id})",
            overwrite=overwrite)
        await ctx.reply(f'{ctx.author.mention} channel locked.')
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {channel.name}. Error raised: {e}"
        )


# UNLOCK


async def _text_unlock(ctx, channel):

    try:
        channel = channel or ctx.channel
        await channel.set_permissions(
            ctx.guild.default_role,
            reason=f"Action requested by {ctx.author.name}({ctx.author.id})",
            overwrite=None)
        await ctx.reply(f'{ctx.author.mention} channel unlocked.')
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {channel.name}. Error raised: {e}"
        )


async def _vc_unlock(ctx, channel):
    if not channel: channel = ctx.author.voice.channel
    if not channel: return
    try:
        await channel.set_permissions(
            ctx.guild.default_role,
            reason=f"Action requested by {ctx.author.name}({ctx.author.id})",
            overwrite=None)
        await ctx.reply(f'{ctx.author.mention} channel unlocked.')
    except Exception as e:
        await ctx.reply(
            f"Can not able to {ctx.command.name} {channel.name}. Error raised: {e}"
        )


# EXTRA


async def slowmode(ctx, seconds, channel, reason):
    channel = channel or ctx.channel
    if not seconds: seconds = 5
    if seconds:
        if (seconds <= 21600) and (seconds > 0):
            await channel.edit(
                slowmode_delay=seconds,
                reason=
                f"Action Requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
            )
            await ctx.reply(
                f"{ctx.author.mention} {channel} is now in slowmode of **{seconds}**, to reverse type [p]slowmode 0"
            )
        elif seconds == 0 or seconds.lower() == 'off':
            await channel.edit(
                slowmode_delay=seconds,
                reason=
                f"Action Requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
            )
            await ctx.reply(
                f"{ctx.author.mention} {channel} is now not in slowmode.")
        elif (seconds >= 21600) or (seconds < 0):
            await ctx.reply(
                f"{ctx.author.mention} you can't set slowmode in negative numbers or more than 21600 seconds"
            )
        else:
            return


async def _clone(ctx, channel, reason):
    if channel is None: channel = ctx.channel

    new_channel = await channel.clone(
        reason=
        f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
    )
    await channel.delete(
        reason=
        f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
    )
    await new_channel.reply(f"{ctx.author.mention}", delete_after=5)
