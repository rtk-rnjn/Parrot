import discord, asyncio, os
from utilities.database import ticket_update, parrot_db
from datetime import datetime

collection = parrot_db['ticket']


async def check_if_server(guild_id):
    if not collection.find_one({'_id': guild_id}):
        post = {
            "_id": guild_id,
            "ticket-counter": 0,
            "valid-roles": [],
            "pinged-roles": [],
            "ticket-channel-ids": [],
            "verified-roles": [],
            "message_id": None,
            "log": None,
            "category": None,
            "channel_id": None
        }

        collection.insert_one(post)


async def chat_exporter(channel, limit=None):
    with open(f'extra/{channel.id}.txt', 'w+') as f:
        async for msg in channel.history(limit=limit, oldest_first=True):
            f.write(
                f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n"
            )
    with open(f'extra/{channel.id}.txt', 'rb') as fp:
        await channel.send(file=discord.File(fp, 'FUCKING_FILE_NAME.txt'))
    os.remove(f'extra/{channel.id}.txt')


async def log(guild, channel, description, status):
    embed = discord.Embed(title='Parrot Ticket Bot',
                          timestamp=datetime.utcnow(),
                          description=f"```\n{description}\n```",
                          color=discord.Color.blue())
    embed.add_field(name='Status', value=status)
    embed.set_footer(text=f"{guild.name}")
    await channel.send(embed=embed)


async def _new(ctx, args):
    await check_if_server(ctx.guild.id)

    if not args:
        message_content = "Please wait, we will be with you shortly!"

    else:
        message_content = "".join(args)

    data = collection.find_one({'_id': ctx.guild.id})
    ticket_number = data['ticket-counter'] + 1
    cat = ctx.guild.get_channel(data['category'])

    ticket_channel = await ctx.guild.create_text_channel(
        "ticket-{}".format(ticket_number), category=cat, reason="Parrot Ticket bot feature | On request from {ctx.author.name}#{ctx.author.discriminator}")
    await ticket_channel.set_permissions(
        ctx.guild.get_role(ctx.guild.id),
        send_messages=False,
        read_messages=False,
        view_channel=False,
        reason="Parrot Ticket Bot on action | Basic")
    if data['valid-roles']:
        for role_id in data["valid-roles"]:
            role = ctx.guild.get_role(role_id)

            await ticket_channel.set_permissions(
                role,
                send_messages=True,
                read_messages=True,
                add_reactions=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                external_emojis=True,
                view_channel=True,
                reason="Parrot Ticket Bot on action | Role Access")

    await ticket_channel.set_permissions(
        ctx.author,
        send_messages=True,
        read_messages=True,
        add_reactions=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        external_emojis=True,
        view_channel=True,
        reason="Parrot Ticket Bot on action | Basic")

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
    if data['log']:
        log_channel = ctx.guild.get_channel(data['log'])
        await log(
            ctx.guild, log_channel,
            f'ticket-{ticket_number} opened by, {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id})',
            'RUNNING')


async def _close(ctx, bot):
    await check_if_server(ctx.guild.id)

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
            message = await bot.wait_for('message', check=check, timeout=60)
            await ctx.channel.delete(reason=f"Parrot Ticket bot feature | On request from {ctx.author.name}#{ctx.author.discriminator}")
            index = data["ticket-channel-ids"].index(channel_id)
            ticket_channel_ids = data['ticket-channel-ids']
            del ticket_channel_ids[index]
            post = {'ticket-channel-ids': ticket_channel_ids}
            await ticket_update(ctx.guild.id, post)
            if data['log']:
                log_channel = ctx.guild.get_channel(data['log'])
                await log(
                    ctx.guild, log_channel,
                    f'{ctx.channel.name} closed by, {message.author.name}#{message.author.discriminator} ({message.author.id})',
                    'CLOSED')
        except asyncio.TimeoutError:
            em = discord.Embed(
                title="Parrot Ticket Bot",
                description=
                "You have run out of time to close this ticket. Please run the command again.",
                color=discord.Color.blue())
            await ctx.reply(embed=em)


