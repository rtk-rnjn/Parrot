from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from core.utils import PaginationView

from .guide import automod_embeds

if TYPE_CHECKING:
    from core import Parrot


class Automod(commands.Cog):
    """Automod rule management."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="automod", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx: commands.Context[Parrot]) -> None:
        """Shows the help message for the automod feature."""

    @automod.command(name="guide", aliases=["help"])
    @commands.has_permissions(administrator=True)
    async def automod_help(self, ctx: commands.Context[Parrot]) -> None:
        """Shows the help message for the automod feature."""
        embeds = automod_embeds()
        view = PaginationView(author=ctx.author, items=embeds)
        await view.start(ctx)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Automod(bot))
