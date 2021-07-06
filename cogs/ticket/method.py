import discord, asyncio
from database.ticket import collection, ticket_on_join, ticket_update
import chat_exporter, io


async def _new(ctx, args):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)

    if not args:
        message_content = "Please wait, we will be with you shortly!"

    else:
        message_content = "".join(args)

    data = collection.find_one({'_id': ctx.guild.id})
    ticket_number = data['ticket-counter'] + 1
    cat = ctx.guild.get_channel(data['category'])

    ticket_channel = await ctx.guild.create_text_channel(
        "ticket-{}".format(ticket_number), category=cat)
    await ticket_channel.set_permissions(ctx.guild.get_role(ctx.guild.id),
                                         send_messages=False,
                                         read_messages=False)

    for role_id in data["valid-roles"]:
        role = ctx.guild.get_role(role_id)

        await ticket_channel.set_permissions(role,
                                             send_messages=True,
                                             read_messages=True,
                                             add_reactions=True,
                                             embed_links=True,
                                             attach_files=True,
                                             read_message_history=True,
                                             external_emojis=True)

    await ticket_channel.set_permissions(ctx.author,
                                         send_messages=True,
                                         read_messages=True,
                                         add_reactions=True,
                                         embed_links=True,
                                         attach_files=True,
                                         read_message_history=True,
                                         external_emojis=True)

    em = discord.Embed(title="New ticket from {}#{}".format(
        ctx.author.name, ctx.author.discriminator),
                       description="{}".format(message_content),
                       color=0x00a8ff)

    await ticket_channel.send(embed=em)
    await ticket_channel.send("To close the ticket, type `[p]close`")
    await ticket_channel.send("To save the ticket transcript, type `[p]save`")
    await ticket_channel.send(f'{ctx.author.mention}', delete_after=2)
    pinged_msg_content = ""
    non_mentionable_roles = []
    if data["pinged-roles"]:
        for role_id in data["pinged-roles"]:
            role = ctx.guild.get_role(role_id)
            pinged_msg_content += role.mention
            pinged_msg_content += " "
            if role.mentionable:
                pass
            else:
                await role.edit(mentionable=True)
                non_mentionable_roles.append(role)
        await ticket_channel.send(pinged_msg_content)
        for role in non_mentionable_roles:
            await role.edit(mentionable=False)

    ticket_channel_ids = data["ticket-channel-ids"]
    ticket_channel_ids.append(ticket_channel.id)
    post = {
        'ticket-counter': ticket_number,
        'ticket-channel-ids': ticket_channel_ids
    }
    await ticket_update(ctx.guild.id, post)
    created_em = discord.Embed(
        title="Parrot Ticket Bot",
        description="Your ticket has been created at {}".format(
            ticket_channel.mention),
        color=discord.Color.blue())
    await ctx.reply(embed=created_em)


async def _close(ctx, bot):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)
    data = collection.find_one({'_id': ctx.guild.id})
    if ctx.channel.id in data["ticket-channel-ids"]:
        channel_id = ctx.channel.id

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and message.content.lower(
            ) == "close"

        try:
            em = discord.Embed(
                title="Parrot Ticket Bot",
                description=
                "Are you sure you want to close this ticket? Reply with `close` if you are sure.",
                color=discord.Color.blue())
            await ctx.reply(embed=em)
            await bot.wait_for('message', check=check, timeout=60)
            await ctx.channel.delete()
            index = data["ticket-channel-ids"].index(channel_id)
            ticket_channel_ids = data['ticket-channel-ids']
            del ticket_channel_ids["ticket-channel-ids"][index]
            post = {'ticket-channel-ids': ticket_channel_ids}
            await ticket_update(ctx.guild.id, post)
        except asyncio.TimeoutError:
            em = discord.Embed(
                title="Parrot Ticket Bot",
                description=
                "You have run out of time to close this ticket. Please run the command again.",
                color=discord.Color.blue())
            await ctx.reply(embed=em)


async def _save(ctx, bot):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)
    data = collection.find_one({'_id': ctx.guild.id})
    if ctx.channel.id in data["ticket-channel-ids"]:

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and message.content.lower(
            ) == "save"

        try:
            em = discord.Embed(
                title="Parrot Ticket Bot",
                description=
                "Are you sure you want to save the transcript of this ticket? Reply with `save` if you are sure.",
                color=discord.Color.blue())
            await ctx.reply(embed=em)
            await bot.wait_for('message', check=check, timeout=60)
            transcript = await chat_exporter.export(ctx.channel)
            if transcript is None: return
            transcript_file = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{ctx.channel.name}.html")
            await ctx.reply(file=transcript_file)
        except asyncio.TimeoutError:
            em = discord.Embed(
                title="Parrot Ticket Bot",
                description=
                "You have run out of time to save the transcript of this ticket. Please run the command again.",
                color=discord.Color.blue())
            await ctx.reply(embed=em)


