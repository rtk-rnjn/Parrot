from discord.ext import commands
import discord, typing, aiohttp

from discord import Webhook, AsyncWebhookAdapter

from core.cog import Cog
from core.bot import Parrot
from core.ctx import Context

from database.global_chat import gchat_update, collection, gchat_on_join


class WorldChatSetup(Cog, name="global chat"):
		def __init__(self, bot: Parrot):
				self.bot = bot

		@commands.command()
		@commands.has_permissions(manage_guild=True)
		@commands.guild_only()
		@commands.cooldown(1, 60, commands.BucketType.guild)
		@commands.bot_has_permissions(manage_channels=True,
																	manage_webhooks=True,
																	manage_roles=True)
		async def gchatsetup(self,
												ctx: Context,
												setting: str = None,
												*,
												arg: typing.Union[discord.Role]):
				"""
				This command will connect your server with other servers which then connected to #global-chat must try this once
				
				Syntax:
				`Gchatsetup [Setting:Text] [Arguments:Text]`

				Cooldown of 60 seconds after one time use, per guild.

				Permissions:
				Need Manage Channels, Manage Webhook, and Manage Roles permissions for the bot, and Manage Server permission for the user.
				"""
				if not collection.find_one({'_id': ctx.guild.id}):
						await gchat_on_join(ctx.guild.id)

				if not setting:
						guild = ctx.guild
						overwrites = {
								guild.default_role:
								discord.PermissionOverwrite(read_messages=True,
																						send_messages=True,
																						read_message_history=True),
								guild.me:
								discord.PermissionOverwrite(read_messages=True,
																						send_messages=True,
																						read_message_history=True)
						}
						channel = await guild.create_text_channel(
								'global-chat',
								topic="Hmm. Please be calm, be very calm",
								overwrites=overwrites)

						webhook = await channel.create_webhook(name="GlobalChat",
																									avatar=await
																									ctx.me.avatar_url.read())

						post = {'chanel_id': channel.id, 'webhook': webhook.url}

						await gchat_update(guild.id, post)
						await ctx.send(f"{channel.mention} created successfully.")
						return

				if (setting.lower() == 'ignore-role'
								or 'ignore_role') and (arg is not None):
						post = {'ignore-role': arg.id}
						await gchat_update(ctx.guild.id, post)
						await ctx.send(
								f"{ctx.author.mention} *{arg.name} ({arg.id})* will be ignored from global chat!"
						)

		@commands.command()
		@commands.is_owner()
		async def broadcast(self, ctx: Context, *, message: str):
				"""
				To broadcast all over the global channel. Only for owners.

				Syntax:
				`Broadcast <Message:Text>`
				"""
				data = collection.find({})

				for webhooks in data:
						hook = webhooks['webhook']
						try:

								async def send_webhook():
										async with aiohttp.ClientSession() as session:
												webhook = Webhook.from_url(
														f"{hook}", adapter=AsyncWebhookAdapter(session))

												await webhook.send(
														content=f"{message}",
														username="SYSTEM",
														avatar_url=f"{self.bot.guild.me.avatar_url}")

								await send_webhook()
						except:
								continue


def setup(bot):
		bot.add_cog(WorldChatSetup(bot))
