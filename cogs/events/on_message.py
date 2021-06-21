from datetime import datetime

from core.cog import Cog
from core.bot import Parrot

class SupportMail(Cog):
	"""No commands in this category, you can actually send message to owner directly by DMing the bot. Mainly for complains"""

	def __init__(self, bot: Parrot):
		self.bot = bot

	@Cog.listener()
	async def on_message(self, message):
		if message.author.bot: return
		
		empty_array = []
		modmail_channel = self.bot.get_channel(837637146453868554)

		if str(message.channel.type) == "private":
			if message.attachments != empty_array:
				files = message.attachments
				await modmail_channel.send(f"> **Message from {message.author.name}#{message.author.discriminator}**")

				for file in files:
					await modmail_channel.send(file.url)
			else:
				await modmail_channel.send(f"> **Message from {message.author.name}#{message.author.discriminator}**\n```\n{message.content}```\n\n> ID: {message.author.id}\n> AT: {datetime.utcnow()}")

		elif message.channel == modmail_channel and message.content.startswith("<"):
			member_object = message.mentions[0]
			if message.attachments != empty_array:
				files = message.attachments
				await member_object.send(f"> **Message from {message.author.name}#{message.author.discriminator}**")

				for file in files:
					await member_object.send(file.url)
			else:
				index = message.content.index(" ")
				string = message.content
				mod_message = string[index:]
				await member_object.send(f"> **Message from {message.author.name}#{message.author.discriminator}**\n```\n{mod_message}```\n\n> ID: {message.author.id}\n> AT: {datetime.utcnow()}")
		
		#if message.channel.id == 833255204430020618:
		#	
		#	msg = message.content
		#	key = 'MOvDyLB35FoAktTcorVUeCTS5'  --EXPIRED--
		#	if msg.startswith("$") or msg.startswith("<") or msg.startswith("!") or msg.startswith("-") or msg.startswith(";;") or msg.startswith("owo") or msg.startswith(","): return
		#	params = {
		#		"message": msg,
		#		"key": key
		#	}
		#	req = requests.get(url="https://some-random-api.ml/chatbot", params=params)
		#	if req.status_code != 200: return
		#	res = req.json()

		#	try: await self.bot.get_channel(833255204430020618).send(f"{message.author.mention} {res['response']}")
		#	except: pass


def setup(bot):
	bot.add_cog(SupportMail(bot)) 
