from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING

import discord
from colorama import Fore
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from redis import asyncio

if TYPE_CHECKING:
    from core.bot import Parrot


_log = logging.getLogger("bot.cogs.owner")


class Owner(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        _log.info("Cog loaded: %s", self.__class__.__name__)

    def _format_traceback(self, error: Exception) -> str:
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = "".join(tb)
        return f"```ansi\n{Fore.RED}{tb_str}{Fore.RESET}\n```"

    @commands.command(name="redis-repl", aliases=["redis-cli", "redis"])
    @commands.is_owner()
    async def redis_repl(self, ctx: commands.Context[Parrot]) -> None:
        """Start a Redis REPL session."""
        await ctx.send("Starting Redis REPL session. Type `exit` to quit.")

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        while True:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=300)
            except asyncio.TimeoutError:
                await ctx.send("Redis REPL session timed out.")
                break

            if msg.content.lower() == "exit":
                await ctx.send("Exiting Redis REPL session.")
                break

            codeblock = codeblock_converter(msg.content)
            try:
                result = await self.bot.database_manager.redis_client.execute_command(codeblock.content)
                await msg.reply(result)
            except Exception as e:
                tb_fmt = self._format_traceback(e)
                await msg.reply(tb_fmt)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Owner(bot))
