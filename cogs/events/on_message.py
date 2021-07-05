from datetime import datetime
from core.bot import Parrot
from core.ctx import Context
from core.cog import Cog

async def spam_filter(msg1, msg2, msg3, msg4, msg5):
		if msg1.author == msg2.author == msg3.author == msg4.author == msg5.author:
				_1 = (msg1.created_at - msg2.created_at).seconds
				_2 = (msg2.created_at - msg3.created_at).seconds
				_3 = (msg3.created_at - msg4.created_at).seconds
				_4 = (msg4.created_at - msg5.created_at).seconds
				_5 = (datetime.utcnow() - msg1.created_at).seconds
				avg = (_1 + _2 + _3 + _4 + _5) / 5

				if avg >= 1.5: return True


class Msg(Cog):
		"""No commands in this category, you can actually send message to owner directly by DMing the bot. Mainly for complains"""
		def __init__(self, bot: Parrot):
				self.bot = bot

		@Cog.listener()
		async def on_message(self, message):
				if message.channel.id == 796645162860150784:
						messages = await message.channel.history(limit=5).flatten()
						if await spam_filter(messages[0], messages[1], messages[2],
																messages[3], messages[4]):
								await message.channel.send(
										f"{message.author.mention} you done? You send **5** message in less than **1.5s**. Slowdown",
										delete_after=5)


def setup(bot):
		bot.add_cog(Msg(bot))
