# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import traceback
from typing import Any, Awaitable, Callable, Optional, Dict, Union, List
import jishaku  # noqa: F401
import datetime
import asyncio
import re
from collections import Counter, deque, defaultdict
import discord
from discord.ext import commands, tasks, pomice

from lru import LRU

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
from .__template import post as POST

from time import time

from .Context import Context

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

dbl_token = os.environ["TOPGG"]

CHANGE_LOG_ID = 796932292458315776


class Parrot(commands.AutoShardedBot):
    """A custom way to organise a commands.AutoSharedBot."""

    def __init__(self, *args, **kwargs) -> None:
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
        self._CogMixin__cogs = commands.core._CaseInsensitiveDict()
        self._seen_messages = 0
        self._change_log = None
        self._error_log_token = os.environ["CHANNEL_TOKEN1"]
        self.color = 0x87CEEB
        self.error_channel = None
        self.persistent_views_added = False
        self.spam_control = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.user
        )
        self._auto_spam_count = Counter()
        self.resumes = defaultdict(list)
        self.identifies = defaultdict(list)
        self._prev_events = deque(maxlen=10)

        self.mystbin = Client()
        self.pomice = pomice.NodePool()

        # caching variables
        self.server_config = LRU(256)
        self.message_cache: Dict[int, Any] = {}
        self.banned_users: Dict[int, Any] = {}
        self.afk = set()

    def __repr__(self):
        return f"<core.{self.user.name}>"

    @property
    def server(self) -> Optional[discord.Guild]:
        return self.get_guild(SUPPORT_SERVER_ID)  # Main server

    @property
    def invite(self) -> str:
        clientID = self.user.id
        perms = discord.Permissions.none()
        perms.read_messages = True
        perms.external_emojis = True
        perms.moderate_members = True
        perms.send_messages = True
        perms.manage_roles = True
        perms.manage_channels = True
        perms.ban_members = True
        perms.kick_members = True
        perms.manage_messages = True
        perms.embed_links = True
        perms.read_message_history = True
        perms.attach_files = True
        perms.add_reactions = True

        url = (
            f"https://discord.com/api/oauth2/authorize?client_id={clientID}&permissions={perms.value}"
            f"&redirect_uri={SUPPORT_SERVER}&scope=bot%20applications.commands"
        )
        return url

    @property
    def github(self) -> str:
        return GITHUB

    @property
    def support_server(self) -> str:
        return SUPPORT_SERVER

    async def change_log(self) -> Optional[discord.Message]:
        """For the command `announcement` to let the users know the most recent change"""
        if self._change_log is None:
            self._change_log = (
                await self.get_channel(CHANGE_LOG_ID).history(limit=1).flatten()
            )

        return self._change_log[0]

    @property
    def author_obj(self) -> Optional[discord.User]:
        return self.get_user(MASTER_OWNER)

    @property
    def author_name(self) -> str:
        return f"{AUTHOR_NAME}#{AUTHOR_DISCRIMINATOR}"  # cant join str and int, ofc

    async def db_latency(self) -> float:
        ini = time()
        await self.mongo.parrot_db.server_config.find_one({})
        fin = time()
        return fin - ini

    async def setup_hook(self):
        await self.start_nodes()
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                print(f"{ext} loaded successfully")
            except Exception as e:
                traceback.print_exc()

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

    async def on_socket_raw_receive(self, msg) -> None:
        self._prev_events.append(msg)

    async def before_identify_hook(self, shard_id, *, initial):
        self._clear_gateway_data()
        self.identifies[shard_id].append(discord.utils.utcnow())
        await super().before_identify_hook(shard_id, initial=initial)

    async def db(self, db_name: str):
        return self.mongo[db_name]

    async def on_autopost_success(self) -> None:
        st = f"[{self.user.name.title()}] Posted server count ({self.topggpy.guild_count}), shard count ({self.shard_count})"
        print(st)

    def run(self) -> None:
        """To run connect and login into discord"""
        super().run(TOKEN, reconnect=True)

    async def start_nodes(self):
        await self.pomice.create_node(
            bot=self.bot, host='127.0.0.1', port='1728', password='MY_SUPER_SECRET_PASSWORD', identifier='MAIN'
        )

    async def on_ready(self) -> None:
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        print(f"[{self.user.name.title()}] Ready: {self.user} (ID: {self.user.id})")
        print(
            f"[{self.user.name.title()}] Using discord.py of version: {discord.__version__ }"
        )

        ls = await self.mongo.parrot_db.afk.distinct("messageAuthor")
        self.afk = set(ls)
        VCS = await self.mongo.parrot_db.server_config.distinct("vc")
        for channel in VCS:
            if channel:
                channel = await self.getch(
                    self.get_channel, self.fetch_channel, channel, force_fetch=False
                )
                try:
                    if channel:
                        await channel.connect()
                except (discord.HTTPException, asyncio.TimeoutError):
                    pass

    async def on_connect(self) -> None:
        print(f"[{self.user.name.title()}] Logged in")
        return

    async def on_disconnect(self) -> None:
        print(f"[{self.user.name.title()}] disconnect from discord")
        return

    async def on_shard_resumed(self, shard_id) -> None:
        print(f"[{self.user.name.title()}] Shard ID {shard_id} has resumed...")
        self.resumes[shard_id].append(discord.utils.utcnow())

    async def process_commands(self, message: discord.Message) -> None:

        ctx: Context = await self.get_context(message, cls=Context)

        if ctx.command is None:
            # ignore if no command found
            return

        if str(ctx.channel.type) == "public_thread":
            # no messages in discord.Thread
            return

        if self.is_ws_ratelimited():
            print(f"Can not process command of message {message}. Ratelimited")
            return
        if not self.is_ready():
            print(f"Can not process command of message {message}. Bot isn't ready yet")
            return

        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.timestamp()
        retry_after = bucket.update_rate_limit(current)
        author_id = message.author.id
        if retry_after:
            self._auto_spam_count[author_id] += 1
            if self._auto_spam_count[author_id] >= 3:
                print(f"Stops the command process of message {message}. Spam")
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
                    print(
                        f"Stops the command process of message {message}. User banned"
                    )
                    return

            _true = await _can_run(ctx)
            if not _true:
                await ctx.reply(
                    f"{ctx.author.mention} `{ctx.command.qualified_name}` is being disabled in "
                    f"**{ctx.channel.mention}** by the staff!",
                    delete_after=10.0,
                )
                return

        await self.invoke(ctx)
        await ctx.release(0)

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

    async def resolve_member_ids(self, guild: discord.Guild, member_ids: list):
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
        self, guild: discord.Guild, member_id: int
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
        channel: discord.TextChannel,
        messageID: int,
        *,
        fetch: bool = True,
        cache: bool = True,
        partial: bool = False,
    ) -> Union[discord.Message, discord.PartialMessage]:
        """|coro|

        Get message from cache. Fetches if not found, and stored in cache

        Parameters
        -----------
        channel: discord.TextChannel
            The channel to look in.
        messageID: int
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
        if cache:
            cached_message = set(self._connection._messages)
            for msg in cached_message:
                # looping the deque is O(n). I am ok with it!
                # this may crash if, the deque mutated.
                if msg.id == messageID:
                    self.message_cache[msg.id] = msg
                    return msg
                await asyncio.sleep(0)

        if partial:
            return channel.get_partial_message(messageID)

        try:
            return self.message_cache[messageID]
        except KeyError:
            if fetch:
                async for msg in channel.history(
                    limit=1,
                    before=discord.Object(messageID + 1),
                    after=discord.Object(messageID - 1),
                ):
                    if msg:
                        self.message_cache[messageID] = msg
                        return msg

    async def get_prefix(self, message: discord.Message) -> Union[str, List[str]]:
        """Dynamic prefixing"""
        try:
            prefix = self.server_config[message.guild.id]["prefix"]
        except KeyError:
            if data := await self.mongo.parrot_db.server_config.find_one(
                {"_id": message.guild.id}
            ):
                prefix = data["prefix"]
                post = data
                self.server_config[message.guild.id] = post
            else:
                POST["_id"] = message.guild.id
                prefix = "$"  # default prefix
                await self.mongo.parrot_db.server_config.insert_one(POST)
                self.server_config[message.guild.id] = POST

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
        _id: Optional[int] = None,
        *,
        force_fetch: bool = True,
    ) -> Any:
        if _id is None:
            if get_function is not None:
                something = get_function
            if isinstance(fetch_function, Awaitable) and something is None:
                return await fetch_function
            return something
        else:
            try:
                something = get_function(_id)
                if something is None and force_fetch:
                    return await fetch_function(_id)
                return something
            except Exception as e:
                return None

    @tasks.loop(count=1)
    async def update_server_config_cache(self, guild_id: int):
        if data := await self.mongo.parrot_db.server_config.find_one({"_id": guild_id}):
            self.server_config[guild_id] = data

    @tasks.loop(count=1)
    async def update_banned_members(self):
        async for data in self.mongo.parrot_db.banned_users.find({}):
            self.banned_users[data["_id"]] = data
