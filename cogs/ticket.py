from discord.ext import commands
import discord, json, asyncio

import chat_exporter, io
class ticket(commands.Cog, name="Ticket", command_attrs=dict(hidden=False)):
	"""A simple ticket serverive, trust me it's better than YAG. LOL!"""
	def __init__(self, bot):
		self.bot = bot 

	@commands.command(hidden=False)
	@commands.guild_only()
	@commands.cooldown(1, 60, commands.BucketType.member)
	@commands.bot_has_permissions(manage_channels=True, embed_links=True)
	async def new(self, ctx, *, args = None):
			'''
			This creates a new ticket. Add any words after the command if you'd like to send a message when we initially create your ticket.
			
			Syntax:
			`New [Argument:Text]`

			Cooldown is of 60 seconds after one time use, per member

			Permissions:
			Need Manage Channels and Embed Links permissions for the bot.
			'''

			await self.bot.wait_until_ready()

			if args == None:
					message_content = "Please wait, we will be with you shortly!"
			
			else:
					message_content = "".join(args)

			with open("data.json") as f:
					data = json.load(f)

			for current_guild in data['guild']:
				if current_guild['id'] == ctx.guild.id:
					ticket_number = int(current_guild["ticket-counter"])
					ticket_number += 1
					break
			print(current_guild)
			ticket_channel = await ctx.guild.create_text_channel("ticket-{}".format(ticket_number))
			await ticket_channel.set_permissions(ctx.guild.get_role(ctx.guild.id), send_messages=False, read_messages=False)

			for role_id in current_guild["valid-roles"]:
					role = ctx.guild.get_role(role_id)

					await ticket_channel.set_permissions(role, send_messages=True, read_messages=True, add_reactions=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)
			
			await ticket_channel.set_permissions(ctx.author, send_messages=True, read_messages=True, add_reactions=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)

			em = discord.Embed(title="New ticket from {}#{}".format(ctx.author.name, ctx.author.discriminator), description= "{}".format(message_content), color=0x00a8ff)

			await ticket_channel.send(embed=em)
			await ticket_channel.send("To close the ticket, type `$close`")
			await ticket_channel.send("To save the ticket transcript, type `$save`")
			await ticket_channel.send(f'{ctx.author.mention}', delete_after=2)
			pinged_msg_content = ""
			non_mentionable_roles = []

			if current_guild["pinged-roles"] != []:

					for role_id in current_guild["pinged-roles"]:
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
			
			current_guild["ticket-channel-ids"].append(ticket_channel.id)

			current_guild["ticket-counter"] = int(ticket_number)
			with open("data.json", 'w') as f:
					json.dump(data, f)
			
			created_em = discord.Embed(title="Parrot Ticket Bot", description="Your ticket has been created at {}".format(ticket_channel.mention), color=discord.Color.blue())
			
			await ctx.send(embed=created_em)


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
			with open('data.json') as f:
					data = json.load(f)

			for current_guild in data['guild']:
				if current_guild['id'] == ctx.guild.id:
					break
			
			if ctx.channel.id in current_guild["ticket-channel-ids"]:

					channel_id = ctx.channel.id

					def check(message):
							return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() == "close"

					try:

							em = discord.Embed(title="Parrot Ticket Bot", description="Are you sure you want to close this ticket? Reply with `close` if you are sure.", color=discord.Color.blue())
					
							await ctx.send(embed=em)
							await self.bot.wait_for('message', check=check, timeout=60)
							await ctx.channel.delete()

							index = current_guild["ticket-channel-ids"].index(channel_id)
							del current_guild["ticket-channel-ids"][index]

							with open('data.json', 'w') as f:
									json.dump(data, f)
					
					except asyncio.TimeoutError:
							em = discord.Embed(title="Parrot Ticket Bot", description="You have run out of time to close this ticket. Please run the command again.", color=discord.Color.blue())
							await ctx.send(embed=em)

	
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
			with open('data.json') as f:
					data = json.load(f)

			for current_guild in data['guild']:
				if current_guild['id'] == ctx.guild.id:
					break
			
			if ctx.channel.id in current_guild["ticket-channel-ids"]:

					def check(message):
						return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() == "save"

					try:

							em = discord.Embed(title="Parrot Ticket Bot", description="Are you sure you want to save the transcript of this ticket? Reply with `save` if you are sure.", color=discord.Color.blue())
					
							await ctx.send(embed=em)
							await self.bot.wait_for('message', check=check, timeout=60)
							transcript = await chat_exporter.export(ctx.channel)
							if transcript is None: return

							transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{ctx.channel.name}.html")

							await ctx.send(file=transcript_file)

					except asyncio.TimeoutError:
							em = discord.Embed(title="Parrot Ticket Bot", description="You have run out of time to save the transcript of this ticket. Please run the command again.", color=discord.Color.blue())
							await ctx.send(embed=em)



	@commands.command(hidden=False)
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.guild_only()
	@commands.bot_has_permissions(embed_links=True)
	async def addaccess(self,ctx, role:discord.Role=None):
			'''
			This can be used to give a specific role access to all tickets. This command can only be run if you have an admin-level role for this bot.
			
			Syntax:
			`Addaccess <Role:Mention/ID>`

			Cooldown of 5 seconds after one time use, per member.

			Permissions:
			Need Embed Links permission for the bot and Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			(`Help addadminrole` for more info)
			'''

			with open('data.json') as f:
					data = json.load(f)
			
			role_id = role.id

			valid_user = False

			for current_guild in data['guild']: 
				if current_guild['id'] == ctx.guild.id:
					break
	
			for role_id in current_guild["verified-roles"]:
					try:
							if ctx.guild.get_role(role_id) in ctx.author.roles:
									valid_user = True
					except:
							pass
			
			if valid_user or ctx.author.guild_permissions.administrator:
					role_id = int(role_id)

					if role_id not in current_guild["valid-roles"]:

							try:
									role = ctx.guild.get_role(role_id)

									with open("data.json") as f:
											data = json.load(f)

									for current_guild in data['guild']:
										if current_guild["id"] == ctx.guild.id:
											break

									current_guild["valid-roles"].append(role_id)

									with open('data.json', 'w') as f:
											json.dump(data, f)
									
									em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully added `{}` to the list of roles with access to tickets.".format(role.name), color=discord.Color.blue())

									await ctx.send(embed=em)

							except:
									em = discord.Embed(title="Parrot Ticket Bot", description="That isn't a valid role ID. Please try again with a valid role ID.")
									await ctx.send(embed=em)
					
					else:
							em = discord.Embed(title="Parrot Ticket Bot", description="That role already has access to tickets!", color=discord.Color.blue())
							await ctx.send(embed=em)
			
			else:
					em = discord.Embed(title="Parrot Ticket Bot", description="Sorry, you don't have permission to run that command.", color=discord.Color.blue())
					await ctx.send(embed=em)


	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.command(hidden=False)
	@commands.guild_only()
	@commands.bot_has_permissions(embed_links=True)
	async def delaccess(self,ctx, role:discord.Role=None):
			'''
			This can be used to remove a specific role's access to all tickets. This command can only be run if you have an admin-level role for this bot.
			
			Syntax:
			`Delaccess <Role:Mention/ID>`

			Cooldown of 5 seconds after one time use, per member.

			Permissions:
			Need Embed Links permission for the bot and Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			(`Help addadminrole` for more info)
			'''
			
			role_id = role.id

			with open('data.json') as f:
					data = json.load(f)
			
			valid_user = False
			for current_guild in data['guild']:
				if current_guild['id'] == ctx.guild.id:
					break
					
			for role_id in current_guild["verified-roles"]:
					try:
							if ctx.guild.get_role(role_id) in ctx.author.roles:
									valid_user = True
					except:
							pass

			if valid_user or ctx.author.guild_permissions.administrator:

					try:
							role_id = int(role_id)
							role = ctx.guild.get_role(role_id)

							with open("data.json") as f:
									data = json.load(f)
							
							for current_guild in data['guild']:
								if current_guild['id'] == ctx.guild.id:
									break 

							valid_roles = current_guild["valid-roles"]

							if role_id in valid_roles:
									index = valid_roles.index(role_id)

									del valid_roles[index]

									current_guild["valid-roles"] = valid_roles

									with open('data.json', 'w') as f:
											json.dump(data, f)

									em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully removed `{}` from the list of roles with access to tickets.".format(role.name), color=discord.Color.blue())

									await ctx.send(embed=em)
							
							else:
									
									em = discord.Embed(title="Parrot Ticket Bot", description="That role already doesn't have access to tickets!", color=discord.Color.blue())
									await ctx.send(embed=em)

					except:
							em = discord.Embed(title="Parrot Ticket Bot", description="That isn't a valid role ID. Please try again with a valid role ID.")
							await ctx.send(embed=em)
			
			else:
					em = discord.Embed(title="Parrot Ticket Bot", description="Sorry, you don't have permission to run that command.", color=discord.Color.blue())
					await ctx.send(embed=em)


	@commands.command(hidden=False)
	@commands.guild_only()
	@commands.has_permissions(administrator=True)
	@commands.bot_has_permissions(embed_links=True)
	async def addadminrole(self, ctx, role:discord.Role=None):
			'''
			This command gives all users with a specific role access to the admin-level commands for the bot, such as `Addpingedrole` and `Addaccess`.
			
			Syntax:
			`Addadminrole <Role:Mention/ID>`

			Cooldown of 5 seconds after one time use, per member.

			Permissions:
			Need Embed Links permission for the bot and Administrator permission for the user.
			'''
			role_id = role.id
			try:
					role_id = int(role_id)
					role = ctx.guild.get_role(role_id)

					with open("data.json") as f:
							data = json.load(f)

					for current_guild in data['guild']:
						if current_guild['id'] == ctx.guild.id:
							break 

					current_guild["verified-roles"].append(role_id)

					with open('data.json', 'w') as f:
							json.dump(data, f)
					
					em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully added `{}` to the list of roles that can run admin-level commands!".format(role.name), color=discord.Color.blue())
					await ctx.send(embed=em)

			except:
					em = discord.Embed(title="Parrot Ticket Bot", description="That isn't a valid role ID. Please try again with a valid role ID.")
					await ctx.send(embed=em)


	@commands.command(hidden=False)
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def addpingedrole(self, ctx, role:discord.Role=None):
			'''
			This command adds a role to the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot.
			
			Syntax:
			`Addpingedrole <Role:Mention/ID>`

			Cooldown of 5 seconds after one time use, per member.

			Permissions:
			Need Embed Links permission for the bot and Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			(`Help addadminrole` for more info)
			'''
			role_id = role.id
			with open('data.json') as f:
					data = json.load(f)
			
			valid_user = False

			for current_guild in data['guild']:
				if current_guild['id'] == ctx.guild.id:
					break 

			for role_id in current_guild["verified-roles"]:
					try:
							if ctx.guild.get_role(role_id) in ctx.author.roles:
									valid_user = True
					except:
							pass
			
			if valid_user or ctx.author.guild_permissions.administrator:

					role_id = int(role_id)

					if role_id not in current_guild["pinged-roles"]:

							try:
									role = ctx.guild.get_role(role_id)

									with open("data.json") as f:
											data = json.load(f)

									for current_guild in data['guild']:
										if current_guild['id'] == ctx.guild.id:
											break

									current_guild["pinged-roles"].append(role_id)

									with open('data.json', 'w') as f:
											json.dump(data, f)

									em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully added `{}` to the list of roles that get pinged when new tickets are created!".format(role.name), color=discord.Color.blue())

									await ctx.send(embed=em)

							except:
									em = discord.Embed(title="Parrot Ticket Bot", description="That isn't a valid role ID. Please try again with a valid role ID.")
									await ctx.send(embed=em)
							
					else:
							em = discord.Embed(title="Parrot Ticket Bot", description="That role already receives pings when tickets are created.", color=discord.Color.blue())
							await ctx.send(embed=em)
			
			else:
					em = discord.Embed(title="Parrot Ticket Bot", description="Sorry, you don't have permission to run that command.", color=discord.Color.blue())
					await ctx.send(embed=em)


	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.has_permissions(administrator=True)
	@commands.bot_has_permissions(embed_links=True)
	async def deladminrole(self, ctx, role:discord.Role=None):
			"""
			This command removes access for all users with the specified role to the admin-level commands for the bot, such as `Addpingedrole` and `Addaccess`.
			
			Syntax:
			`Deladminrole <Role:Mention/ID>`

			Cooldown of 5 seconds after one time use, per member.

			Permissions:
			Need Embed Links permission for the bot and Administrator permission for the user.
			"""
			role_id = role.id
			try:
					role_id = int(role_id)
					role = ctx.guild.get_role(role_id)

					with open("data.json") as f:
							data = json.load(f)

					for current_guild in data['guild']:
						if current_guild['id'] == ctx.guild.id:
							break 

					admin_roles = current_guild["verified-roles"]

					if role_id in admin_roles:
							index = admin_roles.index(role_id)

							del admin_roles[index]

							current_guild["verified-roles"] = admin_roles

							with open('data.json', 'w') as f:
									json.dump(data, f)
							
							em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully removed `{}` from the list of roles that get pinged when new tickets are created.".format(role.name), color=discord.Color.blue())

							await ctx.send(embed=em)
					
					else:
							em = discord.Embed(title="Parrot Ticket Bot", description="That role isn't getting pinged when new tickets are created!", color=discord.Color.blue())
							await ctx.send(embed=em)

			except:
					em = discord.Embed(title="Parrot Ticket Bot", description="That isn't a valid role ID. Please try again with a valid role ID.")
					await ctx.send(embed=em)


	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def delpingedrole(self, ctx, role:discord.Role=None):
			'''
			This command removes a role from the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot.
			
			Syntax:
			`Delpingedrole <Role:Mention/ID>`

			Cooldown of 5 seconds after one time use, per member.

			Permissions:
			Need Embed Links permission for the bot and Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			(`Help addadminrole` for more info)
			'''
			role_id = role.id 
			with open('data.json') as f:
					data = json.load(f)
			
			valid_user = False
			for current_guild in data['guild']:
				if current_guild['id'] == ctx.guild.id:
					break 

			for role_id in current_guild["verified-roles"]:
					try:
							if ctx.guild.get_role(role_id) in ctx.author.roles:
									valid_user = True
					except:
							pass
			
			if valid_user or ctx.author.guild_permissions.administrator:

					try:
							role_id = int(role_id)
							role = ctx.guild.get_role(role_id)

							with open("data.json") as f:
									data = json.load(f)
							
							for current_guild in data['guild']:
								if current_guild['id'] == ctx.guild.id:
									break

							pinged_roles = current_guild["pinged-roles"]

							if role_id in pinged_roles:
									index = pinged_roles.index(role_id)

									del pinged_roles[index]

									current_guild["pinged-roles"] = pinged_roles

									with open('data.json', 'w') as f:
											json.dump(data, f)

									em = discord.Embed(title="Parrot Ticket Bot", description="You have successfully removed `{}` from the list of roles that get pinged when new tickets are created.".format(role.name), color=discord.Color.blue())
									await ctx.send(embed=em)
							
							else:
									em = discord.Embed(title="Parrot Ticket Bot", description="That role already isn't getting pinged when new tickets are created!", color=discord.Color.blue())
									await ctx.send(embed=em)

					except:
							em = discord.Embed(title="Parrot Ticket Bot", description="That isn't a valid role ID. Please try again with a valid role ID.")
							await ctx.send(embed=em)
			
			else:
					em = discord.Embed(title="Parrot Ticket Bot", description="Sorry, you don't have permission to run that command.", color=discord.Color.blue())
					await ctx.send(embed=em)
		
def setup(bot):
	bot.add_cog(ticket(bot))
