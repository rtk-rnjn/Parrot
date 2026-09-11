from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from rapidfuzz import fuzz, process

if TYPE_CHECKING:
    from core import Parrot


class Telephone(commands.Cog):
    """Ever thought to talk to your friends in a different server? Well, now you can!"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    def _search_guild(self, server: str) -> discord.Guild | None:
        """Searches for a guild by name using fuzzy matching."""
        if server.isdigit():
            guild = self.bot.get_guild(int(server))
            if guild:
                return guild

        guilds = {guild.name: guild for guild in self.bot.guilds}
        match, score, _ = process.extractOne(server, guilds.keys(), scorer=fuzz.ratio)
        if score >= 80:  # Adjust the threshold as needed
            return guilds[match]
        return None

    @commands.group(name="telephone", aliases=["phone", "tel", "call"])
    async def telephone(self, ctx: commands.Context[Parrot], *, server: str) -> None:
        """Starts a game of telephone in the specified server."""
        # Implementation of the telephone game goes here
        await ctx.send(f"Starting a game of telephone in {server}!")

    @telephone.command(name="enable", aliases=["on"])
    @commands.has_permissions(administrator=True)
    async def enable(self, ctx: commands.Context[Parrot]) -> None:
        """Enables the telephone game in the server."""
        # Implementation of enabling the telephone game goes here
        await ctx.send("The telephone game has been enabled!")

    @telephone.command(name="disable", aliases=["off"])
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx: commands.Context[Parrot]) -> None:
        """Disables the telephone game in the server."""
        # Implementation of disabling the telephone game goes here
        await ctx.send("The telephone game has been disabled!")

    @telephone.command(name="block", aliases=["ban"])
    @commands.has_permissions(administrator=True)
    async def block(self, ctx: commands.Context[Parrot], *, server: str) -> None:
        """Blocks a server from calling the telephone game."""
        # Implementation of blocking a server goes here
        await ctx.send(f"The server {server} has been blocked from calling the telephone game!")

    @commands.command(name="unblock", aliases=["unban"])
    @commands.has_permissions(administrator=True)
    async def unblock(self, ctx: commands.Context[Parrot], *, server: str) -> None:
        """Unblocks a server from calling the telephone game."""
        # Implementation of unblocking a server goes here
        await ctx.send(f"The server {server} has been unblocked!")

    @commands.command(name="pickup", aliases=["pickup", "pick"])
    async def pickup(self, ctx: commands.Context[Parrot]) -> None:
        """Allows a user to pick up the telephone."""
        # Implementation of picking up the telephone goes here
        await ctx.send(f"{ctx.author.mention} has picked up the telephone!")

    @commands.command(name="hangup", aliases=["hang"])
    async def hangup(self, ctx: commands.Context[Parrot]) -> None:
        """Allows a user to hang up the telephone."""
        # Implementation of hanging up the telephone goes here
        await ctx.send(f"{ctx.author.mention} has hung up the telephone!")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Telephone(bot))
