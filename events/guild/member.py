from core.cog import Cog


class Member(Cog):
		def __init__(self, bot):
				self.bot = bot

		@Cog.listener()
		async def on_member_join(self, member):
				pass

		@Cog.listener()
		async def on_member_remove(self, member):
				pass

		@Cog.listener()
		async def on_member_update(self, before, after):
				pass
		
		@Cog.listener()
		async def on_voice_state_update(self, member, before, after):
				pass


def setup(bot):
		bot.add_cog(Member(bot))
