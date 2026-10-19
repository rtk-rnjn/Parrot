from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .dashboard import ConfigDashboard

if TYPE_CHECKING:
    from core import Bot


_log = logging.getLogger(__name__)


class Config(commands.Cog, name="Server Settings", command_attrs={"hidden": True}):
    """Interactive dashboard for every server setting."""

    help_emoji = "\N{GEAR}\N{VARIATION SELECTOR-16}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    @commands.command(name="config", aliases=["settings", "configure", "configurations"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def config(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Open the server settings dashboard.

        This command opens a dashboard for configuring every server setting.
        The dashboard is interactive and updates in place, so you can use the same message to change settings without cluttering the chat.
        Use the buttons and dropdowns to navigate through different sections and make changes.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None, "This command can only be used in a server (guild)."

        config = await self.bot.database.get_guild_settings(ctx.guild.id)
        dashboard = ConfigDashboard(ctx.author, bot=self.bot, guild=ctx.guild, config=config)
        await ctx.typing()
        return await dashboard.start(ctx)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Config(bot))
