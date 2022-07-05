from __future__ import annotations

from typing import Optional

import discord
from cogs.ticket import method as mt
from core import Cog, Context, Parrot
from discord.ext import commands


class Ticket(Cog):
    """A simple ticket service, trust me it's better than YAG. LOL!"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="ticket_", id=892425759287824415)

    @commands.command(hidden=True)
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(
        manage_channels=True, embed_links=True, manage_roles=True
    )
    @Context.with_type
    async def new(self, ctx: Context, *, args: Optional[str] = None):
        """This creates a new ticket.
        Add any words after the command if you'd like to send a message when we initially create your ticket."""
        await mt._new(ctx, args)

    @commands.command(hidden=True)
    @commands.bot_has_permissions(manage_channels=True, embed_links=True)
    @Context.with_type
    async def close(self, ctx: Context):
        """Use this to close a ticket.
        This command only works in ticket channels."""
        await mt._close(ctx, self.bot)

    @commands.command(hidden=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def save(self, ctx: Context, limit: Optional[int] = 100):
        """Use this to save the transcript of a ticket.
        This command only works in ticket channels."""
        await mt._save(ctx, self.bot, limit)
