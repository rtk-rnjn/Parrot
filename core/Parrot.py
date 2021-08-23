
from __future__ import annotations
import jishaku
import os, typing
from async_property import async_property
from discord.ext import commands
import discord, traceback
from utilities.config import EXTENSIONS, OWNER_IDS, CASE_INSENSITIVE, STRIP_AFTER_PREFIX, TOKEN
from utilities.database import parrot_db, cluster
from time import time

collection = parrot_db['server_config']

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"


class Parrot(commands.AutoShardedBot):
    """A custom way to organise a commands.AutoSharedBot."""
    def __init__(self, *args, **kwargs):
        super().__init__(
            command_prefix=self.get_prefix,
            case_insensitive=CASE_INSENSITIVE,
            intents=discord.Intents.all(),
            activity=discord.Activity(type=discord.ActivityType.listening,
                                      name="$help"),
            status=discord.Status.dnd,
            strip_after_prefix=STRIP_AFTER_PREFIX,
            owner_ids=OWNER_IDS,
            allowed_mentions=discord.AllowedMentions(everyone=False,
                                                     roles=True,
                                                     replied_user=True,
                                                     users=True),
            member_cache_flags=discord.MemberCacheFlags.from_intents(
                discord.Intents.all()),
            shard_count=3,
            **kwargs)  
        self._BotBase__cogs = commands.core._CaseInsensitiveDict() # to make cog case insensitive
        self.color = 0x87CEEB
        
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
        return self.get_guild() # Main server
    
    @async_property
    async def db_latency(self) -> int:
        ini = time()
        data = collection.find({})
        fin = time()
        return fin - ini
    
    async def db(self, db_name: str):
        return cluster[db_name]
        
    def run(self):
        super().run(TOKEN, reconnect=True)

    async def on_ready(self):
        print(
            f"[Parrot] {self.user.name}#{self.user.discriminator} ready to take commands"
        )
        print(f"[Parrot] Currently in {len(self.guilds)} Guilds")
        print(f"[Parrot] Connected to {len(self.users)} Users")
        print(f"[Parrot] Spawned {len(self.shards)} Shards")

    async def on_connect(self) -> None:
        print(
            f"[Parrot] Logged in as {self.user.name}#{self.user.discriminator}"
        )
        return

    async def on_disconnect(self) -> None:
        print(
            f"[PARROT] {self.user.name}#{self.user.discriminator} disconnect from discord"
        )
        return

    async def on_resumed(self) -> None:
        print(f"[PARROT] resumed {self.user.name}#{self.user.discriminator}")
        return

    async def get_prefix(self, message: discord.Message) -> str:
        if not message.guild: return ''
        else:
            data = await collection.find_one({"_id": message.guild.id})
            if not data:
                await collection.insert_one({
                    '_id': message.guild.id,
                    'prefix': '$',
                    'mod_role': None,
                    'action_log': None,
                    'mute_role': None
                })
                return commands.when_mentioned_or('$')(self, message)
            prefix = data['prefix']
        return commands.when_mentioned_or(prefix)(self, message)
