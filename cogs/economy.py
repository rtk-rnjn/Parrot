from discord.ext import commands
import discord, random

from core.cog import Cog
from core.bot import Parrot
from core.ctx import Context

from database.economy import collection, ge_update, ge_on_join
from utilities.checks import user_premium_cd

class Economy(Cog, name="economy"):
		def __init__(self, bot: Parrot):
				self.bot = bot

		@commands.command(aliases=["with"])
		@user_premium_cd()
		@commands.guild_only()
		async def withdraw(self, ctx: Context, money: int):
				'''Withdraw your money, from your bank account'''
				if money < 0:
						return await ctx.reply(
								f'{ctx.author.mention} money can not be negative')

				x = collection.find_one({'_id': ctx.author.id})
				if x:
						coins_walt = x['wallet']
						coins_bank = x['bank']

						if coins_bank - money < 0:
								return await ctx.reply(
										f'{ctx.author.mention} you do not have enough money to withdraw money'
								)
						else:
								coins_walt += money
								coins_bank -= money
								await ge_update(ctx.author.id, coins_bank, coins_walt)
								return await ctx.reply(
										f"{ctx.author.mention} deposited **{money}** coins in the bank"
								)
				else:
						await ge_on_join(ctx.author.id)
						embed = discord.Embed(
								title=f"Balance of {ctx.author.name}",
								description=
								"Welcome to Parrot Economy, before depositing you must have an account!",
								colour=ctx.author.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						await ctx.reply(embed=embed)

		@commands.command(aliases=['rob'])
		@user_premium_cd()
		@commands.guild_only()
		async def steal(self, ctx, *, member: discord.Member):
				'''Want more money? Try stealing others.'''

				x = collection.find({'_id': ctx.author.id})
				y = collection.find({'_id': member.id})

				if x and y:
						coins_walt_x = x['wallet']
						coins_bank_x = x['bank']
						coins_walt_y = y['wallet']
						coins_bank_y = y['bank']
						if coins_walt_y == 0:
								return await ctx.reply(
										f"{ctx.author.mention} **{member.name}#{member.discriminator}** don't have enough money to be robbed."
								)
						money = random.randint(0, coins_walt_y)
						coins_walt_y -= money
						coins_walt_x += money

						await ge_update(member.id, coins_bank_y, coins_walt_y)
						await ge_update(ctx.author.id, coins_bank_x, coins_walt_x)

						return await ctx.reply(
								f"{ctx.author.mention} you robbed **{member.name}#{member.discriminator}** and recieved **{money}**"
						)
				if not y:
						return await ctx.reply(
								f"{ctx.author.mention} **{member.name}#{member.discriminator}** don't have Parrot Economy"
						)
				if not x:
						await ge_on_join(ctx.author.id)
						embed = discord.Embed(
								title=f"Balance of {ctx.author.name}",
								description=
								"Welcome to Parrot Economy, before robbing money you must have an account!",
								colour=ctx.author.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						await ctx.reply(embed=embed)

		@commands.command()
		@user_premium_cd()
		@commands.guild_only()
		async def slots(self, ctx: Context, money: int):
				'''Want more money? Try gambling slots.'''

				if money < 0:
						return await ctx.reply(
								f'{ctx.author.mention} money can not be negative')

				x = collection.find({'_id': ctx.author.id})

				if x:
						coins_walt = x['wallet']
						coins_bank = x['bank']
						if coins_walt - money < 0:
								return await ctx.reply(
										f"{ctx.author.mention} you don't have enough money to slots"
								)

						emoji = ["🍇", "🍉", "🍊", "🍎"]
						first = random.choice(emoji)
						second = random.choice(emoji)
						third = random.choice(emoji)
						if first == second == third:
								await ctx.reply(
										f"{ctx.author.mention}\n\nYour slots results:\n> |{first}|{second}|{third}|\n\nYayy!! you won **{money*10}** money"
								)
								coins_walt['wallet'] += (money * 10)
						else:
								await ctx.reply(
										f"{ctx.author.mention}\n\nYour slots results:\n> |{first}|{second}|{third}|\n\nYou lost {money} money :'("
								)
								coins_walt['wallet'] -= money

						await ge_update(ctx.author.id, coins_bank, coins_walt)
				else:
						await ge_on_join(ctx.author.id)
						embed = discord.Embed(
								title=f"Balance of {ctx.author.name}",
								description=
								"Welcome to Parrot Economy, before playing slots you must have a account!",
								colour=ctx.author.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						await ctx.reply(embed=embed)

		@commands.command(aliases=['send'])
		@user_premium_cd()
		@commands.guild_only()
		async def give(self, ctx: Context, member: discord.Member, money: int):
				'''You can give your Parrot coins to other user too'''

				if money < 0:
						return await ctx.reply(
								f'{ctx.author.mention} money can not be negative')

				x = collection.find({'_id': ctx.author.id})
				y = collection.find({'_id': member.id})

				if x and y:
						coins_walt_x = x['wallet'] - money
						coins_bank_x = x['bank']
						if coins_walt_x < 0:
								return await ctx.reply(
										f"{ctx.author.mention} you don't have **{money}** in your wallet to send it to **{member.name}#{member.discriminator}**"
								)
						coins_walt_y = y['wallet'] + money
						coins_bank_y = y['bank']

						await ge_update(member.id, coins_bank_y, coins_walt_y)
						await ge_update(ctx.author.id, coins_bank_x, coins_walt_x)

						return await ctx.reply(
								f"{ctx.author.mention} **{member.name}#{member.discriminator}** recieved **{money}** from you"
						)
				if not y:
						return await ctx.reply(
								f"{ctx.author.mention} **{member.name}#{member.discriminator}** don't have Parrot Economy"
						)
				if not x:
						await ge_on_join(ctx.author.id)
						embed = discord.Embed(
								title=f"Balance of {ctx.author.name}",
								description=
								"Welcome to Parrot Economy, before giving money you must have an account!",
								colour=ctx.author.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						await ctx.reply(embed=embed)

		@commands.command(aliases=["dep"])
		@user_premium_cd()
		@commands.guild_only()
		async def deposit(self, ctx: Context, money: int):
				'''Save your money by depositing all the money in the bank'''

				if money < 0:
						return await ctx.reply(
								f'{ctx.author.mention} money can not be negative')

				x = collection.find_one({'_id': ctx.author.id})
				if x:
						coins_walt = x['wallet']
						coins_bank = x['bank']

						if coins_walt - money < 0:
								return await ctx.reply(
										f'{ctx.author.mention} you do not have enough money to deposit money'
								)
						else:
								coins_walt -= money
								coins_bank += money
								await ge_update(ctx.author.id, coins_bank, coins_walt)
								return await ctx.reply(
										f"{ctx.author.mention} deposited **{money}** coins in the bank"
								)
				else:
						await ge_on_join(ctx.author.id)
						embed = discord.Embed(
								title=f"Balance of {ctx.author.name}",
								description=
								"Welcome to Parrot Economy, before depositing you must have an account!",
								colour=ctx.author.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						await ctx.reply(embed=embed)

		@commands.command()
		@user_premium_cd()
		@commands.guild_only()
		async def beg(self, ctx: Context):
				'''Beg from internet, hope someone will give you money'''

				inc = random.randint(0, 100)
				someone = [
						"someone", "Mr. X", "Mother nature", "PewDiePie", "CarryMinati",
						"Parrot", "this internet", "the guy who punched you yesterday",
						"girl with whom you had fun last night", "your father", "the Boss"
				]

				gives = [
						'gives you', 'gifted you', 'unconditionally gives you',
						'slaps, and give'
				]

				x = collection.find_one({'_id': ctx.author.id})
				if x:
						coins_walt = x['wallet'] + inc
						coins_bank = x['bank']
						await ctx.reply(
								f"{ctx.author.mention} {random.choice(someone)} {random.choice(gives)} **{inc}** coins to you"
						)
						await ge_update(ctx.author.id, coins_bank, coins_walt)
						return
				else:
						await ge_on_join(ctx.author.id)
						embed = discord.Embed(
								title=f"Balance of {ctx.author.name}",
								description=
								"Welcome to Parrot Economy, before begging you must have an account!",
								colour=ctx.author.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						await ctx.reply(embed=embed)

		@commands.command(aliases=['bal'])
		@user_premium_cd()
		@commands.guild_only()
		async def balance(self, ctx: Context, member: discord.User = None):
				'''To check your balance, if not, then it will open a Parrot Economy bank account for you'''
				if member.bot: return

				if member is None:
						target = ctx.author

				x = collection.find_one({'_id': target.id})

				if not x:
						await ge_on_join(target.id)
						embed = discord.Embed(title=f"Balance of {target.name}",
																	description="Welcome to Parrot Economy",
																	colour=target.colour)
						embed.add_field(name="Wallet", value=400)
						embed.add_field(name="Bank", value=0)
						return await ctx.reply(embed=embed)
				elif target == ctx.author:
						coins_bank = x['bank']
						coins_walt = x['wallet']
						await ge_on_join(ctx.author.id)
						embed = discord.Embed(title=f"Balance of {target.name}",
																	colour=target.colour)
						embed.add_field(name="Wallet", value=coins_walt)
						embed.add_field(name="Bank", value=coins_bank)
						return await ctx.reply(embed=embed)
				else:
						return await ctx.reply(
								f"{ctx.author.mention} **{member.name}#{member.discriminator}** don't have Parrot Economy"
						)


def setup(bot):
		bot.add_cog(Economy(bot))
