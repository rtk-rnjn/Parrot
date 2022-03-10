from __future__ import annotations
from asyncio.log import logger

from concurrent.futures import ThreadPoolExecutor
from functools import wraps, partial
import asyncio

from discord.ext import commands
import discord

from typing import Any, Optional, Union
from core import Context

from .log import get_logger



def convert_bool(text: Union[str, bool]) -> bool:
    """True/False converter"""
    if str(text).lower() in ("yes", "y", "true", "t", "1", "enable", "on", "o"):
        return True
    if str(text).lower() in ("no", "n", "false", "f", "0", "disable", "off", "x"):
        return False
    return False


def reason_convert(text: commands.clean_content) -> str:
    """To strip the reason."""
    return text[:450:] or "No reason provided"


class ToAsync:
    def __init__(self, *, executor: Optional[ThreadPoolExecutor] = None):

        self.executor = executor

    def __call__(self, blocking):
        @wraps(blocking)
        async def wrapper(*args, **kwargs):

            loop = asyncio.get_event_loop()
            if not self.executor:
                self.executor = ThreadPoolExecutor()

            func = partial(blocking, *args, **kwargs)

            return await loop.run_in_executor(self.executor, func)

        return wrapper


class BannedMember(commands.Converter):
    """A coverter that is used for fetching Banned Member of Guild"""

    async def convert(self, ctx: Context, argument: Any) -> Optional[discord.User]:
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                ban_entry = await ctx.guild.fetch_ban(discord.Object(id=member_id))
                return ban_entry.user
            except discord.NotFound:
                raise commands.BadArgument(
                    "User Not Found! Probably this member has not been banned before."
                ) from None

        ban_list = await ctx.guild.bans()
        for entry in ban_list:
            if argument in (entry.user.name, str(entry.user)):
                return entry.user
            if str(entry.user) == argument:
                return entry.user

        raise commands.BadArgument(
            "User Not Found! Probably this member has not been banned before."
        ) from None


class WrappedMessageConverter(commands.MessageConverter):
    """A converter that handles embed-suppressed links like <http://example.com>."""

    async def convert(self, ctx: Context, argument: str) -> discord.Message:
        """Wrap the commands.MessageConverter to handle <> delimited message links."""
        # It's possible to wrap a message in [<>] as well, and it's supported because its easy
        if argument.startswith("[") and argument.endswith("]"):
            argument = argument[1:-1]
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]

        return await super().convert(ctx, argument)
