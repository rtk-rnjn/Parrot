from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    Coroutine,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from lru import LRU

import discord
from core import Context
from discord.ext import commands
from utilities.config import LRU_CACHE

NUMBER = Union[int, float]

KT = TypeVar("KT", bound=Any)
VT = TypeVar("VT", bound=Any)


def convert_bool(text: Union[str, bool]) -> bool:
    """True/False converter"""
    return str(text).lower() in {"yes", "y", "true", "t", "1", "enable", "on", "o"}


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

        self.executor = executor or ThreadPoolExecutor()

    def __call__(self, blocking) -> Callable[..., Coroutine]:
        @wraps(blocking)
        async def wrapper(*args, **kwargs) -> Any:

            return await asyncio.get_event_loop().run_in_executor(
                self.executor, partial(blocking, *args, **kwargs)
            )

        return wrapper


class BannedMember(commands.Converter):
    """A coverter that is used for fetching Banned Member of Guild"""

    async def convert(
        self, ctx: Context, argument: Union[str, NUMBER, Any]
    ) -> Optional[discord.User]:
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

    async def convert(self, ctx: Context, argument: str) -> discord.Member:
        """Convert a user mention or ID to a member object."""
        try:
            m: discord.Member = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(
                    f"{argument} is not a valid member or member ID."
                ) from None
            else:
                m: Optional[discord.Member] = await ctx.bot.get_or_fetch_member(
                    ctx.guild, member_id
                )
                if m is None:
                    # hackban case
                    return type(
                        "_Hackban",
                        (),
                        {"id": member_id, "__str__": lambda s: f"Member ID {s.id}"},
                    )()

        if not can_execute_action(ctx, ctx.author, m):
            raise commands.BadArgument(
                f"{ctx.author.mention} can not {ctx.command.qualified_name} the {m}, as the their's role is above you"
            )
        return m


class Cache(dict, Generic[KT, VT]):
    def __init__(
        self,
        cache_size: Optional[int] = LRU_CACHE,
        *,
        callback: Optional[Callable[[KT, VT], Any]] = None,
    ) -> None:
        self.cache_size: int = cache_size
        self.__internal_cache: "LRU" = LRU(
            self.cache_size, callback=callback or (lambda a, b: ...)
        )

        self.items: Callable[[], List[Tuple[int, Any]]] = self.__internal_cache.items  # type: ignore
        self.peek_first_item: Callable[[], Optional[Tuple[int, Any]]] = self.__internal_cache.peek_first_item  # type: ignore
        self.peek_last_item: Callable[[], Optional[Tuple[int, Any]]] = self.__internal_cache.peek_last_item  # type: ignore
        self.get_size: Callable[[], int] = self.__internal_cache.get_size  # type: ignore
        self.set_size: Callable[[int], None] = self.__internal_cache.set_size  # type: ignore
        self.has_key: Callable[[object], bool] = self.__internal_cache.has_key  # type: ignore
        self.update: Callable[..., None] = self.__internal_cache.update  # type: ignore
        self.values: Callable[[], List[Any]] = self.__internal_cache.values  # type: ignore
        self.keys: Callable[[], List[Any]] = self.__internal_cache.keys  # type: ignore

    def __repr__(self) -> str:
        return repr(self.__internal_cache)

    def __len__(self) -> int:
        return len(self.__internal_cache)

    def __getitem__(self, __k: KT) -> VT:
        return self.__internal_cache[__k]

    def __delitem__(self, __v: KT) -> None:
        del self.__internal_cache[__v]

    def __contains__(self, __o: object) -> bool:
        return self.has_key(__o)

    def __setitem__(self, __k: KT, __v: VT) -> None:
        self.__internal_cache[__k] = __v

    def get(self, __k: KT) -> VT:
        return self.__internal_cache.get(__k)

    def pop(self, __k: KT, *args: Any) -> VT:
        return self.__internal_cache.pop(__k, *args)
