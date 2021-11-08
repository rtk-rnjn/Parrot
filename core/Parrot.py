from __future__ import annotations

import jishaku
import os, typing
from async_property import async_property

import datetime, re
import json, asyncio
import copy
import logging
import traceback
import aiohttp
import sys
from collections import Counter, deque, defaultdict

from discord.ext import commands
import discord, traceback, asyncio, topgg

from utilities.config import EXTENSIONS, OWNER_IDS, CASE_INSENSITIVE, STRIP_AFTER_PREFIX, TOKEN
from utilities.database import parrot_db, cluster
from utilities.checks import _can_run

from time import time

from .Context import Context

collection = parrot_db['server_config']
collection_ban = parrot_db['banned_users']

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

intents = discord.Intents.default()
intents.members = True

dbl_token = os.environ['TOPGG']

CHANGE_LOG_ID = 796932292458315776
SUPPORT_SERVER_ID = 741614680652644382

class Parrot(commands.AutoShardedBot):
    """A custom way to organise a commands.AutoSharedBot."""
    def __init__(self, *args, **kwargs):
        super().__init__(
            command_prefix=self.get_prefix,
            case_insensitive=CASE_INSENSITIVE,
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.listening,
                                      name="@Parrot config gsetup"),
            status=discord.Status.dnd,
            strip_after_prefix=STRIP_AFTER_PREFIX,
            owner_ids=OWNER_IDS,
            allowed_mentions=discord.AllowedMentions(everyone=False,
                                                     replied_user=False),
            member_cache_flags=discord.MemberCacheFlags.from_intents(
                discord.Intents.all()),
            shard_count=3,
            **kwargs)
        self._seen_messages = 0
        self._change_log = None
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()
        self.color = 0x87CEEB
        self.topggpy = topgg.DBLClient(self,
                                       dbl_token,
                                       autopost=True,
                                       post_shard_count=True)
        self.persistent_views_added = False
        self.spam_control = commands.CooldownMapping.from_cooldown(10, 12.0, commands.BucketType.user)
        self._auto_spam_count = Counter()
        self.resumes = defaultdict(list)
        self.identifies = defaultdict(list)
        self._prev_events = deque(maxlen=10)

        self.session = aiohttp.ClientSession(loop=self.loop)
        for ext in EXTENSIONS:
            try:
                self.load_extension(ext)
                print(f"[EXTENSION] {ext} was loaded successfully!")
            except Exception as e:
                tb = traceback.format_exception(type(e), e, e.__traceback__)
                tbe = "".join(tb) + ""
                print(f"[WARNING] Could not load extension {ext}: {tbe}")

    @property
    def server(self) -> typing.Optional[discord.Guild]:
        return self.get_guild(SUPPORT_SERVER_ID)  # Main server

    @property
    def invite(self) -> str:
        return discord.utils.oauth_url(
            self.user.id,
            permissions=discord.Permissions.all_channel(),
            redirect_uri='https://discord.gg/NEyJxM7G7f')

    @property
    def github(self) -> str:
        return "https://github.com/ritik0ranjan/Parrot"

    @property
    def support_server(self) -> str:
        return "https://discord.gg/NEyJxM7G7f"

    @async_property
    async def change_log(self) -> typing.Optional[discord.Message]:
        """For the command `announcement` to let the users know the most recent change"""
        if self._change_log is None:
            self._change_log = await self.get_channel(
                CHANGE_LOG_ID).history(limit=1).flatten()

        return self._change_log[0]

    @async_property
    async def db_latency(self) -> int:
        ini = time()
        data = await collection.find_one({'_id': 741614680652644382})
        fin = time()
        return fin - ini

    def _clear_gateway_data(self):
        one_week_ago = discord.utils.utcnow() - datetime.timedelta(days=7)
        for shard_id, dates in self.identifies.items():
            to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
            for index in reversed(to_remove):
                del dates[index]

        for shard_id, dates in self.resumes.items():
            to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
            for index in reversed(to_remove):
                del dates[index]

    async def on_socket_raw_receive(self, msg):
        self._prev_events.append(msg)

    async def before_identify_hook(self, shard_id, *, initial):
        self._clear_gateway_data()
        self.identifies[shard_id].append(discord.utils.utcnow())
        await super().before_identify_hook(shard_id, initial=initial)

    async def db(self, db_name: str):
        return cluster[db_name]

    async def on_dbl_vote(self, data):
        """An event that is called whenever someone votes for the bot on Top.gg."""
        if data["type"] == "test":
            # this is roughly equivalent to
            # `return await on_dbl_test(data)` in this case
            return self.dispatch("dbl_test", data)

        print(f"Received a vote:\n{data}")

    def run(self):
        """"To run connect and login into discord"""
        super().run(TOKEN, reconnect=True)

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = discord.utils.utcnow()

        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_connect(self) -> None:
        print(
            f"[Parrot] Logged in as {self.user}"
        )
        return

    async def on_disconnect(self) -> None:
        print(
            f"[Parrot] {self.user} disconnect from discord"
        )
        return
    
    async def on_shard_resumed(self, shard_id):
        print(f'Shard ID {shard_id} has resumed...')
        self.resumes[shard_id].append(discord.utils.utcnow())

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is None:
            # ignore if no command found
            return

        if ctx.command is not None:
            _true = await _can_run(ctx)
            if await collection_ban.find_one({'_id': message.author.id}):
                # if user is banned
                return
            if not _true: 
                await ctx.reply(f'{ctx.author.mention} `{ctx.command.qualified_name}` is being disabled in **{ctx.channel.name}** by the staff!', delete_after=10.0)
                return
    
        await self.invoke(ctx)

    async def on_message(self, message: discord.Message):
        self._seen_messages += 1

        if not message.guild:
            # to prevent the usage of command in DMs
            return

        await self.process_commands(message)

    async def resolve_member_ids(self, guild: discord.Guild, member_ids: list):
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
        elif total_need_resolution <= 100:
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

    async def get_or_fetch_member(self, guild, member_id):
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

    async def get_prefix(self, message: discord.Message) -> str:
        """Dynamic prefixing"""
        data = await collection.find_one({"_id": message.guild.id})
        if data := await collection.find_one({"_id": message.guild.id}):
            prefix = data['prefix']
        else:
            prefix = '$' # default prefix
            await collection.insert_one({
                '_id': message.guild.id,
                'prefix': '$',     # to make entry
                'mod_role': None,  # in database
                'action_log': None,
                'mute_role': None
            })
        return commands.when_mentioned_or(prefix)(self, message)
    
    async def send_raw(self, channel_id: int, content: str, **kwargs):
        await self.http.send_message(channel_id, content, **kwargs)
