from discord.ext import commands 
import discord  
import json 

class _Balance(commands.Cog, name="Economy"):
	
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=['bal'])
	async def balance(self, ctx, target: discord.Member=None):
				'''To check your balance, if not, then it will open a Parrot Economy bank account for you'''
				with open('bank.json', encoding='utf-8') as f:
						try:
								bank = json.load(f)
						except ValueError:
								bank = {}
								bank['users'] = []
				if target is None:
					target = ctx.author

				for current_user in bank['users']:
						if current_user['name'] == target.id:

								coins_walt = current_user['wallet']
								coins_bank = current_user['bank']

								embed = discord.Embed(
										title=f"Balance of {target.name}",
										colour=target.colour)
								embed.add_field(name="Wallet", value=coins_walt)
								embed.add_field(name="Bank", value=coins_bank)
								await ctx.send(embed=embed)
								break
				else:
						bank['users'].append({
								'name': target.id,
								'wallet': 400,
								'bank': 0
						})
						embed = discord.Embed(
								title=f"Balance of {target.name}",
								description="Welcome to Parrot Economy",
								colour=target.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						await ctx.send(embed=embed)

				with open('bank.json', 'w+') as f:
						json.dump(bank, f)
	@balance.error
	async def balance_error(self, ctx, error):
		if isinstance(error, commands.errors.MemberNotFound):
			await ctx.send(f'{ctx.author.mention} that member is not visible in this server by me or member you specified is invalid! Do check the name/ID again')
			
def setup(bot):
	bot.add_cog(_Balance(bot))