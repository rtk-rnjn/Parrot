import discord, aiohttp, datetime, time
from discord.ext import commands

from core import Cog, Parrot, Context

class nsfw(Cog, name="nsfw", description="Want some fun? These are best commands! :')"):
	'''Want some fun? These are best commands! :')'''
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def anal(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Anal`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""

		url = 'https://nekobot.xyz/api/image'
		params = {"type": "anal"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 

		img = res['message']
		
		em = discord.Embed(title="Anal", timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)


	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def gonewild(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Gonewild`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "gonewild"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return  
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def hanal(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hanal`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "hanal"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def hentai(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hentai`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "hentai"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return  
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)


	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def holo(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Holo`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "holo"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return  
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def neko(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hkitsune`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "neko"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def hneko(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hkitsune`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "hneko"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return  
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def hkitsune(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hkitsune`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "hkitsune"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def kemonomimi(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Kemonomimi`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "kemonomimi"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def pgif(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Pgif`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "pgif"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command(name="4k")
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def _4k(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`4k`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "4k"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 

		# 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def kanna(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Kanna`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "kanna"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 

		# 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def ass(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Ass`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "ass"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		# 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def pussy(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Pussy`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "pussy"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 

		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def thigh(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Thigh`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "thigh"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def hthigh(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hthigh`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "hthigh"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 

		# 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def gah(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Gah`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "gah"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)


	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def paizuri(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Paizuri`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "paizuri"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def tentacle(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Tentacle`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "tentacle"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def boobs(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Boobs`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "boobs"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return 
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def hboobs(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hboobs`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "hboobs"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def yaoi(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Yaoi`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "yaoi"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def hmidriff(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hmidriff`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "hmidriff"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		
		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def hass(self, ctx: Context):
		"""
		To get Random ^^.
		
		Usage:
		`Hass`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		url = 'https://nekobot.xyz/api/image'
		params = {"type": "hass"}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return

		img = res['message']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)
	
	@commands.command(aliases=['randnsfw'])
	@commands.guild_only()
	@commands.is_nsfw()
	@commands.bot_has_permissions(embed_links=True)
	async def randomnsfw(self, ctx: Context, *, subreddit:str=None):
		"""
		To get Random ^^ from subreddit.
		
		Usage:
		`Randomnsfw [Subreddit:Text]`
		
		Permission: 
		Need Embed Links Permission for the bot.
		
		NOTE: Command will only run in NSFW Marked Channels
		"""
		if subreddit is None: subreddit = "NSFW"
		end = time() + 60
		while time() < end:
			url = f'https://memes.blademaker.tv/api/{subreddit}'
			async with aiohttp.ClientSession() as session:
				async with session.get(url) as r:
					if r.status == 200:
						res = await r.json()
					else:
						return
			if res['nsfw']: break

		img = res['image']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)
		
		
	@commands.command(aliases=['nsfwdm'])
	@commands.dm_only()
	async def n(self, ctx: Context):
		"""
		Best command I guess. It return random ^^
		
		Usage:
		`NsfwDM`
		
		NOTE: Command will only run in DM Channels
		"""
		
		async with aiohttp.ClientSession() as session:
			async with session.get("https://scathach.redsplit.org/v3/nsfw/gif/") as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		
		img = res['url']
		
		em = discord.Embed(timestamp=datetime.datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		em.set_image(url=img)

		await ctx.reply(embed=em)
		
def setup(bot):
	bot.add_cog(nsfw(bot))
