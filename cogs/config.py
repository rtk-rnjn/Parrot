from discord.ext import commands

from core.cog import Cog
from core.bot import Parrot
from core.ctx import Context

class BotConfig(Cog, name="config"):
		def __init__(self, bot: Parrot):
				self.bot = bot
		
		@commands.command(name='config')
		@commands.check_any(commands.has_permission(administrator=True), commands.is_owner())
		async def config_bot(self, ctx: Context, setting: str, *, args:str):
			pass