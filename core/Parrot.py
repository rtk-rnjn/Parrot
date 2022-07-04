# -*- coding: utf-8 -*-

from __future__ import annotations
from contextlib import suppress
import io

import os
import sys
import traceback
import types
from typing import (
    Any,
    Awaitable,
    Callable,
    Collection,
    Iterator,
    Mapping,
    Optional,
    Dict,
    Sequence,
    Set,
    Type,
    Union,
    List,
)
import jishaku  # type: ignore  # noqa: F401
import datetime
import asyncio
import re
import discord
import pymongo

from aiohttp import ClientSession  # type: ignore
from collections import Counter, deque, defaultdict

from discord.ext import commands, tasks, ipc
from discord import app_commands

from lru import LRU
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore

try:
    import topgg  # type: ignore

    HAS_TOP_GG = True
except ImportError:
    HAS_TOP_GG = False

from utilities.config import (
    EXTENSIONS,
    OWNER_IDS,
    CASE_INSENSITIVE,
    STRIP_AFTER_PREFIX,
    TOKEN,
    AUTHOR_NAME,
    AUTHOR_DISCRIMINATOR,
    MASTER_OWNER,
    GITHUB,
    SUPPORT_SERVER,
    SUPPORT_SERVER_ID,
)

from utilities.checks import _can_run
from utilities.paste import Client
from utilities.converters import ToAsync

from .__template import post as POST

from time import perf_counter

from .Context import Context
from .Cog import Cog

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

dbl_token = os.environ["TOPGG"]

CHANGE_LOG_ID = 796932292458315776
ERROR_LOG_WEBHOOK_ID = 924513442273054730
STARTUP_LOG_WEBHOOK_ID = 985926507530690640


