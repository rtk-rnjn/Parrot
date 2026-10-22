# core/bot.py

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import logging
import os
import re
from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, override

import aiohttp
import discord
import jishaku
import pomice
from discord.ext import commands
from dotenv import load_dotenv
from pomice.exceptions import NodeConnectionFailure
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError
from watchfiles import awatch

from .help import Help as BotHelp
from .utils import AsyncTimerDispatcher, ConfirmationLayout, DatabaseManager, DisambiguatorView

if TYPE_CHECKING:
    from extensions.reminder import Reminder

_ = load_dotenv()


DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

RESTRICTED_MODE = os.environ.get("RESTRICTED_MODE", "False").lower() in (
    "true",
    "1",
    "yes",
)
LAVALINK_PASSWORD = os.environ.get("LAVALINK_PASSWORD", "youshallnotpass")
OWNER_ID = os.getenv("OWNER_ID")

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

LOADABLE_COGS = [
    "extensions.automod",
    "extensions.cc",
    "extensions.chess",
    "extensions.config",
    "extensions.events",
    "extensions.fun.easter",
    "extensions.fun.fun",
    "extensions.fun.hanukkah",
    "extensions.fun.love",
    "extensions.fun.pride",
    "extensions.fun.snakes",
    "extensions.games",
    "extensions.giveaway",
    "extensions.global_chat",
    "extensions.highlight",
    "extensions.hub",
    "extensions.image",
    "extensions.leveling",
    "extensions.meta",
    "extensions.misc",
    "extensions.misc.math",
    "extensions.misc.wiki",
    "extensions.mod",
    "extensions.music",
    "extensions.nasa",
    "extensions.nsfw",
    "extensions.owner",
    "extensions.reminder",
    "extensions.rtfm",
    "extensions.rtfm.linter",
    "extensions.rtfm.w3schools",
    "extensions.starboard",
    "extensions.stats",
    "extensions.suggestion",
    "extensions.supercell",
    "extensions.tags",
    "extensions.telephone",
    "extensions.ticket",
    "extensions.todo",
    "extensions.welcomer",
]

_log = logging.getLogger(__name__)
SHUTDOWN_STEP_TIMEOUT = 10
SPAM_HIGH_THRESHOLD = 5
SPAM_MEDIUM_THRESHOLD = 3
MAX_AUTOCOMPLETE_RESULTS = 25

EXTENSIONS_DIRECTORY = Path(__file__).resolve().parents[1] / "extensions"


