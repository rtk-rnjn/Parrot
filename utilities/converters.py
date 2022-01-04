from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import wraps, partial
import asyncio

from discord.ext import commands
import discord

from typing import Optional


def convert_bool(text: str) -> Optional[bool]:
    if text.lower() in ('yes', 'y', 'true', 't', '1', 'enable', 'on', 'o'):
        return True
    if text.lower() in ('no', 'n', 'false', 'f', '0', 'disable', 'off', 'x'):
        return False
    return None


def reason_convert(text: commands.clean_content) -> str:
    return text[:450:]


class to_async:
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
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument(
                    "This member has not been banned before.") from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument,
                                    ban_list)

        if entity is None:
            raise commands.BadArgument(
                "This member has not been banned before.")

        return entity
