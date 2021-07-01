from discord.ext import commands
import discord, json, typing, asyncio

from core.bot import Parrot
from core.cog import Cog
from core.ctx import Context

from utilities.checks import mod_cd, is_mod
from database.server_config import collection, guild_join, guild_update


class mod(Cog, name="moderator", description="A simple moderator's tool for managing the server."):
		"""A simple moderator's tool for managing the server."""
		def __init__(self, bot: Parrot):
				self.bot = bot

		def cog_check(self, ctx):
				return ctx.guild is not None

		@commands.group()
		@commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
		@mod_cd()
		@commands.bot_has_permissions(manage_roles=True)
		async def role(self, ctx: Context):
				"""Role Management of the server."""
				pass

		@role.command(name="bots")
		@commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
		@mod_cd()
		@commands.bot_has_permissions(manage_roles=True)
		async def add_role_bots(self, ctx: Context, operator:typing.Optional[str]='+', role: discord.Role, *, reason: commands.clean_content = None):
				"""Gives a role to the all bots."""
				reason=f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
				for member in ctx.guild.members:
						try:
								if not member.bot: pass
								else:
									if operator == '+':
										await member.add_roles(role, reason=reason)
									elif operator == '-':
										await member.remove_roles(role, reason=reason)
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
								)

		@role.command(name="humans")
		@commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
		@mod_cd()
		@commands.bot_has_permissions(manage_roles=True)
		async def add_role_human(self,
														ctx: Context, operator:typing.Optional[str]='+', 
														role: discord.Role,
														*,
														reason: commands.clean_content = None):
				"""Gives a role to the all humans."""
				reason=f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
				for member in ctx.guild.members:
						try:
								if member.bot: pass
								else:
									if operator == '+':
										await member.add_roles(role, reason=reason)
									elif operator == '-':
										await member.remove_roles(role, reason=reason)
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
								)

		@role.command(name="add", aliases=['arole', 'giverole', 'grole'])
		@commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
		@commands.guild_only()
		@mod_cd()
		@commands.bot_has_permissions(manage_roles=True)
		async def add_role(self,
											ctx: Context,
											member: discord.Member,
											role: discord.Role,
											*,
											reason: commands.clean_content = None):
				"""Gives a role to the specified member(s)."""
				guild = ctx.guild

				if guild.me.top_role < member.top_role:
						await ctx.reply(
								f"{ctx.author.mention} can't give the role to {member.name} as it's role is above the bot"
						)

				try:
						await member.add_roles(
								role,
								reason=
								f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
						)
						await ctx.reply(
								f"{ctx.author.mention} given {role.name}({role.id}) to {member.name}"
						)
				except Exception as e:
						await ctx.reply(
								f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
						)

		@role.command(name='remove', aliases=['urole', 'removerole', 'rrole'])
		@commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
		@commands.bot_has_permissions(manage_roles=True)
		@mod_cd()
		async def un_role(self,
											ctx: Context,
											member: discord.Member,
											role: discord.Role,
											*,
											reason: commands.clean_content = None):
				"""Remove the mentioned role from mentioned/id member"""
				guild = ctx.guild

				if guild.me.top_role < member.top_role:
						await ctx.reply(
								f"{ctx.author.mention} can't give the role to {member.name} as it's role is above the bot"
						)
				try:
						await member.remove_roles(
								role,
								reason=
								f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
						)
						await ctx.reply(
								f"{ctx.author.mention} removed {role.name}({role.id}) from {member.name}"
						)
				except Exception as e:
						await ctx.reply(
								f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
						)

		@commands.group(aliases=['hackban'])
		@commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
		@commands.bot_has_permissions(ban_members=True)
		@mod_cd()
		async def ban(self,
									ctx: Context,
									member: discord.User,
									days: typing.Optional[int] = None,
									*,
									reason: commands.clean_content = None):
				"""To ban a member from guild."""

				if days is None: days = 0
				try:
						if member.id == ctx.author.id or member.id == self.bot.user.id:
								pass
						else:
								await ctx.guild.ban(
										member,
										reason=
										f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}',
										delete_message_days=days)
								await ctx.reply(
										f"**`{member.name}#{member.discriminator}`** is banned! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Reason: **{reason}**"
								)
				except Exception as e:
						await ctx.reply(
								f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
						)

		@ban.command(name='mass')
		@commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
		@commands.bot_has_permissions(ban_members=True)
		@mod_cd()
		async def mass_ban(self,
											ctx: Context,
											members: commands.Greedy[discord.User],
											days: typing.Optional[int] = None,
											*,
											reason: commands.clean_content = None):
				"""To Mass ban list of members, from the guild"""
				if days is None: days = 0
				_list = members
				for member in members:
						try:
								if member.id == ctx.author.id or member.id == self.bot.user.id:
										pass
								else:
										await ctx.guild.ban(
												member,
												reason=
												f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}',
												delete_message_days=days)
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
								)
								_list.remove(member)
				await ctx.reply(
						f"**{', '.join([member.name for member in members])}** are banned! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Total: **{len(members)}**! Reason: **{reason}**"
				)

		@ban.command(aliases=['softkill'])
		@mod_cd()
		@commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
		@commands.bot_has_permissions(ban_members=True)
		async def softban(self,
											ctx: Context,
											member: commands.Greedy[discord.Member],
											*,
											reason: commands.clean_content = None):
				"""To Ban a member from a guild then immediately unban"""

				for member in member:
						try:
								if member.id == ctx.author.id or member.id == self.bot.user.id:
										pass
								else:
										await member.ban(
												reason=
												f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
										)

										banned_users = await ctx.guild.bans()
										member_n, member_d = member.name, member.discriminator
										for ban_entry in banned_users:
												user = ban_entry.user
												if (user.name, user.discriminator) == (member_n,
																															member_d):
														await ctx.guild.unban(user)

										await ctx.reply(
												f'**`{member.name}#{member.discriminator}`** is banned then unbanned! Responsible moderator: **`{ctx.author.name}#{ctx.authoe.discriminator}`**! Reason: **{reason}**'
										)
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
								)

						await asyncio.sleep(0.25)

		@commands.command(
				hidden=False,
				brief="Blocks a user from replying message in that channel.")
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_permissions=True,
																	manage_roles=True)
		@mod_cd()
		async def block(self,
										ctx: Context,
										member: commands.Greedy[discord.Member],
										*,
										reason: commands.clean_content = None):
				"""Blocks a user from replying message in that channel."""

				for member in member:
						try:
								if member.id == ctx.author.id or member.id == self.bot.user.id:
										pass  # cant mod the calling author or the bot itself
								else:
										await ctx.channel.set_permissions(
												member,
												send_messages=False,
												reason=
												f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
										)
										await ctx.reply(
												f'{ctx.author.mention} overwrite permission(s) for **{member.name}** has been created! **View Channel, and Send Messages** is denied!'
										)
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
								)
						await asyncio.sleep(0.25)

		@commands.command(
				aliases=['nuke'],
				hidden=False,
				brief="To clone the channel or to nukes the channel (clones and delete)."
		)
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_channels=True))
		@commands.bot_has_permissions(manage_channels=True)
		@commands.guild_only()
		@mod_cd()
		async def clone(self,
										ctx: Context,
										channel: discord.TextChannel,
										*,
										reason: commands.clean_content = None):
				"""To clone the channel or to nukes the channel (clones and delete)."""

				if channel is None: channel = ctx.channel

				new_channel = await channel.clone(
						reason=
						f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
				)
				await channel.delete(
						reason=
						f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
				)
				await new_channel.reply(f"{ctx.author.mention}", delete_after=5)

		@commands.group()
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@mod_cd()
		@commands.bot_has_permissions(kick_members=True)
		async def kick(self,
									ctx: Context,
									member: discord.Member,
									*,
									reason: commands.clean_content = None):
				"""To kick a member from guild."""
				try:
						if member.id == ctx.author.id or member.id == self.bot.user.id:
								pass
						else:
								await member.kick(
										reason=
										f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
								)
								await ctx.reply(
										f'**`{member.name}#{member.discriminator}`** is kicked! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Reason: **{reason}**'
								)
				except Exception as e:
						await ctx.reply(
								f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
						)

		@kick.command(name='mass')
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@mod_cd()
		@commands.bot_has_permissions(kick_members=True)
		async def mass_kick(self,
												ctx: Context,
												members: commands.Greedy[discord.Member],
												*,
												reason: commands.clean_content = None):
				"""To kick a member from guild."""
				_list = members
				for member in members:
						try:
								if member.id == ctx.author.id or member.id == self.bot.user.id:
										pass
								else:
										await member.kick(
												reason=
												f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
										)
						except Exception as e:
								_list.remove(member)
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
								)
						await asyncio.sleep(0.25)
				await ctx.reply(
						f"**{', '.join([member.name for member in members])}** are kicked! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Total: **{len(members)}**! Reason: **{reason}**"
				)

		@commands.group()
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_permissions=True,
																	manage_roles=True)
		@mod_cd()
		async def lock(self, ctx: Context):
				"""To lock the channel"""
				pass

		@lock.command(name='text')
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_permissions=True,
																	manage_roles=True)
		@mod_cd()
		async def text_lock(self,
												ctx: Context,
												*,
												channel: discord.TextChannel = None):
				"""To lock the text channel"""
				if channel is None:
						try:
								channel = ctx.channel
								overwrite = channel.overwrites_for(ctx.guild.default_role)
								overwrite.send_messages = False
								await channel.set_permissions(
										ctx.guild.default_role,
										reason=
										f"Action requested by {ctx.author.name}({ctx.author.id})",
										overwrite=overwrite)
								await ctx.reply(f'{ctx.author.mention} channel locked.')
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {channel.name}. Error raised: {e}"
								)

		@lock.command(name='vc')
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_permissions=True,
																	manage_roles=True)
		@mod_cd()
		async def vc_lock(self,
											ctx: Context,
											*,
											channel: discord.VoiceChannel = None):
				"""To lock the Voice Channel"""
				if not channel: channel = ctx.author.voice.channel
				if not channel: return
				try:
						overwrite = channel.overwrites_for(ctx.guild.default_role)
						overwrite.connect = False
						await channel.set_permissions(
								ctx.guild.default_role,
								reason=
								f"Action requested by {ctx.author.name}({ctx.author.id})",
								overwrite=overwrite)
						await ctx.reply(f'{ctx.author.mention} channel locked.')
				except Exception as e:
						await ctx.reply(
								f"Can not able to {ctx.command.name} {channel.name}. Error raised: {e}"
						)

		@commands.group()
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_channels=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_roles=True,
																	manage_permissions=True)
		@mod_cd()
		async def unlock(self,
										ctx: Context,
										channel: commands.Greedy[discord.TextChannel],
										*,
										reason: commands.clean_content = None):
				"""To unlock the channel (Text channel)"""
				pass

		@unlock.command(name='text')
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_permissions=True,
																	manage_roles=True)
		@mod_cd()
		async def text_unlock(self,
													ctx: Context,
													*,
													channel: discord.TextChannel = None):
				"""To unlock the text channel"""
				if channel is None:
						try:
								channel = ctx.channel
								await channel.set_permissions(
										ctx.guild.default_role,
										reason=
										f"Action requested by {ctx.author.name}({ctx.author.id})",
										overwrite=None)
								await ctx.reply(f'{ctx.author.mention} channel locked.')
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {channel.name}. Error raised: {e}"
								)

		@unlock.command(name='vc')
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_permissions=True,
																	manage_roles=True)
		@mod_cd()
		async def vc_unlock(self,
												ctx: Context,
												*,
												channel: discord.VoiceChannel = None):
				"""To unlock the Voice Channel"""
				if not channel: channel = ctx.author.voice.channel
				if not channel: return
				try:
						await channel.set_permissions(
								ctx.guild.default_role,
								reason=
								f"Action requested by {ctx.author.name}({ctx.author.id})",
								overwrite=None)
						await ctx.reply(f'{ctx.author.mention} channel locked.')
				except Exception as e:
						await ctx.reply(
								f"Can not able to {ctx.command.name} {channel.name}. Error raised: {e}"
						)

		@commands.has_permissions(kick_members=True)
		@commands.check_any(is_mod(),
												commands.bot_has_permissions(manage_roles=True))
		@mod_cd()
		@commands.group()
		async def mute(self,
									ctx: Context,
									member: discord.Member,
									seconds: typing.Optional[int] = None,
									*,
									reason: commands.clean_content = None):
				"""To restrict a member to sending message in the Server"""

				if not collection.find_one({'_id': ctx.guild.id}):
						await guild_join(ctx.guild.id)

				data = collection.find_one({'_id': ctx.guild.id})

				muted = ctx.guild.get_role(data['mute_role']) or discord.utils.get(
						ctx.guild.roles, name="Muted")

				if not muted:
						muted = await ctx.guild.create_role(
								name="Muted",
								reason=
								f"Setting up mute role. it's first command is execution, by {ctx.author.name}({ctx.author.id})"
						)
						for channel in ctx.guild.channels:
								try:
										await channel.set_permissions(muted,
																									send_messages=False,
																									read_message_history=False)
								except Exception:
										pass
						await guild_update(ctx.guild.id, {'mute_role': muted.id})
				if seconds is None: seconds = 0
				try:
						if member.id == ctx.author.id or member.id == self.bot.user.id:
								pass
						else:
								await member.add_roles(
										muted,
										reason=
										f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
								)
								await ctx.reply(
										f"{ctx.author.mention} **{member.name}** has been successfully muted {'for' + str(seconds) if (seconds > 0) and (type(seconds) is int) else ''}!"
								)
				except Exception as e:
						await ctx.reply(
								f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
						)

				if seconds > 0:
						await asyncio.sleep(seconds)
						try:
								await member.remove_roles(
										muted,
										reason=
										f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: Mute Duration Expired"
								)
						except Exception:
								pass

		@commands.has_permissions(kick_members=True)
		@commands.check_any(is_mod(),
												commands.bot_has_permissions(manage_roles=True))
		@mod_cd()
		@mute.command()
		async def mass(self,
									ctx: Context,
									members: commands.Greedy[discord.Member],
									seconds: typing.Optional[int] = None,
									*,
									reason: commands.clean_content = None):
				"""To mass mute"""
				if not collection.find_one({'_id': ctx.guild.id}):
						await guild_join(ctx.guild.id)

				data = collection.find_one({'_id': ctx.guild.id})

				muted = ctx.guild.get_role(data['mute_role']) 

				for role in ctx.guild.roles: 
					if 'muted' in (role.name).lower().split():
						muted = role
						break

				if not muted:
						muted = await ctx.guild.create_role(
								name="Muted",
								reason=
								f"Setting up mute role. it's first command is execution, by {ctx.author.name}({ctx.author.id})"
						)
						for channel in ctx.guild.channels:
								try:
										await channel.set_permissions(muted,
																									send_messages=False,
																									read_message_history=False)
								except Exception:
										pass
						await guild_update(ctx.guild.id, {'mute_role': muted.id})
				if seconds is None: seconds = 0
				for member in members:
						try:
								if member.id == ctx.author.id or member.id == self.bot.user.id:
										pass
								else:
										await member.add_roles(
												muted,
												reason=
												f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
										)
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
								)

				await ctx.reply(
						f"{ctx.author.mention} **{', '.join([member.name for member in members])}** has been successfully muted {'for' + str(seconds) if (seconds > 0) and (type(seconds) is int) else ''}!"
				)

				if seconds > 0:
						await asyncio.sleep(seconds)
						for member in members:
								try:
										await member.remove_roles(
												muted,
												reason=
												f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: Mute Duration Expired"
										)
								except Exception:
										pass

		@commands.group(aliases=['purge'])
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_messages=True))
		@mod_cd()
		@commands.bot_has_permissions(read_message_history=True,
																	manage_messages=True)
		async def clean(self, ctx: Context, amount: int):
				"""To delete bulk message."""

				deleted = await ctx.channel.purge(limit=amount + 1, bulk=True)
				await ctx.reply(
						f"{ctx.author.mention} {len(deleted)} message deleted :')",
						delete_after=5)

		@clean.command(name='user')
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_messages=True))
		@mod_cd()
		@commands.bot_has_permissions(manage_messages=True,
																	read_message_history=True)
		async def purgeuser(self, ctx: Context, member: discord.Member,
												amount: int):
				"""To delete bulk message, of a specified user."""
				def check_usr(m):
						return m.author == member

				await ctx.channel.purge(limit=amount, bulk=True, check=check_usr)
				await ctx.reply(f"{ctx.author.mention} message deleted :')",
												delete_after=5)

		@commands.command(brief='To set slowmode in the specified channel.')
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_channels=True))
		@commands.bot_has_permissions(manage_channels=True)
		@mod_cd()
		async def slowmode(self,
											ctx: Context,
											seconds: typing.Union[int, str],
											channel: discord.TextChannel = None,
											*,
											reason: commands.clean_content = None):
				"""To set slowmode in the specified channel"""
				channel = channel or ctx.channel
				if not seconds: seconds = 5
				if seconds:
						if (seconds <= 21600) and (seconds > 0):
								await channel.edit(
										slowmode_delay=seconds,
										reason=
										f"Action Requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
								)
								await ctx.reply(
										f"{ctx.author.mention} {channel} is now in slowmode of **{seconds}**, to reverse type [p]slowmode 0"
								)
						elif seconds == 0 or seconds.lower() == 'off':
								await channel.edit(
										slowmode_delay=seconds,
										reason=
										f"Action Requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
								)
								await ctx.reply(
										f"{ctx.author.mention} {channel} is now not in slowmode.")
						elif (seconds >= 21600) or (seconds < 0):
								await ctx.reply(
										f"{ctx.author.mention} you can't set slowmode in negative numbers or more than 21600 seconds"
								)
						else:
								return  # I dont want to tell error

		@commands.command(brief='To Unban a member from a guild')
		@commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
		@commands.bot_has_permissions(ban_members=True)
		@mod_cd()
		async def unban(self,
										ctx: Context,
										member: discord.User,
										*,
										reason: commands.clean_content = None):
				"""To Unban a member from a guild"""

				await ctx.guild.unban(
						member,
						reason=
						f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
				)
				await ctx.reply(
						f"**`{member.name}#{member.discriminator}`** is unbanned! Responsible moderator: **`{ctx.author.name}#{ctx.author.discriminator}`**! Reason: **{reason}**"
				)

		@commands.command(hidden=False,
											brief='Unblocks a user from the text channel.')
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_permissions=True,
																								manage_roles=True,
																								manage_channels=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_permissions=True,
																	manage_roles=True)
		@mod_cd()
		async def unblock(self,
											ctx: Context,
											member: commands.Greedy[discord.Member],
											*,
											reason: commands.clean_content = None):
				"""Unblocks a user from the text channel"""

				for member in member:
						try:
								if member.permissions_in(ctx.channel).send_messages:
										await ctx.reply(
												f"{ctx.author.mention} {member.name} is already unblocked. They can send message"
										)
								else:
										await ctx.channel.set_permissions(
												member,
												view_channel=None,
												send_messages=None,
												overwrite=None,
												reason=
												f"Action requested by {ctx.author.name}({ctx.author.id}) || Reason: {reason}"
										)
								await ctx.reply(
										f'{ctx.author.mention} overwrite permission(s) for **{member.name}** has been deleted!'
								)
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}"
								)
						await asyncio.sleep(0.25)

		@commands.group()
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_roles=True)
		@mod_cd()
		async def unmute(self,
										ctx: Context,
										member: discord.Member,
										*,
										reason: commands.clean_content = None):
				"""To allow a member to sending message in the Text Channels, if muted."""
				if not collection.find_one({'_id': ctx.guild.id}):
						await guild_join(ctx.guild.id)

				data = collection.find_one({'_id': ctx.guild.id})

				muted = ctx.guild.get_role(data['mute_role']) or discord.utils.get(
						ctx.guild.roles, name="Muted")
				try:
						if muted in member.roles:
								await ctx.reply(
										f'{ctx.author.mention} **{member.name}** has been unmuted now!'
								)
								await member.remove_roles(
										muted,
										reason=
										f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
								)
						else:
								await ctx.reply(
										f"{ctx.author.mention} **{member.name}** already unmuted :')"
								)
				except Exception as e:
						await ctx.reply(
								f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}\n\nMake sure that the bot role is above the target role"
						)

		@unmute.command(name='mass')
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_roles=True)
		@mod_cd()
		async def unmute_mass(self,
													ctx: Context,
													member: commands.Greedy[discord.Member],
													*,
													reason: commands.clean_content = None):
				"""To allow a member to sending message in the Text Channels, if muted."""
				if not collection.find_one({'_id': ctx.guild.id}):
						await guild_join(ctx.guild.id)

				data = collection.find_one({'_id': ctx.guild.id})

				muted = ctx.guild.get_role(data['mute_role']) or discord.utils.get(
						ctx.guild.roles, name="Muted")
				for member in member:
						try:
								if muted in member.roles:
										await ctx.reply(
												f'{ctx.author.mention} **{member.name}** has been unmuted now!'
										)
										await member.remove_roles(
												muted,
												reason=
												f'Action requested by: {ctx.author.name}({ctx.author.id}) || Reason: {reason}'
										)
								else:
										await ctx.reply(
												f"{ctx.author.mention} **{member.name}** already unmuted :')"
										)
						except Exception as e:
								await ctx.reply(
										f"Can not able to {ctx.command.name} {member.name}#{member.discriminator}. Error raised: {e}\n\nMake sure that the bot role is above the target role"
								)

						await asyncio.sleep(0.25)

		@commands.command(
				pass_context=True, )
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(embed_links=True)
		@mod_cd()
		@commands.guild_only()
		async def warn(self, ctx: Context, member: discord.Member, *,
									reason: commands.clean_content):
				"""
		To warn a user

		Syntax:
		`Warn <User:Mention/ID> <Reason>`

		Permissions:
		Need Kick Members permission, for the user and Embed Links for the bot.
		"""
				with open('reports.json', encoding='utf-8') as f:
						try:
								report = json.load(f)
						except ValueError:
								report = {}
								report['users'] = []

				for current_guild in report['reports']:
						if (current_guild['guild_id']
										== ctx.guild.id) and (current_guild['name'] == member.id):
								current_guild['reasons'].append(reason)
								break
				else:
						report['reports'].append({
								'guild_id': ctx.guild.id,
								'name': member.id,
								'reasons': [
										reason,
								]
						})
				with open('json/reports.json', 'w+') as f:
						json.dump(report, f)

				try:
						await member.send(
								f"{member.name}#{member.discriminator} you are being warned for {reason}"
						)
				except Exception:
						await ctx.reply(
								f"{member.name}#{member.discriminator} you are being warned for {reason}"
						)
						pass

		@commands.command(pass_context=True)
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(embed_links=True)
		@commands.guild_only()
		@mod_cd()
		async def warnings(self, ctx: Context, member: discord.Member):
				"""
		To see the number of times the user is being warned

		Syntax:
		`Warn <User:Mention/ID> <Reason>`

		Permissions:
		Need Kick Members permission, for the user and Embed Links for the bot.
		"""
				with open('json/reports.json', encoding='utf-8') as f:
						report = json.load(f)
				for current_guild in report['reports']:
						if (current_guild['guild_id']
										== ctx.guild.id) and (current_guild['name'] == member.id):
								await ctx.reply(
										f"{member.name} has been reported {len(current_guild['reasons'])} times : {', '.join(current_guild['reasons'])}"
								)
								break
				else:
						await ctx.reply(f"{member.name} has never been reported")

		@commands.command()
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(embed_links=True)
		@commands.guild_only()
		@mod_cd()
		async def clearwarn(self, ctx: Context, member: discord.Member):
				"""
		To clear all the warning from the user

		Syntax:
		`Warn <User:Mention/ID> <Reason>`

		Permissions:
		Need Kick Members permission, for the user and Embed Links for the bot.
		"""
				with open('json/reports.json', 'r', encoding='utf-8') as f:
						report = json.load(f)
				for current_guild in report['reports']:
						if member.id == current_guild['name']:
								if (current_guild['guild_id']
												== ctx.guild.id) and (current_guild['name']
																							== member.id):
										current_guild['reasons'] = []
										await ctx.reply(
												f"{ctx.author.mention} cleared all the warning from {member.name}"
										)
										break
						else:
								await ctx.reply(
										f"{ctx.author.mention} {member.name} never being reported")
				with open('json/reports.json', 'w+') as f:
						json.dump(report, f)


def setup(bot):
		bot.add_cog(mod(bot))
