from discord.ext import commands
import discord, asyncio

import chat_exporter, io

from core.bot import Parrot
from core.ctx import Context
from core.cog import Cog

from database.ticket import collection, ticket_on_join, ticket_update
from utilities.checks import has_verified_role_ticket

class ticket(Cog, name="ticket", command_attrs=dict(hidden=False)):
	"""A simple ticket service, trust me it's better than YAG. LOL!"""
	def __init__(self, bot: Parrot):
		self.bot = bot 

	@commands.command(hidden=False)
	@commands.guild_only()
	@commands.cooldown(1, 60, commands.BucketType.member)
	@commands.bot_has_permissions(manage_channels=True, embed_links=True, manage_roles=True)
	async def new(self, ctx: Context, *, args = None):
			'''
			This creates a new ticket. Add any words after the command if you'd like to send a message when we initially create your ticket.
			
			Syntax:
			`New [Argument:Text]`

			Permissions:
			Need Manage Channels and Embed Links permissions for the bot.
			'''
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)

			await self.bot.wait_until_ready()

			if not args:
					message_content = "Please wait, we will be with you shortly!"
			
			else:
					message_content = "".join(args)

			data = collection.find_one({'_id': ctx.guild.id})
			ticket_number = data['ticket-counter'] + 1

			ticket_channel = await ctx.guild.create_text_channel("ticket-{}".format(ticket_number))
			await ticket_channel.set_permissions(ctx.guild.get_role(ctx.guild.id), send_messages=False, read_messages=False)

			for role_id in data["valid-roles"]:
					role = ctx.guild.get_role(role_id)

					await ticket_channel.set_permissions(role, send_messages=True, read_messages=True, add_reactions=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)
			
			await ticket_channel.set_permissions(ctx.author, send_messages=True, read_messages=True, add_reactions=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)

			em = discord.Embed(title="New ticket from {}#{}".format(ctx.author.name, ctx.author.discriminator), description= "{}".format(message_content), color=0x00a8ff)

			await ticket_channel.send(embed=em)
			await ticket_channel.send("To close the ticket, type `[p]close`")
			await ticket_channel.send("To save the ticket transcript, type `[p]save`")
			await ticket_channel.send(f'{ctx.author.mention}', delete_after=2)
			pinged_msg_content = ""
			non_mentionable_roles = []
			if data["pinged-roles"]:
					for role_id in data["pinged-roles"]:
							role = ctx.guild.get_role(role_id)
							pinged_msg_content += role.mention
							pinged_msg_content += " "
							if role.mentionable:
									pass
							else:
									await role.edit(mentionable=True)
									non_mentionable_roles.append(role)
					await ticket_channel.send(pinged_msg_content)
					for role in non_mentionable_roles:
							await role.edit(mentionable=False)
			
			ticket_channel_ids = data["ticket-channel-ids"]
			ticket_channel_ids.append(ticket_channel.id)
			post = {'ticket-counter': ticket_number, 'ticket-channel-ids': ticket_channel_ids}
			await ticket_update(ctx.guild.id, post)			
			created_em = discord.Embed(title="Parrot Ticket Bot", description="Your ticket has been created at {}".format(ticket_channel.mention), color=discord.Color.blue())
			await ctx.reply(embed=created_em)


	@commands.command(hidden=False)
	@commands.guild_only()
	@commands.bot_has_permissions(manage_channels=True, embed_links=True)
	async def close(self, ctx):
			'''
			Use this to close a ticket. This command only works in ticket channels.
			
			Syntax:
			`Close`

			Permissions:
			Need Manage Channels for the bot
			'''
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)
			data = collection.find_one({'_id':ctx.guild.id})
			if ctx.channel.id in data["ticket-channel-ids"]:
					channel_id = ctx.channel.id
					def check(message):
							return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() == "close"
					try:
							em = discord.Embed(title="Parrot Ticket Bot", description="Are you sure you want to close this ticket? Reply with `close` if you are sure.", color=discord.Color.blue())
							await ctx.reply(embed=em)
							await self.bot.wait_for('message', check=check, timeout=60)
							await ctx.channel.delete()
							index = data["ticket-channel-ids"].index(channel_id)
							ticket_channel_ids = data['ticket-channel-ids']
							del ticket_channel_ids["ticket-channel-ids"][index]
							post = {'ticket-channel-ids': ticket_channel_ids}
							await ticket_update(ctx.guild.id, post)
					except asyncio.TimeoutError:
							em = discord.Embed(title="Parrot Ticket Bot", description="You have run out of time to close this ticket. Please run the command again.", color=discord.Color.blue())
							await ctx.reply(embed=em)

	
	@commands.command(hidden=False)
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.guild_only()
	@commands.bot_has_permissions(embed_links=True)
	async def save(self, ctx):
			'''
			Use this to save the transcript of a ticket. This command only works in ticket channels.
			
			Syntax:
			`Save`

			Permissions:
			Need Embed Links for the bot
			'''
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)
			data = collection.find_one({'_id':ctx.guild.id})
			if ctx.channel.id in data["ticket-channel-ids"]:
					def check(message):
						return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() == "save"
					try:
							em = discord.Embed(title="Parrot Ticket Bot", description="Are you sure you want to save the transcript of this ticket? Reply with `save` if you are sure.", color=discord.Color.blue())
							await ctx.reply(embed=em)
							await self.bot.wait_for('message', check=check, timeout=60)
							transcript = await chat_exporter.export(ctx.channel)
							if transcript is None: return
							transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{ctx.channel.name}.html")
							await ctx.reply(file=transcript_file)
					except asyncio.TimeoutError:
							em = discord.Embed(title="Parrot Ticket Bot", description="You have run out of time to save the transcript of this ticket. Please run the command again.", color=discord.Color.blue())
							await ctx.reply(embed=em)



	@commands.command(hidden=False)
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.guild_only()
	@has_verified_role_ticket()
	@commands.bot_has_permissions(embed_links=True)
	async def addaccess(self, ctx: Context, *, role:discord.Role):
			'''
			This can be used to give a specific role access to all tickets. This command can only be run if you have an admin-level role for this bot.
			
			Syntax:
			`Addaccess <Role:Mention/ID>`

			Permissions:
			Need Embed Links permission for the bot and Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			(`Help addadminrole` for more info)
			'''
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)
			data = collection.find_one({'_id': ctx.guild.id})
			if role.id not in data["valid-roles"]:
				valid_roles = data["valid-roles"].append(role.id)
				post = {'valid-roles': valid_roles}
				await ticket_update(ctx.guild.id, post)
				em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully added `{}` to the list of roles with access to tickets.".format(role.name), color=discord.Color.blue())
				await ctx.reply(embed=em)
			else:
					em = discord.Embed(title="Parrot Ticket Bot", description="That role already has access to tickets!", color=discord.Color.blue())
					await ctx.reply(embed=em)


	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.command(hidden=False)
	@commands.guild_only()
	@has_verified_role_ticket()
	@commands.bot_has_permissions(embed_links=True)
	async def delaccess(self, ctx: Context, *, role:discord.Role):
			'''
			This can be used to remove a specific role's access to all tickets. This command can only be run if you have an admin-level role for this bot.
			
			Syntax:
			`Delaccess <Role:Mention/ID>`

			Permissions:
			Need Embed Links permission for the bot and Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			(`Help addadminrole` for more info)
			'''
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)
			data = collection.find_one({'_id':ctx.guild.id})
			valid_roles = data["valid-roles"]
			if role.id in valid_roles:
					index = valid_roles.index(role.id)
					del valid_roles[index]
					post = {'valid-roles': valid_roles}
					await ticket_update(ctx.guild.id, post)
					em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully removed `{}` from the list of roles with access to tickets.".format(role.name), color=discord.Color.blue())
					await ctx.reply(embed=em)
			else:	
					em = discord.Embed(title="Parrot Ticket Bot", description="That role already doesn't have access to tickets!", color=discord.Color.blue())
					await ctx.reply(embed=em)


	@commands.command(hidden=False)
	@commands.guild_only()
	@commands.has_permissions(administrator=True)
	@commands.bot_has_permissions(embed_links=True)
	async def addadminrole(self, ctx: Context, *, role:discord.Role):
			'''
			This command gives all users with a specific role access to the admin-level commands for the bot, such as `Addpingedrole` and `Addaccess`.
			
			Syntax:
			`Addadminrole <Role:Mention/ID>`

			Permissions:
			Need Embed Links permission for the bot and Administrator permission for the user.
			'''
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)
			data = collection.find_one({'_id':ctx.guild.id})
			if role.id not in data['verified-roles']:
				verified_roles = data["verified-roles"].append(role.id)
				await ticket_update(ctx.guild.id, {"verified-roles": verified_roles})
				em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully added `{}` to the list of roles that can run admin-level commands!".format(role.name), color=discord.Color.blue())
				await ctx.reply(embed=em)
			else:
				em = discord.Embed(title="Parrot Ticket Bot", description="That role already getting pinged when new tickets are created!", color=discord.Color.blue())
				await ctx.reply(embed=em)
			

	@commands.command(hidden=False)
	@commands.guild_only()
	@has_verified_role_ticket()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def addpingedrole(self, ctx: Context, *, role:discord.Role):
			'''
			This command adds a role to the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot.
			
			Syntax:
			`Addpingedrole <Role:Mention/ID>`

			Permissions:
			Need Embed Links permission for the bot and Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			(`Help addadminrole` for more info)
			'''
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)
			data = collection.find_one({'_id':ctx.guild.id})
			if role.id not in data["pinged-roles"]:
					pinged_roles = data["pinged-roles"].append(role.id)
					post = { 'pinged-roles': pinged_roles}
					await ticket_update(ctx.guild.id, post)
					em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully added `{}` to the list of roles that get pinged when new tickets are created!".format(role.name), color=discord.Color.blue())
					await ctx.reply(embed=em)
			else:
					em = discord.Embed(title="Parrot Ticket Bot", description="That role already receives pings when tickets are created.", color=discord.Color.blue())
					await ctx.reply(embed=em)


	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.has_permissions(administrator=True)
	@commands.bot_has_permissions(embed_links=True)
	async def deladminrole(self, ctx: Context, *, role:discord.Role):
			"""
			This command removes access for all users with the specified role to the admin-level commands for the bot, such as `Addpingedrole` and `Addaccess`.
			
			Syntax:
			`Deladminrole <Role:Mention/ID>`

			Permissions:
			Need Embed Links permission for the bot and Administrator permission for the user.
			"""
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)
			data = collection.find_one({'_id':ctx.guild.id})
			admin_roles = data["verified-roles"]
			if role.id in admin_roles:
					index = admin_roles.index(role.id)
					del admin_roles[index]
					post = {"verified-roles": admin_roles}
					await ticket_update(ctx.guild.id, post)
					em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully removed `{}` from the list of roles that get pinged when new tickets are created.".format(role.name), color=discord.Color.blue())
					await ctx.reply(embed=em)
			else:
					em = discord.Embed(title="Parrot Ticket Bot", description="That role isn't getting pinged when new tickets are created!", color=discord.Color.blue())
					await ctx.reply(embed=em)


	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@has_verified_role_ticket()
	@commands.bot_has_permissions(embed_links=True)
	async def delpingedrole(self, ctx: Context, *, role:discord.Role):
			'''
			This command removes a role from the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot.
			
			Syntax:
			`Delpingedrole <Role:Mention/ID>`

			Permissions:
			Need Embed Links permission for the bot and Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			(`Help addadminrole` for more info)
			'''
			if not collection.find_one({'_id': ctx.guild.id}): await ticket_on_join(ctx.guild.id)
			data = collection.find_one({'_id':ctx.guild.id})
			pinged_roles = data["pinged-roles"]
			if role.id in pinged_roles:
					index = pinged_roles.index(role.id)
					del pinged_roles[index]
					post = {'pinged-roles': pinged_roles}
					await ticket_update(ctx.guild.id, post)
					em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully removed `{}` from the list of roles that get pinged when new tickets are created.".format(role.name), color=discord.Color.blue())
					await ctx.reply(embed=em)
			else:
					em = discord.Embed(title="Parrot Ticket Bot", description="That role already isn't getting pinged when new tickets are created!", color=discord.Color.blue())
					await ctx.reply(embed=em)
		
def setup(bot):
	bot.add_cog(ticket(bot))
