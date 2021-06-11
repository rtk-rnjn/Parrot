from discord.ext import commands
from datetime import datetime 
from pygicord import Paginator
import discord

class help1(commands.Cog, name="Help"):
	def __init__(self, bot):
		self.bot = bot


	@commands.command(breif="Shows this message", hidden=False, name="help")
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def help(self, ctx, cmd:str=None):
		"""
		Shows this message.

		Syntax:
		`Help [Command:Name]`

		Permissions:
		Need Embed Links permission, for the bot.
		"""
		help_ = discord.utils.get(self.bot.commands, name="help")
		
		
		temp = []
		if not cmd:
			for cog in self.bot.cogs: temp.append(cog) 
			
			emb = discord.Embed(title=f"Welcome to help menu of Parrot", description=f"```\n{help_.help}```\n**Category**```\n{', '.join(temp)}```\n```\nPaginate for short intro of the Categories.\n[p]help [Category:Name] for category help.\n[p]help [Command:Name] for command help.```", timestamp=datetime.utcnow(), color=discord.Color.blue())
			emb.set_thumbnail(url=f"{ctx.guild.me.avatar_url}")
			emb.set_footer(text=f"{ctx.author.name}")
			
			temp = []
			temp.append(emb)
			
			for cog in self.bot.cogs:
				
				if (self.bot.cogs[cog].description is None) or (self.bot.cogs[cog].description == ""): description = "N/A"
				else: description = self.bot.cogs[cog].description

				e = discord.Embed(title=f"Help with {cog}", description=f"```\n{description}```", timestamp=datetime.utcnow(), color=discord.Color.blue())
				temp.append(e)
				e.set_footer(text=f"{ctx.author.name}")	
				e.set_thumbnail(url=f"{ctx.guild.me.avatar_url}")
			
			paginator = Paginator(pages=temp)
			return await paginator.start(ctx)


		em_list = []
		if cmd: 
			cog = cmd

			if cog in self.bot.cogs:

				if not self.bot.cogs[cog].description: description = "No description"
				else: description = self.bot.cogs[cog].description

				embed = discord.Embed(title=f"Help with {cog}", description=f"```\n{description}```", timestamp=datetime.utcnow(), color=discord.Color.blue())
				commands = []

				for command in self.bot.cogs[cog].get_commands():
					commands.append(command.name)

				embed.add_field(name="Commands", value=f"```\n{', '.join(commands)}```", inline=False)
				embed.set_thumbnail(url=f"{ctx.guild.me.avatar_url}")
				embed.set_footer(text=f"{ctx.author.name}")
				em_list.append(embed)

				for command in self.bot.cogs[cog].get_commands():

					cmd_em = discord.Embed(title=f"Help with {command.name}", description=f"```\n{command.help}```", timestamp=datetime.utcnow(), color=discord.Color.blue())
					cmd_em.set_thumbnail(url=f"{ctx.guild.me.avatar_url}")
					cmd_em.set_footer(text=f"{ctx.author.name}")
					cmd_em.add_field(name="Usage", value=f"```\n[p]{command.name} {command.signature}```", inline=True)
					if command.aliases == []: pass
					else: cmd_em.add_field(name="Aliases", value=f"```\n{'|'.join(command.aliases)}```")
					em_list.append(cmd_em)

				paginator = Paginator(pages=em_list)
				return await paginator.start(ctx)


		if cmd: name = cmd.lower()
		cmd = discord.utils.get(self.bot.commands, name=f"{name}")

		if cmd:

			if cmd.aliases == []: aliases = "None"
			else: aliases = '|'.join(cmd.aliases)

			em = discord.Embed(title=f"Help for `{cmd}`", description=f"```\n{cmd.help}```\n**Usage**```\n[p]{cmd.name} {cmd.signature}```\n**Aliases**```\n{aliases}```", timestamp=datetime.utcnow(), color = discord.Color.blue())
			em.set_thumbnail(url=f"{ctx.guild.me.avatar_url}")
			em.set_footer(text=f"{ctx.author.name}")
			return await ctx.send(embed=em)


def setup(bot):
	bot.add_cog(help1(bot))