async def _save(ctx, bot):
    await check_if_server(ctx.guild.id)

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
            message = await bot.wait_for('message', check=check, timeout=60)
            await chat_exporter(ctx.channel)

            if data['log']:
                log_channel = ctx.guild.get_channel(data['log'])
                await log(
                    ctx.guild, log_channel,
                    f'{ctx.channel.name} transcript created by, {message.author.name}#{message.author.discriminator} ({message.author.id})',
                    'RUNNING')
        except asyncio.TimeoutError:
            em = discord.Embed(
                title="Parrot Ticket Bot",
                description=
                "You have run out of time to save the transcript of this ticket. Please run the command again.",
                color=discord.Color.blue())
            await ctx.reply(embed=em)


# CONFIG


async def _addaccess(ctx, role):
    await check_if_server(ctx.guild.id)

    collection.update_one({'_id': ctx.guild.id},
                          {'$addToSet': {
                              'valid-roles': role.id
                          }})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=
        "You have successfully added `{}` to the list of roles with access to tickets."
        .format(role.name),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _delaccess(ctx, role):
    await check_if_server(ctx.guild.id)
    collection.update_one({'_id': ctx.guild.id},
                          {'$addToSet': {
                              'valid-roles': role.id
                          }})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=
        "You have successfully removed `{}` from the list of roles with access to tickets."
        .format(role.name),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _addadimrole(ctx, role):
    await check_if_server(ctx.guild.id)
    collection.update_one({'_id': ctx.guild.id},
                          {'$addToSet': {
                              "verified-roles": role.id
                          }})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=
        "You have successfully added `{}` to the list of roles that can run admin-level commands!"
        .format(role.name),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _addpingedrole(ctx, role):
    await check_if_server(ctx.guild.id)
    collection.update_one({'_id': ctx.guild.id},
                          {'$addToSet': {
                              'pinged-roles': role.id
                          }})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=
        "You have successfully added `{}` to the list of roles that get pinged when new tickets are created!"
        .format(role.name),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _deladminrole(ctx, role):
    await check_if_server(ctx.guild.id)
    collection.update_one({'_id': ctx.guild.id},
                          {'$pull': {
                              'verified-roles': role.id
                          }})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=
        "You have successfully removed `{}` from the list of roles that get pinged when new tickets are created."
        .format(role.name),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _delpingedrole(ctx, role):
    await check_if_server(ctx.guild.id)
    collection.update_one({'_id': ctx.guild.id},
                          {'$pull': {
                              'pinged-roles': role.id
                          }})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=
        "You have successfully removed `{}` from the list of roles that get pinged when new tickets are created."
        .format(role.name),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _setcategory(ctx, channel):
    await check_if_server(ctx.guild.id)
    collection.update_one({'_id': ctx.guild.id},
                          {'$set': {
                              'category': channel.id
                          }})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=
        "You have successfully added `{}` where new tickets will be created.".
        format(channel.name),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _setlog(ctx, channel):
    await check_if_server(ctx.guild.id)
    collection.update_one({'_id': ctx.guild.id}, {'$set': {'log': channel.id}})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=
        "You have successfully added `{}` where tickets action will be logged."
        .format(channel.name),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow())
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


# AUTO/ REACTION


async def _auto(ctx, channel, message):

    embed = discord.Embed(title='Parrot Ticket Bot',
                          description=message,
                          color=discord.Color.blue())
    embed.set_footer(text=f"{ctx.guild.name}")
    message = await channel.send(embed=embed)
    await message.add_reaction('✉️')
    post = {'message_id': message.id, 'channel_id': channel.id}
    await ticket_update(ctx.guild.id, post)
    em = discord.Embed(title="Parrot Ticket Bot",
                       description="All set at {}".format(channel.name),
                       color=discord.Color.blue())
    await ctx.reply(embed=em)
