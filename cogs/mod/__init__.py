from discord.ext import commands
import discord, json, typing, re
from core import Parrot, Context, Cog
from utilities.checks import mod_cd, is_mod
from utilities.converters import reason_convert, convert_time
from cogs.mod import method as mt
from database.server_config import collection, guild_join
import datetime
class mod(Cog,
					name="moderator",
					description="A simple moderator's tool for managing the server."):
		"""A simple moderator's tool for managing the server."""
		def __init__(self, bot: Parrot):
				self.bot = bot

		async def cog_check(self, ctx):
			if ctx.guild:
				if not collection.find_one({'_id': ctx.guild.id}):
					await guild_join(ctx.guild.id)
					return True
			else: 
				raise commands.NoPrivateMessage()

		async def log(self, ctx, cmd, performed_on, reason):
			if not collection.find_one({'_id': ctx.guild.id}):
				await guild_join(ctx.guild.id)
			
			data = collection.find_one({'_id': ctx.guild.id})

			embed = discord.Embed(title=f"`{cmd}` Used", description=f"```\nREASON: {reason}\n```", timestamp=datetime.utcnow())
			embed.add_field(name="Action Performed by:", value=f"{ctx.author.mention}", inline=True)
			embed.add_field(name="Action Performed on:", value=f"{ctx.author.mention}", inline=True)
			embed.set_footer(text=f"{ctx.guild.name}")
			return await self.bot.get_channel(data['action_log']).send(embed=embed)

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
		async def add_role_bots(self,
														ctx: Context,
														operator: str,
														role: discord.Role,
														*,
														reason: reason_convert = None):
				"""Gives a role to the all bots."""
				await mt._add_roles_bot(ctx, operator, role, reason)
				await self.log(ctx, 'Role', 'Bots', f'{reason}')

		@role.command(name="humans")
		@commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
		@mod_cd()
		@commands.bot_has_permissions(manage_roles=True)
		async def add_role_human(self,
														ctx: Context,
														operator: str,
														role: discord.Role,
														*,
														reason: reason_convert = None):
				"""Gives a role to the all humans."""
				await mt._add_roles_humans(ctx, operator, role, reason)
				await self.log(ctx, 'Role', 'Humans', f'{reason}')

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
											reason: reason_convert = None):
				"""Gives a role to the specified member(s)."""
				await mt._add_roles(ctx, member, role, reason)
				await self.log(ctx, 'Role add', f'{member.mention}', f'{reason}')
		@role.command(name='remove', aliases=['urole', 'removerole', 'rrole'])
		@commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
		@commands.bot_has_permissions(manage_roles=True)
		@mod_cd()
		async def remove_role(self,
													ctx: Context,
													member: discord.Member,
													role: discord.Role,
													*,
													reason: reason_convert = None):
				"""Remove the mentioned role from mentioned/id member"""
				await mt._remove_roles(ctx, member, role, reason)
				await self.log(ctx, 'Role removed', f'{member.mention}', f'{reason}')

		@commands.command(aliases=['hackban'])
		@commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
		@commands.bot_has_permissions(ban_members=True)
		@mod_cd()
		async def ban(self,
									ctx: Context,
									member: discord.User,
									days: typing.Optional[int] = None,
									*,
									reason: reason_convert = None):
				"""To ban a member from guild."""

				if days is None: days = 0
				await mt._ban(ctx, member, days, reason)
				await self.log(ctx, 'Ban', f'{member.mention}', f'{reason}')
		@commands.command(name='massban')
		@commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
		@commands.bot_has_permissions(ban_members=True)
		@mod_cd()
		async def mass_ban(self,
											ctx: Context,
											members: commands.Greedy[discord.User],
											days: typing.Optional[int] = None,
											*,
											reason: reason_convert = None):
				"""To Mass ban list of members, from the guild"""
				if days is None: days = 0
				await mt._mass_ban(ctx, members, days, reason)
				await self.log(ctx, 'Mass Ban', f'{", ".join([member.mention for member in members])}', f'{reason}')
		@commands.command(aliases=['softkill'])
		@mod_cd()
		@commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
		@commands.bot_has_permissions(ban_members=True)
		async def softban(self,
											ctx: Context,
											member: commands.Greedy[discord.Member],
											*,
											reason: reason_convert = None):
				"""To Ban a member from a guild then immediately unban"""
				await mt._softban(ctx, member, reason)
				await self.log(ctx, 'Soft Ban', f'{", ".join([member.mention for member in member])}', f'{reason}')
		@commands.command()
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_permissions=True,
																	manage_roles=True)
		@mod_cd()
		async def block(self,
										ctx: Context,
										member: commands.Greedy[discord.Member],
										*,
										reason: reason_convert = None):
				"""Blocks a user from replying message in that channel."""

				await mt._block(ctx, member, reason)
				await self.log(ctx, 'Block', f'{", ".join([member.mention for member in member])}', f'{reason}')
		@commands.command(aliases=['nuke'])
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_channels=True))
		@commands.bot_has_permissions(manage_channels=True)
		@commands.guild_only()
		@mod_cd()
		async def clone(self,
										ctx: Context,
										channel: discord.TextChannel,
										*,
										reason: reason_convert = None):
				"""To clone the channel or to nukes the channel (clones and delete)."""
				await mt._clone(ctx, channel, reason)
				await self.log(ctx, 'Clone', f'{channel.mention}', f'{reason}')
		@commands.command()
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@mod_cd()
		@commands.bot_has_permissions(kick_members=True)
		async def kick(self,
									ctx: Context,
									member: discord.Member,
									*,
									reason: reason_convert = None):
				"""To kick a member from guild."""
				await mt._kick(ctx, member, reason)
				await self.log(ctx, 'Kick', f'{member.mention}', f'{reason}')
		@commands.command(name='masskick')
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@mod_cd()
		@commands.bot_has_permissions(kick_members=True)
		async def mass_kick(self,
												ctx: Context,
												members: commands.Greedy[discord.Member],
												*,
												reason: reason_convert = None):
				"""To kick a member from guild."""
				await mt._mass_kick(ctx, members, reason)
				await self.log(ctx, 'Mass Kick', f'{", ".join([member.mention for member in members])}', f'{reason}')
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
				await mt._text_lock(ctx, channel)
				await self.log(ctx, 'Text Lock', f'{channel.mention}', f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id})')
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
				await mt._vc_lock(ctx, channel)
				await self.log(ctx, 'VC Lock', f'{channel.mention}', f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id})')
		@commands.group()
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_channels=True))
		@commands.bot_has_permissions(manage_channels=True,
																	manage_roles=True,
																	manage_permissions=True)
		@mod_cd()
		async def unlock(self, ctx: Context):
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
				await mt._text_unlock(ctx, channel)
				await self.log(ctx, 'Text Un-Lock', f'{channel.mention}', f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id})')
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
				await mt._vc_unlock(ctx, channel)
				await self.log(ctx, 'VC Un-Lock', f'{channel.mention}', f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id})')

		@commands.has_permissions(kick_members=True)
		@commands.check_any(is_mod(),
												commands.bot_has_permissions(manage_roles=True))
		@mod_cd()
		@commands.command()
		async def mute(self,
									ctx: Context,
									member: discord.Member,
									seconds: typing.Union[convert_time, int] = None,
									*,
									reason: reason_convert = None):
				"""To restrict a member to sending message in the Server"""
				await mt._mute(ctx, member, seconds, reason)
				await self.log(ctx, 'Mute', f'{member.mention}', f'{reason} | For {seconds}s')
		@commands.command()
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(manage_roles=True)
		@mod_cd()
		async def unmute(self,
										ctx: Context,
										member: discord.Member,
										*,
										reason: reason_convert = None):
				"""To allow a member to sending message in the Text Channels, if muted."""
				await mt._unmute(ctx, member, reason)
				await self.log(ctx, 'Un-Mute', f'{member.mention}', f'{reason}')
		@commands.group(aliases=['purge'])
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_messages=True))
		@mod_cd()
		@commands.bot_has_permissions(read_message_history=True,
																	manage_messages=True)
		async def clean(self, ctx: Context, amount: int):
				"""To delete bulk message."""
				await ctx.message.delete()
				deleted = await ctx.channel.purge(limit=amount, bulk=True)
				await ctx.send(
						f"{ctx.author.mention} {len(deleted)} message deleted :')",
						delete_after=5)
				await self.log(ctx, 'Clean', f'{ctx.channel.mention}', f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id}) | Total message deleted {len(deleted)}')

		@clean.command(name='user', aliases=['member'])
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_messages=True))
		@mod_cd()
		@commands.bot_has_permissions(manage_messages=True,
																	read_message_history=True)
		async def purgeuser(self, ctx: Context, amount: int, *,
												member: discord.Member):
				"""To delete bulk message, of a specified user."""
				def check_usr(m):
						return m.author == member

				deleted = await ctx.channel.purge(limit=amount, bulk=True, check=check_usr)
				await ctx.send(f"{ctx.author.mention} message deleted :')",
											delete_after=5)
				await self.log(ctx, 'Clean user', f'{ctx.channel.mention}', f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id}) | Total message deleted {len(deleted)}')

		@clean.command(name='bots')
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_messages=True))
		@mod_cd()
		@commands.bot_has_permissions(manage_messages=True,
																	read_message_history=True)
		async def purgebots(self, ctx: Context, amount: int):
				"""To delete bulk message, of bots"""
				def check(m):
						return m.author.bot

				deleted = await ctx.channel.purge(limit=amount, bulk=True, check=check)
				await ctx.send(f"{ctx.author.mention} message deleted :')",
											delete_after=5)
				await self.log(ctx, 'Clean Bots', f'{ctx.channel.mention}', f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id}) | Total message deleted {len(deleted)}')
		@clean.command()
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_messages=True))
		@mod_cd()
		@commands.bot_has_permissions(manage_messages=True,
																	read_message_history=True)
		async def regex(self, ctx: Context, amount: int, *, regex: str):
				"""
				To delete bulk message, matching the regex
				"""
				def check(m):
						return re.search(regex, m.message.context)

				deleted = await ctx.channel.purge(limit=amount, bulk=True, check=check)
				await ctx.send(f"{ctx.author.mention} message deleted :')",
											delete_after=5)
				await self.log(ctx, 'Clean Regex', f'{ctx.channel.mention}', f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id}) | Total message deleted {len(deleted)}')
		@commands.command()
		@commands.check_any(is_mod(),
												commands.has_permissions(manage_channels=True))
		@commands.bot_has_permissions(manage_channels=True)
		@mod_cd()
		async def slowmode(self,
											ctx: Context,
											seconds: typing.Union[int, str],
											channel: discord.TextChannel = None,
											*,
											reason: reason_convert = None):
				"""To set slowmode in the specified channel"""
				await mt._slowmode(ctx, seconds, channel, reason)
				await self.log(ctx, 'Slowmode', f'{channel.mention}', f'{reason} | For {seconds}s') 
		@commands.command(brief='To Unban a member from a guild')
		@commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
		@commands.bot_has_permissions(ban_members=True)
		@mod_cd()
		async def unban(self,
										ctx: Context,
										member: discord.User,
										*,
										reason: reason_convert = None):
				"""To Unban a member from a guild"""

				await mt._unban(ctx, member, reason)
				await self.log(ctx, 'Un-Ban', f'{member.mention}', f'{reason}')

		@commands.command()
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
											reason: reason_convert = None):
				"""Unblocks a user from the text channel"""

				await mt._unblock(ctx, member, reason)
				await self.log(ctx, 'Un-Block', f'{", ".join([member.mention for member in member])}', f'{reason}')

		@commands.command()
		@commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
		@commands.bot_has_permissions(embed_links=True)
		@mod_cd()
		@commands.guild_only()
		async def warn(self, ctx: Context, member: discord.Member, *,
									reason: reason_convert):
				"""
		To warn a user
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
		@mod_cd()
		async def warnings(self, ctx: Context, member: discord.Member):
				"""
		To see the number of times the user is being warned
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
		@mod_cd()
		async def clearwarn(self, ctx: Context, member: discord.Member):
				"""
		To clear all the warning from the user
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
