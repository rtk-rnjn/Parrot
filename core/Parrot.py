# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import datetime
import io
import logging
import logging.handlers
import os
import re
import sys
import traceback
import types
from collections import Counter, defaultdict, deque
from contextlib import suppress
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Collection,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
)

import discord
import jishaku  # type: ignore  # noqa: F401
import pymongo
import wavelink
from aiohttp import ClientSession  # type: ignore
from discord import app_commands
from discord.ext import commands, ipc, tasks  # type: ignore
from lru import LRU
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore

try:
    import topgg  # type: ignore

    HAS_TOP_GG = True
except ImportError:
    HAS_TOP_GG = False

from time import perf_counter

from utilities.checks import _can_run
from utilities.config import (
    AUTHOR_DISCRIMINATOR,
    AUTHOR_NAME,
    CASE_INSENSITIVE,
    EXTENSIONS,
    GITHUB,
    HEROKU,
    LRU_CACHE,
    MASTER_OWNER,
    OWNER_IDS,
    STRIP_AFTER_PREFIX,
    SUPPORT_SERVER,
    SUPPORT_SERVER_ID,
    TO_LOAD_IPC,
    TOKEN,
    UNLOAD_EXTENSIONS,
)
from utilities.converters import ToAsync
from utilities.paste import Client

from .__template import post as POST
from .Context import Context

if TYPE_CHECKING:
    from discord.ext.commands.cooldowns import CooldownMapping
    from pymongo.collection import Collection as PyMongoCollection
    from typing_extensions import TypeAlias

    from .Cog import Cog

    if HAS_TOP_GG:
        from topgg.types import BotVoteData

    MongoCollection: TypeAlias = PyMongoCollection

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

intents = discord.Intents.default()
intents.members = True  # type: ignore
intents.message_content = True  # type: ignore

dbl_token = os.environ["TOPGG"]

CHANGE_LOG_ID = 796932292458315776
ERROR_LOG_WEBHOOK_ID = 924513442273054730
STARTUP_LOG_WEBHOOK_ID = 985926507530690640
VOTE_LOG_WEBHOOK_ID = 897741476006592582

logger = logging.getLogger("discord")
logger.setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)

