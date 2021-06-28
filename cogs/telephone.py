# "_id": guild_id,
# "channel": None,
# "pingrole": None,
# "is_line_busy": False,
# "memberping": None,
# "blocked": []

from discord.ext import commands
import discord, random, asyncio, typing

from core.cog import Cog
from core.bot import Parrot
from core.ctx import Context

from database.telephone import collection, telephone_update, telephone_on_join

class Telephone(Cog, name='telephone'):
	"""Fun cog to make real calls over the server"""

	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.command()
	@commands.cooldown(1, 30, commands.BucketType.guild)
	@commands.guild_only()
	@commands.has_permissions(manage_guild=True)
	async def telsetup(self, ctx: Context, setting: str, *, arg: typing.Union[discord.TextChannel, discord.Role, discord.Member, int]):
		"""
		To set the telephone phone line, in the server to call and receive the call from other server.

		Syntax:
		`Telsetup <Settings:Text> <Arguments:Text>`

		Permissions:
		Need Manage Server permission for the user.
		"""
		settings = ['channel', 'pingrole', 'memberping']

		if not collection.find_one({'_id': ctx.guild.id}):
			await telephone_on_join(ctx.guild.id)

		if not arg or not settings:
			data = collection.find_one({'_id': ctx.guild.id})
			await ctx.send(f"Invalid setting. Available setting type: `channel`, `pingrole`, `memberping`, `block`. This server current Telephone Settings are:-\n"
										 f"> Telephone Channel:\n`{data['channel']}`\n"
										 f"> Telephone Pingrole:\n`{data['pingrole']}`\n"
										 f"> Telephone Memberping:\n`{data['memberping']}`\n"
										 f"> Telephone Blocked:\n`{', '.join(data['blocked'])}`\n"
										 f"> Is your line busy:\n`{data['is_line_busy']}`")

		if (setting.lower() in settings) and (type(arg) in [discord.TextChannel, discord.Role, discord.Member]):
				await telephone_update(ctx.guild.id, setting.lower(), arg.id)
				await ctx.reply(f'{ctx.author.mention} Success! {setting.lower()}: {arg.name} ({arg.id})')

		if setting.lower() == 'block' and (type(arg) == int):
			collection.update_one({'_id': ctx.guild.id}, { '$addToSet': { 'blocked': int(arg) } })
			await ctx.reply(f'{ctx.author.mention} Success! blocked: {arg}')
			return

	@commands.command()
	@commands.max_concurrency(1, commands.BucketType.guild)
	@commands.guild_only()
	@commands.cooldown(1, 30, commands.BucketType.guild)
	async def dial(self, ctx: Context, number: typing.Union[discord.Guild, int]):
		"""
		To dial to other server. Do not misuse this. Else you RIP :|

		Syntax:
		`Dial <Number:Whole Number>`
		"""
		channel = ctx.channel
		self_guild = collection.find_one({'_id': ctx.guild.id})
		if not self_guild: return await ctx.reply(f"{ctx.author.mention} no telephone line channel is set for this server, ask your Server Manager to fix this.")
		target_guild = collection.find_one({'_id': number})
		if not target_guild: return await ctx.reply(f"{ctx.author.mention} no telephone line channel is set for the **{number}** server, or the number you entered do not match with any other server!")

		if target_guild['is_line_busy']:
			return await ctx.reply(f"Can not make a connection to **{number} ({self.bot.get_guild(target_guild['_id']).name})**. Line busy!")

		await ctx.reply(f"Calling to **{number} ({self.bot.get_guild(target_guild['_id']).name})** ... Waiting for the response ...")
		
		target_channel = self.bot.get_channel(target_guild['channel'])
		if not target_channel: return await ctx.reply("Calling failed! Possible reasons: `Channel deleted`, missing `View Channels` permission.")

		if (target_guild['_id'] in self_guild['blocked']) or (self_guild['_id'] in target_guild['blocked']):
			return await ctx.reply(f'Calling failed! Possible reasons: They blocked You, You blocked Them.')

		await target_channel.send(f"**Incomming call from {ctx.guild.id}. {ctx.guild.name} ...**\n`pickup` to pickup | `hangup` to reject")
		try:
			temp_message = target_channel.send(f'{self.bot.get_guild(target_guild["_id"]).get_role(target_guild["pingrole"]).mention} {self.bot.get_user(target_guild["memberping"]).mention}')
			await temp_message.delete()
		except Exception:
			pass

		def check(m):
			return (m.content.lower() == "pickup" or "hangup") and (m.channel == channel or target_channel)

		try:
			_talk = await self.bot.wait_for('message', check=check, timeout=60)
		except Exception:
			await asyncio.sleep(0.5)
			await target_channel.send(f"Line disconnected from **{ctx.guild.id} ({ctx.guild.name})**. Reason: Line Inactive for more than 60 seconds")
			await ctx.reply(f"Line disconnected from **{number} ({self.bot.get_guild(number).name})**. Reason: Line Inactive for more than 60 seconds")

			await telephone_update(ctx.guild.id, 'is_line_busy', False)
			await telephone_update(number, 'is_line_busy', False)
			return

		if _talk.content.lower() == 'hangup':
			await ctx.reply(f'Disconnected')
			await target_channel.send(f'Disconnected')
			await telephone_update(ctx.guild.id, 'is_line_busy', False)
			await telephone_update(number, 'is_line_busy', False)
			return

		elif _talk.content.lower() == 'pickup':
			await ctx.reply(f"Connected. Say {random.choice(['hi', 'hello', 'heya'])}")
			await target_channel.send(f"Connected. Say {random.choice(['hi', 'hello', 'heya'])}")
			
			await telephone_update(ctx.guild.id, 'is_line_busy', True)
			await telephone_update(number, 'is_line_busy', True)
			
			while True:
				def check(m):
					if (m.channel == target_channel) or (m.channel == channel): return True
					if m.author.bot: return False
					return False
				try:
					talk_message = await self.bot.wait_for('message', check=check, timeout=60.0)
				except Exception:
					await asyncio.sleep(0.5)
					await target_channel.send(f"Line disconnected from **{ctx.guild.id} ({ctx.guild.name})**. Reason: Line Inactive for more than 60 seconds")
					await ctx.reply(f"Line disconnected from **{number} ({self.bot.get_guild(number).name})**. Reason: Line Inactive for more than 60 seconds")

					await telephone_update(ctx.guild.id, 'is_line_busy', False)
					await telephone_update(number, 'is_line_busy', False)
					return

				if talk_message.content.lower() == 'hangup':
					await telephone_update(ctx.guild.id, 'is_line_busy', False)
					await telephone_update(number, 'is_line_busy', False)
					await ctx.send(f'Disconnected')
					await target_channel.send(f'Disconnected')
					return

				elif talk_message.channel == target_channel:
					await channel.send(f"**{talk_message.author.name}#{talk_message.author.discriminator}** {talk_message.clean_content}")

				if talk_message.channel == channel:
					await target_channel.send(f"**{talk_message.author.name}#{talk_message.author.discriminator}** {talk_message.clean_content}")

def setup(bot):
	bot.add_cog(Telephone(bot))
