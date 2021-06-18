import discord, datetime, traceback, sys, math
from discord.ext import commands


class CommandErrorHandler(commands.Cog, name="Error Handler"):
	"""This category is of no use for you, ignore it."""

	def __init__(self, bot):
			self.bot = bot

	@commands.Cog.listener()
	async def on_command_error(self, ctx, error):
		# if command has local error handler, return
		if hasattr(ctx.command, 'on_error'): return

		# get the original exception
		error = getattr(error, 'original', error)
	
		if isinstance(error, commands.CommandNotFound): return

		elif isinstance(error, commands.BotMissingPermissions):
			missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_perms]
			if len(missing) > 2:
				fmt = '{}, and {}'.format(", ".join(missing[:-1]), missing[-1])
			else:
				fmt = ' and '.join(missing)
			_message = f'Error: Bot Missing permissions. Please provide the following permission(s) to the bot.```\n{fmt}```'
			return await ctx.send(_message)
			

		elif isinstance(error, commands.DisabledCommand):
			return await ctx.send(f'{ctx.author.mention} this command has been disabled. Consider asking your Server Manager to fix this out!')
			

		elif isinstance(error, commands.CommandOnCooldown):
			return await ctx.reply(f"Error: Command On Cooldown. You are on command cooldown, please retry in **{math.ceil(error.retry_after)}**s.")
			

		elif isinstance(error, commands.MissingPermissions):
			missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_perms]
			if len(missing) > 2:
				fmt = '{}, and {}'.format("**, **".join(missing[:-1]), missing[-1])
			else:
				fmt = ' and '.join(missing)
			_message = 'Error: Missing Permissions. You need the the following permission(s) to use the command.```\n{}```'.format(fmt)
			await ctx.reply(_message)
			return 

		elif isinstance(error, commands.NoPrivateMessage):
			try:
				await ctx.reply('Error: No Private Message. This command cannot be used in direct messages. It can only be used in server')
			except discord.Forbidden:
				pass
			return

		elif isinstance(error, commands.NSFWChannelRequired):
			em = discord.Embed(timestamp=datetime.datetime.utcnow())
			em.set_image(url="https://i.imgur.com/oe4iK5i.gif")
			await ctx.reply(content="Error: NSFW Channel Required. This command will only run in NSFW marked channel. https://i.imgur.com/oe4iK5i.gif", embed=em)
			return 

		elif isinstance(error, commands.NotOwner):
			await ctx.reply(f"Error: Not Owner. You must have ownership of the bot to run {ctx.command.name}")
			return
			
		elif isinstance(error, commands.PrivateMessageOnly):
			return await ctx.reply(f"Error: Private Message Only. This comamnd will only work in DM messages")

		elif isinstance(error, commands.BadArgument):
			if isinstance(error, commands.MessageNotFound):
					return await ctx.reply(f'Error: Message Not Found. Message ID/Link you provied is either invalid or deleted!')
			elif isinstance(error, commands.MemberNotFound):
					return await ctx.reply(f'Error: Member Not Found. Member ID/Mention/Name you provided is invalid or bot can not see that Member')
			elif isinstance(error, commands.UserNotFound):
					return await ctx.reply(f'Error: User Not Found. User ID/Mention/Name you provided is invalid or bot can not see that User')
			elif isinstance(error, commands.ChannelNotFound):
					return await ctx.reply(f'Error: Channel Not Found. Channel ID/Mention/Name you provided is invalid or bot can not see that Channel')
			elif isinstance(error, commands.RoleNotFound):
					return await ctx.reply(f'Error: Role Not Found. Role ID/Mention/Name you provided is invalid or bot can not see that Role')
			elif isinstance(error, commands.EmojiNotFound):
					return await ctx.reply(f'Error: Emoji Not Found. Emoji ID/Name you provided is invalid or bot can not see that Emoji')
	
		elif isinstance(error, commands.MissingRequiredArgument):
			return await ctx.reply(f"Error: Missing Required Argument. Please use proper syntax.```\n[p]{ctx.command.name} {ctx.command.signature}```")
		
		else:
			print('Ignoring exception in command {}:'.format(ctx.command))

		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
	
def setup(bot):
		bot.add_cog(CommandErrorHandler(bot))
