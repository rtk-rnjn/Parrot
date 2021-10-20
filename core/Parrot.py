from __future__ import annotations

import jishaku
import os, typing
from async_property import async_property

from discord.ext import commands
import discord, traceback, asyncio, topgg

from utilities.config import EXTENSIONS, OWNER_IDS, CASE_INSENSITIVE, STRIP_AFTER_PREFIX, TOKEN
from utilities.database import parrot_db, cluster

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
        # self.persistent_views_added = False

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
        print(
            f"[Parrot] {self.user} ready to take commands"
        )
        print(f"[Parrot] Currently in {len(self.guilds)} Guilds")
        print(f"[Parrot] Connected to {len(self.users)} Users")

    async def on_connect(self) -> None:
        print(
            f"[Parrot] Logged in as {self.user.name}#{self.user.discriminator}"
        )
        return

    async def on_disconnect(self) -> None:
        print(
            f"[Parrot] {self.user.name}#{self.user.discriminator} disconnect from discord"
        )
        return

    async def on_resumed(self) -> None:
        print(f"[Parrot] resumed {self.user.name}#{self.user.discriminator}")
        return

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is None:
            # ignore if no command found
            return

        await self.invoke(ctx)

    async def on_message(self, message: discord.Message):
        self._seen_messages += 1

        if not message.guild:
            # to prevent the usage of command in DMs
            return

        await self.process_commands(message)

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
