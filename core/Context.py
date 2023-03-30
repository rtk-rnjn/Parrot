# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import datetime
import functools
import io
import time
from contextlib import suppress
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import aiohttp

import discord
from discord.ext import commands
from utilities.emotes import emojis

CONFIRM_REACTIONS: Tuple = (
    "\N{THUMBS UP SIGN}",
    "\N{THUMBS DOWN SIGN}",
)

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec("P")

    MaybeAwaitableFunc = Callable[P, "MaybeAwaitable[T]"]  # type: ignore

T = TypeVar("T")
MaybeAwaitable = Union[T, Awaitable[T]]

Callback = MaybeAwaitable
# BotT = TypeVar("BotT", bound=commands.Bot)

# VOTER_ROLE_ID = 836492413312040990


class Context(commands.Context[commands.Bot], Generic[T]):
    """A custom implementation of commands.Context class."""

    if TYPE_CHECKING:
        from .Cog import Cog
        from .Parrot import Parrot

    prefix: Optional[str]
    command: commands.Command[Any, ..., Any]
    cog: Optional[Cog]
    bot: Parrot

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<core.Context author={self.author} guild={self.guild} channel={self.channel} command={self.command}>"

    @property
    def session(self) -> "aiohttp.ClientSession":
        return self.bot.http_session

    async def tick(
        self, emoji: Union[discord.PartialEmoji, discord.Emoji, str] = None
    ) -> None:
        await self.message.add_reaction(emoji or "\N{WHITE HEAVY CHECK MARK}")

    async def ok(self) -> None:
        return await self.tick()

    async def wrong(
        self, emoji: Union[discord.PartialEmoji, discord.Emoji, str] = None
    ) -> None:
        await self.message.add_reaction(emoji or "\N{CROSS MARK}")

    async def cross(self) -> None:
        return await self.wrong()

    async def is_voter(self) -> Optional[bool]:
        # if member := self.bot.server.get_member(self.author.id):
        #     return member._roles.has(VOTER_ROLE_ID)

        # if data := await self.bot.mongo.extra.user_misc.find_one(
        #     {
        #         "_id": self.author.id,
        #         "topgg_vote_expires": {"$gte": discord.utils.utcnow()},
        #     }
        # ):
        #     return True

        # if self.bot.HAS_TOP_GG:
        #     return await self.bot.topgg.get_user_vote(self.author.id)

        # TODO: FIX VOTING ROLE ADDING SYSTEM

        return True

    async def dj_role(
        self,
    ) -> Optional[discord.Role]:
        if channel := getattr(self.author.voice, "channel"):  
            # channel: discord.VoiceChannel
            members = sum(not m.bot for m in channel.members)  # type: ignore  # channel is surely the voice channel
            if members <= 3:
                return self.guild.default_role

        perms = self.author.guild_permissions
        if perms.manage_guild or perms.manage_channels:
            return self.guild.default_role
        try:
            dj_role = self.guild.get_role(
                self.bot.server_config[self.guild.id]["dj_role"] or 0
            )
            author_dj_role = discord.utils.find(
                lambda r: r.name.lower() == "dj",
                self.author.roles,
            )
            server_dj_role = discord.utils.find(
                lambda r: r.name.lower() == "dj",
                self.guild.roles,
            )
            return dj_role or author_dj_role or server_dj_role
        except KeyError:
            if data := await self.bot.mongo.parrot_db.server_config.find_one(
                {"_id": self.guild.id}
            ):
                return self.guild.get_role(data.get("dj_role") or 0)
        return None

    async def muterole(
        self,
    ) -> Optional[discord.Role]:
        try:
            author_muted = discord.utils.find(
                lambda m: m.name.lower() == "muted", self.author.roles
            )
            global_muted = discord.utils.find(
                lambda m: m.name.lower() == "muted", self.guild.roles
            )
            return (
                self.guild.get_role(
                    self.bot.server_config[self.guild.id]["mute_role"] or 0
                )
                or global_muted
                or author_muted
            )
        except KeyError:
            if data := await self.bot.mongo.parrot_db.server_config.find_one(
                {"_id": self.guild.id}
            ):
                return self.guild.get_role(data["mute_role"] or 0)
        return None

    async def modrole(
        self,
    ) -> Optional[discord.Role]:
        try:
            return self.guild.get_role(
                self.bot.server_config[self.guild.id]["mod_role"] or 0
            )
        except KeyError:
            if data := await self.bot.mongo.parrot_db.server_config.find_one(
                {"_id": self.guild.id}
            ):
                return self.guild.get_role(data["mod_role"] or 0)
        return None

    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.MessageReference]:
        ref = self.message.reference
        if ref is not None and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    @staticmethod
    def with_type(func: Callable[..., Any]) -> Coroutine[Any, Any, Any]:
        @functools.wraps(func)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:

            context = args[0] if isinstance(args[0], commands.Context) else args[1]
            async with context.typing():
                return await func(*args, **kwargs)

        return wrapped

    async def send(
        self,
        content: Optional[str] = None,
        *,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        perms: discord.Permissions = self.channel.permissions_for(self.me)
        if not (perms.send_messages and perms.embed_links):
            with suppress(discord.Forbidden):
                await self.author.send(
                    (
                        "Bot don't have either Embed Links/Send Messages permission in that channel. "
                        "Please give sufficient permissions to the bot."
                    )
                )
                return None
        if bold:
            content = f"**{content}**"
        if italic:
            content = f"*{content}*"
        if underline:
            content = f"__{content}__"
        embeds: Union[discord.Embed, List[discord.Embed]] = kwargs.get(
            "embed"
        ) or kwargs.get("embeds")

        def __set_embed_defaults(embed: discord.Embed, /):
            if not embed.color:
                embed.color = self.bot.color
            if not embed.timestamp:
                embed.timestamp = discord.utils.utcnow()
            if not embed.footer:
                embed.set_footer(
                    text=f"Requested by {self.author}",
                    icon_url=self.author.display_avatar.url,
                )

        if isinstance(embeds, (list, tuple)):
            for embed in embeds:
                if isinstance(embed, discord.Embed):
                    __set_embed_defaults(embed)
        else:
            if isinstance(embeds, discord.Embed):
                __set_embed_defaults(embeds)

        return await super().send(str(content)[:1990] if content else None, **kwargs)

    async def reply(
        self, content: Optional[str] = None, **kwargs: Any
    ) -> Optional[discord.Message]:
        try:
            return await self.send(
                content, reference=kwargs.get("reference") or self.message, **kwargs
            )
        except discord.HTTPException:  # message deleted
            return await self.send(content, **kwargs)

    async def error(self, *args: Any, **kwargs: Any) -> Optional[discord.Message]:
        """Similar to send, but if the original message is deleted, it will delete the error message as well."""
        embed: discord.Embed = kwargs.get("embed")
        if isinstance(embed, discord.Embed) and not embed.color:
            # if no color is set, set it to red
            embed.color = discord.Color.red()

        msg: Optional[discord.Message] = await self.reply(
            *args,
            **kwargs,
        )
        if isinstance(msg, discord.Message):
            try:
                await self.wait_for(
                    "message_delete",
                    check=lambda m: m.id == self.message.id,
                    timeout=30,
                )
            except asyncio.TimeoutError:
                return msg
            else:
                return await msg.delete(delay=0)
        return msg

    async def entry_to_code(
        self, entries: List[Tuple[Any, Any]]
    ) -> Optional[discord.Message]:
        width = max(len(str(a)) for a, b in entries)
        output = ["```"]
        output.extend(f"{name:<{width}}: {entry}" for name, entry in entries)
        output.append("```")
        return await self.send("\n".join(output))

    async def indented_entry_to_code(
        self, entries: List[Tuple[Any, Any]]
    ) -> Optional[discord.Message]:
        width = max(len(str(a)) for a, b in entries)
        output = ["```"]
        output.extend(f"\u200b{name:>{width}}: {entry}" for name, entry in entries)
        output.append("```")
        return await self.send("\n".join(output))

    async def emoji(self, emoji: str) -> str:
        return emojis[emoji]

    async def prompt(
        self,
        message: Optional[str] = None,
        *,
        timeout: float = 60.0,
        delete_after: bool = True,
        reacquire: bool = True,
        author_id: Optional[int] = None,
        **kwargs: Any,
    ) -> Optional[bool]:
        """|coro|

        An interactive reaction confirmation dialog.

        Parameters
        -----------
        message: str
            The message to show along with the prompt.
        timeout: float
            How long to wait before returning.
        delete_after: bool
            Whether to delete the confirmation message after we're done.
        reacquire: bool
            Whether to release the database connection and then acquire it
            again when we're done.
        author_id: Optional[int]
            The member who should respond to the prompt. Defaults to the author of the
            Context's message.
        Returns
        --------
        Optional[bool]
            ``True`` if explicit confirm,
            ``False`` if explicit deny,
            ``None`` if deny due to timeout
        """
        author_id = author_id or self.author.id
        view = ConfirmationView(
            timeout=timeout,
            delete_after=delete_after,
            reacquire=reacquire,
            ctx=self,
            author_id=author_id,
        )
        view.message = await self.send(message, view=view, **kwargs)
        await view.wait()
        return view.value

    async def release(
        self,
        _for: Union[int, float, datetime.datetime] = None,
        *,
        result: Optional[T] = None,
    ) -> Optional[T]:
        if isinstance(_for, datetime.datetime):
            await discord.utils.sleep_until(_for, result)
        else:
            await asyncio.sleep(_for or 0, result)

    async def safe_send(
        self, content: str, *, escape_mentions: bool = True, **kwargs: Any
    ) -> Optional[discord.Message]:
        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop("file", None)
            return await self.send(
                file=discord.File(fp, filename="message_too_long.txt"), **kwargs
            )  # must have `Attach Files` permissions
        return await self.send(content, **kwargs)

    async def bulk_add_reactions(
        self,
        message: Optional[discord.Message] = None,
        *reactions: Union[discord.Emoji, discord.PartialEmoji, str],
    ) -> None:
        if message is None or not isinstance(message, discord.Message):
            message: discord.Message = self.message

        coros: List[Coroutine] = [
            message.add_reaction(reaction) for reaction in reactions
        ]
        await asyncio.wait(coros)

    async def confirm(
        self,
        channel: discord.TextChannel,
        user: Union[discord.Member, discord.User],
        *args: Any,
        timeout: float = 60,
        delete_after: bool = False,
        **kwargs: Any,
    ) -> Optional[bool]:
        """|coro|

        Reaction based Prompt

        Parameters
        -----------
        channel: Channel
            Message that will be sent in the channel
        timeout: float
            How long to wait before returning.
        delete_after: bool
            Whether to delete the confirmation message after we're done.
        user: Union[Member, User]
            The member who should respond to the prompt.

        Returns
        -----------
        Optional[bool]
            ``True`` if explicit confirm,
            ``None`` if deny due to timeout
        """

        message: Optional[discord.Message] = await channel.send(*args, **kwargs)
        await self.bulk_add_reactions(message, *CONFIRM_REACTIONS)

        def check(payload: discord.RawReactionActionEvent) -> bool:
            return (
                payload.message_id == message.id
                and payload.user_id == user.id
                and str(payload.emoji) in CONFIRM_REACTIONS
            )

        try:
            payload: discord.RawReactionActionEvent = await self.bot.wait_for(
                "raw_reaction_add", check=check, timeout=timeout
            )
            return str(payload.emoji) == "\N{THUMBS UP SIGN}"
        except asyncio.TimeoutError:
            return None
        finally:
            if delete_after:
                await message.delete(delay=0)

    async def wait_for(
        self,
        event_name: str,
        *,
        timeout: Optional[float] = None,
        check: Optional[Callable[..., bool]] = None,
        suppress_error: bool = False,
        **kwargs: Any,
    ) -> Any:
        """|coro|

        Waits for a given event to be triggered.

        Parameters
        -----------
        event_name: str
            The event name to wait for.
        timeout: float
            How long to wait for the event to be triggered.
        **kwargs: Any
            The arguments to pass to the event.

        Examples
        -----------

        ```python
        # Wait for the message to be sent
        await ctx.wait_for("message", timeout=10, author__id=741614468546560092)
        ```
        ```python
        await ctx.wait_for("on_message_edit", check=lambda m: m.author.id == self.bot.user.id)
        ```

        Raises
        -----------
        asyncio.TimeoutError
            If the event is not triggered before the given timeout.
        """
        if event_name.lower().startswith("on_"):
            event_name = event_name[3:].lower()

        def outer_check(**kw: Any) -> Callable[..., bool]:
            """Check function for the event"""
            if check is not None:
                return check

            def __suppress_attr_error(
                func: Callable, *args: Any, **kwargs: Any
            ) -> bool:
                """Suppress attribute error for the function."""
                try:
                    func(*args, **kwargs)
                    return True
                except AttributeError:
                    return False

            def __internal_check(
                *args,
            ) -> bool:
                """Main check function"""
                convert_pred = [
                    (attrgetter(k.replace("__", ".")), v) for k, v in kw.items()
                ]
                return all(
                    all(pred(i) == val for i in args if __suppress_attr_error(pred, i))
                    for pred, val in convert_pred
                )

            return __internal_check

        try:
            return await self.bot.wait_for(
                event_name, timeout=timeout, check=outer_check(**kwargs)
            )
        except asyncio.TimeoutError:
            if suppress_error:
                await self.message.add_reaction("\N{ALARM CLOCK}")
                return None
            raise

    async def paginate(
        self,
        entries: List[Any],
        *,
        _type: str = "SimplePages",
        **kwargs: Any,
    ) -> None:
        """|coro|

        Paginates a list of entries.

        Parameters
        -----------
        entries: List[str]
            A list of entries to paginate.
        _type: str
            The type of paginator to use.
        **kwargs: Any
            The arguments to pass to the paginator.

        Raises
        -----------
        ValueError
            If the paginator type is not found.
        """
        if not entries:
            raise commands.BadArgument("Cannot paginate an empty list.")

        if _type == "SimplePages":
            from cogs.meta.robopage import SimplePages

            pages = SimplePages(
                entries,
                ctx=self,
                **kwargs,
            )
            await pages.start()
            return

        if _type == "PaginationView":
            from utilities.paginator import PaginationView

            pages = PaginationView(entries)
            await pages.start(
                ctx=self,
            )
            return

        raise ValueError("Invalid paginator type")

    async def multiple_wait_for(
        self,
        events: Union[
            List[Tuple[str, Callable[..., bool]]], Dict[str, Callable[..., bool]]
        ],
        *,
        return_when: Literal[
            "FIRST_COMPLETED", "ALL_COMPLETED", "FIRST_EXCEPTION"
        ] = "FIRST_COMPLETED",
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Tuple[Set[asyncio.Task], Set[asyncio.Task]]:
        """|coro|

        To wait for multiple events at once.

        Parameters
        -----------
        events: List[Tuple[str, Callable[..., bool]]]
            A list of events to wait for.
        return_when: str
            `return_when` indicates when this function should return. It must be one of the following constants

            ```ini
            +-----------------+-----------------------------------+
            | FIRST_COMPLETED | The function will return when any |
            |                 | future finishes or is cancelled.  |
            +-----------------+-----------------------------------+
            |                 | The function will return when any |
            |                 | future finishes by raising an     |
            | FIRST_EXCEPTION | exception. If no future raises an |
            |                 | exception then it is equivalent   |
            |                 | to ALL_COMPLETED.                 |
            +-----------------+-----------------------------------+
            |  ALL_COMPLETED  | The function will return when all |
            |                 | futures finish or are cancelled.  |
            +-----------------+-----------------------------------+
            ```

        timeout: Optional[float]
            The maximum amount of time in seconds to wait for the events to finish.

        Returns
        -----------
        Tuple[Set[asyncio.Task], Set[asyncio.Task]]
            A tuple of two sets of tasks, the first set is the finished tasks, the second set is the cancelled tasks.

        Raises
        -----------
        asyncio.TimeoutError
            If the event is not triggered before the given timeout.
        """
        if isinstance(events, dict):
            events = list(events.items())  # type: ignore

        _events: Set[Coroutine[Any, Any, Any]] = {
            self.wait_for(event, check=check, timeout=timeout, **kwargs)
            for event, check in events
        }

        return await asyncio.wait(
            _events,
            timeout=timeout + 0.001,
            return_when=getattr(asyncio, return_when, "FIRST_COMPLETED"),
        )

    async def wait_for_till(
        self,
        events: Union[
            List[Tuple[str, Callable[..., bool]]], Dict[str, Callable[..., bool]]
        ],
        *,
        _for: Union[float, int, None] = None,
        after: Union[float, int] = None,
        **kwargs: Any,
    ) -> List[Any]:
        """|coro|

        Returns multiple event record at given time.

        Parameters
        -----------
        events: List[Tuple[str, Callable[..., bool]]]
            A list of events to wait for.
        _for: Union[float, int, None]
            The amount of time to wait for the event to be triggered.
        after: Union[float, int]
            The amount of time to wait after the event is triggered.
        **kwargs: Any
            The arguments to pass to the event.

        Raises
        -----------
        asyncio.TimeoutError
            If the event is not triggered before the given timeout.

        Returns
        -----------
        List[Any]
            The list of discord Objects.
        """
        if after:
            await self.release(after)
        done_result: List[Any] = []

        _for = _for or 0
        now = time.time() + _for

        def __internal_appender(completed_result: Iterable[asyncio.Task]) -> None:
            for task in completed_result:
                done_result.append(task.result())

        while time.time() <= now:
            done, _ = await self.multiple_wait_for(
                events, return_when="FIRST_COMPLETED", **kwargs
            )
            __internal_appender(done)

        if not _for:
            done, _ = await self.multiple_wait_for(
                events, return_when="FIRST_COMPLETED", **kwargs
            )
            __internal_appender(done)

        return done_result

    async def retry(
        self,
        callback: Callable[..., Any],
        *args: Any,
        multiplier: int = 5,
        retries: 5,
        exception: Type[Exception] = Exception,
        **kwargs: Any,
    ):
        errors: Dict[int, str] = {}
        for retry in range(max(retries, 1)):
            try:
                return await discord.utils.maybe_coroutine(callback, *args, **kwargs)
            except exception as e:
                errors[retry] = e
                await self.release(multiplier * retry)

        raise errors[retry]


class ConfirmationView(discord.ui.View):
    def __init__(
        self,
        *,
        timeout: float,
        author_id: int,
        reacquire: bool,
        ctx: Context,
        delete_after: bool,
    ) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.delete_after: bool = delete_after
        self.author_id: int = author_id
        self.ctx: Context = ctx
        self.reacquire: bool = reacquire
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message(
            "This confirmation dialog is not for you.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.reacquire:
            await asyncio.sleep(0)
        if self.delete_after and self.message:
            self.stop()
            await self.message.delete(delay=0)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        self.value = True
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        self.value = False
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()
        self.stop()
