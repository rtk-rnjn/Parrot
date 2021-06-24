from discord.ext import commands
import discord, json, asyncio, datetime
from utilities.paginator import Paginator

from core.bot import Parrot
from core.ctx import Context
from core.cog import Cog

class Telephone(Cog, name="Telephone"):
		"""Fun cog to make real calls over the server"""

		def __init__(self, bot: Parrot):
				self.bot = bot

		@commands.command()
		@commands.cooldown(1, 30, commands.BucketType.guild)
		@commands.guild_only()
		@commands.has_permissions(manage_guild=True)
		async def settelchannel(self, ctx: Context, channel: discord.TextChannel = None):
				"""
				To set the telephone phone line, in the server to call and receive the call from other server.

				Syntax:
				`Settelchannel [Text Channel:Mention/ID]`

				Cooldown of 30 seconds after one time use, per guild.

				Permissions:
				Need Manage Server permission for the user.
				"""
				if channel is None: channel = ctx.channel
				with open("json/tel.json") as f:
						tel = json.load(f)

				for current_guild in tel['guilds']:
						if current_guild['id'] == ctx.guild.id:
								await ctx.send(f"{ctx.author.mention} **{channel.name} ({channel.id})** already setup to telephone line.")
								break
				else:
						tel['guilds'].append(
								{
										"id": ctx.guild.id,
										"channels": channel.id,
										"is_line_busy": False,
										"pingrole": None,
										"memberping": None,
										"blocked": []
								}
						)
						await ctx.send(f"{ctx.author.mention} successfully added **{channel.name} ({channel.id})** to the telephone line.")
				with open("json/tel.json", "w+") as f:
						json.dump(tel, f)

		@commands.command()
		@commands.cooldown(1, 30, commands.BucketType.guild)
		@commands.guild_only()
		@commands.has_permissions(manage_guild=True)
		async def edittelchannel(self, ctx: Context, channel: discord.TextChannel = None):
				"""
				To edit the already set the telephone line, in the server to call and receive the call from other server.

				Syntax:
				`Edittelchannel [Text Channel:Mention/ID]`

				Cooldown of 30 seconds after one time use, per guild.

				Permissions:
				Need Manage Server permission for the user.
				"""
				if channel is None: channel = ctx.channel
				with open("json/tel.json") as f:
						tel = json.load(f)

				for current_guild in tel['guilds']:
						if current_guild['id'] == ctx.guild.id:
								current_guild['channel'] = channel.id
								await ctx.send(f"{ctx.author.mention} **{channel.name} ({channel.id})** is now your telephone line.")
								break
				else:
						tel['guilds'].append(
								{
										"id": ctx.guild.id,
										"channels": channel.id,
										"is_line_busy": False,
										"pingrole": None,
										"memberping": None,
										"blocked": []
								}
						)
						await ctx.send(f"{ctx.author.mention} **{channel.name} ({channel.id})** is now your telephone line.")
				with open("json/tel.json", "w+") as f:
						json.dump(tel, f)

		@commands.command()
		@commands.cooldown(1, 30, commands.BucketType.guild)
		@commands.guild_only()
		@commands.has_permissions(manage_guild=True)
		async def telpingrole(self, ctx: Context, role: discord.Role):
				"""
				A normal phone call usually rings when someone calls, isn't it? Set the ping role (optional) to know someone is calling and we need to pick that up! LOL

				Syntax:
				`Telpingrole <Role:Mention/ID>

				Cooldown of 30 seconds after one time use, per guild.

				Permissions:
				Need Manage Server permission for the user.
				"""
				with open("json/tel.json") as f:
						tel = json.load(f)

				for current_guild in tel['guilds']:
						if current_guild['id'] == ctx.guild.id:
								current_guild['pingrole'] = role.id
								await ctx.send(f"{ctx.author.mention} **{role.name} ({role.id})** is now your telephone line ringing role.")
								break
				else:
						tel['guilds'].append(
								{
										"id": ctx.guild.id,
										"channels": ctx.channel.id,
										"is_line_busy": False,
										"pingrole": role.id,
										"memberping": None,
										"blocked": []
								}
						)
						await ctx.send(f"{ctx.author.mention} **{role.name} ({role.id})** is now your telephone line ringing role.")

				with open("json/tel.json", "w+") as f:
						json.dump(tel, f)

		@commands.command()
		@commands.cooldown(1, 30, commands.BucketType.guild)
		@commands.guild_only()
		@commands.has_permissions(manage_guild=False)
		async def telpingmember(self, ctx: Context, member: discord.Member):
				"""
				A normal phone call usually rings when someone calls, isn't it? Set the ping member (optional) to know someone is calling and we need to pick that up! LOL

				Syntax:
				`Telpingmember <User:Mention/ID>

				Cooldown of 30 seconds after one time use, per guild.

				Permissions:
				Need Manage Server permission for the user.
				"""
				with open("json/tel.json") as f:
						tel = json.load(f)

				for current_guild in tel['guilds']:
						if current_guild['id'] == ctx.guild.id:
								current_guild['memberping'] = member.id
								await ctx.send(f"{ctx.author.mention} **{member.name} ({member.id})** is now your telephone line ringing member.")
								break
				else:
						tel['guilds'].append(
								{
										"id": ctx.guild.id,
										"channels": ctx.channel.id,
										"is_line_busy": False,
										"pingrole": None,
										"memberping": member.id,
										"blocked": []
								}
						)
						await ctx.send(f"{ctx.author.mention} **{member.name} ({member.id})** is now your telephone line ringing member.")

				with open("json/tel.json", "w+") as f:
						json.dump(tel, f)

		@commands.command()
		@commands.cooldown(1, 30, commands.BucketType.guild)
		@commands.guild_only()
		@commands.has_permissions(manage_guild=True)
		async def telblock(self, ctx: Context, *, args):
				"""
				To block the specific incoming number or, blocks all the call.

				Syntax:
				`Telblock <Argument:Number/All>`
				(To block multiple, then the Number should be separated by space. Ex, [p]telblock 123456789 999444555)

				Cooldown of 30 seconds after one time use, per guild.

				Permissions:
				Need Manage Server permission for the user.
				"""
				with open("json/tel.json") as f:
						tel = json.load(f)

				if args.lower() == "all":
						for current_guild in tel['guilds']:
								if current_guild['id'] == ctx.guild.id:
										current_guild['blocked'] = False
										await ctx.send(f"{ctx.author.mention} all incoming calls blocked! To revert the change type `[p]telblock none`")
										break
						else:
								tel['guilds'].append(
										{
												"id": ctx.guild.id,
												"channels": ctx.channel.id,
												"is_line_busy": False,
												"pingrole": None,
												"memberping": None,
												"blocked": False
										}
								)
								await ctx.send(f"{ctx.author.mention} all incoming calls blocked! To revert the change type `[p]telblock none`")

				if args.lower() == "none":
						for current_guild in tel['guilds']:
								if current_guild['id'] == ctx.guild.id:
										current_guild['blocked'] = []
										await ctx.send(f"{ctx.author.mention} all incoming calls allowed!")
										break
						else:
								tel['guilds'].append(
										{
												"id": ctx.guild.id,
												"channels": ctx.channel.id,
												"is_line_busy": False,
												"pingrole": None,
												"memberping": None,
												"blocked": []
										}
								)
								await ctx.send(f"{ctx.author.mention} all incoming calls allowed!")

				try:
						args = args.replace(",", "")
						numbers = args.split(" ")
						for current_guild in tel['guilds']:
								if current_guild['id'] == ctx.guild.id:
										current_guild['blocked'] = numbers
										await ctx.send(f"{ctx.author.mention} **{', '.join(numbers)}** are blocked! They can't call you, neither you can! To revert the change type `[p]telblock none`")
										break
						else:
								tel['guilds'].append(
										{
												"id": ctx.guild.id,
												"channels": ctx.channel.id,
												"is_line_busy": False,
												"pingrole": None,
												"memberping": None,
												"blocked": numbers
										}
								)
								await ctx.send(f"{ctx.author.mention} **{', '.join(numbers)}** are blocked! They can't call you, neither you can! To revert the change type `[p]telblock none`")
				except Exception:
						pass

				with open("json/tel.json", "w+") as f:
						json.dump(tel, f)

		@commands.command()
		@commands.cooldown(1, 5, commands.BucketType.member)
		@commands.guild_only()
		async def telnumber(self, ctx: Context):
				"""
				To display the telephone number. Basically return the Server ID.

				Syntax:
				`Telnumber`

				Cooldown of 5 seconds after one time use, per member.
				"""
				await ctx.send(f"{ctx.author.mention} Telephone number of this guild is **{ctx.guild.id}**")

		@commands.command()
		@commands.cooldown(1, 5, commands.BucketType.member)
		@commands.guild_only()
		async def telchannel(self, ctx: Context):
				"""
				To display the telephone line channel.

				Syntax:
				`Telchannel`

				Cooldown of 5 seconds after one time use, per member.
				"""
				with open("tel.json") as f:
						tel = json.load(f)

				for current_guild in tel['guilds']:
						if current_guild['id'] == ctx.guild.id:
								channel = self.bot.get_channel(current_guild['channels'])
								await ctx.send(f"{ctx.author.mention} Telephone number of this guild is **{channel.mention} ({channel.id})**")
								break

		@commands.command()
		@commands.cooldown(1, 60, commands.BucketType.guild)
		@commands.guild_only()
		async def dial(self, ctx: Context, number: int):
				"""
				To dial to other server. :|

				Syntax:
				`Dial <Number:Whole Number>`

				Cooldown of 60 seconds after one time use, per guild.
				"""
				with open("json/tel.json") as f:
						tel = json.load(f)

				for current_guild in tel['guilds']:
						if current_guild['id'] == ctx.guild.id:
								break
				else: # if no server id exists, then exit
						return await ctx.send(f"{ctx.author.mention} no telephone line channel is set for this server, ask your Server Manager to fix this.")

				for target_guild in tel['guilds']:
						if target_guild['id'] == number:
								break
				else: # if dialing server channel is not exists, then exit
						return await ctx.send(f"{ctx.author.mention} no telephone line channel is set for the **{number}** server, or the number you entered do not match with any other server, or the server is deleted!")

				if target_guild['is_line_busy']: # if telephone line is busy, then exit
						return await ctx.send(f"Can not make a connection to **{number} ({self.bot.get_guild(target_guild['id']).name})**. Line busy!")

				channel = ctx.channel
				message = await ctx.send(f"Calling to **{number} ({self.bot.get_guild(target_guild['id']).name})** ...")
				target_channel = self.bot.get_channel(target_guild['channels'])

				await asyncio.sleep(0.5) # i don't know, why there is a wait here, probably to make it realistic *thinking*

				# check whether connection are being blocked from user itself, or not!
				if (target_guild['id'] in current_guild['blocked']) or (current_guild['id'] in target_guild['blocked']) or (target_guild['blocked'] is False or current_guild['blocked'] is False): return await message.edit(content="Calling failed! Possible reasons: `They blocked You`, `You blocked Them`.")
				if target_channel is None: return await message.edit(content="Calling failed! Possible reasons: `Channel deleted`, `Missing View Channels permission`.")

				try:
						t_message = await target_channel.send(f"{self.bot.get_guild(target_guild['id']).get_role(target_guild['pingrole']).mention} {self.bot.get_user(target_guild['memberping']).mention} ...")
						await asyncio.sleep(0.25)
						await t_message.edit(content=f"Incoming call from **{current_guild['id']} ({self.bot.get_guild(current_guild['id']).name})** ...```\n`pickup` to accept``` ```\n`hungup` to reject```")
				except Exception:
						t_message = await target_channel.send(f"Incoming call from **{current_guild['id']} ({self.bot.get_guild(current_guild['id']).name})** ...```\n`pickup` to accept``````\n`hungup` to reject```")

				def check(m):
						return (m.content.lower() == "pickup" or m.content.lower() == "hangup") and (m.channel == target_channel or m.channel == target_channel)

				try:
						_talk = await self.bot.wait_for('message', check=check, timeout=60)
				except Exception:
						await asyncio.sleep(0.5)
						await t_message.edit(content=f"Line disconnected from **{ctx.guild.id} ({ctx.guild.name})**. Reason: Line Inactive for more than 60 seconds")
						await message.edit(content=f"Line disconnected from **{number} ({self.bot.get_guild(number).name})**. Reason: Line Inactive for more than 60 seconds")

						target_guild['is_line_busy'] = False
						current_guild['is_line_busy'] = False
						with open("json/tel.json", "w+") as f:
								json.dump(tel, f)
						return

				if _talk.content.lower() == "hangup":
						print("hungup detected")
						await asyncio.sleep(0.5)
						await message.edit(content=f"{ctx.author.mention} **{number} {self.bot.get_guild(number).name}** is busy! Please Try later")

						target_guild['is_line_busy'] = False
						current_guild['is_line_busy'] = False
						with open("json/tel.json", "w+") as f:
								json.dump(tel, f)

						return

				if _talk.content.lower() == "pickup":
						await asyncio.sleep(0.25)
						await message.edit(content=f"{ctx.author.mention} **{number}** picked up the phone! Say Hi")
						await t_message.edit(content="Line connected! Say Hi")

						current_guild['is_line_busy'] = True
						target_guild['is_line_busy'] = True
						with open("json/tel.json", "w+") as f:
								json.dump(tel, f)

						while True:
								def check(m):
										if (m.channel == target_channel) or (m.channel == channel) or (m.content.lower() == "pickup" or m.content.lower() == "hangup"): return True
										if m.author.bot: return False
										return False

								try:
										talk = await self.bot.wait_for('message', check=check, timeout=60)
								except Exception:
										await asyncio.sleep(0.5)
										await target_channel.send(content=f"Line disconnected from **{ctx.guild.id} ({ctx.guild.name})**. Reason: Line Inactive for more than 60 seconds")
										await channel.send(content=f"Line disconnected from **{number} ({self.bot.get_guild(number).name})**. Reason: Line Inactive for more than 60 seconds")

										target_guild['is_line_busy'] = False
										current_guild['is_line_busy'] = False
										with open("json/tel.json", "w+") as f:
												json.dump(tel, f)
										return

								talk_msg = (str(talk.content).replace("@", "@\u200b").replace("&", "&\u200b").replace("!", "!\u200b"))[:300:]  # to prevent mentions
								
								if talk_msg.lower() == "hangup":
										print("YES")
										current_guild['is_line_busy'] = False
										target_guild['is_line_busy'] = False
										with open("json/tel.json", "w+") as f:
												json.dump(tel, f)

										await asyncio.sleep(0.5)
										await channel.send(content=f"Line **{number} {self.bot.get_guild(number).name}** disconnected!")
										await target_channel.send(content=f"Line **{ctx.guild.id} {ctx.guild.name}** disconnected!")

										return								
								
								if talk.channel == target_channel:
										await channel.send(f"**{talk.author.name}#{talk.author.discriminator}** {talk_msg}")

								if talk.channel == channel:
										await target_channel.send(f"**{talk.author.name}#{talk.author.discriminator}** {talk_msg}")

		@commands.command()	
		@commands.guild_only()
		@commands.cooldown(1, 10, commands.BucketType.guild)
		@commands.bot_has_permissions(embed_links=True)
		async def phonebook(self, ctx: Context):
				"""
				To get the list of all the telephone lines, basically the servers connected to the telephone.

				Syntax:
				`Phonebook`

				Cooldown of 10 seconds after one time use, per guild.

				Permissions
				Need Embed Links permissions for the bot
				"""
				em_list = []

				with open("json/tel.json") as f:
						tel = json.load(f)

				for guild in tel['guilds']:
						id = guild['id']
						Embed = discord.Embed(title="PhoneBook", description=f"```\nNAME: {self.bot.get_guild(id).name}\nTNUM: {id}```", timestamp=datetime.datetime.utcnow())
						Embed.set_footer(text=f"{ctx.author.name}")
						Embed.set_thumbnail(url=f'{ctx.guild.me.avatar_url}')
						em_list.append(Embed)

				paginator = Paginator(pages=em_list, timeout=60.0)
				try:
						await paginator.start(ctx)
				except Exception:
						pass

def setup(bot):
		bot.add_cog(Telephone(bot))
