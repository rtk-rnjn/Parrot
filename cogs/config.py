from discord.ext import commands
import discord, typing, aiohttp
from discord import Webhook, AsyncWebhookAdapter
from core.cog import Cog
from core.bot import Parrot
from core.ctx import Context

from database.server_config import collection as csc, guild_join, guild_update
from database.global_chat import collection as cgc, gchat_on_join, gchat_update

class BotConfig(Cog, name="config"):
		def __init__(self, bot: Parrot):
				self.bot = bot
		
		@commands.group()
		@commands.guild_only()
		@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
		@commands.bot_has_permissions(embed_links=True)
		async def config(self, ctx: Context):
				"""
				To config the bot, mod role, prefix, or you can disable the commands and cogs.

				Syntax:
				`Config [Setting:Text] [Arguments:Text]`

				Permission:
				Need Embed Links permission for the bot and Administration permission for the user 
				"""
				'''if args.lower() == 'show':
					if not csc.find_one({'_id': ctx.guild.id}): await guild_join(ctx.guild.id)
					data = csc.find_one({'_id': ctx.guild.id})
					prefix = data['prefix']
					# disabled_cmds = data['disabled_cmds'] 

					disabled_cogs = data['disabled_cogs'] # simply a list of array
					try: channel = ctx.guild.get_channel(data['action_log'])
					except Exception: channel = "NA" 
					
					try: mute = ctx.guild.get_role(data['mute_role']).mention
					except Exception: mute = "NA"
					
					try: mod = ctx.guild.get_role(data['mod_role'])
					except Exception: mod = "NA"

					embed = discord.Embed(description=f"This server current Bot settings are:-\n"
																						f"> Prefix:\n`{prefix}`, `@Parrot#9209`\n"
																						f"> Mute Role:\n{mute}\n\n"
																						f"> Mod Role:\n{mod}\n\n"
																						f"> Action Log:\n{channel}\n\n"
																						f"> Disabled Cogs:\n{', '.join(disabled_cogs) if disabled_cogs else 'NA'}")
					
					await ctx.send(embed=embed)
				else: pass'''
				pass
		
		@config.command()
		@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
		async def botprefix(self, ctx: Context, *, arg:commands.clean_content):
				"""
				To set the prefix of the bot. Whatever prefix you passed, will be case sensitive. It is advised to keep a symbol as a prefix.

				Syntax:
				`Config {prefix} <Argument:Text>` 
				
				Permission:
				Need Administration permission for the user 
				"""
				if not csc.find_one({'_id': ctx.guild.id}): await guild_join(ctx.guild.id)
				if len(arg) > 6:
						return await ctx.reply(f"{ctx.author.mention} length of prefix can not be more than 6 characters.")
				post = {'prefix': arg}
				await guild_update(ctx.guild.id, post)

				await ctx.reply(f"{ctx.author.mention} success! Prefix for **{ctx.guild.name}** is **{arg}**.")
		
		@config.command(aliases=['mute-role'])
		@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
		async def mute_role(self, ctx: Context, *, role:discord.Role):
				"""
				To set the mute role of the server. By default role with name `Muted` is consider as mute role.

				Syntax:
				`Config {mute-role} <Role:Mention/ID>`
				
				Permission:
				Need Administration permission for the user 
				"""
				if not csc.find_one({'_id': ctx.guild.id}): await guild_join(ctx.guild.id)
				post = {'mute_role': role.id}
				await guild_update(ctx.guild.id, post)

				await ctx.reply(f"{ctx.author.mention} success! Mute role for **{ctx.guild.name}** is **{role.name} ({role.id})**")

		@config.command(aliases=['mod-role'])
		@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
		async def mod_role(self, ctx: Context, *, role:discord.Role):
				"""
				To set mod role of the server. People with mod role can accesss the Moderation power of Parrot. By default the mod functionality works on the basis of permission

				Syntax:
				`Config {mod-role} <Role:Mention/ID> 
				
				Permission:
				Need Administration permission for the user 
				"""
				if not csc.find_one({'_id': ctx.guild.id}): await guild_join(ctx.guild.id)

				post = {'mod_role': role.id}
				await guild_update(ctx.guild.id, post)

				await ctx.reply(f"{ctx.author.mention} success! Mod role for **{ctx.guild.name}** is **{role.name} ({role.id})**")

		@config.command(aliases=['action-log'])
		@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
		async def actionlog(self, ctx: Context, *, channel:discord.TextChannel=None):
				"""
				To set the action log, basically the mod log.

				Syntax:
				`Config {actionlog} <Channel:Mention/ID>`
				
				Permission:
				Need Administration permission for the user 
				"""
				channel = channel or ctx.channel
				if not csc.find_one({'_id': ctx.guild.id}): await guild_join(ctx.guild.id)

				post = {'action_log': channel.id}
				await guild_update(ctx.guild.id, post)

				await ctx.reply(f"{ctx.author.mention} success! Action log for **{ctx.guild.name}** is **{channel.name} ({channel.id})**")

	#	@config.command(aliases=['disable-cog'])
	#	@commands.check_any(commands.has_permission(administrator=True), commands.is_owner())
	#	async def disable_cog(self, ctx: Context, cog:str, channel:discord.TextChannel=None):
	#			"""
	#			To disable the cog; cog means category, as every command is being listed in some category.
	#			
	#			Syntax:
	#			`Config {disable-cog} <Cog:Text> [Channel:Mention/ID]`
	#
	#			Permission:
	#			Need Administration permission for the user
	#
	#			Note: If no channel is specified. Then it will consider the current woking channel.
	#			"""
	#			if not csc.find_one({'_id': ctx.guild.id}): await guild_join(ctx.guild.id)
	#
	#			channel = channel or ctx.channel 
	#			if not cog in self.bot.cogs: return await ctx.reply(f"{ctx.author.mention} Invalid Cog name.")
	#	
	#			# post = {'disabled_cogs': []}

		@config.command(aliases=['g-setup'])
		@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
		@commands.bot_has_permissions(manage_channels=True, manage_webhooks=True, manage_roles=True)
		async def gchatsetup(self, ctx: Context, setting: str = None, *, role: typing.Union[discord.Role]):
				"""
				This command will connect your server with other servers which then connected to #global-chat must try this once
				
				Syntax:
				`Config {gchatsetup} [Setting:Text] [Role:Mention/ID]`

				Cooldown of 60 seconds after one time use, per guild.

				Permissions:
				Need Manage Channels, Manage Webhook, and Manage Roles permissions for the bot, and Manage Server permission for the user.
				"""
				if not cgc.find_one({'_id': ctx.guild.id}): await gchat_on_join(ctx.guild.id)

				if not setting:
						guild = ctx.guild
						overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True), guild.me: discord.PermissionOverwrite(read_messages=True,send_messages=True, read_message_history=True)}
						channel = await guild.create_text_channel('global-chat', topic="Hmm. Please be calm, be very calm", overwrites=overwrites)

						webhook = await channel.create_webhook(name="GlobalChat", avatar=await ctx.me.avatar_url.read())

						post = {'chanel_id': channel.id, 'webhook': webhook.url}

						await gchat_update(guild.id, post)
						await ctx.send(f"{channel.mention} created successfully.")
						return

				if (setting.lower() == 'ignore-role' or 'ignore_role') and (role is not None):
						post = {'ignore-role': role.id}
						await gchat_update(ctx.guild.id, post)
						await ctx.reply(f"{ctx.author.mention} success! **{role.name} ({role.id})** will be ignored from global chat!")
		
	
		@commands.command(hidden=True)
		@commands.is_owner()
		async def broadcast(self, ctx: Context, *, message: str):
				"""
				To broadcast all over the global channel. Only for owners.

				Syntax:
				`Broadcast <Message:Text>`
				"""
				data = cgc.find({})

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
		bot.add_cog(BotConfig(bot))