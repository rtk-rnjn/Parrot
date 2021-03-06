from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from typing import Any, Callable, Optional, Union

import discord
from core import Context
from discord.ext import commands


def convert_bool(text: Union[str, bool]) -> bool:
    """True/False converter"""
    if str(text).lower() in ("yes", "y", "true", "t", "1", "enable", "on", "o"):
        return True
    return False


class ActionReason(commands.Converter):
    """Action reason converter"""

    async def convert(self, ctx: Context, argument: str = None) -> str:
        """Convert the argument to a action string"""
        ret = f"Action requested by {ctx.author} (ID: {ctx.author.id}) | Reason: {argument or 'no reason provided'}"

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(
                f"Reason is too long ({len(argument)}/{reason_max})"
            )
        return ret


class ToAsync:
    """Converts a blocking function to an async function"""

    def __init__(self, *, executor: Optional[ThreadPoolExecutor] = None) -> None:

        self.executor = executor

    def __call__(self, blocking) -> Callable:
        @wraps(blocking)
        async def wrapper(*args, **kwargs) -> Any:

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

        async for entry in ctx.guild.bans():
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


def can_execute_action(
    ctx: Context, user: discord.Member, target: discord.Member
) -> bool:
    return (
        user.id in ctx.bot.owner_ids
        or user == ctx.guild.owner
        or user.top_role > target.top_role
    )


class MemberID(commands.Converter):
    """A converter that handles user mentions and user IDs."""

    async def convert(self, ctx: Context, argument: str):
        """Convert a user mention or ID to a member object."""
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(
                    f"{argument} is not a valid member or member ID."
                ) from None
            else:
                m = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
                if m is None:
                    # hackban case
                    return type(
                        "_Hackban",
                        (),
                        {"id": member_id, "__str__": lambda s: f"Member ID {s.id}"},
                    )()

        if not can_execute_action(ctx, ctx.author, m):
            await ctx.send(
                f"{ctx.author.mention} can not {ctx.command.qualified_name} the {m}, as the their's role is above you"
            )
        return m