@ToAsync()
def func(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return function(*args, **kwargs)


__all__ = ("Parrot",)


class Parrot(commands.AutoShardedBot):
    """A custom way to organise a commands.AutoSharedBot."""

    user: Optional[discord.ClientUser]
    help_command: Optional[commands.HelpCommand]

    http_session: ClientSession
    mongo: AsyncIOMotorClient

    cogs: Mapping[str, Cog]
    extensions: Mapping[str, types.ModuleType]

    commands: Set[commands.Command]
    cached_messages: Sequence[discord.Message]
    guilds: List[discord.Guild]

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
            allowed_mentions=discord.AllowedMentions(
                everyone=False, replied_user=False
            ),
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
            shard_count=1,
            max_messages=5000,
            **kwargs,
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()
        self._CogMixin__cogs = commands.core._CaseInsensitiveDict()  # pycord be like
        self._seen_messages = 0
        self._change_log = None

        self._error_log_token = os.environ["CHANNEL_TOKEN2"]
        self._startup_log_token = os.environ["CHANNEL_TOKEN3"]

        self.color = 0x87CEEB
        self.colour = self.color

        self.error_channel: Optional[discord.TextChannel] = None
        self.persistent_views_added: bool = False
        self.spam_control = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.user
        )

        self._was_ready = False

        # Top.gg
        self.HAS_TOP_GG = HAS_TOP_GG
        if self.HAS_TOP_GG:
            self.topgg = None
            self.topgg_webhook = None

        self._auto_spam_count: Counter = Counter()
        self.resumes = defaultdict(list)
        self.identifies = defaultdict(list)
        self._prev_events = deque(maxlen=10)

        self.mystbin = Client()

        # caching variables
        self.server_config: Dict[int, Dict[str, Any]] = LRU(256)  # type: ignore
        self.message_cache: Dict[int, discord.Message] = {}
        self.banned_users: Dict[int, Dict[str, Union[str, bool, int]]] = {}
        self.afk: Set[int] = set()

        self.opts: Dict[str, Any] = {}
        self.func: Callable = func

        # IPC
        self.ipc = ipc.Server(
            bot=self,
            host="localhost",
            port=1730,
            secret_key=os.environ["IPC_KEY"],
        )
        self.ipc_client = ipc.Client(
            host="localhost",
            port=1730,
            secret_key=os.environ["IPC_KEY"],
        )

        # Extensions
        self._successfully_loaded: List[str] = []
        self._failed_to_load: Dict[str, str] = {}

    def __repr__(self):
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
        if self._change_log is None:
            self._change_log = [
                msg async for msg in self.get_channel(CHANGE_LOG_ID).history(limit=1)
            ]

        return self._change_log[0]

    @property
    def author_obj(self) -> Optional[discord.User]:
        return self.get_user(MASTER_OWNER)

    @property
    def author_name(self) -> str:
        return f"{AUTHOR_NAME}#{AUTHOR_DISCRIMINATOR}"  # cant join str and int, ofc

    async def setup_hook(self):
        await self.ipc.start()
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                print(f"[{self.user.name.title()}] {ext} loaded successfully")
                self._successfully_loaded.append(ext)
            except Exception as e:
                self._failed_to_load[ext] = str(e)
                traceback.print_exc()
        if self.HAS_TOP_GG:
            self.topgg = topgg.DBLClient(
                self,
                os.environ["TOPGG"],
                autopost=True,
                post_shard_count=True,
                session=self.http_session,
            )
            self.topgg_webhook = topgg.WebhookManager(self)

    async def db_latency(self) -> float:
        ini = perf_counter()
        await self.mongo.parrot_db.server_config.find_one({})
        fin = perf_counter()
        return fin - ini

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
        webhook = discord.Webhook.from_url(
            f"https://discordapp.com/api/webhooks/{ERROR_LOG_WEBHOOK_ID}/{self._error_log_token}",
            session=self.http_session,
        )
        if webhook is not None:
            try:
                await webhook.send(
                    f"```py\nIgnoring exception in {event}\n{trace}\n``````py\nArgs: {args}\nKwargs: {kwargs}```",
                    avatar_url=self.user.avatar.url,
                    username=self.user.name,
                )
            except discord.HTTPException:
                await webhook.send(
                    file=discord.File(
                        io.BytesIO(
                            f"Ignoring exception in {event}\n{trace}\nArgs: {args}\nKwargs: {kwargs}".encode(
                                "utf-8"
                            )
                        ),
                        filename="traceback.txt",
                    ),
                    avatar_url=self.user.avatar.url,
                    username=self.user.name,
                )

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
            webhook = discord.Webhook.from_url(
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

    def run(self) -> None:
        """To run connect and login into discord"""
        super().run(TOKEN, reconnect=True)

    async def on_ready(self) -> None:
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        if self._was_ready:
            return
        webhook = discord.Webhook.from_url(
            f"https://discordapp.com/api/webhooks/{STARTUP_LOG_WEBHOOK_ID}/{self._startup_log_token}",
            session=self.http_session,
        )
        if webhook is None:
            return
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
            fail_msg = ""
            if self._failed_to_load:
                for k, v in self._failed_to_load.items():
                    fail_msg += (
                        f"> \N{CROSS MARK} Failed to load: `{k}`\nError: `{v}`\n"
                    )
                await webhook.send(
                    f"\N{CROSS MARK} | `{'`, `'.join(self._failed_to_load)}`",
                    avatar_url=self.user.avatar.url,
                    username=self.user.name,
                )
        self._was_ready = True

        print(f"[{self.user.name.title()}] Ready: {self.user} (ID: {self.user.id})")
        print(
            f"[{self.user.name.title()}] Using discord.py of version: {discord.__version__}"
        )

        ls: List[Optional[int]] = await self.mongo.parrot_db.afk.distinct(
            "messageAuthor"
        )
        self.afk = set(ls)
        VCS = await self.mongo.parrot_db.server_config.distinct("vc")
        await self.update_opt_in_out.start()
        for channel in VCS:
            if channel is not None:
                channel = await self.getch(
                    self.get_channel, self.fetch_channel, channel, force_fetch=False
                )
                try:
                    if channel is not None:
                        await channel.connect()
                except (discord.HTTPException, asyncio.TimeoutError):
                    pass
            await asyncio.sleep(0)

    async def on_connect(self) -> None:
        print(f"[{self.user.name.title()}] Logged in")
        return

    async def on_disconnect(self) -> None:
        webhook = discord.Webhook.from_url(
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
        webhook = discord.Webhook.from_url(
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

    async def process_commands(self, message: discord.Message) -> Optional[Context]:

        ctx: Context = await self.get_context(message, cls=Context)

        if ctx.command is None:
            # ignore if no command found
            return

        if str(ctx.channel.type) == "public_thread":
            # no messages in discord.Thread
            return

        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.timestamp()
        retry_after = bucket.update_rate_limit(current)
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
                true = self.banned_users[ctx.author.id].get("command")
                if true:
                    return

            can_run = await _can_run(ctx)
            if not can_run:
                await ctx.reply(
                    f"{ctx.author.mention} `{ctx.command.qualified_name}` is being disabled in "
                    f"**{ctx.channel.mention}** by the staff!",
                    delete_after=10.0,
                )
                return

        if guild := self.opts.get(ctx.guild.id):
            if ctx.author.id in guild.get("command", []):
                return

        await self.invoke(ctx)
        return ctx

    async def on_message(self, message: discord.Message) -> None:
        self._seen_messages += 1

        if message.guild is None or message.author.bot:
            # to prevent the usage of command in DMs
            return

        if re.fullmatch(rf"<@!?{self.user.id}>", message.content):
            return await message.channel.send(
                f"Prefix: `{await self.get_guild_prefixes(message.guild)}`"
            )

        await self.process_commands(message)

    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        if after.guild is None or after.author.bot:
            return

        if before.content != after.content and before.author.id in OWNER_IDS:
            await self.process_commands(after)

    async def resolve_member_ids(
        self, guild: discord.Guild, member_ids: List[int]
    ) -> Iterator[Optional[discord.Member]]:
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
                members = await guild.query_members(
                    limit=1, user_ids=needs_resolution, cache=True
                )
                if members:
                    yield members[0]
        elif total_need_resolution <= 100:
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
        self, guild: discord.Guild, member_id: Union[int, discord.Object]
    ) -> Optional[discord.Member]:
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
        member_id = (
            member_id.id if isinstance(member_id, discord.Object) else int(member_id)
        )

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard = self.get_shard(guild.shard_id)
        if shard.is_ws_ratelimited():
            try:
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

    async def get_or_fetch_message(
        self,
        channel: Union[
            discord.TextChannel, discord.PartialMessageable, discord.Object, int
        ],
        message: int,
        *,
        fetch: bool = True,
        cache: bool = True,
        partial: bool = False,
        force_fetch: bool = False,
    ) -> Union[discord.Message, discord.PartialMessage]:
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
                channel = self.get_channel(channel)
        elif isinstance(channel, discord.Object):
            if force_fetch:
                channel = await self.getch(
                    self.get_channel, self.fetch_channel, channel.id, force_fetch=True
                )
            else:
                channel = self.get_channel(channel.id)

        if force_fetch:
            msg = await channel.fetch_message(message)
            self.message_cache[message] = msg
            return msg

        if cache and (msg := self._connection._get_message(message)):
            self.message_cache[message] = msg
            return msg

        if partial:
            return channel.get_partial_message(message)

        try:
            return self.message_cache[message]
        except KeyError:
            if fetch:
                async for msg in channel.history(
                    limit=1,
                    before=discord.Object(message + 1),
                    after=discord.Object(message - 1),
                ):
                    self.message_cache[message] = msg
                    return msg

    async def get_prefix(
        self, message: discord.Message
    ) -> Union[str, Callable, List[str]]:
        """Dynamic prefixing"""
        try:
            prefix: str = self.server_config[message.guild.id]["prefix"]
        except KeyError:
            if data := await self.mongo.parrot_db.server_config.find_one(
                {"_id": message.guild.id}
            ):
                data: Dict[str, Any] = data
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
            prefix = match.group(1)
        return commands.when_mentioned_or(prefix)(self, message)

    async def get_guild_prefixes(self, guild: discord.Guild) -> Optional[str]:
        try:
            return self.server_config[guild.id]["prefix"]
        except KeyError:
            if data := await self.mongo.parrot_db.server_config.find_one(
                {"_id": guild.id}
            ):
                return data.get("prefix")

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
            if not isinstance(get_function, Callable):
                something = get_function
            if (
                isinstance(fetch_function, Awaitable)
                and something is None
                and force_fetch
            ):
                return await fetch_function
            return something
        with suppress(discord.HTTPException):
            _id = _id.id if isinstance(_id, discord.Object) else int(_id)
            something = get_function(_id)
            if something is None and force_fetch:
                return await fetch_function(_id)
            return something

        return None

    @tasks.loop(count=1)
    async def update_server_config_cache(self, guild_id: int):
        if data := await self.mongo.parrot_db.server_config.find_one({"_id": guild_id}):
            self.server_config[guild_id] = data

    @tasks.loop(count=1)
    async def update_banned_members(self):
        async for data in self.mongo.parrot_db.banned_users.find({}):
            self.banned_users = {}
            self.banned_users[data["_id"]] = data

    @tasks.loop(count=1)
    async def update_opt_in_out(self):
        async for data in self.mongo.extra.misc.find({}):
            data: Dict[str, Any] = data
            _id: int = data.pop("_id")
            self.opts = {}
            self.opts[_id] = data
            await asyncio.sleep(0)
