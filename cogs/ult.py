from typing import Optional
from discord.ext import commands
from time import time 
import discord
from datetime import datetime, timedelta 
from psutil import Process, virtual_memory
from discord import __version__ as discord_version
from platform import python_version

from core.cog import Cog
from core.bot import Parrot
from core.ctx import Context

class ult(Cog, name="Utilities", description="Basic commands for the bots."):
	'''Basic commands for the bots.'''
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.command(name="ping")
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def ping(self, ctx: Context):
		'''
		Get the latency of bot.
		
		Syntax:
		`Ping`

		Permissions:
		Need Embed Links permission for the bot
		'''
		start = time()
		message = await ctx.reply(f"Pong! latency: {self.bot.latency*1000:,.0f} ms.")
		end = time()
		await message.edit(content=f"Pong! latency: {self.bot.latency*1000:,.0f} ms. Response time: {(end-start)*1000:,.0f} ms.")


	@commands.command(aliases=['av'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def avatar(self, ctx: Context, *, member: discord.Member= None):
			'''
			Get the avatar of the user. Make sure you don't misuse.
			
			Syntax:
			`Avatar [User:Mention/ID]`

			Permissions:
			Need Embed Links permission for the bot
			'''
			if member is None:
					member = ctx.author
			embed = discord.Embed(timestamp=datetime.utcnow())
			embed.add_field(name=member.name,value=f'[Download]({member.avatar_url})')
			embed.set_image(url=member.avatar_url)
			embed.set_footer(text=f'Requested by {ctx.author.name}', icon_url= ctx.author.avatar_url)
			await ctx.reply(embed=embed)


	@commands.command(name="owner")
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def owner(self, ctx: Context):
		'''
		Get the freaking bot owner name.
		
		Syntax:
		`Owner`

		Permissions:
		Need Embed Links permission for the bot
		'''
		await ctx.reply(embed=discord.Embed(title="Owner Info", description='This bot is being hosted by !! Ritik Ranjan [\*.\*]. He is actually a dumb bot developer. He do not know why he made this shit bot. But it\'s cool', timestamp=datetime.utcnow()))


	@commands.command(aliases=['guildavatar', 'serverlogo', 'servericon'])
	@commands.bot_has_permissions(embed_links=True)
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	async def guildicon(self, ctx: Context, server:int=None):
			'''
			Get the freaking server icon
			
			Syntax:
			`Guildicon`
			Permissions:
			Need Embed Links permission for the bot
			'''
			guild = self.bot.get_guild(server) or ctx.guild
			embed = discord.Embed(timestamp=datetime.utcnow())
			embed.set_image(url = guild.icon_url)
			embed.set_footer(text=f"{ctx.author.name}")
			await ctx.reply(embed=embed)


	@commands.command(name="serverinfo", aliases=["guildinfo", "si", "gi"])
	@commands.bot_has_permissions(	embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.guild_only()
	async def server_info(self, ctx: Context):
		'''
		Get the basic stats about the server
		
		Syntax:
		`Serverinfo`

		Permissions:
		Need Embed Links permission for the bot. It will be better if you give Ban Member permission too for counting the number of bans.
		'''
		embed = discord.Embed(title="Server information",
						colour=ctx.guild.owner.colour,
						timestamp=datetime.utcnow())

		embed.set_thumbnail(url=ctx.guild.icon_url)
		embed.set_footer(text=f'ID: {ctx.guild.id}')
		statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members)))]

		fields = [("Owner", ctx.guild.owner, True),
					("Region", str(ctx.guild.region).capitalize(), True),
					("Created at", ctx.guild.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
					("Total Members", f'Members: {len(ctx.guild.members)}\nHumans: {len(list(filter(lambda m: not m.bot, ctx.guild.members)))}\nBots: {len(list(filter(lambda m: m.bot, ctx.guild.members)))} ', True),
					("Humans", len(list(filter(lambda m: not m.bot, ctx.guild.members))), True),
					("Bots", len(list(filter(lambda m: m.bot, ctx.guild.members))), True),
					("Statuses", f":green_circle: {statuses[0]} :yellow_circle:  {statuses[1]} :red_circle: {statuses[2]} :black_circle: {statuses[3]}", True),
					("Total channels", f'Categories:{len(ctx.guild.categories)}\nText: {len(ctx.guild.text_channels)}\nVoice:{len(ctx.guild.voice_channels)}', True),
					#("Banned members", len(await ctx.guild.bans()), True),
					("Roles", len(ctx.guild.roles), True),
					#("Invites", len(await ctx.guild.invites()), True),
					]

		for name, value, inline in fields:
			embed.add_field(name=name, value=value, inline=inline)
		try: embed.add_field(name="Banned Members", value=f"{len(await ctx.guild.bans())}", inline=True)
		except: pass
		await ctx.reply(embed=embed)


	@commands.command(name="stats")
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def show_bot_stats(self, ctx: Context):
		'''
		Get the bot stats
		
		Syntax:
		`Stats`
		
		Permissions:
		Need Embed Links permission for the bot.
		'''
		embed = discord.Embed(title="Bot stats",
						colour=ctx.author.colour,
						thumbnail=f"{ctx.guild.me.avatar_url}",
						timestamp=datetime.utcnow())

		proc = Process()
		with proc.oneshot():
			uptime = timedelta(seconds=time()-proc.create_time())
			cpu_time = timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user)
			mem_total = virtual_memory().total / (1024**2)
			mem_of_total = proc.memory_percent()
			mem_usage = mem_total * (mem_of_total / 100)
		VERSION="v2.7"
		x = len(self.bot.users)
		y = len(self.bot.guilds)
		fields = [
				("Bot version", f"`{VERSION}`", True),
				("Python version", "`"+str(python_version())+"`", True),
				("discord.py version", "`"+str(discord_version)+"`", True),
				("Uptime", "`"+str(uptime)+"`", True),
				("CPU time", "`"+str(cpu_time)+"`", True),
				("Memory usage", f"`{mem_usage:,.3f} / {mem_total:,.0f} MiB ({mem_of_total:.0f}%)`", True),
				("Total users on count", "`"+str(x)+"`", True),
				("Owner",'`!! Ritik Ranjan [*.*]`', True),
				("Total guild on count", "`"+str(y)+"`", True)]
		for name, value, inline in fields:
			embed.add_field(name=name, value=value, inline=inline)
		await ctx.reply(embed=embed)


	@commands.command(name="userinfo", aliases=["memberinfo", "ui", "mi"])
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.guild_only()
	async def user_info(self, ctx: Context, *, member:discord.User=None):
		'''
		Get the basic stats about the user
		
		Syntax:
		`Userinfo`

		Permissions:
		Need Embed Links permission for the bot.
		'''
		target = member or ctx.author
		roles = [role for role in target.roles]
		embed = discord.Embed(title="User information",
						colour=target.colour,
						timestamp=datetime.utcnow())

		embed.set_thumbnail(url=target.avatar_url)
		embed.set_footer(text=f"{target.id}")
		fields = [("Name", str(target), True),
					#("ID", target.id, True),
					("Created at", target.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
					("Status", str(target.status).title(), True),
					("Activity", f"{str(target.activity.type).split('.')[-1].title() if target.activity else 'N/A'} {target.activity.name if target.activity else ''}", True),
					("Joined at", target.joined_at.strftime("%d/%m/%Y %H:%M:%S"), True),
					("Boosted", bool(target.premium_since), True),
					("Bot?", target.bot, True),
					(f"Roles ({len(roles)})", " ".join([role.mention for role in roles]), False)]
					
		for name, value, inline in fields:
			embed.add_field(name=name, value=value, inline=inline)

		await ctx.reply(embed=embed)


	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def invite(self, ctx: Context):
		"""
		Get the invite of the bot! Thanks for seeing this command

		Syntax:
		`Invite`

		Permissions:
		Need Embed Links permission for the bot.
		"""
		em = discord.Embed(title="ADD ME IN YOUR SERVER", url="https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=0&scope=bot", timestamp=datetime.utcnow())
		em.set_footer(text=f"{ctx.author.name}")
		await ctx.reply(embed=em)

	@commands.command(aliases=['suggestions', 'suggest'])
	@commands.guild_only()
	@commands.cooldown(1, 120, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def feedback(self, ctx: Context, *, remark:str):
		"""
		To reply the feedback to the developers. Kindly do not spam this command. Else ^^

		Syntax:
		`Feedback <remark>`

		Cooldown of 300 seconds after one time use, per member.

		Permissions:
		Need Embed Links permission for the bot.

		NOTE: Your feedback is important, also I will buy you a cup of coffee, if your suggestion is useful. Also, `<remark>` should be more than 20 characters.
		"""
		if len(remark) <= 20: return
		else:
			embed = discord.Embed(title='Suggestion', description=f"```css\n{remark}```", color=discord.Color.blue(), timestamp=datetime.utcnow())
			embed.set_footer(text=f"{ctx.author.name}")
			await self.bot.get_channel(834662716492873758).reply(embed=embed)

def setup(bot):
	bot.add_cog(ult(bot))