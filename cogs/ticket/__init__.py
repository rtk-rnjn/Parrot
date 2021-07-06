from discord.ext import commands
import discord

from core import Parrot, Context, Cog

from utilities.checks import has_verified_role_ticket
from cogs.ticket import method as mt

class ticket(Cog, name="ticket"):
	"""A simple ticket service, trust me it's better than YAG. LOL!"""
	def __init__(self, bot: Parrot):
		self.bot = bot 

	@commands.command()
	@commands.cooldown(1, 60, commands.BucketType.member)
	@commands.bot_has_permissions(manage_channels=True, embed_links=True, manage_roles=True)
	async def new(self, ctx: Context, *, args = None):
			'''
			This creates a new ticket. Add any words after the command if you'd like to send a message when we initially create your ticket.
			'''
			await self.bot.wait_until_ready()
			await mt._new(ctx, args)

	@commands.command()
	@commands.bot_has_permissions(manage_channels=True, embed_links=True)
	async def close(self, ctx):
			'''
			Use this to close a ticket. This command only works in ticket channels.
			'''
			await self.bot.wait_until_ready()
			await mt._close(ctx, self.bot)
	
	@commands.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def save(self, ctx):
			'''
			Use this to save the transcript of a ticket. This command only works in ticket channels.
			'''
			await self.bot.wait_until_ready()
			await mt._save(ctx, self.bot)


	@commands.group()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@has_verified_role_ticket()
	@commands.bot_has_permissions(embed_links=True)
	async def ticketconfig(self, ctx: Context):
			pass

	@ticketconfig.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@has_verified_role_ticket()
	@commands.bot_has_permissions(embed_links=True)
	async def addaccess(self, ctx: Context, *, role:discord.Role):
			'''
			This can be used to give a specific role access to all tickets. This command can only be run if you have an admin-level role for this bot.
			
			Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			'''
			await mt._addaccess(ctx, role)

	@commands.cooldown(1, 5, commands.BucketType.member)
	@ticketconfig.command()
	@has_verified_role_ticket()
	@commands.bot_has_permissions(embed_links=True)
	async def delaccess(self, ctx: Context, *, role:discord.Role):
			'''
			This can be used to remove a specific role's access to all tickets. This command can only be run if you have an admin-level role for this bot.
			
			Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			'''
			await mt._delaccess(ctx, role)


	@ticketconfig.command()
	@commands.has_permissions(administrator=True)
	@commands.bot_has_permissions(embed_links=True)
	async def addadminrole(self, ctx: Context, *, role:discord.Role):
			'''
			This command gives all users with a specific role access to the admin-level commands for the bot, such as `Addpingedrole` and `Addaccess`.
			'''
			await mt._addadimrole(ctx, role)
			

	@ticketconfig.command(hidden=False)
	@has_verified_role_ticket()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def addpingedrole(self, ctx: Context, *, role:discord.Role):
			'''
			This command adds a role to the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot.
			'''
			await mt._addpingedrole(ctx, role)


	@ticketconfig.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.has_permissions(administrator=True)
	@commands.bot_has_permissions(embed_links=True)
	async def deladminrole(self, ctx: Context, *, role:discord.Role):
			"""
			This command removes access for all users with the specified role to the admin-level commands for the bot, such as `Addpingedrole` and `Addaccess`.
			"""
			await mt._deladminrole(ctx, role)


	@ticketconfig.command()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@has_verified_role_ticket()
	@commands.bot_has_permissions(embed_links=True)
	async def delpingedrole(self, ctx: Context, *, role:discord.Role):
			'''
			This command removes a role from the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot.
			'''
			await mt._delpingedrole(ctx, role)
		
def setup(bot):
	bot.add_cog(ticket(bot))
