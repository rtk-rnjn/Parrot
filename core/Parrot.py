# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import datetime
import io
import logging
import logging.handlers
import os
import re
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
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

import aiohttp
import jishaku  # type: ignore  # noqa: F401
import pymongo
import wavelink
from aiohttp import ClientSession  # type: ignore
from lru import LRU
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore

import discord
from discord import app_commands
from discord.ext import commands, ipc, tasks  # type: ignore

try:
    import topgg  # type: ignore

    HAS_TOP_GG = True
except ImportError:
    HAS_TOP_GG = False

from time import perf_counter

from utilities.checks import _can_run
from utilities.config import (
    CASE_INSENSITIVE,
    CHANGE_LOG_CHANNEL_ID,
    EXTENSIONS,
    GITHUB,
    HEROKU,
    MASTER_OWNER,
    OWNER_IDS,
    STRIP_AFTER_PREFIX,
    SUPPORT_SERVER,
    SUPPORT_SERVER_ID,
    TO_LOAD_IPC,
    TOKEN,
    UNLOAD_EXTENSIONS,
    VERSION,
    WEBHOOK_ERROR_LOGS,
    WEBHOOK_JOIN_LEAVE_LOGS,
    WEBHOOK_STARTUP_LOGS,
    WEBHOOK_VOTE_LOGS,
)
from utilities.converters import Cache, ToAsync
from utilities.paste import Client

from .__template import post as POST
from .Context import Context

if TYPE_CHECKING:
    from discord.ext.commands.cooldowns import CooldownMapping
    from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
    from typing_extensions import TypeAlias

    from .Cog import Cog

    if HAS_TOP_GG:
        from topgg.types import BotVoteData

    MongoCollection: TypeAlias = AsyncIOMotorCollection  # type: ignore
    MongoDatabase: TypeAlias = AsyncIOMotorDatabase  # type: ignore

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

intents = discord.Intents.default()
intents.members = True  # type: ignore
intents.message_content = True  # type: ignore

dbl_token = os.environ["TOPGG"]

CHANGE_LOG_ID = CHANGE_LOG_CHANNEL_ID
DEFAULT_PREFIX: Literal["$"] = "$"

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("discord.http").setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename=".discord.log",
    encoding="utf-8",
    maxBytes=1 * 1024 * 1024,  # 1 MiB
    backupCount=1,  # Rotate through 1 files
)
DT_FMT = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name:<10}: {module}.{funcName} - {message}",
    DT_FMT,
    style="{",
)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logger.addHandler(handler)

log = logging.getLogger("core.parrot")


