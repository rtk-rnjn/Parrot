from __future__ import annotations

import asyncio
import datetime
import functools
import importlib.util
import io
import logging
from collections.abc import Awaitable, Callable, Iterable
from contextlib import suppress
from io import BytesIO
from operator import attrgetter
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

import aiohttp
import humanize
import PIL
from bs4 import BeautifulSoup
from PIL import Image

import discord
from discord.ext import commands
from utilities.converters import ToImage, emoji_to_url
from utilities.emotes import emojis
from utilities.regex import LINKS_RE

CONFIRM_REACTIONS: tuple = (
    "\N{THUMBS UP SIGN}",
    "\N{THUMBS DOWN SIGN}",
)

if TYPE_CHECKING:
    from pymongo.results import UpdateResult
    from typing_extensions import ParamSpec

    from .Parrot import Parrot

    P = ParamSpec("P")
    BotT = TypeVar("BotT", bound="Parrot")

    MaybeAwaitableFunc = Callable[P, "MaybeAwaitable[T]"]
else:
    BotT = TypeVar("BotT", bound="commands.Bot")

T = TypeVar("T")
MaybeAwaitable = T | Awaitable[T]

Callback = MaybeAwaitable

VOTER_ROLE_ID = 1139439408723013672
log = logging.getLogger("core.context")


if importlib.util.find_spec("lxml") is not None:
    HTML_PARSER = "lxml"
else:
    HTML_PARSER = "html.parser"


