from discord.ext import commands 
import discord, json, datetime
from math import ceil

class Leveling(commands.Cog, name="Leveling"):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=['level'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def rank(self, ctx, target:discord.Member=None):
		"""
		To get your (or your friend's) chat experience

		Syntax:
		`Rank [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links permission for the bot.
		"""
		with open("config.json") as f:
			guilds = json.load(f)

		if ctx.guild.id in guilds['guilds']: return
		if target is None: target = ctx.author

		with open('level.json', encoding='utf-8') as f:
			level = json.load(f)
		for current_guild in level['levels']:
			if (current_guild['guild_id'] == ctx.guild.id) and (current_guild['name'] == target.id):
				xp = current_guild['xp']
				lvl = current_guild['lvl']
				await ctx.send(embed=discord.Embed(title=f"{target.name}", description=f"`{target.name}` Chat experience is **{xp}** and on level **{int(lvl / 100)}**! GG!", timestamp=datetime.datetime.utcnow()))
				break
		else:
			level['levels'].append({
				'guild_id': ctx.guild.id,
				'name': target.id,
				'xp': 10,
				'lvl': 1
			})
			await ctx.send(embed=discord.Embed(title=f"{target.name}", description=f"`{target.name}` Chat experience is **10** and on level **0**! GG!"), timestamp=datetime.datetime.utcnow())
		with open('level.json', 'w+') as f:
			json.dump(level, f)


	@commands.command(aliases=['lb'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def leaderboard(self, ctx):
		"""
		To get leaderboard of the server, in terms of chat experience

		Syntax:
		`Leaderboard`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links permission for the bot.
		"""
		with open("level.json") as f:
			level = json.load(f)
		
		lb = []
		
		for temp in level['levels']:
			if temp['guild_id'] == ctx.guild.id:
				lb.append(temp)

		sort_lb = sorted(lb, key=lambda i : i['lvl'], reverse=True)
		
		name1 = self.bot.get_user(sort_lb[0]['name']).mention
		lvl1 = sort_lb[0]['lvl']

		name2 = self.bot.get_user(sort_lb[1]['name']).mention
		lvl2 = sort_lb[1]['lvl']

		name3 = self.bot.get_user(sort_lb[2]['name']).mention
		lvl3 = sort_lb[2]['lvl']

		name4 = self.bot.get_user(sort_lb[3]['name']).mention
		lvl4 = sort_lb[3]['lvl']

		name5 = self.bot.get_user(sort_lb[4]['name']).mention
		lvl5 = sort_lb[4]['lvl']

		name6 = self.bot.get_user(sort_lb[5]['name']).mention
		lvl6 = sort_lb[5]['lvl']

		name7 = self.bot.get_user(sort_lb[6]['name']).mention
		lvl7 = sort_lb[6]['lvl']

		name8 = self.bot.get_user(sort_lb[7]['name']).mention
		lvl8 = sort_lb[7]['lvl']

		name9 = self.bot.get_user(sort_lb[8]['name']).mention
		lvl9 = sort_lb[8]['lvl']

		name10 = self.bot.get_user(sort_lb[9]['name']).mention
		lvl10 = sort_lb[9]['lvl']

		
		embed = discord.Embed(title=f"Leaderboard of {ctx.guild.name}", description=f"\n`[1]` **{name1}** `{lvl1}` level\n`[2]` **{name2}** `{lvl2}` level\n`[3]` **{name3}** `{lvl3}` level\n`[4]` **{name4}** `{lvl4}` level\n`[5]` **{name5}** `{lvl5}` level\n`[6]` **{name6}** `{lvl6}` level\n`[7]` **{name7}** `{lvl7}` level\n`[8]` **{name8}** `{lvl8}` level\n`[9]` **{name9}** `{lvl9}` level\n`[10]` **{name10}** `{lvl10}` level", timestamp=datetime.datetime.utcnow())
		embed.set_footer(text=f"{ctx.author.name}")
		await ctx.send(embed=embed)


	@commands.command(aliases=['disablel', 'dleveling'])
	@commands.guild_only()
	@commands.cooldown(1, 30, commands.BucketType.guild)
	@commands.has_permissions(manage_guild=True)
	async def disableleveling(self, ctx):
		"""
		This command will disable the leveling system in the server.

		Syntax:
		`Disableleveling`

		Cooldown of 30 seconds after one time use, per guild.

		Permissions:
		Need Manage Server permissions for the user.
		"""

		with open("config.json") as f:
			guild = json.load(f)

		if ctx.guild.id in guild['guilds']:
			return await ctx.send(f"{ctx.author.mention} `leveling system` already disabled!")

		guild['guilds'].append(ctx.guild.id)

		with open("config.json", "w+") as f:
			json.dump(guild, f)

		await ctx.reply(f"{ctx.author.mention} Successfully disabled `leveling system` in this server.")


	@commands.command(aliases=['enablel', 'eleveling'])
	@commands.guild_only()
	@commands.cooldown(1, 30, commands.BucketType.guild)
	@commands.has_permissions(manage_guild=True)
	async def enableleveling(self, ctx):
		"""
                This command will enable the leveling system in the server.

                Syntax:
                `Disableleveling`

                Cooldown of 30 seconds after one time use, per guild.

                Permissions:
                Need Manage Server permissions for the user.
                """

		with open("config.json") as f:
			guild = json.load(f)

		if ctx.guild.id not in guild['guilds']:
			return await ctx.send(f"{ctx.author.mention} `leveling system` already enabled!")

		guild['guilds'].remove(ctx.guild.id)

		with open("config.json", "w+") as f:
			json.dump(guild, f)

		await ctx.reply(f"{ctx.author.mention} Successfully enabled `leveling system` in this server.")



def setup(bot):
	bot.add_cog(Leveling(bot))
