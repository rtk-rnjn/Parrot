import discord
import aiohttp
import re
import asyncio, json
from discord.ext import commands
from discord import Webhook, AsyncWebhookAdapter


class MessageEvents(commands.Cog, name="Global Chat"):
		def __init__(self, bot):
				self.bot = bot

		@commands.Cog.listener()
		async def on_message(self, message):
				if not message.guild:
						return
				with open("json/wchat.json") as f:
					channels_ = json.load(f)


				if not message.channel.id in channels_:
						return

				if message.author.bot:
						return

				role = discord.utils.get(message.guild.roles, name="gc-ignore")
				if role != None:
						if role in message.author.roles:
								return

				if message.content.startswith("w!"):
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

				with open("json/webhook.json") as g:
					webhooks = json.load(g)
				for hook in webhooks:
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
