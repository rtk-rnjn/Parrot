import discord, json, math
from discord.ext import commands


class _Give(commands.Cog, name="Economy"):
		
		def __init__(self, bot):
				self.bot = bot

		@commands.command(aliases=['send'])
		@commands.cooldown(1, 10, commands.BucketType.user)
		async def give(self, ctx, user: discord.Member, money:int):
				'''You can give your Parrot coins to other user too'''
				with open('bank.json', encoding='utf-8') as f:
						bank = json.load(f)
				
				if type(money) is not int: 
					await ctx.send(f"{ctx.author.mention} :\ what you want to give to {user.name}? Money you give, must be a number, real interger type number, like 11, 236, 300 not 'five', 5.0")
					return
				for current_user in bank['users']:
						if current_user['name'] == ctx.author.id:
								if not current_user['wallet'] >= money: 
									return await ctx.send(f"{ctx.author.mention} you don't have {money} in your wallet to send it to {user.name}")
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
						if target['name'] == user.id:
								if target['name'] == None:
										await ctx.send(
												f"{ctx.author.mention} that user don't have parrot economy"
										)
								else:
										add_mny = money
										current_user['wallet'] -= add_mny
										target['wallet'] += add_mny
										await ctx.send(
												f"{ctx.author.mention} you gave **{add_mny}** coins to **{user.name}!!** Good!! "
										)
								break
				with open('bank.json', 'w+') as f:
						json.dump(bank, f)

		@give.error
		async def give_error(self, ctx, error):
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
								'ERROR: MissingRequiredArgument. Please use proper syntax.\n```\n[p]give <member.mention/ID> <amount:number>```'
						)


def setup(bot):
		bot.add_cog(_Give(bot))