handler = logging.handlers.RotatingFileHandler(
    filename="discord.log",
    encoding="utf-8",
    maxBytes=1 * 1024 * 1024,  # 1 MiB
    backupCount=1,  # Rotate through 1 files
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
handler.setFormatter(formatter)
logger.addHandler(handler)


T = TypeVar("T")


@ToAsync()
def func(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return function(*args, **kwargs)


__all__ = ("Parrot",)


class Parrot(commands.AutoShardedBot, Generic[T]):
    """A custom way to organise a commands.AutoSharedBot."""

    __version__: str

    user: discord.ClientUser
    help_command: Optional[commands.HelpCommand]

    http_session: ClientSession
    mongo: AsyncIOMotorClient

    cogs: Mapping[str, Cog]
    extensions: Mapping[str, types.ModuleType]

    commands: Set[commands.Command]
    cached_messages: Sequence[discord.Message]
    guilds: Sequence[discord.Guild]

    tree_cls: Type[app_commands.CommandTree]
    tree: app_commands.CommandTree

    owner_id: Optional[int]
    owner_ids: Optional[Collection[int]]

    voice_clients: List[discord.VoiceProtocol]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(
            command_prefix=self.get_prefix,
            case_insensitive=CASE_INSENSITIVE,
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.watching, name="you"),
            status=discord.Status.dnd,
            strip_after_prefix=STRIP_AFTER_PREFIX,
            owner_ids=set(OWNER_IDS),
            allowed_mentions=discord.AllowedMentions(everyone=False, replied_user=False),
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
            shard_count=1,
            max_messages=5000,
            **kwargs,
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()
        self._CogMixin__cogs = commands.core._CaseInsensitiveDict()  # pycord be like
        self._seen_messages: int = 0
        self._change_log: List[discord.Message] = []

        self._error_log_token: str = os.environ["CHANNEL_TOKEN2"]
        self._startup_log_token: str = os.environ["CHANNEL_TOKEN3"]
        self._vote_log_token: str = os.environ["CHANNEL_TOKEN4"]

        self.color: int = 0x87CEEB
        self.colour: int = self.color

        self.error_channel: Optional[discord.TextChannel] = None
        self.persistent_views_added: bool = False
        self.spam_control: CooldownMapping = commands.CooldownMapping.from_cooldown(3, 5, commands.BucketType.user)

        self._was_ready: bool = False
        self.lock: "asyncio.Lock" = asyncio.Lock()
        self.ON_HEROKU: bool = HEROKU

        # Top.gg
        self.HAS_TOP_GG = HAS_TOP_GG
        if self.HAS_TOP_GG:
            self.topgg: "topgg.DBLClient"
            self.topgg_webhook: "topgg.WebhookManager"

        self._auto_spam_count: Counter = Counter()
        self.resumes: Dict[int, List[datetime.datetime]] = defaultdict(list)
        self.identifies: Dict[int, List[datetime.datetime]] = defaultdict(list)
        self._prev_events: "deque[str]" = deque(maxlen=10)

        self.mystbin = Client()

        # caching variables
        self.server_config: Dict[int, Dict[str, Any]] = LRU(LRU_CACHE)  # type: ignore
        self.message_cache: Dict[int, discord.Message] = {}
        self.banned_users: Dict[int, Dict[str, Union[str, bool, int]]] = {}
        self.afk: Set[int] = set()

        self.opts: Dict[int, Any] = {}
        self.func: Callable = func

        # IPC
        self.ipc: "ipc.Server" = ipc.Server(
            bot=self,
            host="localhost",
            port=1730,
            secret_key=os.environ["IPC_KEY"],
        )
        self.ipc_client: "ipc.Client" = ipc.Client(
            host="localhost",
            port=1730,
            secret_key=os.environ["IPC_KEY"],
        )

        # Extensions
        self._successfully_loaded: List[str] = []
        self._failed_to_load: Dict[str, str] = {}

        # Wavelink
        self.wavelink = wavelink.NodePool()

        self.GLOBAL_HEADERS: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": f"Discord Bot '{self.user}' @ {self.github}",
        }

        self.UNDER_MAINTENANCE: bool = False
        self.UNDER_MAINTENANCE_REASON: Optional[str] = None
        self.UNDER_MAINTENANCE_OVER: Optional[datetime.datetime] = None

    def __repr__(self) -> str:
        return f"<core.{self.user.name}>"

    @property
    def server(self) -> Optional[discord.Guild]:
        return self.get_guild(SUPPORT_SERVER_ID)  # Main server

    @property
    def invite(self) -> str:
        return discord.utils.oauth_url(
            self.user.id,
            permissions=discord.Permissions(1099780451414),
            scopes=("bot", "applications.commands"),
            disable_guild_select=False,
        )

    @property
    def github(self) -> str:
        return GITHUB

    @property
    def support_server(self) -> str:
        return SUPPORT_SERVER

    async def change_log(self) -> Optional[discord.Message]:
        """For the command `announcement` to let the users know the most recent change"""
        if not self._change_log:
            self._change_log = [msg async for msg in self.get_channel(CHANGE_LOG_ID).history(limit=1)]

        return self._change_log[0]

    @property
    def author_obj(self) -> Optional[discord.User]:
        return self.get_user(MASTER_OWNER)

    @property
    def author_name(self) -> str:
        return f"{AUTHOR_NAME}#{AUTHOR_DISCRIMINATOR}"  # cant join str and int, ofc

    async def setup_hook(self) -> None:
        if TO_LOAD_IPC:
            self.ipc.start()
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                print(f"[{self.user.name.title()}] {ext} loaded successfully")
                self._successfully_loaded.append(ext)
            except commands.ExtensionFailed as e:
                self._failed_to_load[ext] = str(e)
                traceback.print_exc()
            else:
                if ext in UNLOAD_EXTENSIONS:
                    await self.unload_extension(ext)
                    print(f"[{self.user.name.title()}] {ext} unloaded successfully")

        if self.HAS_TOP_GG:
            self.topgg = topgg.DBLClient(
                self,
                os.environ["TOPGG"],
                autopost=True,
                post_shard_count=True,
                session=self.http_session,
            )
            self.topgg_webhook = topgg.WebhookManager(self)

        self.reminder_task.start()

    async def db_latency(self) -> float:
        ini = perf_counter()
        await self.mongo.parrot_db.server_config.find_one({})
        return perf_counter() - ini

    def _clear_gateway_data(self) -> None:
        one_week_ago = discord.utils.utcnow() - datetime.timedelta(days=7)
        for _, dates in self.identifies.items():
            to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
            for index in reversed(to_remove):
                del dates[index]

        for _, dates in self.resumes.items():
            to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
            for index in reversed(to_remove):
                del dates[index]

    async def on_socket_raw_receive(self, msg: str) -> None:
        self._prev_events.append(msg)

    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        print(f"Ignoring exception in {event}", file=sys.stderr)
        traceback.print_exc()
        trace = traceback.format_exc()
        webhook: discord.Webhook = discord.Webhook.from_url(
            f"https://discordapp.com/api/webhooks/{ERROR_LOG_WEBHOOK_ID}/{self._error_log_token}",
            session=self.http_session,
        )

        _CONTENT = f"```py\nIgnoring exception in {event}\n{trace}\n``````py\nArgs: {args}\nKwargs: {kwargs}```"
        _FILE = discord.utils.MISSING

        if len(_CONTENT) > 1990:
            _FILE: discord.File = discord.File(
                io.BytesIO(f"Ignoring exception in {event}\n{trace}\nArgs: {args}\nKwargs: {kwargs}".encode("utf-8")),
                filename="traceback.py",
            )
            _CONTENT = discord.utils.MISSING

        if webhook is not None:
            with suppress(discord.HTTPException):
                await webhook.send(
                    _CONTENT,
                    file=_FILE,
                    avatar_url=self.user.avatar.url,
                    username=self.user.name,
                )

    async def before_identify_hook(self, shard_id: int, *, initial: bool = False) -> None:
        self._clear_gateway_data()
        self.identifies[shard_id].append(discord.utils.utcnow())
        await super().before_identify_hook(shard_id, initial=initial)

    async def db(self, db_name: str):
        return self.mongo[db_name]

    async def on_autopost_success(self) -> None:
        if self.HAS_TOP_GG:
            webhook: discord.Webhook = discord.Webhook.from_url(
                f"https://discordapp.com/api/webhooks/{STARTUP_LOG_WEBHOOK_ID}/{self._startup_log_token}",
                session=self.http_session,
            )
            if webhook is not None:
                with suppress(discord.HTTPException):
                    await webhook.send(
                        f"```py\n{self.user.name} posted server count ({self.topgg.guild_count}), shard count ({self.shard_count}).\n```",
                        avatar_url=self.user.avatar.url,
                        username=self.user.name,
                    )

            st = f"[{self.user.name.title()}] Posted server count ({self.topgg.guild_count}), shard count ({self.shard_count})"
            print(st)

    async def on_dbl_vote(self, data: BotVoteData) -> None:
        if self.HAS_TOP_GG:
            if data.type == "test":
                return self.dispatch("dbl_test", data)

            webhook: discord.Webhook = discord.Webhook.from_url(
                f"https://discordapp.com/api/webhooks/{VOTE_LOG_WEBHOOK_ID}/{self._vote_log_token}",
                session=self.http_session,
            )
            if webhook is not None:
                with suppress(discord.HTTPException):
                    user: discord.User = await self.getch(self.get_user, self.fetch_user, data.user)
                    await webhook.send(
                        f"Received a vote from {user} ({user.id})",
                        avatar_url=self.user.avatar.url,
                        username=self.user.name,
                    )

    async def on_dbl_test(self, data: BotVoteData) -> None:
        webhook: discord.Webhook = discord.Webhook.from_url(
            f"https://discordapp.com/api/webhooks/{VOTE_LOG_WEBHOOK_ID}/{self._vote_log_token}",
            session=self.http_session,
        )
        if webhook is not None:
            with suppress(discord.HTTPException):
                await webhook.send(
                    f"Received a test vote of data: {data}",
                    avatar_url=self.user.avatar.url,
                    username=self.user.name,
                )

    def run(self) -> None:
        """To run connect and login into discord"""
        super().run(TOKEN, reconnect=True)

    async def close(self) -> None:
        """To close the bot"""
        if TO_LOAD_IPC and self.HAS_TOP_GG:
            await self.topgg_webhook.close()

        self.reminder_task.cancel()

        return await super().close()

    async def on_ready(self) -> None:
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        if self._was_ready:
            return

        webhook: discord.Webhook = discord.Webhook.from_url(
            f"https://discordapp.com/api/webhooks/{STARTUP_LOG_WEBHOOK_ID}/{self._startup_log_token}",
            session=self.http_session,
        )
        if webhook is not None:
            await webhook.send(
                f"```py\n{self.user.name.title()} is online!\n```",
                avatar_url=self.user.avatar.url,
                username=self.user.name,
            )
            with suppress(discord.HTTPException):
                await webhook.send(
                    f"\N{WHITE HEAVY CHECK MARK} | `{'`, `'.join(self._successfully_loaded)}`",
                    avatar_url=self.user.avatar.url,
                    username=self.user.name,
                )
            with suppress(discord.HTTPException):
                if self._failed_to_load:
                    fail_msg = "\n".join(
                        f"> \N{CROSS MARK} Failed to load: `{k}` ```\n{v}```" for k, v in self._failed_to_load.items()
                    )

                    await webhook.send(
                        f"\N{CROSS MARK} | `{'`, `'.join(self._failed_to_load)}`",
                        avatar_url=self.user.avatar.url,
                        username=self.user.name,
                    )
                    if len(fail_msg) < 1990:
                        await webhook.send(
                            f"{fail_msg}",
                            avatar_url=self.user.avatar.url,
                            username=self.user.name,
                        )


        print(f"[{self.user.name.title()}] Ready: {self.user} (ID: {self.user.id})")
        print(f"[{self.user.name.title()}] Using discord.py of version: {discord.__version__}")

        ls: List[Optional[int]] = await self.mongo.parrot_db.afk.distinct("messageAuthor")
        self.afk = set(ls)

        await self.update_opt_in_out.start()

        if TO_LOAD_IPC:
            # connect to Lavalink server
            success = await self.ipc_client.request("start_wavelink_nodes", host="127.0.0.1", port=1018, password="password")
            if success["status"] == "ok":
                print(f"[{self.user.name}] Wavelink node connected successfully")

            # start webserver to receive Top.GG webhooks
            success = await self.ipc_client.request("start_dbl_server", port=1019, end_point="/dblwebhook")
            if success["status"] == "ok":
                print(f"[{self.user.name}] DBL server started successfully")

        self._was_ready = True

    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting."""
        print(f"[{self.user.name}] Wavelink Node {node.identifier} is ready!")

    async def on_connect(self) -> None:
        print(f"[{self.user.name.title()}] Logged in")
        return

    async def on_disconnect(self) -> None:
        webhook: discord.Webhook = discord.Webhook.from_url(
            f"https://discordapp.com/api/webhooks/{STARTUP_LOG_WEBHOOK_ID}/{self._startup_log_token}",
            session=self.http_session,
        )
        if webhook is not None:
            await webhook.send(
                f"```py\n{self.user.name.title()} disconnected from discord\n```",
                avatar_url=self.user.avatar.url,
                username=self.user.name,
            )

        print(f"[{self.user.name.title()}] disconnect from discord")
        return

    async def on_shard_resumed(self, shard_id: int) -> None:
        webhook: discord.Webhook = discord.Webhook.from_url(
            f"https://discordapp.com/api/webhooks/{STARTUP_LOG_WEBHOOK_ID}/{self._startup_log_token}",
            session=self.http_session,
        )
        if webhook is not None:
            await webhook.send(
                f"```py\n{self.user.name.title()} resumed shard {shard_id}\n```",
                avatar_url=self.user.avatar.url,
                username=self.user.name,
            )

        print(f"[{self.user.name.title()}] Shard ID {shard_id} has resumed...")
        self.resumes[shard_id].append(discord.utils.utcnow())

    async def process_commands(self, message: discord.Message) -> None:
        ctx: Context = await self.get_context(message, cls=Context)
        if ctx.command is None or str(ctx.channel.type) == "public_thread":
            return

        if self.UNDER_MAINTENANCE and ctx.author.id not in self.owner_ids:
            await ctx.send(
                embed=discord.Embed(
                    title="Bot under maintenance!",
                    description=self.UNDER_MAINTENANCE_REASON or "N/A"
                ).add_field(
                    name="ETA?", value=discord.utils.format_dt(self.UNDER_MAINTENANCE_OVER, "R") if self.UNDER_MAINTENANCE_OVER else "N/A"
                ).add_field(
                    name="Message From?", value=self.author_name
                ).add_field(
                    name="Have Question?", value=f"[Join Support Server]({self.support_server})"
                ).set_author(
                    name=ctx.author, icon_url=ctx.author.display_avatar.url, url=self.support_server
                )
            )
            return

        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.timestamp()
        retry_after: Optional[float] = bucket.update_rate_limit(current)
        author_id = message.author.id
        if retry_after:
            self._auto_spam_count[author_id] += 1
            if self._auto_spam_count[author_id] >= 3:
                return
        else:
            self._auto_spam_count.pop(author_id, None)
        if ctx.command is not None:
            if not self.banned_users:
                await self.update_banned_members.start()
            try:
                self.banned_users[ctx.author.id]
            except KeyError:
                pass
            else:
                if self.banned_users[ctx.author.id].get("command"):
                    return
            can_run: Optional[bool] = await _can_run(ctx)
            if not can_run:
                return await ctx.reply(
                    f"{ctx.author.mention} `{ctx.command.qualified_name}` is being disabled in **{ctx.channel.mention}** by the staff!",
                    delete_after=10.0
                )

        if guild := self.opts.get(ctx.guild.id):
            if ctx.author.id in guild.get("command", []):
                return
        await self.invoke(ctx)
        return

    async def on_message(self, message: discord.Message) -> None:
        self._seen_messages += 1

        if message.guild is None or message.author.bot:
            # to prevent the usage of command in DMs
            return

        if re.fullmatch(rf"<@!?{self.user.id}>", message.content):
            await message.channel.send(f"Prefix: `{await self.get_guild_prefixes(message.guild)}`")
            return

        await self.process_commands(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None or after.author.bot:
            return

        if before.content != after.content and before.author.id in OWNER_IDS:
            await self.process_commands(after)

    async def resolve_member_ids(self, guild: discord.Guild, member_ids: Iterable[int]) -> AsyncGenerator[discord.Member, None]:
        """|coro|

        Bulk resolves member IDs to member instances, if possible.

        Members that can't be resolved are discarded from the list.

        This is done lazily using an asynchronous iterator.

        Note that the order of the resolved members is not the same as the input.

        Parameters
        -----------
        guild: Guild
            The guild to resolve from.
        member_ids: Iterable[int]
            An iterable of member IDs.

        Yields
        --------
        Member
            The resolved members.
        """
        needs_resolution = []
        for member_id in member_ids:
            member = guild.get_member(member_id)
            if member is not None:
                yield member
            else:
                needs_resolution.append(member_id)

        total_need_resolution = len(needs_resolution)
        if total_need_resolution == 1:
            shard = self.get_shard(guild.shard_id)
            if shard.is_ws_ratelimited():
                try:
                    member = await guild.fetch_member(needs_resolution[0])
                except discord.HTTPException:
                    pass
                else:
                    yield member
            else:
                members = await guild.query_members(limit=1, user_ids=needs_resolution, cache=True)
                if members:
                    yield members[0]
        elif total_need_resolution <= 100 and total_need_resolution > 1:
            # Only a single resolution call needed here
            resolved = await guild.query_members(limit=100, user_ids=needs_resolution, cache=True)
            for member in resolved:
                yield member
        else:
            # We need to chunk these in bits of 100...
            for index in range(0, total_need_resolution, 100):
                to_resolve = needs_resolution[index : index + 100]
                members = await guild.query_members(limit=100, user_ids=to_resolve, cache=True)
                for member in members:
                    yield member

    async def get_or_fetch_member(self, guild: discord.Guild, member_id: Union[int, discord.Object]) -> Optional[discord.Member]:
        """|coro|

        Looks up a member in cache or fetches if not found.

        Parameters
        -----------
        guild: Guild
            The guild to look in.
        member_id: int
            The member ID to search for.

        Returns
        ---------
        Optional[Member]
            The member or None if not found.
        """
        member_id = member_id.id if isinstance(member_id, discord.Object) else int(member_id)

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard = self.get_shard(guild.shard_id)
        if shard.is_ws_ratelimited():
            try:
                return await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        return members[0] if members else None

    async def get_or_fetch_message(
        self,
        channel: Union[discord.TextChannel, discord.PartialMessageable, discord.Object, int],
        message: int,
        *,
        fetch: bool = True,
        cache: bool = True,
        partial: bool = False,
        force_fetch: bool = False,
    ) -> Union[discord.Message, discord.PartialMessage, None]:
        """|coro|

        Get message from cache. Fetches if not found, and stored in cache

        Parameters
        -----------
        channel: discord.TextChannel
            The channel to look in.
        message: int
            The message ID to search for.
        fetch: bool
            To fetch the message from channel or not.
        cache: bool
            To get message from internal cache.
        partaial: bool
            If found nothing from cache, it will give the discord.PartialMessage

        Returns
        ---------
        Optional[discord.Message]
            The Message or None if not found.
        """
        if isinstance(channel, int):
            if force_fetch:
                channel = await self.getch(self.get_channel, self.fetch_channel, channel, force_fetch=True)
            else:
                channel = self.get_channel(channel)
        elif isinstance(channel, discord.Object):
            if force_fetch:
                channel = await self.getch(self.get_channel, self.fetch_channel, channel.id, force_fetch=True)
            else:
                channel = self.get_channel(channel.id)

        channel: discord.TextChannel = channel  # type: ignore
        if force_fetch:
            msg = await channel.fetch_message(message)  # type: ignore
            self.message_cache[message] = msg
            return msg

        if cache and (msg := self._connection._get_message(message)):
            self.message_cache[message] = msg
            return msg

        if partial:
            return channel.get_partial_message(message)  # type: ignore

        try:
            return self.message_cache[message]
        except KeyError:
            if fetch:
                async for msg in channel.history(  # type: ignore
                    limit=1,
                    before=discord.Object(message + 1),
                    after=discord.Object(message - 1),
                ):
                    self.message_cache[message] = msg
                    return msg

        return None

    async def get_prefix(self, message: discord.Message) -> Union[str, Callable, List[str]]:
        """Dynamic prefixing"""
        if message.guild is None:
            return commands.when_mentioned_or("$")(self, message)
        try:
            prefix: str = self.server_config[message.guild.id]["prefix"]
        except KeyError:
            if data := await self.mongo.parrot_db.server_config.find_one({"_id": message.guild.id}):
                prefix = data["prefix"]
                post = data
                self.server_config[message.guild.id] = post
            else:
                FAKE_POST = POST.copy()
                FAKE_POST["_id"] = message.guild.id
                prefix = "$"  # default prefix
                try:
                    await self.mongo.parrot_db.server_config.insert_one(FAKE_POST)
                except pymongo.errors.DuplicateKeyError:
                    return commands.when_mentioned_or("$")(self, message)
                self.server_config[message.guild.id] = FAKE_POST

        comp = re.compile(f"^({re.escape(prefix)}).*", flags=re.I)
        match = comp.match(message.content)
        if match is not None:
            prefix = match[1]
        return commands.when_mentioned_or(prefix)(self, message)

    async def get_guild_prefixes(self, guild: discord.Guild) -> str:
        try:
            return self.server_config[guild.id]["prefix"]
        except KeyError:
            if data := await self.mongo.parrot_db.server_config.find_one({"_id": guild.id}):
                return data.get("prefix", "$")
        return "$"

    async def invoke_help_command(self, ctx: Context) -> None:
        return await ctx.send_help(ctx.command)

    async def getch(
        self,
        get_function: Union[Callable, Any],
        fetch_function: Union[Callable, Awaitable],
        _id: Union[int, discord.Object] = None,
        *,
        force_fetch: bool = True,
    ) -> Any:

        if _id is None:
            something = None
            if not callable(get_function):
                something = get_function
            if isinstance(fetch_function, Awaitable) and something is None and force_fetch:
                return await fetch_function
            return something

        with suppress(discord.HTTPException):
            _id = _id.id if isinstance(_id, discord.Object) else int(_id)
            something = get_function(_id)
            if something is None and force_fetch and callable(fetch_function):
                return await fetch_function(_id)
            return something

        return None

    @tasks.loop(count=1)
    async def update_server_config_cache(self, guild_id: int):
        if data := await self.mongo.parrot_db.server_config.find_one({"_id": guild_id}):
            self.server_config[guild_id] = data

    @tasks.loop(count=1)
    async def update_banned_members(self):
        self.banned_users = {}
        async for data in self.mongo.parrot_db.banned_users.find({}):
            self.banned_users[data["_id"]] = data

    @tasks.loop(count=1)
    async def update_opt_in_out(self):
        self.opts = {}
        async for data in self.mongo.extra.misc.find({}):
            data: Dict[str, Any] = data
            _id: int = data.pop("_id")
            self.opts[_id] = data
            await asyncio.sleep(0)

    @tasks.loop(seconds=3)
    async def reminder_task(self):
        collection: MongoCollection = self.mongo.parrot_db["timers"]
        async with self.lock:
            async for data in collection.find({"expires_at": {"$lte": discord.utils.utcnow().timestamp()}}):
                await collection.delete_one({"_id": data["_id"]})
                self.dispatch("timer_complete", **data)

    @reminder_task.before_loop
    async def before_reminder_task(self):
        await self.wait_until_ready()