class Context(commands.Context[commands.Bot], Generic[BotT]):
    """A custom implementation of commands.Context class."""

    bot: BotT | Parrot
    guild: discord.Guild
    command: commands.Command
    me: discord.Member
    author: discord.Member

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if self.guild is not None:
            self.guild_collection = self.bot.guild_level_db[f"{self.guild.id}"]
        self.user_collection = self.bot.user_db[f"{self.author.id}"]

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} author=`{self.author}` ({self.author.id}) guild=`{self.guild}` ({self.guild.id}) "
            f"channel=`{self.channel}` ({self.channel.id}) command={self.command.qualified_name}>"
        )

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.http_session

    async def tick(self, emoji: discord.PartialEmoji | discord.Emoji | str | None = None) -> None:
        await self.message.add_reaction(emoji or "\N{WHITE HEAVY CHECK MARK}")

    async def ok(self) -> None:
        return await self.tick()

    async def wrong(self, emoji: discord.PartialEmoji | discord.Emoji | str | None = None) -> None:
        await self.message.add_reaction(emoji or "\N{CROSS MARK}")

    async def cross(self) -> None:
        return await self.wrong()

    async def is_voter(self) -> bool | None:
        if member := self.bot.server.get_member(self.author.id):
            return member._roles.has(VOTER_ROLE_ID)

        # if await self.bot.user_collections_ind.find_one(
        #     {
        #         "_id": self.author.id,
        #         "topgg_vote_expires": {"$gte": discord.utils.utcnow()},
        #     },
        # ):
        #     return True

        if self.bot.HAS_TOP_GG:
            return await self.bot.topgg.get_user_vote(self.author.id)

        return False

    async def dj_role(self) -> discord.Role | None:
        assert self.guild is not None and isinstance(self.author, discord.Member)

        if self.author.voice and (channel := self.author.voice.channel):
            # channel: discord.VoiceChannel
            members = sum(not m.bot for m in channel.members)  # channel is surely the voice channel
            if members <= 3:
                return self.guild.default_role

        perms = self.author.guild_permissions
        if perms.manage_guild or perms.manage_channels:
            return self.guild.default_role
        try:
            dj_role = self.guild.get_role(self.bot.guild_configurations_cache[self.guild.id]["dj_role"] or 0)
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
            if data := await self.bot.guild_configurations.find_one({"_id": self.guild.id}):
                return self.guild.get_role(data.get("dj_role") or 0)
        return None

    @staticmethod
    async def get_mute_role(bot: Parrot, guild: discord.Guild) -> discord.Role | None:
        try:
            global_muted = discord.utils.find(lambda m: m.name.lower() == "muted", guild.roles)
            return guild.get_role(bot.guild_configurations_cache[guild.id]["mute_role"] or 0) or global_muted
        except KeyError:
            if data := await bot.guild_configurations.find_one({"_id": guild.id}):
                return guild.get_role(data["mute_role"] or 0)
        return None

    async def muterole(self) -> discord.Role | None:
        try:
            author_muted = discord.utils.find(lambda m: m.name.lower() == "muted", self.author.roles)
            global_muted = discord.utils.find(lambda m: m.name.lower() == "muted", self.guild.roles)
            return (
                self.guild.get_role(self.bot.guild_configurations_cache[self.guild.id]["mute_role"] or 0)
                or global_muted
                or author_muted
            )
        except KeyError:
            if data := await self.bot.guild_configurations.find_one({"_id": self.guild.id}):
                return self.guild.get_role(data["mute_role"] or 0)
        return None

    async def modrole(self) -> discord.Role | None:
        try:
            return self.guild.get_role(self.bot.guild_configurations_cache[self.guild.id]["mod_role"] or 0)
        except KeyError:
            if data := await self.bot.guild_configurations.find_one({"_id": self.guild.id}):
                return self.guild.get_role(data["mod_role"] or 0)
        return None

    @discord.utils.cached_property
    def replied_reference(self) -> discord.MessageReference | None:
        ref = self.message.reference
        if ref is not None and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    @staticmethod
    def with_type(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapped(*args: Any, **kwargs: Any) -> discord.Message | None:
            context = args[0] if isinstance(args[0], commands.Context) else args[1]
            async with context.typing():
                return await func(*args, **kwargs)

        return wrapped

    async def send(
        self,
        content: Any = None,
        *,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        **kwargs: Any,
    ) -> discord.Message:
        assert isinstance(self.me, discord.Member)

        perms: discord.Permissions = self.channel.permissions_for(self.me)
        if not (perms.send_messages and perms.embed_links):
            with suppress(discord.Forbidden):
                return await self.author.send(
                    (
                        "Bot don't have either Embed Links/Send Messages permission in that channel. "
                        "Please give sufficient permissions to the bot."
                    ),
                    view=self.send_view(),
                )

        if bold:
            content = f"**{content}**"
        if italic:
            content = f"*{content}*"
        if underline:
            content = f"__{content}__"

        return await super().send(str(content)[:1990] if content else None, **kwargs)

    async def reply(self, content: str | None = None, **kwargs: Any) -> discord.Message:
        try:
            return await self.send(content, reference=kwargs.get("reference") or self.message, **kwargs)
        except discord.HTTPException:  # message deleted
            return await self.send(content, **kwargs)

    async def error(self, *args: Any, **kwargs: Any) -> discord.Message:
        """Similar to send, but if the original message is deleted, it will delete the error message as well."""
        embed: discord.Embed | None = kwargs.get("embed")
        if isinstance(embed, discord.Embed) and not embed.color:
            # if no color is set, set it to red
            embed.color = discord.Color.red()

        msg: discord.Message | None = await self.reply(
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
                await msg.delete(delay=0)
        return msg

    async def entry_to_code(self, entries: list[tuple[Any, Any]]) -> discord.Message:
        width = max(len(str(a)) for a, b in entries)
        output = ["```"]
        output.extend(f"{name:<{width}}: {entry}" for name, entry in entries)
        output.append("```")
        return await self.send("\n".join(output))

    async def indented_entry_to_code(self, entries: list[tuple[Any, Any]]) -> discord.Message:
        width = max(len(str(a)) for a, b in entries)
        output = ["```"]
        output.extend(f"\u200b{name:>{width}}: {entry}" for name, entry in entries)
        output.append("```")
        return await self.send("\n".join(output))

    async def emoji(self, emoji: str) -> discord.PartialEmoji:
        return emojis[emoji]

    async def prompt(
        self,
        message: str | None = None,
        *,
        timeout: float = 60.0,
        delete_after: bool = True,
        reacquire: bool = True,
        author_id: int | None = None,
        **kwargs: Any,
    ) -> bool | None:
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
        _for: int | float | datetime.datetime | None = None,
        *,
        result: T | None = None,
    ) -> T | None:
        if isinstance(_for, datetime.datetime):
            await discord.utils.sleep_until(_for, result)
        else:
            await asyncio.sleep(_for or 0, result)

    async def safe_send(self, content: str, *, escape_mentions: bool = True, **kwargs: Any) -> discord.Message:
        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop("file", None)
            return await self.send(
                file=discord.File(fp, filename="message_too_long.txt"),
                **kwargs,
            )  # must have `Attach Files` permissions
        return await self.send(content, **kwargs)

    async def bulk_add_reactions(
        self,
        message: discord.Message | None = None,  # type: ignore
        *reactions: discord.Emoji | discord.PartialEmoji | str,
    ) -> None:
        if message is None or not isinstance(message, discord.Message):
            message: discord.Message = self.message

        tasks: list[asyncio.Task[None]] = [asyncio.create_task(message.add_reaction(reaction)) for reaction in reactions]
        await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    async def get_or_fetch_message(self, *args: Any, **kwargs: Any) -> discord.PartialMessage | discord.Message | None:
        """Shortcut for bot.get_or_fetch_message(...)."""
        return await self.bot.get_or_fetch_message(*args, **kwargs)

    async def confirm(
        self,
        channel: discord.TextChannel,
        user: discord.Member | discord.User,
        *args: Any,
        timeout: float = 60,
        delete_after: bool = False,
        **kwargs: Any,
    ) -> bool | None:
        message: discord.Message = await channel.send(*args, **kwargs)
        await self.bulk_add_reactions(message, *CONFIRM_REACTIONS)

        def check(payload: discord.RawReactionActionEvent) -> bool:
            return (
                payload.message_id == message.id and payload.user_id == user.id and str(payload.emoji) in CONFIRM_REACTIONS
            )

        try:
            payload: discord.RawReactionActionEvent = await self.bot.wait_for(
                "raw_reaction_add",
                check=check,
                timeout=timeout,
            )
            return str(payload.emoji) == "\N{THUMBS UP SIGN}"
        except asyncio.TimeoutError:
            return None
        finally:
            if delete_after:
                await message.delete(delay=0)

    def outer_check(
        self,
        check: Callable[..., bool] | None = None,
        operator: Callable[[Iterable[object]], bool] = all,
        **kw: Any,
    ) -> Callable[..., bool]:
        """Check function for the event."""
        if check is not None:
            return check

        def __suppress_attr_error(func: Callable, *args: Any, **kwargs: Any) -> bool:
            """Suppress attribute error for the function."""
            try:
                func(*args, **kwargs)
                return True
            except AttributeError:
                return False

        def __internal_check(
            *args,
        ) -> bool:
            """Main check function."""
            convert_pred = [(attrgetter(k.replace("__", ".")), v) for k, v in kw.items()]
            return operator(
                all(pred(i) == val for i in args if __suppress_attr_error(pred, i)) for pred, val in convert_pred
            )

        return __internal_check

    async def wait_for(
        self,
        _event_name: str,
        *,
        timeout: float | None = None,
        check: Callable[..., bool] | None = None,
        suppress_error: bool = False,
        operator: Callable[[Iterable[object]], bool] = all,
        **kwargs: Any,
    ) -> Any:
        if _event_name.lower().startswith("on_"):
            _event_name = _event_name[3:].lower()

        try:
            return await self.bot.wait_for(
                _event_name,
                timeout=timeout,
                check=self.outer_check(check, operator, **kwargs),
            )
        except asyncio.TimeoutError:
            if suppress_error:
                await self.message.add_reaction("\N{ALARM CLOCK}")
                return None
            raise

    async def paginate(
        self,
        entries: list[Any] | str,
        *,
        module: str = "SimplePages",
        **kwargs: Any,
    ) -> None:
        if not entries:
            msg = "Cannot paginate an empty list."
            raise commands.BadArgument(msg)

        if module == "SimplePages":
            from utilities.robopages import SimplePages

            assert isinstance(entries, list)

            pages = SimplePages(
                entries,
                ctx=self,
                **kwargs,
            )
            await pages.start()
            return

        if module == "PaginationView":
            from utilities.paginator import PaginationView

            assert isinstance(entries, list)

            pages = PaginationView(entries)
            await pages.start(
                ctx=self,
            )
            return

        if module == "JishakuPaginatorInterface":
            from jishaku.paginators import PaginatorInterface

            assert isinstance(entries, str)

            pages = commands.Paginator(**kwargs)
            for line in entries.split("\n"):
                pages.add_line(line)

            interface = PaginatorInterface(self.bot, pages, owner=self.author)
            await interface.send_to(self)

        msg = "Invalid paginator type"
        raise ValueError(msg)

    async def multiple_wait_for(
        self,
        events: list[tuple[str, Callable[..., bool]]] | dict[str, Callable[..., bool]],
        *,
        return_when: Literal["FIRST_COMPLETED", "ALL_COMPLETED", "FIRST_EXCEPTION"] = "FIRST_COMPLETED",
        timeout: float | None = None,
    ) -> list[Any]:
        if isinstance(events, dict):
            events = list(events.items())

        _events: set[asyncio.Task[Any]] = {
            self.bot.loop.create_task(self.wait_for(event, check=check)) for event, check in events
        }

        completed, pendings = await asyncio.wait(
            _events,
            timeout=timeout,
            return_when=getattr(asyncio, return_when.upper(), "FIRST_COMPLETED"),
        )

        for pending in pendings:
            pending.cancel()
            log.info("Cancelled pending task %s", pending.get_name() or "unnamed")

        return [r.result() for r in completed]

    async def wait_for_message(self, *, timeout: float | None = None) -> discord.Message:
        try:
            return await self.bot.wait_for(
                "message",
                timeout=timeout,
                check=lambda m: m.author == self.author and m.channel == self.channel,
            )
        except asyncio.TimeoutError as e:
            msg = "You took too long to respond."
            raise commands.BadArgument(msg) from e

    async def wait_for_till(
        self,
        events: list[tuple[str, Callable[..., bool]]] | dict[str, Callable[..., bool]],
        *,
        _for: float | int | None = None,
        after: float | int | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        if after:
            await self.release(after)
        done_result: list[Any] = []

        _for = _for or 0
        now = discord.utils.utcnow().timestamp() + _for

        def __internal_appender(completed_result: Iterable[asyncio.Task]) -> None:
            for task in completed_result:
                done_result.append(task.result())

        while discord.utils.utcnow().timestamp() <= now:
            done = await self.multiple_wait_for(events, return_when="FIRST_COMPLETED", **kwargs)
            __internal_appender(done)

        if not _for:
            done = await self.multiple_wait_for(events, return_when="FIRST_COMPLETED", **kwargs)
            __internal_appender(done)

        return done_result

    async def wait_for_delete(self, message: discord.Message | None = None, *, timeout: float | None = None) -> Any:
        message = message or self.message
        await self.wait_for("on_message_delete", message__id=message.id, timeout=timeout)

    async def retry(
        self,
        callback: Callable[..., Any],
        *args: Any,
        multiplier: int = 5,
        retries: int = 5,
        exception: type[Exception] = Exception,
        **kwargs: Any,
    ) -> type[Exception]:
        errors: dict[int, Exception] = {}
        retry: int = 0
        for retry in range(max(retries, 1)):
            try:
                return await discord.utils.maybe_coroutine(callback, *args, **kwargs)
            except exception as e:
                errors[retry] = e
                await self.release(multiplier * retry)

        raise errors[retry]

    async def database_game_update(
        self,
        game_name: str,
        *,
        win: bool = False,
        loss: bool = False,
        set: dict = None,
        **kw: Any,
    ) -> bool:
        if set is None:
            set = {}
        set_kwargs: dict[str, Any] = {f"game_{game_name}_{k}": v for k, v in set.items()}
        kwargs = {"$set": set_kwargs}
        if not win and not loss:
            update_result: UpdateResult = await self.bot.game_collections.update_one(
                {
                    "_id": self.author.id,
                },
                {
                    "$inc": {
                        f"game_{game_name}_played": 1,
                    },
                    **kwargs,
                },
                upsert=True,
            )
        elif win:
            update_result: UpdateResult = await self.bot.game_collections.update_one(
                {
                    "_id": self.author.id,
                },
                {
                    "$inc": {
                        f"game_{game_name}_played": 1,
                        f"game_{game_name}_won": 1,
                    },
                    **kwargs,
                },
                upsert=True,
            )
        else:
            update_result: UpdateResult = await self.bot.game_collections.update_one(
                {
                    "_id": self.author.id,
                },
                {
                    "$inc": {
                        f"game_{game_name}_played": 1,
                        f"game_{game_name}_loss": 1,
                    },
                    **kwargs,
                },
                upsert=True,
            )

        return bool(update_result.modified_count)

    async def database_command_update(
        self,
        *,
        success: bool = False,
        error: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if self.command is None:
            return {}

        cmd = self.command.qualified_name
        cmd = cmd.replace(" ", "_")
        now = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if error:
            kwargs["$addToSet"] = {
                f"command_{cmd}_errors": {
                    "error": error,
                    "time": now,
                },
            }

        update_result_cmd_user: UpdateResult = await self.bot.command_collections.update_one(
            {"_id": self.author.id},
            {
                "$inc": {
                    f"command_{cmd}_used": 1,
                    f"command_{cmd}_success": 1 if success else 0,
                },
                "$set": {"type": "user"},
                **kwargs,
            },
            upsert=True,
        )

        update_result_cmd_guild: UpdateResult = await self.bot.command_collections.update_one(
            {"_id": self.guild.id},
            {
                "$inc": {
                    f"command_{cmd}_used": 1,
                    f"command_{cmd}_success": 1 if success else 0,
                },
                "$set": {"type": "guild"},
                **kwargs,
            },
            upsert=True,
        )

        return {
            "user": bool(update_result_cmd_user.modified_count),
            "guild": bool(update_result_cmd_guild.modified_count),
        }

    def send_view(self, **kw: Any) -> SentFromView:
        return SentFromView(self, **kw)

    def link_view(self, *, url: str, label: str) -> LinkView:
        return LinkView(url=url, label=label)

    def check_buffer(self, buffer: BytesIO) -> BytesIO:
        if (size := buffer.getbuffer().nbytes) > 15000000:
            msg = f"Provided image size ({humanize.naturalsize(size)}) is larger than 15 MB size limit."
            raise commands.BadArgument(
                msg,
            )

        try:
            Image.open(buffer)
        except PIL.UnidentifiedImageError as e:
            msg = "Could not open provided image. Make sure it is a valid image types"
            raise commands.BadArgument(msg) from e
        finally:
            buffer.seek(0)

        return buffer

    async def to_image(self, entity: Any = None) -> BytesIO:  # type: ignore
        if self.message.attachments:
            buf = BytesIO(await self.message.attachments[0].read())
            buf.seek(0)
            return self.check_buffer(buf)

        if self.message.reference and self.message.reference.resolved.attachments:  # type: ignore
            buf = BytesIO(await self.message.reference.resolved.attachments[0].read())  # type: ignore
            buf.seek(0)
            return self.check_buffer(buf)

        if (
            (ref := self.message.reference)
            and (embeds := ref.resolved.embeds)  # type: ignore
            and (image := embeds[0].image)
            and entity is None
        ):
            return await ToImage().convert(self, image.url)  # type: ignore

        if (ref := self.message.reference) and (content := ref.resolved.content) and entity is None:  # type: ignore
            return await ToImage().convert(self, content)

        if (stickers := self.message.stickers) and stickers[0].format != discord.StickerFormatType.lottie:
            response = await self.bot.http_session.get(self.message.stickers[0].url)
            buf = BytesIO(await response.read())
            buf.seek(0)
            return buf

        if entity is None:
            entity: BytesIO = BytesIO(await self.author.display_avatar.read())
            entity.seek(0)
        elif isinstance(entity, int):
            return await ToImage().convert(self, str(entity))
        elif isinstance(entity, discord.Emoji | discord.PartialEmoji):
            entity: BytesIO = BytesIO(await entity.read())
            entity.seek(0)
        elif isinstance(entity, discord.User | discord.Member):
            entity: BytesIO = BytesIO(await entity.display_avatar.read())
            entity.seek(0)
        else:
            url = LINKS_RE.findall(entity)
            if not url:
                url = await emoji_to_url(entity)
                url = LINKS_RE.findall(url)
            if not url:
                msg = "Could not convert input to Emoji, Member, or Image URL"
                raise commands.BadArgument(msg)

            url = url[0]

            response = await self.bot.http_session.get(url)
            if "https://tenor.com" in url or "https://media.tenor" in url:
                html = await response.read()
                url_tenor = await asyncio.to_thread(self.__scrape_tenor, html)
                resp = await self.bot.http_session.get(url_tenor)
                entity = BytesIO(await resp.read())
            else:
                entity = BytesIO(await response.read())
            entity.seek(0)

        return self.check_buffer(entity)

    def __scrape_tenor(self, html: str) -> str:
        soup = BeautifulSoup(html, features=HTML_PARSER)
        find = soup.find("div", {"class": "Gif"})
        return find.img["src"]  # type: ignore


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
        self.value: bool | None = None
        self.delete_after: bool = delete_after
        self.author_id: int = author_id
        self.ctx: Context = ctx
        self.reacquire: bool = reacquire
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("This confirmation dialog is not for you.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        if self.reacquire:
            await asyncio.sleep(0)
        if self.delete_after and self.message:
            self.stop()
            await self.message.delete(delay=0)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.value = True
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.value = False
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()
        self.stop()


class SentFromView(discord.ui.View):
    def __init__(self, ctx: Context, *, timeout: float | None = 180, label: str | None = None) -> None:
        super().__init__(timeout=timeout)
        self.ctx = ctx

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.blurple,
                label=label or f"Sent from {ctx.guild.name}",
                disabled=True,
            ),
        )


class LinkView(discord.ui.View):
    def __init__(self, *, timeout: float | None = 180, url: str, label: str = "Link") -> None:
        super().__init__(timeout=timeout)
        self.url = url

        self.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label=label, url=url))
