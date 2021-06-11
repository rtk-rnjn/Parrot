from discord.ext import commands 
import discord, random, asyncio
import json 

class Economy(commands.Cog, name="Economy"):
	
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=["with"])
	async def withdraw(self, ctx, amount: int):
		'''Withdraw your money, from your bank account'''
		with open('json/bank.json', encoding='utf-8') as f:
				bank = json.load(f)
		print(1)
		if amount < 0:
				await ctx.send(f'{ctx.author.mention} amount can not be negative')
		else:
				for current_user in bank['users']:
						if current_user['name'] == ctx.author.id:
								if (current_user['bank'] - amount) < 0:
										await ctx.send(f'{ctx.author.mention} you do not have enough amount to withdraw money')
								else:
										current_user['bank'] = current_user['bank'] - amount
										current_user['wallet'] = current_user['wallet'] + amount
										await ctx.send(f'{ctx.author.mention} withdrew **{amount}** money')
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
		with open('json/bank.json', 'w+') as f:
				json.dump(bank, f)


	@commands.command(aliases=['rob'])
	@commands.cooldown(1, 10, commands.BucketType.user)
	async def steal(self, ctx, user: discord.Member):
		'''Want more money? Try stealing others.'''
		with open('json/bank.json', encoding='utf-8') as f:
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
		with open('json/bank.json', 'w+') as f:
				json.dump(bank, f)

	@commands.command()
	async def slots(self, ctx, amount:int):
		'''Want more money? Try gambling slots.'''
		with open('json/bank.json', encoding='utf-8') as f:
				bank = json.load(f)
		for current_user in bank['users']:
			if current_user['name'] == ctx.author.id:
				break
		if current_user['wallet'] < 1: 
			await ctx.send("You can not slots, as you don't have enough money")
		else:
			x = ["🍇", "🍉", "🍊", "🍎"]
			first = random.choice(x)
			second = random.choice(x)
			third = random.choice(x)
			if first == second == third:
				await ctx.send(f"Your slots results: |{first}|{second}|{third}|")
				await asyncio.sleep(1)
				await ctx.send(f"Yayy!! you won {amount*10} money")
				current_user['wallet'] += (amount*10)
			else:
				await ctx.send(f"Your slots results: |{first}|{second}|{third}|")
				await asyncio.sleep(1)
				await ctx.send(f"You lost {amount} money :'(")
				current_user['wallet'] -= amount
		with open('json/bank.json', 'w+') as f:
					json.dump(bank, f)
	
	@commands.command(aliases=['send'])
	@commands.cooldown(1, 10, commands.BucketType.user)
	async def give(self, ctx, user: discord.Member, money:int):
			'''You can give your Parrot coins to other user too'''
			with open('json/bank.json', encoding='utf-8') as f:
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
			with open('json/bank.json', 'w+') as f:
					json.dump(bank, f)
					
	@commands.command(aliases=["dep"])
	async def deposit(self, ctx, amount: int):
			'''Save your money by depositing all the money in the bank'''
			with open('json/bank.json', encoding='utf-8') as f:
					bank = json.load(f)
			if amount < 0:
					await ctx.send(f'{ctx.author.mention} amount can not be negative')
			else:
					for current_user in bank['users']:
							if current_user['name'] == ctx.author.id:
									if (current_user['wallet'] - amount) < 0:
											await ctx.send(f'{ctx.author.mention} you do not have enough amount to deposit money')
									else:
											current_user['bank'] = current_user['bank'] + amount
											current_user['wallet'] = current_user['wallet'] - amount
											await ctx.send(f'{ctx.author.mention} deposited ' + str(amount) + ' money')
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
			with open('json/bank.json', 'w+') as f:
					json.dump(bank, f)

	@commands.command()
	@commands.cooldown(1, 30, commands.BucketType.user)
	async def beg(self, ctx):
			'''Beg from internet, hope someone will give you money'''
			with open('json/bank.json', encoding='utf-8') as f:
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
			with open('json/bank.json', 'w+') as f:
					json.dump(bank, f)

	@commands.command(aliases=['bal'])
	async def balance(self, ctx, target: discord.Member=None):
				'''To check your balance, if not, then it will open a Parrot Economy bank account for you'''
				with open('json/bank.json', encoding='utf-8') as f:
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

				with open('json/bank.json', 'w+') as f:
						json.dump(bank, f)



def setup(bot):
	bot.add_cog(Economy(bot))