# CONFIG


async def _addaccess(ctx, role):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)
    data = collection.find_one({'_id': ctx.guild.id})
    if role.id not in data["valid-roles"]:
        valid_roles = data["valid-roles"].append(role.id)
        post = {'valid-roles': valid_roles}
        await ticket_update(ctx.guild.id, post)
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "You have successfully added `{}` to the list of roles with access to tickets."
            .format(role.name),
            color=discord.Color.blue())
        await ctx.reply(embed=em)
    else:
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description="That role already has access to tickets!",
            color=discord.Color.blue())
        await ctx.reply(embed=em)


async def _delaccess(ctx, role):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)
    data = collection.find_one({'_id': ctx.guild.id})
    valid_roles = data["valid-roles"]
    if role.id in valid_roles:
        index = valid_roles.index(role.id)
        del valid_roles[index]
        post = {'valid-roles': valid_roles}
        await ticket_update(ctx.guild.id, post)
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "You have successfully removed `{}` from the list of roles with access to tickets."
            .format(role.name),
            color=discord.Color.blue())
        await ctx.reply(embed=em)
    else:
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description="That role already doesn't have access to tickets!",
            color=discord.Color.blue())
        await ctx.reply(embed=em)


async def _addadimrole(ctx, role):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)
    data = collection.find_one({'_id': ctx.guild.id})
    if role.id not in data['verified-roles']:
        verified_roles = data["verified-roles"].append(role.id)
        await ticket_update(ctx.guild.id, {"verified-roles": verified_roles})
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "You have successfully added `{}` to the list of roles that can run admin-level commands!"
            .format(role.name),
            color=discord.Color.blue())
        await ctx.reply(embed=em)
    else:
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "That role already getting pinged when new tickets are created!",
            color=discord.Color.blue())
        await ctx.reply(embed=em)


async def _addpingedrole(ctx, role):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)
    data = collection.find_one({'_id': ctx.guild.id})
    if role.id not in data["pinged-roles"]:
        pinged_roles = data["pinged-roles"].append(role.id)
        post = {'pinged-roles': pinged_roles}
        await ticket_update(ctx.guild.id, post)
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "You have successfully added `{}` to the list of roles that get pinged when new tickets are created!"
            .format(role.name),
            color=discord.Color.blue())
        await ctx.reply(embed=em)
    else:
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "That role already receives pings when tickets are created.",
            color=discord.Color.blue())
        await ctx.reply(embed=em)


async def _deladminrole(ctx, role):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)
    data = collection.find_one({'_id': ctx.guild.id})
    admin_roles = data["verified-roles"]
    if role.id in admin_roles:
        index = admin_roles.index(role.id)
        del admin_roles[index]
        post = {"verified-roles": admin_roles}
        await ticket_update(ctx.guild.id, post)
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "You have successfully removed `{}` from the list of roles that get pinged when new tickets are created."
            .format(role.name),
            color=discord.Color.blue())
        await ctx.reply(embed=em)
    else:
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "That role isn't getting pinged when new tickets are created!",
            color=discord.Color.blue())
        await ctx.reply(embed=em)


async def _delpingedrole(ctx, role):
    if not collection.find_one({'_id': ctx.guild.id}):
        await ticket_on_join(ctx.guild.id)
    data = collection.find_one({'_id': ctx.guild.id})
    pinged_roles = data["pinged-roles"]
    if role.id in pinged_roles:
        index = pinged_roles.index(role.id)
        del pinged_roles[index]
        post = {'pinged-roles': pinged_roles}
        await ticket_update(ctx.guild.id, post)
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "You have successfully removed `{}` from the list of roles that get pinged when new tickets are created."
            .format(role.name),
            color=discord.Color.blue())
        await ctx.reply(embed=em)
    else:
        em = discord.Embed(
            title="Parrot Ticket Bot",
            description=
            "That role already isn't getting pinged when new tickets are created!",
            color=discord.Color.blue())
        await ctx.reply(embed=em)
