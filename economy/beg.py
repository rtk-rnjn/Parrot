import discord
from discord.ext import commands
import json, random, math


class _Beg(commands.Cog, name="Economy"):
	
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	@commands.cooldown(1, 30, commands.BucketType.user)
	async def beg(self, ctx):
			'''Beg from internet, hope someone will give you money'''
			with open('bank.json', encoding='utf-8') as f:
					bank = json.load(f)

			someone = ["someone", "Mr. X", "Mother nature", "PewDiePie", "CarryMinati", "Parrot", "this internet", "the guy who punched you yesterday", "girl with whom you had fun last night", "your father", "the Boss"]

			gives = ['gives you', 'gifted you', 'unconditionally gives you', 'slaps, and give']
			
			for current_user in bank['users']:
					if current_user['name'] == ctx.author.id:
							add_mny = random.randrange(100)
							current_user['wallet'] = current_user['wallet'] + add_mny
							await ctx.send(f'{ctx.author.mention} {random.choice(someone)} {random.choice(gives)} {add_mny} money')
							break
			else:
					bank['users'].append({
							'name': ctx.author.id,
							'wallet': 400,
							'bank': 0
					})
					embed = discord.Embed(
							title=f"Balance of {ctx.author.name}",
							description="Welcome to Parrot Economy",
							colour=ctx.author.colour)
					embed.add_field(name="Wallet", value=400)
					embed.add_field(name="Bank", value=0)
					await ctx.send(embed=embed)
			with open('bank.json', 'w+') as f:
					json.dump(bank, f)

	@beg.error
	async def beg_error(self, ctx, error):
			if isinstance(error, commands.CommandOnCooldown):
					await ctx.send(f"This command is on {str(error.cooldown.type).split('.')[-1]} cooldown, please retry in {(math.ceil(error.retry_after))}s.")

def setup(bot):
	bot.add_cog(_Beg(bot))