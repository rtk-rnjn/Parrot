from discord.ext import commands 
import json
class OnGuildJoin(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_guild_join(self, guild):
		with open("data.json") as f:
			data = json.load(f)

		data['guild'].append(
			{
				"id": guild.id,
				"ticket-counter": 0,
				"valid-roles": [],
				"pinged-roles": [],
				"ticket-channel-ids": [],
				"verified-roles": []
			}
		)

		with open("data.json", "w+") as f:
			json.dump(data, f)

		for channel in guild.text_channels:
			if channel.permission_for(guild.me).send_messages:
				channel.send("Thank you for adding me to this server! Default prefix are `$` and `@Parrot` (Mention)! Consider connecting to global chat, by [p]setupgchat\nFor any feedback consider DMing the bot!")
				break
		
def setup(bot):
	bot.add_cog(OnGuildJoin(bot))