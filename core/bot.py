from discord.ext import commands 
import discord, traceback
from utilities.config import EXTENSIONS, OWNER_IDS, PREFIX, CASE_INSENSITIVE, STRIP_AFTER_PREFIX

class Parrot(commands.AutoShardedBot):
		"""A custom way to organise a commands.AutoSharedBot."""
		
		def __init__(self, *args, **kwargs):
				super().__init__(
					command_prefix=commands.when_mentioned_or(PREFIX),
					case_insensitive=CASE_INSENSITIVE,
					intents=discord.Intents.all(),
					strip_after_prefix=STRIP_AFTER_PREFIX,
					owner_ids=OWNER_IDS,
					member_cache_flags=discord.MemberCacheFlags.from_intents(discord.Intents.all()),
					shard_count=3,
					**kwargs
				)
				for ext in EXTENSIONS:
						try:
								self.load_extension(ext)
								print(f"[EXTENSION] {ext} was loaded successfully!")
						except Exception as e:
								tb = traceback.format_exception(type(e), e, e.__traceback__)
								tbe = "".join(tb) + ""
								print(f"[WARNING] Could not load extension {ext}: {tbe}")

		async def on_ready(self):
				print(f"[Parrot] Logged in as {self.user.name}#{self.user.discriminator} ({self.user.id})")
				print(f"[Parrot] Currently in {len(self.guilds)} Guilds")
				print(f"[Parrot] Connected to {len(self.users)} Users")
				print(f"[Parrot] Spawned {len(self.shards)} Shards")
