import jishaku
import os

from discord.ext import commands
import discord, traceback
from utilities.config import EXTENSIONS, OWNER_IDS, CASE_INSENSITIVE, STRIP_AFTER_PREFIX, TOKEN
from utilities.database import parrot_db

collection = parrot_db['server_config']

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"


class Parrot(commands.AutoShardedBot):
    """A custom way to organise a commands.AutoSharedBot."""
    def __init__(self, *args, **kwargs):
        self._BotBase__cogs = commands.core._CaseInsensitiveDict() # to make cog case insensitive
        super().__init__(
            command_prefix=self.get_prefix,
            case_insensitive=CASE_INSENSITIVE,
            intents=discord.Intents.all(),
            activity=discord.Activity(type=discord.ActivityType.listening,
                                      name="my BOSS's Wife"),
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
        for ext in EXTENSIONS:
            try:
                self.load_extension(ext)
                print(f"[EXTENSION] {ext} was loaded successfully!")
            except Exception as e:
                tb = traceback.format_exception(type(e), e, e.__traceback__)
                tbe = "".join(tb) + ""
                print(f"[WARNING] Could not load extension {ext}: {tbe}")

    def run(self):
        super().run(TOKEN, reconnect=True)

    async def on_ready(self):
        print(
            f"[Parrot] {self.user.name}#{self.user.discriminator} ready to take commands"
        )
        print(f"[Parrot] Currently in {len(self.guilds)} Guilds")
        print(f"[Parrot] Connected to {len(self.users)} Users")
        print(f"[Parrot] Spawned {len(self.shards)} Shards")

    async def on_connect(self):
        print(
            f"[Parrot] Logged in as {self.user.name}#{self.user.discriminator}"
        )

    async def on_disconnect(self):
        print(
            f"[PARROT] {self.user.name}#{self.user.discriminator} disconnect from discord"
        )

    async def on_resumed(self):
        print(f"[PARROT] resumed {self.user.name}#{self.user.discriminator}")

    async def get_prefix(self, message: discord.Message) -> str:
        if not message.guild: return ''
        if message.author.id == 741614468546560092: return ('', '$')
        else:
            if not collection.find_one({"_id": message.guild.id}):
                collection.insert_one({
                    '_id': message.guild.id,
                    'prefix': '$',
                    'mod_role': None,
                    'action_log': None,
                    'mute_role': None
                })
            data = collection.find_one({"_id": message.guild.id})
            prefix = data['prefix']
        return commands.when_mentioned_or(prefix)(self, message)
