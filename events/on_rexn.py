from core.cog import Cog


class OnReaction(Cog):
		def __init__(self, bot):
				self.bot = bot

		@Cog.listener()
		async def on_reaction_add(self, reaction, user):
				pass

		@Cog.listener()
		async def on_raw_reaction_add(self, payload):
				pass

		@Cog.listener()
		async def on_reaction_remove(self, reaction, user):
				pass

		@Cog.listener()
		async def on_raw_reaction_remove(self, payload):
				pass

		@Cog.listener()
		async def on_reaction_clear(self, message, reactions):
				pass

		@Cog.listener()
		async def on_raw_reaction_clear(self, payload):
				pass

		@Cog.listener()
		async def on_reaction_clear_emoji(self, reaction):
				pass

		@Cog.listener()
		async def on_raw_reaction_clear_emoji(self, payload):
				pass


def setup(bot):
		bot.add_cog(OnReaction(bot))
