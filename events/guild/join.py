from core.cog import Cog


class GuildJoin(Cog):
		def __init__(self, bot):
				self.bot = bot

		@Cog.listener()
		async def on_guild_join(self, guild):
				pass

		@Cog.listener()
		async def on_guild_remove(self, guild):
				pass

		@Cog.listener()
		async def on_guild_update(self, before, after):
				pass


def setup(bot):
		bot.add_cog(GuildJoin(bot))
