from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .handlers import resolve
from .models import ErrorResponse
from .utils import random_quote

if TYPE_CHECKING:
    from core import Parrot

    from .models import Context

_log = logging.getLogger("bot.cogs.events.error")

_IGNORED: tuple[type[Exception], ...] = (
    commands.CommandNotFound,
    discord.NotFound,
    discord.Forbidden,
    commands.PrivateMessageOnly,
    commands.NotOwner,
)


def _should_ignore(ctx: Context, error: Exception) -> bool:
    if ctx.guild is None or ctx.author.bot or ctx.command is None:
        return True
    if ctx.command.has_error_handler():
        return True
    return isinstance(error, _IGNORED)


class CommandError(commands.Cog, command_attrs={"hidden": True}):
    """This category is of no use for you, ignore it."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    async def _send_reply(self, ctx: Context, response: ErrorResponse) -> discord.Message:
        embed = discord.Embed(title=response.title, description=response.description, color=discord.Color.red())
        quote = random_quote()
        return await ctx.reply(content=f"-# _{quote}_" if quote else None, embed=embed)

    async def _cleanup(self, ctx: Context, msg: discord.Message, delete_after: float | None) -> None:
        """Remove our reply if the invoking message is deleted, or after `delete_after`."""
        try:
            await self.bot.wait_for("message_delete", timeout=10, check=lambda m: m.id == ctx.message.id)
        except TimeoutError:
            if delete_after:
                await msg.delete(delay=max(delete_after - 10, 0))
            return

        with contextlib.suppress(discord.NotFound):
            await msg.delete(delay=0)

    @staticmethod
    def _log_and_raise(ctx: Context, error: Exception) -> None:
        _log.exception(
            "Error in command `%s` invoked by `%s (ID: %s)` in guild `%s (ID: %s)`",
            ctx.command.qualified_name if ctx.command else None,
            ctx.author,
            ctx.author.id,
            ctx.guild,
            ctx.guild.id if ctx.guild else None,
            exc_info=error,
        )
        raise error

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: commands.CommandError) -> None:
        await self.bot.wait_until_ready()

        original = getattr(error, "original", error)
        if _should_ignore(ctx, original):
            return

        # Owners bypass permission checks.
        if isinstance(original, commands.MissingPermissions) and await self.bot.is_owner(ctx.author):
            await ctx.reinvoke()
            return

        response = resolve(ctx, original)

        if response.reset_cooldown and ctx.command:
            ctx.command.reset_cooldown(ctx)

        msg = await self._send_reply(ctx, response)
        await self._cleanup(ctx, msg, response.delete_after)

        if response.should_raise:
            self._log_and_raise(ctx, original)
