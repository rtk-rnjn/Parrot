import jishaku
import os

from discord.ext import commands
import discord, traceback
from utilities.config import EXTENSIONS, OWNER_IDS, CASE_INSENSITIVE, STRIP_AFTER_PREFIX
from database.server_config import collection, guild_join


os.environ["JISHAKU_HIDE"] = "True"
# os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
# os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

class Parrot(commands.AutoShardedBot):
		"""A custom way to organise a commands.AutoSharedBot."""
		def __init__(self, *args, **kwargs):
				super().__init__(
						command_prefix=self.get_prefix,
						case_insensitive=CASE_INSENSITIVE,
						intents=discord.Intents.all(),
						activity=discord.Activity(type=discord.ActivityType.listening, name="$help"),
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

		async def on_ready(self):
				print(
						f"[Parrot] Logged in as {self.user.name}#{self.user.discriminator} ({self.user.id})"
				)
				print(f"[Parrot] Currently in {len(self.guilds)} Guilds")
				print(f"[Parrot] Connected to {len(self.users)} Users")
				print(f"[Parrot] Spawned {len(self.shards)} Shards")

		async def get_prefix(self, message: discord.Message) -> str:
				if not message.guild: prefix = "$"
				else:
						if not collection.find_one({"_id": message.guild.id}):
								await guild_join(message.guild.id)
						data = collection.find_one({"_id": message.guild.id})
						prefix = data['prefix'] 
				return (prefix, '<@!800780974274248764>', #Commands mention, i dont know
								'<@800780974274248764>', '<@!800780974274248764> ',	# for some reason, commands.when_mentioned_or() is not working
								'<@800780974274248764> ')
