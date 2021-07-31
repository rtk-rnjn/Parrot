import discord, aiohttp, datetime, os
from discord.ext import commands
from pygicord import Paginator

token = os.environ['UB_TOKEN']

class UnbelievaBoatIntegration(commands.Cog, name="UnbelievaBoat Integration"):
		def __init__(self, bot):
				self.bot = bot

		@commands.command(aliases=['ubal', 'umoney'])
		@commands.guild_only()
		@commands.cooldown(1, 30, commands.BucketType.user)
		@commands.bot_has_permissions(embed_links=True)
		async def ucash(self, ctx, member:discord.User=None, server:discord.Guild=None):
				"""
				To check the user balance, of your UnbelievaBoat from Parrot.

				Usage:
				`Ucash [User:Mention/ID] [Server:ID]`
				"""
				if member is None: member = ctx.author
				if server is None: server = ctx.guild

				headers = {"Authorization": token}
				# https://unbelievaboat.com/api/v1/guilds/741614680652644382/users/813647101392846848
				async with aiohttp.ClientSession() as session:
						async with session.get(f"https://unbelievaboat.com/api/v1/guilds/{server.id}/users/{member.id}", headers=headers) as r:
								if r.status == 200:
										js = await r.json()
								else: return

				em = discord.Embed(title="BALANCE", description=f"```\nRANK : {js['rank']}\nCASH : {js['cash']}\nBANK : {js['bank']}\nTOTAL: {js['total']}```", timestamp=datetime.datetime.utcnow())
				em.set_footer(text=f"ID: {js['user_id']}")
				
				await ctx.send(embed=em)


		@commands.command(aliases=['usetbal', 'usetmoney'])
		@commands.has_permissions(manage_guild=True)
		@commands.guild_only()
		@commands.bot_has_permissions(embed_links=True)
		async def usetcash(self, ctx, cash:int, bank:int, *, reason:str=None):
				"""
				To set the user balance, of your UnbelievaBoat from Parrot.

				Usage:
				`Usetcash [Cash:Integer] [Bank:Integer] [Reason:Text]`
				"""
				if reason is None: reason = f"Action done by {ctx.author.name} ({ctx.author.id})"
				headers = {"Authorization": token}

				data = {"cash":f"{cash}", "bank":f"{bank}", "reason":f"{reason}"}

				async with aiohttp.ClientSession() as session:
						r = await session.put(f"https://unbelievaboat.com/api/v1/guilds/{ctx.guild.id}/users/{ctx.author.id}", json=data, headers=headers)
						if r.status == 200:
								js = r.json()
						else:
								return

				em = discord.Embed(title="BALANCE", description=f"```\nCASH : {js['cash']}\nBANK : {js['bank']}\nTOTAL: {js['total']}```", timestamp=datetime.datetime.utcnow())
				em.set_footer(text=f"ID: {js['user_id']}")
				await ctx.send(embed=em)
				

		@commands.command(aliases=['uupdatebal', 'uupdatemoney'])
		@commands.has_permissions(manage_guild=True)
		@commands.guild_only()
		@commands.bot_has_permissions(embed_links=True)
		async def uupdatecash(self, ctx, cash:int, bank:int, *, reason:str=None):
				"""
				To update the user balance, of your UnbelievaBoat from Parrot.

				Usage:
				`Usetcash [Cash:Integer] [Bank:Integer] [Reason:Text]`
				"""
				if reason is None: reason = f"Action done by {ctx.author.name} ({ctx.author.id})"
				headers = {"Authorization": token}

				data = {"cash":f"{cash}", "bank":f"{bank}", "reason":f"{reason}"}
				server = ctx.guild
				async with aiohttp.ClientSession() as session:
						r = await session.patch(f"https://unbelievaboat.com/api/v1/guilds/{server.id}/users/{ctx.author.id}", json=data, headers=headers)
						if r.status == 200:
								js = r.json()
						else:
								return

				em = discord.Embed(title="BALANCE", description=f"```\nCASH : {js['cash']}\nBANK : {js['bank']}\nTOTAL: {js['total']}```", timestamp=datetime.datetime.utcnow())
				em.set_footer(text=f"ID: {js['user_id']}")
				await ctx.send(embed=em)


		@commands.command(alises=['ulb'])
		@commands.guild_only()
		@commands.bot_has_permissions(embed_links=True)
		async def uleaderboard(self, ctx, server:discord.Guild=None, sort:str=None, limit:int=None):
				"""
				To get the leaderboard, of your UnbelievaBoat from Parrot.

				Usage:
				`Uleaderboard [Server:ID] [Sort:Text]`
				"""
				if sort: sort = sort.lower()
				if sort is None: sort = "total"
				if sort not in ['total', 'bank', 'cash']: return
				
				if limit is None: limit = 10
				headers = {"Authorization": token}
				if server is None: server = ctx.guild
				data = {"sort": f"{sort}", "limit": f"{limit}"}
				async with aiohttp.ClientSession() as session:
						async with session.get(f"https://unbelievaboat.com/api/v1/guilds/{server.id}/users/", params=data, headers=headers) as r:
								if r.status == 200:
										js = await r.json()
								else:
										return
				
				em_list = []
				for user in js:
						em = discord.Embed(title="LEADERBOARD", description=f"```\nRANK : {user['rank']}\nID   : {user['user_id']}\nCASH : {user['cash']}\nBANK : {user['bank']}\nTOTAL: {user['total']}```", timestamp=datetime.datetime.utcnow())
						em.set_footer(text=f"{ctx.author.name}")
						em_list.append(em)
				
				paginator = Paginator(pages=em_list, timeout=60.0)
				await paginator.start(ctx)
				
		@commands.command(aliases=[''])
		@commands.guild_only()
		@commands.bot_has_permissions(embed_links=True)
		async def userver(self, ctx, *, server:discord.Guild=None):
				"""
				To get the info of the server from UnbelievaBoat from Parrot.

				Usage:
				`Userver [Server:ID]`
				"""
				if server is None: server = ctx.guild
				headers = {"Authorization": token}
				async with aiohttp.ClientSession() as session:
						async with session.get(f"https://unbelievaboat.com/api/v1/guilds/{server.id}", headers=headers) as r:
								if r.status == 200:
										js = await r.json()
								else:
										return
				em = discord.Embed(title=f"SERVER: {js['name']}", timestamp=datetime.datetime.utcnow(), description=f"```\nOWNER ID: {js['owner_id']}\nMEMBERS : {js['member_count']}\nSYMBOL  : {js['symbol']}```")
				em.set_footer(text=f"{js['id']}")
				await ctx.send(embed=em)
				
				
def setup(bot):
		bot.add_cog(UnbelievaBoatIntegration(bot))
