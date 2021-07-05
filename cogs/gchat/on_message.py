import aiohttp, re, asyncio

from discord import Webhook, AsyncWebhookAdapter

from database.global_chat import collection

from core import Parrot, Cog

class MessageEvents(Cog, name="Global Chat"):
		def __init__(self, bot: Parrot):
				self.bot = bot

		@Cog.listener()
		async def on_message(self, message):
				if not message.guild or message.author.bot:
						return
				
				channel = collection.find_one({'_id': message.guild.id, 'channel_id': message.channel.id})
				
				if not channel: return

				guild = collection.find_one({'_id': message.guild.id})
				data = collection.find({})

				role = message.guild.get_role(guild['ignore-role'])
				if role:
						if role in message.author.roles:
								return

				if message.content.startswith("$"):
						return

				urls = re.findall(
						'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content.lower())
				if urls:
						try:
								return await message.delete()
						except:
								return await message.channel.send(f"{message.author.mention} | URLs aren't allowed.")

				if "discord.gg" in message.content.lower():
						try:
								return await message.delete()
						except:
								return await message.channel.send(f"{message.author.mention} | Advertisements aren't allowed.")
						
				if "discord.com" in message.content.lower():
						try:
								return await message.delete()
						except:
								return await message.channel.send(f"{message.author.mention} | Advertisements aren't allowed.")

				try:
						await asyncio.sleep(0.1)
						await message.delete()
				except:
						return await message.channel.send("Bot requires **Manage Messages** permission(s) to function properly.")

				
				for webhook in data:
						hook = webhook['webhook']
						try:
								async def send_webhook():
										async with aiohttp.ClientSession() as session:
												webhook = Webhook.from_url(f"{hook}", adapter=AsyncWebhookAdapter(session))

												await webhook.send(content=message.clean_content, username=message.author.name+"#"+message.author.discriminator, avatar_url=message.author.avatar_url)

								await send_webhook()
						except:
								continue

## todo: make a system to avoid spam, and bad words.

def setup(bot):
	bot.add_cog(MessageEvents(bot))