class SpamSeverity(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Bot(commands.Bot):
    VERSION = "1.0.0 (Rewrite)"
    DEFAULT_PREFIX = os.environ.get("DEFAULT_PREFIX", "$")

    if TYPE_CHECKING:
        user: discord.ClientUser

    def __init__(self, **kwargs) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        # intents.presences = True - Fuck you discord

        super().__init__(
            command_prefix=Bot.get_prefix,
            intents=intents,
            chunk_guilds_at_startup=False,
            case_insensitive=True,
            activity=discord.Activity(type=discord.ActivityType.playing, name="Imagine having bugs!"),
            status=discord.Status.do_not_disturb,
            allowed_mentions=discord.AllowedMentions(everyone=False, replied_user=False, roles=False),
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
            strip_after_prefix=True,
            shard_id=1,
            max_messages=2**9,  # RAM issues guyz
            owner_ids={int(OWNER_ID)} if OWNER_ID else None,
            help_command=BotHelp(),
            **kwargs,
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.database = DatabaseManager(self)
        self.event_scheduler = AsyncTimerDispatcher(self)

        self._started_at: datetime | None = None

        self.before_invoke(self.__before_invoke)
        self.check_once(self.__check_once)

        self._http_session: aiohttp.ClientSession | None = None

        self.lavalink_node_pool = pomice.NodePool()
        self.default_lavalink_node: pomice.Node | None = None

        self.message_cache: dict[int, discord.Message] = {}
        self._cog_autoreload_task: asyncio.Task[None] | None = None

        self.spam_control = commands.CooldownMapping.from_cooldown(3, 6, commands.BucketType.user)
        self.spam_counter = Counter[int]()
        self.temporary_ban_list: dict[int, float] = {}  # user_id -> timestamp of when the ban expires

        self.__mongodb_watcher = None
        self._listener_tasks: list[asyncio.Task[None]] = []

    @override
    async def setup_hook(self) -> None:
        await self.load_extension(jishaku.__name__)

        count = 0
        for extention in LOADABLE_COGS:
            await self.load_extension(extention)
            count += 1

        _log.info("Loaded %d extensions.", count)

        await self.event_scheduler.start()

        self._cog_autoreload_task = self.loop.create_task(
            self._autoreload_cogs(),
            name=f"{self.__class__.__name__}: _autoreload_cogs",
        )

        self._start_database_listeners()
        self.loop.create_task(self.connect_lavalink_node(), name=f"{self.__class__.__name__}: connect_lavalink_node")

    async def connect_lavalink_node(self) -> None:
        """Attempt to connect to a Lavalink node"""
        try:
            await self.__create_lavalink_node()
            return
        except NodeConnectionFailure:
            _log.warning("Failed to connect to Lavalink node.")

    @staticmethod
    def _cog_extension_paths() -> dict[Path, str]:
        paths: dict[Path, str] = {}
        for extension in LOADABLE_COGS:
            spec = importlib.util.find_spec(extension)
            if spec is None:
                _log.warning("Could not find loaded cog extension: %s", extension)
                continue

            if spec.submodule_search_locations:
                path = Path(next(iter(spec.submodule_search_locations)))
            elif spec.origin:
                path = Path(spec.origin)
            else:
                _log.warning("Could not resolve source path for loaded cog extension: %s", extension)
                continue

            paths[path.resolve()] = extension

        return paths

    async def _autoreload_cogs(self) -> None:
        extension_paths = self._cog_extension_paths()

        async for changes in awatch(EXTENSIONS_DIRECTORY, debounce=3200, yield_on_timeout=True):
            if not changes:
                continue

            extensions: set[str] = set()
            for _, changed_path in changes:
                path = await asyncio.to_thread(Path(changed_path).resolve)
                if path.suffix != ".py":
                    continue

                matches = [
                    (root, extension) for root, extension in extension_paths.items() if path == root or (root.is_dir() and root in path.parents)
                ]
                if matches:
                    extensions.add(max(matches, key=lambda match: len(match[0].parts))[1])

            for extension in extensions:
                try:
                    await self.reload_extension(extension)
                except Exception:  # pylint: disable=broad-exception-caught
                    _log.exception("Could not autoreload cog extension: %s", extension)
                else:
                    _log.info("Autoreloaded cog extension: %s", extension)

    async def on_ready(self) -> None:
        _log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        if self._started_at is not None:
            return

        self._started_at = discord.utils.utcnow()

    async def __create_lavalink_node(self) -> None:
        node = await self.lavalink_node_pool.create_node(
            bot=self,
            host="localhost",
            port=2333,
            password=LAVALINK_PASSWORD,
            identifier="MAIN",
            loop=self.loop,
            spotify_client_id=SPOTIFY_CLIENT_ID,
            spotify_client_secret=SPOTIFY_CLIENT_SECRET,
            session=self.http_session,
        )

        self.default_lavalink_node = node
        _log.info("Connected to Lavalink node with identifier %s", node._identifier)

    @override
    async def get_prefix(self, message: discord.Message, /) -> list[str]:
        if message.guild is not None:
            prefix = await self.database.get_command_prefix(guild_id=message.guild.id)
        else:
            prefix = self.DEFAULT_PREFIX

        prefix = prefix or self.DEFAULT_PREFIX

        return commands.when_mentioned_or(prefix)(self, message)

    @override
    async def start(self, token: str = DISCORD_BOT_TOKEN, *, reconnect: bool = True) -> None:
        await super().start(token, reconnect=reconnect)

    async def on_message(self, message: discord.Message, /) -> None:
        if message.guild is None or message.author.bot or self.user is None:
            return

        if re.fullmatch(rf"<@!?{self.user.id}>", message.content):
            if message.channel.permissions_for(message.guild.me).send_messages:
                prefix = await self.database.get_command_prefix(guild_id=message.guild.id) or self.DEFAULT_PREFIX
                await message.channel.send(f"Prefix: `{prefix}`", reference=message)

            return

        await self.process_commands(message)

    async def process_commands(self, message: discord.Message, /) -> None:
        ctx: commands.Context[Bot] = await self.get_context(message, cls=commands.Context)

        if ctx.author.id in self.temporary_ban_list:
            return

        spam_severity = self._check_for_spam(message)
        match spam_severity:
            case SpamSeverity.HIGH:
                self.loop.create_task(self._temporarily_ban_user(ctx.author, duration=60), name=f"Temporary Ban: {ctx.author} ({ctx.author.id})")
                return

            case SpamSeverity.MEDIUM:
                return

            case SpamSeverity.LOW:
                return

            case SpamSeverity.NONE:
                pass

        await self.invoke(ctx)

    async def invoke(self, ctx: commands.Context[Bot]) -> None:
        disabled = await self.is_command_disabled(ctx)

        if disabled and ctx.command is not None:
            await ctx.command.dispatch_error(ctx, commands.DisabledCommand())
        else:
            await super().invoke(ctx)

    def _check_for_spam(self, message: discord.Message) -> SpamSeverity:
        bucket = self.spam_control.get_bucket(message)
        retry_after = bucket.update_rate_limit(message.created_at.timestamp()) if bucket else None
        if retry_after is not None:
            self.spam_counter[message.author.id] += 1
            if self.spam_counter[message.author.id] >= SPAM_HIGH_THRESHOLD:
                return SpamSeverity.HIGH

            if self.spam_counter[message.author.id] >= SPAM_MEDIUM_THRESHOLD:
                return SpamSeverity.MEDIUM

            return SpamSeverity.LOW

        return SpamSeverity.NONE

    async def _temporarily_ban_user(self, user: discord.User | discord.Member, /, *, duration: float) -> None:
        if user.id in self.temporary_ban_list:
            return

        self.temporary_ban_list[user.id] = discord.utils.utcnow().timestamp() + duration
        user_id = await asyncio.sleep(duration, result=user.id)
        self.temporary_ban_list.pop(user_id, None)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None or after.author.bot:
            return

        with contextlib.suppress(KeyError):
            self.message_cache[after.id] = after

        if before.content != after.content and await self.is_owner(after.author):
            await self.process_commands(after)

    async def __before_invoke(self, ctx: commands.Context[Bot]) -> None:
        if ctx.guild is not None and not ctx.guild.chunked:
            await ctx.bot.wait_until_ready()
            self.loop.create_task(ctx.guild.chunk())

            await self.database.register_guild(ctx.guild.id)
            await self.database.register_user(ctx.author.id)

    async def get_or_fetch_member(self, guild: discord.Guild, member_id: int) -> discord.Member | None:
        member = guild.get_member(member_id)
        if member is not None:
            return member

        try:
            return await guild.fetch_member(member_id)
        except discord.NotFound:
            return None

    async def get_or_fetch_user(self, user_id: int) -> discord.User | None:
        """Return a cached user or fetch and cache it if unavailable."""
        user = self.get_user(user_id)
        if user is not None:
            return user

        try:
            return await self.fetch_user(user_id)
        except discord.NotFound:
            return None

    async def confirm(
        self,
        ctx: commands.Context[Bot],
        prompt: str = "Are you sure?",
        *,
        timeout: float = 30,
    ) -> bool:
        """Ask the command author to confirm an action in the current channel.

        The prompt shows its outcome in place, including when it times out, and a timeout counts as "no".
        """
        view = ConfirmationLayout(ctx.author, prompt, timeout=timeout)
        view.message = await ctx.reply(view=view)
        await view.wait()
        return view.value is True

    @property
    def started_at(self) -> datetime:
        """Return the datetime when the bot was started."""
        if self._started_at is None:
            message = "Bot has not started yet."
            raise RuntimeError(message)
        return self._started_at

    @property
    def reminder(self) -> Reminder:
        """Return the Reminder cog instance."""
        return self.get_cog("Reminder")  # type: ignore[return-value]

    @property
    def http_session(self) -> aiohttp.ClientSession:
        """Return the aiohttp ClientSession used by the bot."""
        if self._http_session is None:
            message = "HTTP session is not initialized. Ensure that the bot is started and the HTTP session is set up."
            raise RuntimeError(message)

        return self._http_session

    def set_http_session(self, session: aiohttp.ClientSession) -> None:
        """Set the aiohttp ClientSession used by the bot."""
        self._http_session = session

    async def disambiguate[T](
        self,
        context: commands.Context[Bot],
        /,
        *,
        matches: list[T],
        entry: Callable[[T], str] = str,
        ephemeral: bool = False,
        embed: discord.Embed | None = None,
    ) -> T:
        """Disambiguate between multiple matches and return the selected one."""
        if len(matches) == 0:
            message = "No results found."
            raise ValueError(message)

        if len(matches) == 1:
            return matches[0]

        if len(matches) > MAX_AUTOCOMPLETE_RESULTS:
            message = "Too many results found. Please refine your search."
            raise ValueError(message)

        view = DisambiguatorView(context, matches, entry)
        embed = embed or (
            discord.Embed(description="Found multiple choices. Please choose the correct one.").set_author(
                name=context.author.display_name,
                icon_url=context.author.display_avatar.url,
            )
        )

        view.message = await context.reply(embed=embed, view=view, ephemeral=ephemeral)
        await view.wait()
        return view.selected

    async def close(self) -> None:
        """Shut everything down once; every step is best-effort so one failure cannot abort the rest."""
        if self.is_closed():
            return

        if self._cog_autoreload_task is not None:
            self._cog_autoreload_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cog_autoreload_task

        # Cogs unload here (and flush pending state) before any cache is cleared.
        await super().close()

        await self._shutdown_step("database listeners", self._stop_database_listeners())
        if self._http_session is not None:
            await self._shutdown_step("HTTP session", self._http_session.close())
        await self._shutdown_step("Redis cache flush", self.database.invalidate_redis())
        await self._shutdown_step("database connections", self.database.close())
        await self._shutdown_step("Lavalink", self.lavalink_node_pool.disconnect())

    @staticmethod
    async def _shutdown_step(name: str, step: Awaitable[object]) -> None:
        try:
            await asyncio.wait_for(step, timeout=SHUTDOWN_STEP_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            _log.warning("Timed out after %ss while shutting down %s", SHUTDOWN_STEP_TIMEOUT, name)
        except Exception:  # pylint: disable=broad-exception-caught
            _log.warning("Error while shutting down %s", name, exc_info=True)

    async def __check_once(self, ctx: commands.Context[Bot]) -> bool:
        if RESTRICTED_MODE:
            return await self.is_owner(ctx.author)
        return True

    async def get_or_fetch_message(self, channel: discord.abc.Messageable, message_id: int) -> discord.Message:
        """Return a cached message or fetch and cache it if unavailable."""

        for message in self.cached_messages:
            if message.id == message_id:
                return message

        try:
            return self.message_cache[message_id]
        except KeyError:
            message = await channel.fetch_message(message_id)
            self.message_cache[message_id] = message
            return message

    async def get_or_fetch[**P, T](
        self,
        sync_function: Callable[P, T | None],
        async_function: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T | None:
        result = sync_function(*args, **kwargs)
        if result is not None:
            return result

        try:
            return await async_function(*args, **kwargs)
        except Exception as e:  # pylint: disable=broad-exception-caught
            _log.exception("Error fetching data: %s", e)
            return None

    # fuck off guyz;

    async def __start_mongodb_listener(self) -> None:
        collection = self.database.guilds_collection

        # Change streams require MongoDB to run as a replica set or sharded cluster.
        # They do not work against a standalone MongoDB server.
        #
        # MongoDB drivers discover replica-set members from the replica-set
        # configuration. The hostnames in `members[n].host` must therefore be
        # reachable and resolvable from the client.
        #
        # When MongoDB runs inside Docker while the bot runs on the host, this can
        # cause a common connectivity problem: MongoDB may advertise its Docker
        # hostname (for example, `mongodb:27017`), which is not resolvable from
        # the host.
        #
        # For a local Docker setup, the advertised replica-set address can be
        # changed from inside the container:
        #
        #   docker exec -it mongodb mongosh
        #   cfg = rs.conf()
        #   cfg.members[0].host = "localhost:27017"
        #   rs.reconfig(cfg, { force: true })
        #
        # Or just: docker exec mongodb mongosh --quiet --eval 'c = rs.conf(); c.members[0].host = "localhost:27017"; rs.reconfig(c)'
        #
        # In production, prefer configuring a hostname that is reachable from
        # every MongoDB client rather than using `localhost`.

        try:
            self.__mongodb_watcher = await collection.watch()
            async for change in self.__mongodb_watcher:
                self.dispatch("mongodb_change", change)
        except PyMongoError as error:
            if self.is_closed():
                _log.debug("MongoDB change stream closed during shutdown: %s", error)
            else:
                _log.warning("MongoDB change stream stopped; guild change events will not be dispatched: %s", error)

    async def __start_redis_listener(self) -> None:
        pub_sub_client = self.database.pub_sub_client

        # Subscribe to all Pub/Sub channels. This is useful when keyspace
        # notifications are enabled and you want to observe Redis key events.
        #
        # For a local Docker Redis instance, keyspace notifications can be enabled
        # with:
        #
        #   docker exec redis redis-cli CONFIG SET notify-keyspace-events KEA
        #
        # `K` enables keyspace notifications, `E` enables keyevent notifications,
        # and `A` enables all supported event classes.

        try:
            await pub_sub_client.psubscribe("*")

            async for message in pub_sub_client.listen():
                if message is None or message["type"] != "pmessage":
                    continue

                channel = message["channel"]
                data = message["data"]

                if isinstance(channel, bytes):
                    channel = channel.decode("utf-8")

                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                self.dispatch("redis_message", channel, data)
        except RedisError as error:
            if self.is_closed():
                _log.debug("Redis listener closed during shutdown: %s", error)
            else:
                _log.warning("Redis listener stopped; key events will not be dispatched: %s", error)

    def _start_database_listeners(self) -> None:
        self._listener_tasks = [
            self.loop.create_task(self.__start_mongodb_listener(), name=f"{self.__class__.__name__}: __start_mongodb_listener"),
            self.loop.create_task(self.__start_redis_listener(), name=f"{self.__class__.__name__}: __start_redis_listener"),
        ]

    async def _stop_database_listeners(self) -> None:
        # Cancel the consumers first so closing the stream underneath them cannot surface as a task error.
        for task in self._listener_tasks:
            task.cancel()
        for task in self._listener_tasks:
            with contextlib.suppress(asyncio.CancelledError, PyMongoError, RedisError):
                await task
        self._listener_tasks = []

        if self.__mongodb_watcher is not None:
            with contextlib.suppress(PyMongoError):
                await self.__mongodb_watcher.close()
            self.__mongodb_watcher = None

        pub_sub_client = self.database.pub_sub_client
        with contextlib.suppress(RedisError, OSError):
            await pub_sub_client.punsubscribe("*")
            await pub_sub_client.aclose()

    async def is_command_disabled(self, ctx: commands.Context[Bot]) -> bool:
        if not ctx.guild or not ctx.command:
            return False

        guild_id, qualified_command = ctx.guild.id, ctx.command.qualified_name

        enabled = await self.database.is_command_enabled(guild_id=guild_id, command_path=qualified_command)

        ignored_roles, allowed_roles, ignored_channels, allowed_channels = await asyncio.gather(
            self.database.get_command_config_ignored_roles(guild_id=guild_id, command_path=qualified_command),
            self.database.get_command_config_allowed_roles(guild_id=guild_id, command_path=qualified_command),
            self.database.get_command_config_ignored_channels(guild_id=guild_id, command_path=qualified_command),
            self.database.get_command_config_allowed_channels(guild_id=guild_id, command_path=qualified_command),
        )

        user_roles = {r.id for r in getattr(ctx.author, "roles", [])}
        channel_id_set = {ctx.channel.id, getattr(ctx.channel, "category_id", None)} - {None}

        depth_check = bool(
            (user_roles & set(ignored_roles))
            or (allowed_roles and not (user_roles & set(allowed_roles)))
            or (channel_id_set & set(ignored_channels))
            or (allowed_channels and not (channel_id_set & set(allowed_channels)))
        )

        return depth_check or not enabled
