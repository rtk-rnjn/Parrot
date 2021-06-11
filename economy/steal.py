import discord, json, random, math
from discord.ext import commands


class _Steal(commands.Cog, name="Economy"):
		
		def __init__(self, bot):
				self.bot = bot

		@commands.command(aliases=['rob'])
		@commands.cooldown(1, 10, commands.BucketType.user)
		async def steal(self, ctx, user: discord.Member):
				'''Want more money? Try stealing others.'''
				with open('bank.json', encoding='utf-8') as f:
						bank = json.load(f)
				for current_user in bank['users']:
						if current_user['name'] == ctx.author.id:
								if current_user['wallet'] < 100:
										return await ctx.send(
												f"{ctx.author.mention} you can't rob. You must have atleast 100 coins"
										)
								break
				else:
						bank['users'].append({
								'name': ctx.author.id,
								'wallet': 400,
								'bank': 0
						})
						embed = discord.Embed(title=f"Balance of {ctx.author.name}",
																	description="Welcome to Parrot Economy",
																	colour=ctx.author.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						await ctx.send(embed=embed)
				for target in bank['users']:
						print(1)
						if target['name'] == user.id:
								if target['name'] == None:
										await ctx.send(
												f"{ctx.author.mention} that user don't have parrot economy"
										)
								if target['wallet'] < 100:
										await ctx.send(
												f"{ctx.author.mention} victim don't have enough coins to be robbed."
										)
								if target['wallet'] > 100:
										add_mny = random.randrange(target['wallet'])
										current_user['wallet'] += add_mny
										target['wallet'] -= add_mny
										await ctx.send(
												f"{ctx.author.mention} you stole **{add_mny}** coins from **{user.name}!!** GG!! "
										)
								break
				with open('bank.json', 'w+') as f:
						json.dump(bank, f)

		@steal.error
		async def steal_error(self, ctx, error):
				if isinstance(error, commands.CommandOnCooldown):
						await ctx.send(
								f"This command is on {str(error.cooldown.type).split('.')[-1]} cooldown, please retry in {(math.ceil(error.retry_after))}s."
						)
				if isinstance(error, commands.errors.MemberNotFound):
						await ctx.send(
								f'{ctx.author.mention} that member is not visible in this server by me or member you specified is invalid! Do check the name/ID again'
						)
				if isinstance(error, commands.MissingRequiredArgument):
						await ctx.send(
								'ERROR: MissingRequiredArgument. Please use proper syntax.\n```\n[p]steal <member.mention/ID>```'
						)


def setup(bot):
		bot.add_cog(_Steal(bot))
