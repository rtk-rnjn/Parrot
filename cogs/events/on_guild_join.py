from core.cog import Cog 
from core.bot import Parrot 
import json

from database.global_chat import gchat_on_join
from database.telephone import telephone_on_join
from database.ticket import ticket_on_join

class OnGuildJoin(Cog):

	def __init__(self, bot: Parrot):
		self.bot = bot

	@Cog.listener()
	async def on_guild_join(self, guild):
		await gchat_on_join(guild.id)
		await telephone_on_join(guild.id)
		await ticket_on_join(guild.id)

		for channel in guild.text_channels:
			if channel.permission_for(guild.me).send_messages:
				channel.send("Thank you for adding me to this server! Default prefix are `$` and `@Parrot` (Mention)! Consider connecting to global chat, by [p]setupgchat\nFor any feedback consider DMing the bot!")
				break
		
def setup(bot):
	bot.add_cog(OnGuildJoin(bot))