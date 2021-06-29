from discord.ext import commands
import discord 

from core.cog import Cog
from core.bot import Parrot
from core.ctx import Context

from database.server_config import collection, guild_join

class BotConfig(Cog, name="config"):
		def __init__(self, bot: Parrot):
				self.bot = bot
		
		@commands.group()
		@commands.check_any(commands.has_permission(administrator=True), commands.is_owner())
		async def config(self, ctx: Context, ):
				"""
				To config the bot, mod role, prefix, or you can disable the commands and cogs.

				Syntax:
				`Config [Setting:Text] [Arguments:Text]`

				Permission:
				Need Administration permission for the user 
				"""
				if not collection.find_one({'_id': ctx.guild.id}): await guild_join(ctx.guild.id)
				data = collection.find_one({'_id': ctx.guild.id})

				prefix = data['prefix']
				disabled_cmds = data['disabled_cmds']
				disabled_cogs = data['disabled_cogs']
				
				try: channel = ctx.guild.get_channel(data['action_log'])
				except Exception: channel = "NA" 
				
				try: mute = ctx.guild.get_role(data['mute_role']).mention
				except Exception: mute = "NA"
				
				try: mod = ctx.guild.get_role(data['mod_role'])
				except Exception: mod = "NA"

				embed = discord.Embed(description=f"This server current Bot settings are:-\n"
											 										f"> Prefix:\n{prefix}, @Parrot"
											 										f"> Mute Role:\n{mute}\n"
																					f"> Mod Role:\n{mod}\n"
																					f"> Action Log:\n{channel}\n")