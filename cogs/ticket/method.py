from __future__ import annotations

import discord
import os
from datetime import datetime

from utilities.database import ticket_update, parrot_db
from core import Context

collection = parrot_db["ticket"]


async def check_if_server(guild_id):
    data = await collection.find_one({"_id": guild_id})
    if not data:
        post = {
            "_id": guild_id,
            "ticket_counter": 0,
            "valid_roles": [],
            "pinged_roles": [],
            "ticket_channel_ids": [],
            "verified_roles": [],
            "message_id": None,
            "log": None,
            "category": None,
            "channel_id": None,
        }

        await collection.insert_one(post)


async def chat_exporter(channel, limit=None):
    with open(f"extra/{channel.id}.txt", "w+") as f:
        async for msg in channel.history(limit=limit, oldest_first=True):
            f.write(
                f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n"
            )
    with open(f"extra/{channel.id}.txt", "rb") as fp:
        await channel.send(file=discord.File(fp, "FILE.txt"))
    os.remove(f"extra/{channel.id}.txt")


async def log(guild, channel, description, status):
    await channel.send(
        embed=discord.Embed(
            title="Parrot Ticket Bot",
            timestamp=datetime.utcnow(),
            description=f"{description}",
            color=discord.Color.blue(),
        )
        .add_field(name="Status", value=status)
        .set_footer(text=f"{guild.name}")
    )


async def _new(ctx: Context, args: str):
    await check_if_server(ctx.guild.id)

    if not args:
        message_content = "Please wait, we will be with you shortly!"

    else:
        message_content = "".join(args)

    data = await collection.find_one({"_id": ctx.guild.id})
    await collection.update_one({"_id": ctx.guild.id}, {"$inc": {"ticket_counter": 1}})
    cat = ctx.guild.get_channel(data["category"])

    ticket_channel = await ctx.guild.create_text_channel(
        "ticket-{}".format(f"{data['ticket_counter']+1}"),
        category=cat,
        reason=f"Parrot Ticket bot feature | On request from {ctx.author.name}#{ctx.author.discriminator}",
    )
    await ticket_channel.set_permissions(
        ctx.guild.get_role(ctx.guild.id),
        send_messages=False,
        read_messages=False,
        view_channel=False,
        reason="Parrot Ticket Bot on action | Basic",
    )
    if data["valid_roles"]:
        for role_id in data["valid_roles"]:
            role = ctx.guild.get_role(role_id)
            if role:
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
                    reason="Parrot Ticket Bot on action | Role Access",
                )

    if data["verified_roles"]:
        for role_id in data["verified_roles"]:
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
                reason="Parrot Ticket Bot on action | Role Access",
            )

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
        reason="Parrot Ticket Bot on action | Basic",
    )

    em = discord.Embed(
        title="New ticket from {}#{}".format(ctx.author.name, ctx.author.discriminator),
        description="{}".format(message_content),
        color=0x00A8FF,
    )

    await ticket_channel.send(content=f"{ctx.author.mention}", embed=em)
    await ticket_channel.send(
        f"To close the ticket, type `{ctx.clean_prefix}close`\nTo save the ticket transcript, type `{ctx.clean_prefix}save`"
    )
    pinged_msg_content = ""
    non_mentionable_roles = []
    if data["pinged_roles"]:
        for role_id in data["pinged_roles"]:
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

    await collection.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"ticket_channel_ids": ticket_channel.id}}
    )
    created_em = discord.Embed(
        title="Parrot Ticket Bot",
        description="Your ticket has been created at {}".format(ticket_channel.mention),
        color=discord.Color.blue(),
    )
    await ctx.reply(embed=created_em)
    if data["log"]:
        log_channel = ctx.guild.get_channel(data["log"])
        if log_channel:
            await log(
                ctx.guild,
                log_channel,
                f"**Channel:** #ticket-{data['ticket_number']+1}\n"
                f"**Opened by:** {ctx.author} ({ctx.author.id})",
                "RUNNING",
            )


