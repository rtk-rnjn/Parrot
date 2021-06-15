import discord, json, random, asyncio
from discord.ext import commands

class _Slots(commands.Cog, name="Economy"):
		
		def __init__(self, bot):
			self.bot = bot

		@commands.command()
		async def slots(self, ctx, amount:int):
			'''Want more money? Try gambling slots.'''
			with open('bank.json', encoding='utf-8') as f:
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
			with open('bank.json', 'w+') as f:
						json.dump(bank, f)
		@slots.error
		async def slots_error(self, ctx, error):
				if isinstance(error, commands.MissingRequiredArgument):
						await ctx.send('ERROR: MissingRequiredArgument. Please use proper syntax.\n```\n[p]slots <amount:number>```')
						
def setup(bot):
	bot.add_cog(_Slots(bot))