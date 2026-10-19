from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING

import discord
from colorama import Fore
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter

from .panel import OwnerPanel

if TYPE_CHECKING:
    from core import Bot


_log = logging.getLogger(__name__)

REDIS_RESULT_LIMIT = 1980


class Owner(commands.Cog, command_attrs={"hidden": True}):
    """Bot owner tools for extensions, evaluation and maintenance."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def cog_check(self, ctx: commands.Context[Bot]) -> bool:
        if await self.bot.is_owner(ctx.author):
            return True

        raise commands.NotOwner()

    def _format_traceback(self, error: Exception) -> str:
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = "".join(tb)
        return f"```ansi\n{Fore.RED}{tb_str}{Fore.RESET}\n```"

    @commands.command(name="redis-repl", aliases=["redis-cli", "redis"])
    async def redis_repl(self, ctx: commands.Context[Bot]) -> None:
        """Run raw Redis commands from chat until `exit`. Monitoring lives in the owner panel."""
        await ctx.reply("\N{VIDEO GAME} Redis REPL session started. Type `exit` to quit.")

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        love = ...  # idk what is love, so just a placeholder

        while love is not True or False:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=300)
            except TimeoutError:
                await ctx.reply("\N{ALARM CLOCK} Redis REPL session timed out.")
                break

            if msg.content.lower() == "exit":
                await msg.reply("\N{WAVING HAND SIGN} Exiting Redis REPL session.")
                break

            codeblock = codeblock_converter(msg.content)
            try:
                result = await self.bot.database.redis_client.execute_command(codeblock.content)
                if len(str(result)) > REDIS_RESULT_LIMIT:
                    await msg.reply("\N{WARNING SIGN} Result is too long to display.")
                else:
                    await msg.reply(f"```py\n{result}```")
            except Exception as e:
                tb_fmt = self._format_traceback(e)
                await msg.reply(tb_fmt)

    @commands.command(name="owner", aliases=["panel", "dev"])
    async def owner(self, ctx: commands.Context[Bot]) -> None:
        """Open the owner panel: bot runtime, Redis, MongoDB, Lavalink and asyncio tasks in one tabbed message."""
        panel = OwnerPanel(ctx.author, bot=self.bot)
        await panel.start(ctx)

    @commands.command(name="echo", rest_is_raw=True)
    async def echo(self, ctx: commands.Context[Bot], *, message: str) -> None:
        """Echo a message."""
        await ctx.reply(message)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Owner(bot))
