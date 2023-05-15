from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

import discord
from core import Context, Parrot
from utilities.chat_exporter import quick_export

if TYPE_CHECKING:
    from pymongo.collection import Collection


async def chat_exporter(
    channel: discord.TextChannel, limit: Optional[int] = 100
) -> None:
    await quick_export(channel)


async def log(
    guild: discord.Guild, channel: discord.TextChannel, description: str, status: str
) -> None:
    await channel.send(
        embed=discord.Embed(
            title="Parrot Ticket Bot",
            timestamp=discord.utils.utcnow(),
            description=f"{description}",
            color=discord.Color.blue(),
        )
        .add_field(name="Status", value=status)
        .set_footer(text=f"{guild.name}")
    )


async def _new(ctx: Context, args: Optional[str] = None) -> None:
    message_content = args or "Please wait, we will be with you shortly!"
    col: Collection = ctx.bot.guild_configurations
    data = await col.find_one_and_update(
        {"_id": ctx.guild.id},
        {"$inc": {"ticket_config.ticket_counter": 1}},
        upsert=True,
        return_document=True,
    )

    data = data["ticket_config"]

    cat: discord.CategoryChannel = ctx.guild.get_channel(data.get("category") or 0)

    ticket_channel: discord.TextChannel = await ctx.guild.create_text_channel(
        f"ticket-{data['ticket_counter'] + 1}",
        category=cat,
        reason=f"Parrot Ticket bot feature | On request from {ctx.author}",
    )

    await ticket_channel.set_permissions(
        ctx.guild.get_role(ctx.guild.id),
        send_messages=False,
        read_messages=False,
        view_channel=False,
        reason="Parrot Ticket Bot on action | Basic",
    )

    for role_id in data.get("valid_roles", []):
        if role := ctx.guild.get_role(role_id):
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

    for role_id in data.get("verified_roles", []):
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
        title=f"New ticket from {ctx.author}",
        description=f"{message_content}",
        color=0x00A8FF,
    )

    await ticket_channel.send(content=f"{ctx.author.mention}", embed=em)
    await ticket_channel.send(
        f"To close the ticket, type `{ctx.clean_prefix}close`\nTo save the ticket transcript, type `{ctx.clean_prefix}save`"
    )

    pinged_msg_content = ""
    for role_id in data.get("pinged_roles", []):
        if role := ctx.guild.get_role(role_id):
            pinged_msg_content += role.mention
            pinged_msg_content += " "

    if pinged_msg_content:
        await ticket_channel.send(pinged_msg_content)

    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id},
        {"$addToSet": {"ticket_channel_ids": ticket_channel.id}},
        upsert=True,
    )
    created_em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"Your ticket has been created at {ticket_channel.mention}",
        color=discord.Color.blue(),
    )

    await ctx.reply(embed=created_em)
    if data.get("log"):
        if log_channel := ctx.guild.get_channel(data["log"]):
            await log(
                ctx.guild,
                log_channel,
                f"**Channel:** #ticket-{data['ticket_number']+1}\n"
                f"**Opened by:** {ctx.author} ({ctx.author.id})",
                "RUNNING",
            )


async def _close(ctx: Context, bot: Parrot) -> None:
    col: Collection = ctx.bot.guild_configurations
    data = await col.find_one({"_id": ctx.guild.id})
    data = data["ticket_config"]

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
            await ctx.bot.guild_configurations.update_one(
                {"_id": ctx.guild.id},
                {"$pull": {"ticket_channel_ids": ctx.channel.id}},
            )
            if data.get("log"):
                if log_channel := ctx.guild.get_channel(data["log"]):
                    await log(
                        ctx.guild,
                        log_channel,
                        f"**Channel:** #{ctx.channel.name}\n"
                        f"**Closed by:** {ctx.author} ({ctx.author.id})",
                        "CLOSED",
                    )
        except asyncio.TimeoutError:
            em = discord.Embed(
                title="Parrot Ticket Bot",
                description="You have run out of time to close this ticket. Please run the command again.",
                color=discord.Color.blue(),
            )
            await ctx.reply(embed=em)


async def _save(ctx: Context, bot: Parrot, limit: int) -> None:
    if data := await ctx.bot.guild_configurations.find_one({"_id": ctx.guild.id}):
        data = data["ticket_config"]
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
            await chat_exporter(ctx.channel, limit)

            if data.get("log"):
                if log_channel := ctx.guild.get_channel(data["log"]):
                    await log(
                        ctx.guild,
                        log_channel,
                        f"**Channel:** #{ctx.channel.name}\n"
                        f"**Opened by:** {ctx.author} ({ctx.author.id})",
                        "RUNNING",
                    )


# CONFIG


async def _addaccess(ctx: Context, role: discord.Role) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"valid_roles": role.id}}, upsert=True
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"You have successfully added `{role.name}` to the list of roles with access to tickets.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _delaccess(ctx: Context, role: discord.Role) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"valid_roles": role.id}}, upsert=True
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"You have successfully removed `{role.name}` from the list of roles with access to tickets.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _addadimrole(ctx: Context, role: discord.Role) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"verified_roles": role.id}}, upsert=True
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"You have successfully added `{role.name}` to the list of roles that can run admin-level commands!",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _addpingedrole(ctx: Context, role: discord.Role) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id}, {"$addToSet": {"pinged_roles": role.id}}, upsert=True
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"You have successfully added `{role.name}` to the list of roles that get pinged when new tickets are created!",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _deladminrole(ctx: Context, role: discord.Role) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id}, {"$pull": {"verified_roles": role.id}}, upsert=True
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"You have successfully removed `{role.name}` from the list of roles that get pinged when new tickets are created.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _delpingedrole(ctx: Context, role: discord.Role) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id}, {"$pull": {"pinged_roles": role.id}}, upsert=True
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"You have successfully removed `{role.name}` from the list of roles that get pinged when new tickets are created.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _setcategory(ctx: Context, channel: discord.TextChannel) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id}, {"$set": {"category": channel.id}}, upsert=True
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"You have successfully added `{channel.name}` where new tickets will be created.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _setlog(ctx: Context, channel: discord.TextChannel) -> None:
    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id}, {"$set": {"log": channel.id}}, upsert=True
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"You have successfully added `{channel.name}` where tickets action will be logged.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )

    em.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=em)


async def _auto(ctx: Context, channel: discord.TextChannel, message: str) -> None:
    embed = discord.Embed(
        title="Parrot Ticket Bot", description=message, color=discord.Color.blue()
    ).set_footer(text=f"{ctx.guild.name}")

    message = await channel.send(embed=embed)
    await message.add_reaction("\N{ENVELOPE}")

    await ctx.bot.guild_configurations.update_one(
        {"_id": ctx.guild.id},
        {"$set": {"message_id": message.id, "channel_id": channel.id}},
        upsert=True,
    )
    em = discord.Embed(
        title="Parrot Ticket Bot",
        description=f"All set at {channel.name}",
        color=discord.Color.blue(),
    )

    await ctx.reply(embed=em)
