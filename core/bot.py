from discord.ext import commands 
import discord


class Parrot(commands.AutoShardedBot):
		"""A custom way to organise a commands.AutoSharedBot."""
		
		def __init__(self, *args, **kwargs):
				super().__init__(
					command_prefix=commands.when_mentioned_or("$"),
					case_insensitive=True,
					intents=discord.Intents.all(),
					trip_after_prefix=True,
					owner_ids=[741614468546560092, 813647101392846848],
					member_cache_flags=discord.MemberCacheFlags.from_intents(discord.Intents.all()),
					shard_count=3,
					**kwargs
				)