@ToAsync()
def func(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return function(*args, **kwargs)


__all__ = ("Parrot",)

# LOCALHOST = "0.0.0.0" if HEROKU else "127.0.0.1"
LOCALHOST = "localhost"
IPC_PORT = 1730
LAVALINK_PORT = 1018
LAVALINK_PASSWORD = "password"
TOPGG_PORT = 1019


class Parrot(commands.AutoShardedBot):
    """A custom way to organise a commands.AutoSharedBot."""

    __version__: str

    user: discord.ClientUser
    help_command: Optional[commands.HelpCommand]

    http_session: ClientSession
    mongo: AsyncIOMotorClient  # type: ignore

    cogs: Mapping[str, Cog]
    extensions: Mapping[str, types.ModuleType]

    cached_messages: Sequence[discord.Message]
    guilds: Sequence[discord.Guild]

    tree_cls: Type[app_commands.CommandTree]
    tree: app_commands.CommandTree

    owner_id: Optional[int]
    owner_ids: Optional[Collection[int]]

    voice_clients: List[discord.VoiceProtocol]

    DBL_SERVER_RUNNING: bool = False
    WAVELINK_NODE_READY: bool = False
    ON_DOCKER: bool = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(
            command_prefix=self.get_prefix,  # type: ignore
            case_insensitive=CASE_INSENSITIVE,
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.watching, name="you"),
            status=discord.Status.dnd,
            strip_after_prefix=STRIP_AFTER_PREFIX,
            owner_ids=set(OWNER_IDS),
            allowed_mentions=discord.AllowedMentions(
                everyone=False, replied_user=False
            ),
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
            shard_count=1,
            max_messages=5000,
            chunk_guilds_at_startup=False,
            **kwargs,
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()
        self._CogMixin__cogs = commands.core._CaseInsensitiveDict()  # pycord be like
        self._seen_messages: int = 0
        self._change_log: List[discord.Message] = []

        self._error_log_token: str = WEBHOOK_ERROR_LOGS
        self._startup_log_token: str = WEBHOOK_STARTUP_LOGS
        self._vote_log_token: str = WEBHOOK_VOTE_LOGS
        self._join_leave_log_token: str = WEBHOOK_JOIN_LEAVE_LOGS

        self.color: int = 0x87CEEB
        self.colour: int = self.color

        self.error_channel: Optional[discord.TextChannel] = None
        self.persistent_views_added: bool = False
        self.spam_control: CooldownMapping = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.user
        )

        self._was_ready: bool = False
        self.lock: "asyncio.Lock" = asyncio.Lock()
        self.timer_task: Optional[asyncio.Task] = None
        self._current_timer: Union[Dict, None] = {}
        self._have_data: asyncio.Event = asyncio.Event()
        self.reminder_event: asyncio.Event = asyncio.Event()
        self.ON_HEROKU: bool = HEROKU

        # Top.gg
        self.HAS_TOP_GG = HAS_TOP_GG
        if self.HAS_TOP_GG:
            self.topgg: "topgg.DBLClient"  # type: ignore
            self.topgg_webhook: "topgg.WebhookManager"  # type: ignore

        self._auto_spam_count: "Counter[int]" = Counter()
        self.resumes: Dict[int, List[datetime.datetime]] = defaultdict(list)
        self.identifies: Dict[int, List[datetime.datetime]] = defaultdict(list)
        self._prev_events: "deque[str]" = deque(maxlen=10)

        self.mystbin: Client = Client()

        # caching variables
        self.guild_configurations_cache: Dict[int, Dict[str, Any]] = Cache(self)
        self.message_cache: Dict[int, discord.Message] = {}
        self.banned_users: Dict[int, Dict[str, Union[int, str, bool]]] = {}
        self.afk: "Set[int]" = set()

        self.func: Callable[..., Any] = func

        self.before_invoke(self.__before_invoke)

        # IPC
        self.HAS_IPC = TO_LOAD_IPC
        self.ipc_server: "ipc.Server" = ipc.Server(
            bot=self,
            host=LOCALHOST,
            port=IPC_PORT,
            secret_key=os.environ["IPC_KEY"],
        )
        self.ipc_client: "ipc.Client" = ipc.Client(
            host=LOCALHOST,
            port=IPC_PORT,
            secret_key=os.environ["IPC_KEY"],
        )

        # Extensions
        self._successfully_loaded: List[str] = []
        self._failed_to_load: Dict[str, str] = {}

        # Wavelink
        self.wavelink: "wavelink.NodePool" = wavelink.NodePool()

        self.GLOBAL_HEADERS: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": f"Discord Bot '{self.user}' {getattr(self, '__version__', VERSION)} @ {self.github}",
        }

        self.UNDER_MAINTENANCE: bool = False
        self.UNDER_MAINTENANCE_REASON: Optional[str] = None
        self.UNDER_MAINTENANCE_OVER: Optional[datetime.datetime] = None

    def init_db(self) -> None:
        # MongoDB Database variables
        # Main DB
        self.main_db: MongoDatabase = self.mongo["mainDB"]
        self.guild_configurations: MongoCollection = self.main_db["guildConfigurations"]
        self.game_collections: MongoCollection = self.main_db["gameCollections"]
        self.command_collections: MongoCollection = self.main_db["commandCollections"]
        self.timers: MongoCollection = self.main_db["timers"]
        self.starboards: MongoCollection = self.main_db["starboards"]
        self.giveaways: MongoCollection = self.main_db["giveawaysCollection"]
        self.user_collections_ind: MongoCollection = self.main_db["userCollections"]
        self.guild_collections_ind: MongoCollection = self.main_db["guildCollections"]
        self.extra_collections: MongoCollection = self.main_db["extraCollections"]
        self.dictionary: MongoCollection = self.main_db["dictionary"]

        # User Message DB
        self.user_message_db: MongoDatabase = self.mongo["userMessageDB"]

        # Guild Message DB
        self.guild_message_db: MongoDatabase = self.mongo["guildMessageDB"]

        # User DB
        self.user_db: MongoDatabase = self.mongo["userDB"]

        # Guild DB
        self.guild_level_db: MongoDatabase = self.mongo["guildLevelDB"]

    def __repr__(self) -> str:
        return f"<core.{self.user.name}>"

    @property
    def server(self) -> Optional[discord.Guild]:
        assert isinstance(SUPPORT_SERVER_ID, int)

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
        log.info("Getting recent message from channel %s", CHANGE_LOG_ID)
        assert isinstance(CHANGE_LOG_ID, int)

        channel: Optional[discord.TextChannel] = self.get_channel(CHANGE_LOG_ID)  # type: ignore

        if not self._change_log and channel is not None:
            self._change_log = [msg async for msg in channel.history(limit=1)]

        if self._change_log:
            return self._change_log[0]

    @property
    def author_obj(self) -> Optional[discord.User]:
        assert isinstance(MASTER_OWNER, int)

        return self.get_user(MASTER_OWNER)

    @property
    def author_name(self) -> str:
        return str(self.author_obj)

    async def setup_hook(self) -> None:
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                self._successfully_loaded.append(ext)
                log.info("Loaded extension %s", ext)
            except (commands.ExtensionFailed, commands.ExtensionNotFound) as e:
                self._failed_to_load[ext] = str(e)
                traceback.print_exc()
                log.error("Failed to load extension %s", ext)
            else:
                if ext in UNLOAD_EXTENSIONS:
                    await self.unload_extension(ext)
                    log.warn("Unloaded extension %s", ext)

        if self.HAS_TOP_GG:
            self.topgg = topgg.DBLClient(  # type: ignore
                self,
                os.environ["TOPGG"],
                autopost=True,
                post_shard_count=True,
                session=self.http_session,
            )
            self.topgg_webhook = topgg.WebhookManager(self)  # type: ignore

        if self.HAS_IPC:
            # thing is you cant run localhost inside docker container
            # so we need to check if we are running inside docker container
            # just by checking if starting the server fails, and raises OSError
            try:
                await self.ipc_server.start()
                log.info("IPC server started")
            except OSError as e:
                log.warn("Failed to start IPC server")
                self.ON_DOCKER = True

            if not self.ON_DOCKER:
                try:
                    success = await self.ipc_client.request(
                        "start_wavelink_nodes",
                        host=LOCALHOST,
                        port=LAVALINK_PORT,
                        password=LAVALINK_PASSWORD,
                    )
                    log.info("Wavelink nodes started: %s", success)

                    # start webserver to receive Top.GG webhooks
                    success = await self.ipc_client.request(
                        "start_dbl_server", port=TOPGG_PORT, end_point="/dblwebhook"
                    )
                    log.info("Top.GG webhook server started: %s", success)
                except aiohttp.ClientConnectionError as e:
                    log.warn("Failed to start IPC server")
                    traceback.print_exc()
                except OSError as e:
                    log.warn("Failed to start IPC server")
                    self.ON_DOCKER = True
                    traceback.print_exc()

        self.timer_task = self.loop.create_task(self.dispatch_timers())

        async def __laod_cache():
            log.info("Fetching guild configurations from database")
            async for data in self.guild_configurations.find({}):
                self.guild_configurations_cache[data["_id"]] = data

        self.loop.create_task(__laod_cache())

    async def db_latency(self) -> float:
        ini = perf_counter()
        await self.guild_configurations.find_one({})
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

    async def _execute_webhook_from_scratch(
        self,
        webhook: Union[discord.Webhook, str, None],
        *,
        content: str,
        username: str,
        avatar_url: str,
        **kw: Any,
    ) -> Optional[dict]:
        payload = {}
        assert isinstance(webhook, (discord.Webhook, str))
        URL = webhook.url if isinstance(webhook, discord.Webhook) else webhook
        if content:
            payload["content"] = content
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url

        if self.http_session.closed:
            log.info("HTTP session is closed. Creating new session")
            self.http_session = aiohttp.ClientSession(loop=self.loop)
        log.info("Executing webhook from scratch (%s). Payload: %s", URL, payload)
        async with self.http_session.post(
            URL, json=payload, headers=self.GLOBAL_HEADERS
        ) as resp:
            return await resp.json()

    async def _execute_webhook(
        self,
        webhook: Union[str, discord.Webhook, None] = None,  # type: ignore
        *,
        webhook_id: Union[str, int, None] = None,
        webhook_token: Optional[str] = None,
        content: str,
        force_file: bool = False,
        filename: Optional[str] = None,
        suppressor: Optional[
            Union[Tuple[Type[Exception]], Type[Exception]]
        ] = Exception,
        **kwargs: Any,
    ) -> Optional[discord.WebhookMessage]:
        if webhook is None and (webhook_id is None and webhook_token is None):
            raise ValueError(
                "must provide atleast webhook_url or webhook_id and webhook_token"
            )

        if webhook_id and webhook_token:
            log.info("Executing webhook with webhook_id and webhook_token")
            BASE_URL = "https://discordapp.com/api/webhooks"
            URL = f"{BASE_URL}/{webhook_id}/{webhook_token}"

        elif isinstance(webhook, str) and not self.http_session.closed:
            URL = webhook

            webhook: discord.Webhook = discord.Webhook.from_url(
                URL, session=self.http_session
            )
        else:
            await self._execute_webhook_from_scratch(
                webhook,
                content=content,
                username=kwargs.pop("username", self.user.name),
                avatar_url=kwargs.pop("avatar_url", self.user.display_avatar.url),
                **kwargs,
            )
            return

        _CONTENT = content
        _FILE = kwargs.pop("file", discord.utils.MISSING)

        if content and len(content) > 1990 or force_file:
            _FILE: discord.File = discord.File(
                io.BytesIO(
                    content.encode("utf-8") if isinstance(content, str) else content
                ),
                filename=filename or "content.txt",
            )
            _CONTENT = discord.utils.MISSING

        if webhook is not None and isinstance(webhook, discord.Webhook):
            try:
                log.info(
                    "Executing webhook with discord.Webhook (%s). Content: %s",
                    webhook.url,
                    content,
                )
                return await webhook.send(
                    content=_CONTENT,
                    file=_FILE,
                    avatar_url=kwargs.pop("avatar_url", self.user.display_avatar.url),
                    username=kwargs.pop("username", self.user.name),
                    **kwargs,
                )
            except suppressor:
                return None
        return None

    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        log.error("Ignoring exception in %s", event, exc_info=True)
        await self._execute_webhook(
            WEBHOOK_ERROR_LOGS,
            content=f"```py\n{traceback.format_exc()}```",
        )
        traceback.print_exc()

    async def before_identify_hook(
        self, shard_id: int, *, initial: bool = False
    ) -> None:
        self._clear_gateway_data()
        self.identifies[shard_id].append(discord.utils.utcnow())
        await super().before_identify_hook(shard_id, initial=initial)

    async def db(self, db_name: str):
        return self.mongo[db_name]

    async def on_autopost_success(self) -> None:
        if self.HAS_TOP_GG:
            st = f"[{self.user.name.title()}] Posted server count ({self.topgg.guild_count}), shard count ({self.shard_count})"
            await self._execute_webhook(
                self._startup_log_token,
                content=f"```css\n{st}```",
            )
            log.info(
                "Posted server count (%s), shard count (%s)",
                self.topgg.guild_count,
                self.shard_count,
            )

    async def on_autopost_error(self, exception: Exception) -> None:
        if self.HAS_TOP_GG:
            await self._execute_webhook(
                self._error_log_token,
                content=f"```css\n{exception}```",
            )
            log.error("Failed to post server count (%s)", exception, exc_info=True)

    async def on_dbl_vote(self, data: BotVoteData) -> None:
        if data["type"] == "test":
            return self.dispatch("dbl_test", data)
        elif data["type"] == "upvote":
            user: Optional[discord.User] = self.get_user(int(data["user"]))
            user = user.name if user is not None else f"Unknown User ({data['user']})"  # type: ignore

            await self._execute_webhook(
                self._vote_log_token,
                content=f"```css\n{user} ({data['user']}) has upvoted the bot```",
            )

    async def on_dbl_test(self, data: BotVoteData) -> None:
        if data["type"] == "test":
            await self._execute_webhook(
                self._vote_log_token,
                content=f"```css\nReceived a test vote from {data['user']} ({data['user']})```",
            )

    def run(self) -> None:
        """To run connect and login into discord"""
        super().run(TOKEN, reconnect=True)

    async def close(self) -> None:
        """To close the bot"""

        if hasattr(self, "http_session"):
            await self.http_session.close()

        if self.timer_task is not None and not self.timer_task.cancelled():
            self.timer_task.cancel()

        return await super().close()

    async def on_ready(self) -> None:
        # sourcery skip: assign-if-exp, hoist-similar-statement-from-if
        # sourcery skip: merge-assign-and-aug-assign, remove-redundant-fstring, swap-nested-ifs
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        if self._was_ready:
            return
        self._was_ready = True

        ready_up_message = (
            f"[{self.user.name.title()}] Ready: {self.user} (ID: {self.user.id})\n"
            f"[{self.user.name.title()}] Using discord.py of version: {discord.__version__}"
        )
        await self._execute_webhook(
            self._startup_log_token,
            content=f"```css\n{ready_up_message}```",
        )

        log.info("Ready: %s (ID: %s)", self.user, self.user.id)

        log.info("Getting all afk users from database")
        ls: List[Optional[int]] = await self.extra_collections.distinct(
            "afk.messageAuthor"
        )
        log.info("Got all afk users from database: %s", ls)
        if ls:
            self.afk = set(ls)  # type: ignore

        content = "```css\n"
        if self.WAVELINK_NODE_READY:
            content += f"- Wavelink Node is ready and running"
        else:
            content += f"- Wavelink Node is not running"

        if self.HAS_TOP_GG:
            if self.DBL_SERVER_RUNNING:
                content += f"\n- Top.gg server is running"
            else:
                content += f"\n- Top.gg server is not running"

        if self.ON_DOCKER:
            content += f"\n- Running on docker"
        else:
            content += f"\n- Running on local machine"

        if self._failed_to_load:
            content += f"\n- Failed to load {len(self._failed_to_load)} cogs"
        else:
            content += f"\n- All cogs loaded successfully"
        content += "```"

        await self._execute_webhook(self._startup_log_token, content=f"{content}")

        for name, error in self._failed_to_load.items():
            st = f"```css\n[{self.user.name.title()}] Failed to load {name} cog due to``````py\n{error}```"
            await self._execute_webhook(self._error_log_token, content=f"{st}")

        # Hmm...
        cog = self.get_cog("Music")
        if cog is not None and not self.WAVELINK_NODE_READY:
            await self.unload_extension("cogs.music")
            await self._execute_webhook(
                self._startup_log_token,
                content="```css\n- Unloaded music cog due to wavelink node not running```",
            )

        VOICE_CHANNEL_ID = 1116780108074713098
        channel: discord.VoiceChannel = await self.getch(
            self.get_channel, self.fetch_channel, VOICE_CHANNEL_ID
        )
        if channel is not None:
            await channel.connect(self_deaf=True, reconnect=True)

    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting."""
        log.info("Wavelink node %s is ready", node.id)

    async def on_connect(self) -> None:
        log.info("Connected to discord")
        return

    async def on_disconnect(self) -> None:
        log.info("Disconnected from discord")
        return

    async def on_shard_resumed(self, shard_id: int) -> None:
        log.info("Shard %s has resumed", shard_id)
        self.resumes[shard_id].append(discord.utils.utcnow())

    async def process_commands(self, message: discord.Message) -> None:
        ctx: Context = await self.get_context(message, cls=Context)

        if ctx.command is None:
            return

        if self.UNDER_MAINTENANCE:
            log.info("Bot is under maintenance, ignoring command. Context %s", ctx)
            await ctx.send(
                embed=discord.Embed(
                    title="Bot under maintenance!",
                    description=self.UNDER_MAINTENANCE_REASON or "N/A",
                )
                .add_field(
                    name="ETA?",
                    value=discord.utils.format_dt(self.UNDER_MAINTENANCE_OVER, "R")
                    if self.UNDER_MAINTENANCE_OVER
                    else "N/A",
                )
                .add_field(name="Message From?", value=self.author_name)
                .add_field(
                    name="Have Question?",
                    value=f"[Join Support Server]({self.support_server})",
                )
                .set_author(
                    name=ctx.author,
                    icon_url=ctx.author.display_avatar.url,
                    url=self.support_server,
                )
            )
            return

        if bucket := self.spam_control.get_bucket(message):
            current = message.created_at.timestamp()
            retry_after: Optional[float] = bucket.update_rate_limit(current)
            author_id = message.author.id
            if retry_after:
                self._auto_spam_count[author_id] += 1
                if self._auto_spam_count[author_id] >= 3:
                    log.info("Auto spam detected, ignoring command. Context %s", ctx)
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
            can_run: Optional[bool] = _can_run(ctx)
            if can_run is False:
                log.info(
                    "User %s is blacklisted or command is blocked, ignoring command. Context %s",
                    ctx,
                )
                assert not isinstance(
                    ctx.channel,
                    (
                        discord.DMChannel,
                        discord.GroupChannel,
                        discord.PartialMessageable,
                    ),
                )
                await ctx.reply(
                    f"{ctx.author.mention} `{ctx.command.qualified_name}` is being disabled in **{ctx.channel.mention}** by the staff!",
                    delete_after=10.0,
                )
                return

        if not getattr(ctx.cog, "ON_TESTING", False):
            log.info("Processing command %s. Context %s", ctx.command, ctx)
            await self.invoke(ctx)

        return

    async def on_message(self, message: discord.Message) -> None:
        self._seen_messages += 1

        if message.guild is None or message.author.bot:
            return

        try:
            self.guild_configurations_cache[message.guild.id]
        except KeyError:
            self.update_server_config_cache.start(message.guild.id)

        if re.fullmatch(rf"<@!?{self.user.id}>", message.content):
            await message.channel.send(
                f"Prefix: `{await self.get_guild_prefixes(message.guild)}`"
            )
            return

        await self.process_commands(message)

    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        if after.guild is None or after.author.bot:
            return

        if before.content != after.content and before.author.id in OWNER_IDS:
            await self.process_commands(after)

    async def resolve_member_ids(
        self, guild: discord.Guild, member_ids: Iterable[int]
    ) -> AsyncGenerator[discord.Member, None]:
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

            if shard and shard.is_ws_ratelimited():
                try:
                    member = await guild.fetch_member(needs_resolution[0])
                except discord.HTTPException:
                    pass
                else:
                    yield member
            else:
                members: List[discord.Member] = await guild.query_members(
                    limit=1, user_ids=needs_resolution, cache=True
                )
                if members:
                    yield members[0]
        elif total_need_resolution <= 100 and total_need_resolution > 1:
            # Only a single resolution call needed here
            resolved = await guild.query_members(
                limit=100, user_ids=needs_resolution, cache=True
            )
            for member in resolved:
                yield member
        else:
            # We need to chunk these in bits of 100...
            for index in range(0, total_need_resolution, 100):
                to_resolve = needs_resolution[index : index + 100]
                members = await guild.query_members(
                    limit=100, user_ids=to_resolve, cache=True
                )
                for member in members:
                    yield member

    async def get_or_fetch_member(
        self,
        guild: discord.Guild,
        member_id: Union[int, discord.Object],
        in_guild: bool = True,
    ) -> Union[discord.Member, discord.User, None]:
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
        if not in_guild:
            return await self.getch(self.get_user, self.fetch_user, member_id)

        member_id = (
            member_id.id if isinstance(member_id, discord.Object) else int(member_id)
        )

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard = self.get_shard(guild.shard_id)
        if shard and shard.is_ws_ratelimited():
            try:
                return await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        return members[0] if members else None

    async def get_or_fetch_message(
        self,
        channel: Union[  # type: ignore
            discord.Object, int, discord.abc.Messageable, discord.PartialMessageable
        ],
        message: int,
        *,
        fetch: bool = True,
        cache: bool = True,
        partial: bool = False,
        force_fetch: bool = False,
        dm_allowed: bool = False,
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
                channel = await self.getch(
                    self.get_channel, self.fetch_channel, channel, force_fetch=True
                )
            else:
                channel = self.get_channel(channel)  # type: ignore
        elif isinstance(channel, (discord.Object, discord.PartialMessageable)):
            if force_fetch:
                channel = await self.getch(
                    self.get_channel, self.fetch_channel, channel.id, force_fetch=True
                )
            else:
                channel = self.get_channel(channel.id)  # type: ignore

        if channel is None:
            return None

        if isinstance(channel, discord.DMChannel) and not dm_allowed:
            raise ValueError("DMChannel is not allowed")

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
            msg = self.message_cache[message]
            log.info("Got message from cache %s", msg)
            return msg
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

    async def get_prefix(
        self, message: discord.Message
    ) -> Union[str, Callable, List[str]]:
        """Dynamic prefixing"""
        if message.guild is None:
            return commands.when_mentioned_or(DEFAULT_PREFIX)(self, message)
        try:
            prefix: str = self.guild_configurations_cache[message.guild.id]["prefix"]
        except KeyError:
            if data := await self.guild_configurations.find_one(
                {"_id": message.guild.id}
            ):
                prefix = data.get("prefix", DEFAULT_PREFIX)
                post = data
                self.guild_configurations_cache[message.guild.id] = post
            else:
                FAKE_POST = POST.copy()
                FAKE_POST["_id"] = message.guild.id
                prefix = DEFAULT_PREFIX  # default prefix
                try:
                    await self.guild_configurations.insert_one(FAKE_POST)
                except pymongo.errors.DuplicateKeyError:  # type: ignore
                    return commands.when_mentioned_or(DEFAULT_PREFIX)(self, message)
                self.guild_configurations_cache[message.guild.id] = FAKE_POST

        comp = re.compile(f"^({re.escape(prefix)}).*", flags=re.I)
        match = comp.match(message.content)
        if match is not None:
            prefix = match[1]
        return commands.when_mentioned_or(prefix)(self, message)

    async def get_guild_prefixes(self, guild: Union[discord.Guild, int]) -> str:  # type: ignore
        if isinstance(guild, int):
            guild: discord.Object = discord.Object(id=guild)

        try:
            return self.guild_configurations_cache[guild.id]["prefix"]
        except KeyError:
            if data := await self.guild_configurations.find_one({"_id": guild.id}):
                return data.get("prefix", DEFAULT_PREFIX)
        return DEFAULT_PREFIX

    async def invoke_help_command(self, ctx: Context) -> None:
        return await ctx.send_help(ctx.command)

    async def getch(
        self,
        get_function: Union[Callable, Any],
        fetch_function: Union[Callable, Awaitable],
        _id: Union[int, discord.Object, None] = None,
        *,
        force_fetch: bool = True,
    ) -> Any:
        log.info(
            "Force fetch (%s), to get (%s). Functions: %s | %s",
            force_fetch,
            _id,
            get_function.__name__,
            fetch_function.__name__,  # type: ignore
        )
        if _id is None:
            something = None
            if not callable(get_function):
                something = get_function
            if (
                isinstance(fetch_function, Awaitable)
                and something is None
                and force_fetch
            ):
                log.info(
                    "Fetching data. function: %s",
                    fetch_function.__name__,  # type: ignore
                )
                return await fetch_function

            log.info(
                "Returning data (%s). function: %s | %s",
                something,
                get_function.__name__,
                fetch_function.__name__,  # type: ignore
            )
            return something

        with suppress(discord.HTTPException):
            _id = _id.id if isinstance(_id, discord.Object) else int(_id)
            something = get_function(_id)
            if something is None and force_fetch and callable(fetch_function):
                log.info(
                    "Fetching data. function: %s",
                    fetch_function.__name__,
                )
                return await fetch_function(_id)
            log.info(
                "Returning data (%s). functions: %s | %s",
                something,
                get_function.__name__,
                fetch_function.__name__,  # type: ignore
            )
            return something

        log.info(
            "Returning data (%s). function: %s | %s",
            None,
            get_function.__name__,
            fetch_function.__name__,  # type: ignore
        )
        return None

    @tasks.loop(count=1)
    async def update_server_config_cache(self, guild_id: int):
        async def __internal_func():
            log.info("Updating server config cache for guild %s", guild_id)
            if data := await self.guild_configurations.find_one({"_id": guild_id}):
                self.guild_configurations_cache[guild_id] = data
            else:
                log.info("Guild %s not found in database, creating new one", guild_id)
                FAKE_POST = POST.copy()
                FAKE_POST["_id"] = guild_id
                try:
                    await self.guild_configurations.insert_one(FAKE_POST)
                except pymongo.errors.DuplicateKeyError:  # type: ignore
                    pass
                finally:
                    self.guild_configurations_cache[guild_id] = FAKE_POST

        self.loop.create_task(__internal_func())

    @tasks.loop(count=1)
    async def update_banned_members(self):
        self.banned_users = {}
        data = await self.extra_collections.find_one({"_id": "banned_users"})
        if data is None:
            return
        for _data in data["users"]:
            self.banned_users[_data["user_id"]] = _data
            await asyncio.sleep(0)

    async def __before_invoke(self, ctx: Context):
        if ctx.guild is not None and not ctx.guild.chunked:
            self.loop.create_task(ctx.guild.chunk())

    async def get_active_timer(self, **filters: Any) -> dict:
        data = await self.timers.find_one(
            {**filters}, sort=[("expires_at", pymongo.ASCENDING)]
        )
        log.info("Received data: %s", data)
        return data

    async def wait_for_active_timers(self, **filters: Any) -> dict:
        timers = await self.get_active_timer(**filters)
        if timers:
            self._have_data.set()
            log.info("Event set")
            return timers

        self._have_data.clear()
        log.info("Event cleared")
        self._current_timer = None
        log.info(
            "Current timers set to None",
        )
        await self._have_data.wait()
        log.info("Event waited")
        return await self.get_active_timer()

    async def dispatch_timers(self):
        log.info("Starting timer task")
        try:
            while not self.is_closed():
                timers = self._current_timer = await self.wait_for_active_timers()
                log.info(
                    "Received timers: %s",
                    timers,
                )
                now = discord.utils.utcnow().timestamp()

                if timers is None:
                    continue

                if timers["expires_at"] > now:
                    log.info(
                        "Sleeping for %s seconds",
                        timers["expires_at"] - now,
                    )
                    await asyncio.sleep(timers["expires_at"] - now)

                await self.call_timer(self.timers, **timers)

                await asyncio.sleep(0)
        except (OSError, discord.ConnectionClosed, pymongo.errors.ConnectionFailure):  # type: ignore
            if self.timer_task:
                self.timer_task.cancel()
                self.timer_task = self.loop.create_task(self.dispatch_timers())

        except asyncio.CancelledError:
            raise

    async def call_timer(self, collection: MongoCollection, **data: Any):
        log.info("Calling timer: %s", data)
        deleted: pymongo.results.DeleteResult = await collection.delete_one(  # type: ignore
            {"_id": data["_id"]}
        )

        log.info("Deleted timer: %s", deleted)
        if deleted.deleted_count == 0:
            return

        if data.get("_event_name"):
            self.dispatch(f"{data['_event_name']}_timer_complete", **data)
        else:
            self.dispatch("timer_complete", **data)

    async def short_time_dispatcher(self, collection: MongoCollection, **data: Any):
        log.info(
            "Sleeping for %s seconds",
            data["expires_at"] - discord.utils.utcnow().timestamp(),
        )
        await asyncio.sleep(discord.utils.utcnow().timestamp() - data["expires_at"])

        await self.call_timer(collection, **data)

    async def create_timer(
        self,
        *,
        expires_at: float,
        _event_name: Optional[str] = None,
        created_at: Optional[float] = None,
        content: Optional[str] = None,
        message: Union[discord.Message, int, None] = None,
        dm_notify: bool = False,
        is_todo: bool = False,
        extra: Optional[Dict[str, Any]] = None,
        **kw,
    ) -> pymongo.results.InsertOneResult:  # type: ignore
        """|coro|

        Master Function to register Timers.

        Parameters
        ----------
        expires_at: :class:`float`
            Timer exprire timestamp
        created_at: :class:`float`
            Timer created timestamp
        content: :class:`str`
            Content of the Timer
        message: :class:`discord.Message`
            Message Object
        dm_notify: :class:`bool`
            To notify the user or not
        is_todo: :class:`bool`
            To provide whether the timer related to `TODO`
        """
        collection: MongoCollection = self.timers

        embed: Optional[Dict[str, Any]] = kw.get("embed_like") or kw.get("embed")
        mod_action: Optional[Dict[str, Any]] = kw.get("mod_action")
        cmd_exec_str: Optional[str] = kw.get("cmd_exec_str")

        # fmt: off
        post = {
            "_id": message.id if isinstance(message, discord.Message) else message,
            "_event_name": _event_name,
            "expires_at": expires_at,
            "created_at": (
                created_at
                or kw.get("created_at")
                or (
                    message.created_at.timestamp() if isinstance(message, discord.Message) else discord.utils.utcnow().timestamp()
                )
            ),
            "content": content,
            "embed": embed,
            "guild": message.guild.id if isinstance(message, discord.Message) and message.guild else "DM",
            "messageURL": message.jump_url if isinstance(message, discord.Message) else kw.get("messageURL"),
            "messageAuthor": message.author.id if isinstance(message, discord.Message) else kw.get("messageAuthor"),
            "messageChannel": message.channel.id if isinstance(message, discord.Message) else kw.get("messageChannel"),
            "dm_notify": dm_notify,
            "is_todo": is_todo,
            "mod_action": mod_action,
            "cmd_exec_str": cmd_exec_str,
            "extra": extra,
            **kw,
        }
        # fmt: on
        insert_data = await collection.insert_one(post)
        log.info("Inserted data: %s", insert_data)
        self._have_data.set()

        if self._current_timer and self._current_timer["expires_at"] > expires_at:
            self._current_timer = post

            if self.timer_task:
                log.info("Cancelling current timer %s", self._current_timer)
                self.timer_task.cancel()

                self.timer_task = self.loop.create_task(self.dispatch_timers())

        return insert_data

    async def delete_timer(self, **kw: Any) -> pymongo.results.DeleteResult:  # type: ignore
        collection: MongoCollection = self.timers
        data = await collection.delete_one({"_id": kw["_id"]})
        delete_count = data.deleted_count
        if delete_count == 0:
            log.info("Deleted data: %s", data)
            return data

        if (
            delete_count
            and self._current_timer
            and self._current_timer["_id"] == kw["_id"]
            and self.timer_task
        ):
            log.info("Rerunning timer task")
            self.timer_task.cancel()
            self.timer_task = self.loop.create_task(self.dispatch_timers())
        return data
