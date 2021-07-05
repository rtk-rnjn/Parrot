# from discord.ext import tasks 
# todo: tasks system

from core import Cog, Parrot, Context

from database.cmd_count import collection, if_not_exists, increment

class CommandErrorHandler(Cog):
		"""This category is of no use for you, ignore it."""
		def __init__(self, bot: Parrot):
				self.bot = bot
		
		@Cog.listener()
		async def on_command_completion(self, ctx: Context):
				"""This event will be triggered when the command is being completed; triggered by [discord.User]!"""
				if ctx.author.bot: return

				if not collection.find_one({'_id': ctx.command.name}): 
					return await if_not_exists(ctx.command.name, 1)
				await increment(ctx.command.name)


def setup(bot):
		bot.add_cog(CommandErrorHandler(bot))
