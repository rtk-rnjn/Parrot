from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot


class Todo(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="todo")
    async def todo(self, ctx: commands.Context) -> None:
        """Manage your to-do list."""
        if ctx.invoked_subcommand is None:
            # List TODO(s)
            await ctx.send_help(ctx.command)


async def setup(bot: Parrot) -> None:
    """Load the Todo cog."""
    await bot.add_cog(Todo(bot))
