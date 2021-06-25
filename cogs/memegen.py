import discord, aiohttp
from discord.ext import commands 
from datetime import datetime 

from core.ctx import Context 
from core.cog import Cog
from core.bot import Parrot 

from utilities.checks import user_premium_cd

class meme(Cog, name="Meme Generator"):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@user_premium_cd()
	async def thefact(self, ctx: Context, *, text:str=None):
		#if member is None: member = ctx.author
		params = {
			"type": "fact",
			"text": f"{text}",
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@user_premium_cd()
	async def stickbug(self, ctx: Context, *, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "stickbug",
			"url": f"{member.avatar_url}",
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@user_premium_cd()
	async def trash(self, ctx: Context, *, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "trash",
			"url": f"{member.avatar_url}",
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@user_premium_cd()
	async def magik(self, ctx: Context, member:discord.Member=None, intensity:int=None):
		if member is None: member = ctx.author
		if intensity is None: intensity = 5
		params = {
			"type": "magik",
			"image": f"{member.avatar_url}",
			"intensity": intensity
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)
	
	
	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def blurpify(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "blurpify",
			"image": f"{member.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def phcomment(self, ctx, *, text:str=None):
		#if member is None: member = ctx.author
		params = {
			"type": "phcomment",
			"image": f"{ctx.author.avatar_url}",
			"text": text,
			"username": f"{ctx.author.name}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)



	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def deepfry(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "deepfry",
			"image": f"{member.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def tweet(self, ctx, *, text:str=None):
		if text is None: text = "No U"
		params = {
			"type": "tweet",
			"text": f"{text}", "username": f"{ctx.author.name}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def trumptweet(self, ctx, *, text:str=None):
		if text is None: text = "No U"
		params = {
			"type": "trumptweet",
			"text": f"{text}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)
	
	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def trap(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "trap",
			"name": f"{member.name}",
			"author": f"{ctx.author.name}",
			"image": f"{member.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def awooify(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "awooify",
			"url": f"{member.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	
	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def animeface(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "animeface",
			"image": f"{member.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def iphonex(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "iphonex",
			"url": f"{member.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def threats(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "threats",
			"url": f"{member.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def clyde(self, ctx, *, text:str):
		params = {
			"type": "clyde",
			"text": f"{text}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)



	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def captcha(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "captcha",
			"url": f"{member.avatar_url}",
			"username": f"{member.name}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def whowouldwin(self, ctx, member:discord.Member):
		#if member is None: member = ctx.author
		params = {
			"type": "whowouldwin",
			"user1": f"{member.avatar_url}",
			"user2": f"{ctx.author.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)
	@whowouldwin.error
	async def www_error(self, ctx, error):
		if isinstance(error, commands.MissingRequiredArgument):
			await ctx.send("Error: Missing Required Argument. Please use proper syntax.\n```\n[p]whowouldwin <member.mention/ID>\n```")

	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def baguette(self, ctx, member:discord.Member=None):
		if member is None: member = ctx.author
		params = {
			"type": "baguette",
			"url": f"{member.avatar_url}"
		}
		url = "https://nekobot.xyz/api/imagegen"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return
		img = res['message']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)
		#

	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def awkwardseal(self, ctx, text1:str, text2:str, font:str="impact", fontsize:int=50):
		"""Meme Generator: Awkward Seal. [p] [text1] [text2] [font:optional:default="impact""] [fontsize:optional:default=50]"""
		params = {
			"template_id": 13757816,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return

		if not res['success'] : return

		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def changemymind(self, ctx, text1:str, text2:str, font:str="impact", fontsize:int=50):
		"""Meme Generator: Change My Mind. [p]changemymind [text1] [text2] [font:optional:default="impact""] [fontsize:optional:default=50]"""
		params = {
			"template_id": 129242436,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return

		if not res['success'] : return

		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def distractedbf(self, ctx, text1:str, text2:str, font:str="impact", fontsize:int=50):
		"""Meme Generator: Distracted BF. [p]distractedbf [text1] [text2] [font:optional:default="impact""] [fontsize:optional:default=50]"""
		params = {
			"template_id": 112126428,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return

		if not res['success'] : return

		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)


	@commands.cooldown(1, 5, commands.BucketType.member)	
	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	async def doge(self, ctx, text1:str, text2:str, font:str="impact", fontsize:int=50):
		"""Meme Generator: Doge. [p]doge [text1] [text2] [font:optional:default="impact""] [fontsize:optional:default=50]"""
		params = {
			"template_id": 8072285,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return

		if not res['success'] : return
		
		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	async def drakeyesno(self, ctx, text1:str, text2:str, font:str="impact", fontsize:int=50):
		"""Meme Generator: Drake Yes No. [p]drakeyesno [text1] [text2] [font:optional:default="impact""] [fontsize:optional:default=50]"""
		params = {
			"template_id": 181913649,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return

		if not res['success'] : return

		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.cooldown(1, 5, commands.BucketType.member)	
	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	async def isthispigeon(self, ctx, text1:str, text2:str, font:str="impact", fontsize:int=50):
		"""Meme Generator: Is this Pigeon? [p]isthispigeon [text1] [text2] [font:optional:default="impact""] [fontsize:optional:default=50]"""
		params = {
			"template_id": 100777631,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return

		if not res['success'] : return

		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	async def twobuttons(self, ctx, text1:str, text2:str, font:str="impact", fontsize:int=50):
		"""Meme Generator: Two Buttons. [p]twobuttons [text1] [text2] [font:optional:default="impact""] [fontsize:optional:default=50]"""
		params = {
			"template_id": 87743020,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else: return

		if not res['success'] : return

		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.command()
	@commands.bot_has_permissions(embed_links=True)
	async def unodraw25(self, ctx, text1:str, text2:str, font:str="impact", fontsize:int=50):
		"""Meme Generator: Draw 25. [p]unodraw25 [text1] [text2] [font:optional:default="impact"] [fontsize:optional:default=50]"""
		params = {
			"template_id": 217743513,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return
#2329rtkmail.ch
		if not res['success'] : return

		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def mastermeme(self, ctx, template:int, text1:str, text2:str, font:str=None, fontsize:int=None):
		"""
		To create a meme as per your choice.

		Usage:
		`Mastermeme <TemplateID:Whole Number> <Text:Text> <Text:Text> [Font:Text] [Fontsize:Whole Number]`

		You can find tons and tons of template at https://imgflip.com/popular_meme_ids or at https://imgflip.com/
		"""
		font = font or "impact"
		fontsize = fontsize or 50
		params = {
			"template_id": template,
			"username": "RitikRanjan",
			"password": "***qwerty123",
			"text0": text1,
			"text1": text2,
			"font": font,
			"max_font_size": fontsize
		}
		url = "https://api.imgflip.com/caption_image"
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					res = await r.json()
				else:
					return

		if not res['success'] : return

		img = res['data']['url']
		em = discord.Embed(title="", timestamp=datetime.utcnow())
		em.set_image(url=img)
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=em)

def setup(bot):
	bot.add_cog(meme(bot))