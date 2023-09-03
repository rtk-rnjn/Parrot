from __future__ import annotations

import io
from typing import TYPE_CHECKING

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

if TYPE_CHECKING:
    from discord.ext.commands._types import Check


def ticket_enabled() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        ticket_config = ctx.bot.guild_configurations_cache[ctx.guild.id]["ticket_config"]
        if not ticket_config["enabled"]:
            msg = "Ticket is not enabled in this server."
            raise commands.DisabledCommand(msg)
        return True

    return commands.check(predicate)


def require_ticket_channel() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        ticket_config = ctx.bot.guild_configurations_cache[ctx.guild.id]["ticket_config"]
        if ctx.channel.id not in ticket_config["ticket_channel_ids"]:
            msg = "This command only works in ticket channels."
            raise commands.BadArgument(msg)
        return True

    return commands.check(predicate)


ENVELOPE = "\N{ENVELOPE}"


class Tickets(Cog):
    """A simple ticket service, trust me it's better than YAG. LOL!."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.ON_TESTING = False

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="ticket_", id=892425759287824415)

    def embed(self, *, description: str) -> discord.Embed:
        return discord.Embed(description=description, color=discord.Color.blurple())

    async def log(self, *, guild: discord.Guild, author: discord.Member | discord.User, args: str) -> None:
        ticket_config = self.bot.guild_configurations_cache[guild.id]["ticket_config"]
        if not ticket_config["enabled"]:
            return

        log_channel: discord.TextChannel = guild.get_channel(ticket_config["log"] or 0)
        if not log_channel:
            return

        await log_channel.send(
            embed=self.embed(
                description=f"{author.mention} (`{author.id}`): {args}",
            ),
        )

    async def new_ticket(self, *, guild: discord.Guild, author: discord.Member | discord.User) -> None:
        ticket_config = self.bot.guild_configurations_cache[guild.id]["ticket_config"]

        mod_role: int = ticket_config["mod_role"]

        category: discord.CategoryChannel = guild.get_channel(ticket_config["category"] or 0)  # type: ignore
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if mod_role:
            if role := guild.get_role(mod_role):
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{ticket_config['ticket_counter']}",
            category=category,
            topic="Ticket",
            reason=f"Requested by {author} ({author.id})",
            overwrites=overwrites,
        )

        await self.bot.guild_configurations.update_one(
            {"_id": guild.id},
            {
                "$set": {
                    "ticket_config.ticket_counter": ticket_config["ticket_counter"] + 1,
                },
                "$addToSet": {
                    "ticket_config.ticket_channel_ids": ticket_channel.id,
                },
            },
        )
        msg = f"{author.mention}\nUse `ticket close` to close the ticket.\nUse `ticket save` to save the transcript of the ticket."
        await ticket_channel.send(msg, embed=self.embed(description=f"Ticket created by {author.mention}"))

    async def close_ticket(
        self,
        guild: discord.Guild,
        author: discord.Member | discord.User,
        channel: discord.TextChannel,
    ) -> None:
        if not channel:
            return

        await channel.delete(reason=f"Closed by {author} ({author.id})")
        await self.log(guild=guild, author=author, args=f"Closed by {author} ({author.id})")

    async def save_ticket(
        self,
        guild: discord.Guild,
        author: discord.Member | discord.User,
        channel: discord.TextChannel,
    ) -> None:
        if not channel:
            return

        messages_string = ""
        async for message in channel.history(limit=1000, oldest_first=True):
            if not message.author.bot:
                messages_string += f"{message.author} ({message.author.id}): {message.content}\n"

        file = discord.File(
            io.BytesIO(messages_string.encode("utf-8")),
            filename=f"{channel.name}.txt",
        )

        await self.log(guild=guild, author=author, args=f"Saved by {author} ({author.id})")
        await channel.send(file=file)

    @commands.group(invoke_without_command=True)
    @commands.has_permissions()
    async def ticket(self, ctx: Context):
        """Ticket configuration."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @ticket.command()
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    @ticket_enabled()
    async def new(self, ctx: Context, *, args: str | None = None):
        """This creates a new ticket.
        Add any words after the command if you'd like to send a message when we initially create your ticket.
        """
        await self.new_ticket(guild=ctx.guild, author=ctx.author)
        await self.log(guild=ctx.guild, author=ctx.author, args=args or "")

    @ticket.command()
    @commands.bot_has_permissions(manage_channels=True)
    @ticket_enabled()
    @require_ticket_channel()
    async def close(self, ctx: Context):
        """Use this to close a ticket.

        This command only works in ticket channels.
        """
        await self.close_ticket(ctx.guild, ctx.author, ctx.channel)

    @ticket.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    @ticket_enabled()
    @require_ticket_channel()
    async def save(self, ctx: Context):
        """Use this to save the transcript of a ticket.

        This command only works in ticket channels.
        """
        await self.save_ticket(ctx.guild, ctx.author, ctx.channel)

    @ticket.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def ticket_enable(self, ctx: Context):
        """Enable ticket system in this server."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "ticket_config.enable": True,
                },
            },
        )
        await ctx.reply(f"{ctx.author.mention} Ticket has been enabled in this server.")

    @ticket.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def ticket_disable(self, ctx: Context):
        """Disable ticket system in this server."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "ticket_config.enable": False,
                },
            },
        )
        await ctx.reply(f"{ctx.author.mention} Ticket has been disabled in this server.")

    @ticket.command(name="category")
    @commands.has_permissions(manage_guild=True)
    async def ticket_category(self, ctx: Context, *, category: discord.CategoryChannel | None = None):
        """Set ticket category."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "ticket_config.category": category.id if category else None,
                },
            },
        )
        await ctx.reply(f"{ctx.author.mention} Ticket category has been set to {category.mention if category else 'None'}.")

    @ticket.command(name="log")
    @commands.has_permissions(manage_guild=True)
    async def ticket_log(self, ctx: Context, *, channel: discord.TextChannel | None = None):
        """Set ticket log channel."""
        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "ticket_config.log": channel.id if channel else None,
                },
            },
        )
        await ctx.reply(f"{ctx.author.mention} Ticket log channel has been set to {channel.mention if channel else 'None'}.")

    @ticket.command(name="reaction")
    @commands.has_permissions(manage_guild=True)
    async def ticket_react(self, ctx: Context, *, channel: discord.TextChannel | None = None):
        """Set ticket auto channel."""
        channel: discord.TextChannel = channel or ctx.channel  # type: ignore
        message = await channel.send(
            embed=discord.Embed(
                title=f"{ctx.guild} Ticket Service",
                description="React to this message to create a ticket.",
                color=discord.Color.blurple(),
            ),
        )
        await message.add_reaction(ENVELOPE)
        await message.reply("Do not delete this message, it is required for the ticket system to work.")

        await self.bot.guild_configurations.update_one(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "ticket_config.message_id": message.id,
                    "ticket_config.channel_id": channel.id,
                },
            },
        )

        await ctx.reply(f"{ctx.author.mention} Ticket reaction channel has been set at this message: {message.jump_url}.")

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None:
            return
        ticket_config = self.bot.guild_configurations_cache[guild.id]["ticket_config"]
        if not ticket_config["enabled"]:
            return

        member = await self.bot.get_or_fetch_member(guild, payload.user_id)
        channel = self.bot.get_channel(payload.channel_id)
        if member is None or member.bot or str(payload.emoji) != ENVELOPE or channel is None:
            return

        message = await self.bot.get_or_fetch_message(channel, payload.message_id)
        if message is None:
            return

        if message.id != ticket_config["message_id"] or payload.channel_id != ticket_config["channel_id"]:
            return

        try:
            await message.remove_reaction(payload.emoji, member)
        except discord.Forbidden:
            pass

        await self.new_ticket(guild=guild, author=member)
        await self.log(guild=guild, author=member, args="New ticket created.")