async def _close(ctx: Context, bot):
    await check_if_server(ctx.guild.id)

    if data := await collection.find_one({"_id": ctx.guild.id}):
        if ctx.channel.id in data["ticket_channel_ids"]:

            try:
                em = discord.Embed(
                    title="Parrot Ticket Bot",
                    description="Are you sure you want to close this ticket?",
                    color=discord.Color.blue(),
                )
                a = await ctx.prompt(f"{ctx.author.mention}", embed=em)
                if not a:
                    return
                await ctx.reply(embed=em)
                await ctx.channel.delete(
                    reason=f"Parrot Ticket bot feature | On request from {ctx.author.name}#{ctx.author.discriminator}"
                )
                await collection.update_one(
                    {"_id": ctx.guild.id},
                    {"$pull": {"ticket_channel_ids": ctx.channel.id}},
                )
                if data["log"]:
                    log_channel = ctx.guild.get_channel(data["log"])
                    if log_channel:
                        await log(
                            ctx.guild,
                            log_channel,
                            f"**Channel:** #{ctx.channel.name}\n"
                            f"**Closed by:** {ctx.author} ({ctx.author.id})",
                            "CLOSED",
                        )
            except Exception:
                em = discord.Embed(
                    title="Parrot Ticket Bot",
                    description="You have run out of time to close this ticket. Please run the command again.",
                    color=discord.Color.blue(),
                )
                await ctx.reply(embed=em)


async def _save(ctx: Context, bot):
    await check_if_server(ctx.guild.id)

    if data := await collection.find_one({"_id": ctx.guild.id}):
        if ctx.channel.id in data["ticket_channel_ids"]:
            em = discord.Embed(
                title="Parrot Ticket Bot",
                description="Are you sure you want to save the transcript of this ticket?",
                color=discord.Color.blue(),
            )
            a = await ctx.prompt(f"{ctx.author.mention}", embed=em)
            if not a:
                return
            await ctx.reply(embed=em)
            await chat_exporter(ctx.channel)

            if data["log"]:
                log_channel = ctx.guild.get_channel(data["log"])
                if log_channel:
                    await log(
                        ctx.guild,
                        log_channel,
                        f"**Channel:** #{ctx.channel.name}\n"
                        f"**Opened by:** {ctx.author} ({ctx.author.id})",
                        "RUNNING",
                    )


# CONFIG


async def _addaccess(ctx, role):
    await check_if_server(ctx.guild.id)

    await collection.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"valid_roles": role.id}}
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="You have successfully added `{}` to the list of roles with access to tickets.".format(
            role.name
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _delaccess(ctx, role):
    await check_if_server(ctx.guild.id)
    await collection.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"valid_roles": role.id}}
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="You have successfully removed `{}` from the list of roles with access to tickets.".format(
            role.name
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _addadimrole(ctx, role):
    await check_if_server(ctx.guild.id)
    await collection.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"verified_roles": role.id}}
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="You have successfully added `{}` to the list of roles that can run admin-level commands!".format(
            role.name
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _addpingedrole(ctx, role):
    await check_if_server(ctx.guild.id)
    await collection.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"pinged_roles": role.id}}
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="You have successfully added `{}` to the list of roles that get pinged when new tickets are created!".format(
            role.name
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _deladminrole(ctx, role):
    await check_if_server(ctx.guild.id)
    await collection.update_one(
        {"_id": ctx.guild.id}, {"$pull": {"verified_roles": role.id}}
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="You have successfully removed `{}` from the list of roles that get pinged when new tickets are created.".format(
            role.name
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _delpingedrole(ctx, role):
    await check_if_server(ctx.guild.id)
    await collection.update_one(
        {"_id": ctx.guild.id}, {"$pull": {"pinged_roles": role.id}}
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="You have successfully removed `{}` from the list of roles that get pinged when new tickets are created.".format(
            role.name
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _setcategory(ctx, channel):
    await check_if_server(ctx.guild.id)
    await collection.update_one(
        {"_id": ctx.guild.id}, {"$set": {"category": channel.id}}
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="You have successfully added `{}` where new tickets will be created.".format(
            channel.name
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _setlog(ctx, channel):
    await check_if_server(ctx.guild.id)
    await collection.update_one({"_id": ctx.guild.id}, {"$set": {"log": channel.id}})
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="You have successfully added `{}` where tickets action will be logged.".format(
            channel.name
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _auto(ctx, channel, message):

    embed = discord.Embed(
        title="Parrot Ticket Bot", description=message, color=discord.Color.blue()
    )
    embed.set_footer(text=f"{ctx.guild.name}")
    message = await channel.send(embed=embed)
    await message.add_reaction("✉️")
    post = {"message_id": message.id, "channel_id": channel.id}
    await ticket_update(ctx.guild.id, post)
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description="All set at {}".format(channel.name),
        color=discord.Color.blue(),
    )
    await ctx.reply(embed=em)
