from datetime import datetime, timedelta
from random import choice

from discord import Embed
from discord.ext.commands import Cog
from discord.ext.commands import command, has_permissions

#from ..db import db

# Here are all the number emotes.
# 0⃣ 1️⃣ 2⃣ 3⃣ 4⃣ 5⃣ 6⃣ 7⃣ 8⃣ 9⃣

numbers = ("1️⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣", "🔟")


class Reactions(Cog):
	def __init__(self, bot):
		self.bot = bot
		self.polls = []
		self.giveaways = []

	@Cog.listener()
	async def on_ready(self):
		if not self.bot.ready:
			#self.colours = {"❤️": self.bot.guild.get_role(653940117680947232),"💛": self.bot.guild.get_role(653940192780222515),"💚": self.bot.guild.get_role(653940254293622794),"💙": self.bot.guild.get_role(653940277761015809),"💜": self.bot.guild.get_role(653940305300815882),"🖤": self.bot.guild.get_role(653940328453373952),}
			#self.reaction_message = await self.bot.get_channel(759432499221889034).fetch_message(759434223802253362)
			self.starboard_channel = self.bot.get_channel(780606217651355678)
			self.bot.cogs_ready.ready_up("reactions")

	@command(name="createpoll", aliases=["mkpoll"])
	@has_permissions(manage_guild=True)
	async def create_poll(self, ctx, hours: int, question: str, *options):
		if len(options) > 10:
			await ctx.send("You can only supply a maximum of 10 options.")

		else:
			embed = Embed(title="Poll",
						  description=question,
						  colour=ctx.author.colour,
						  timestamp=datetime.utcnow())

			fields = [("Options", "\n".join([f"{numbers[idx]} {option}" for idx, option in enumerate(options)]), False),("Instructions", "React to cast a vote!", False)]

			for name, value, inline in fields:
				embed.add_field(name=name, value=value, inline=inline)

			message = await ctx.send(embed=embed)

			for emoji in numbers[:len(options)]:
				await message.add_reaction(emoji)

			self.polls.append((message.channel.id, message.id))

			self.bot.scheduler.add_job(self.complete_poll, "date", run_date=datetime.now()+timedelta(seconds=hours),
									   args=[message.channel.id, message.id])

	@command(name="giveaway")
	@has_permissions(manage_guild=True)
	async def create_giveaway(self, ctx, mins: int, *, description: str):
		embed = Embed(title="Giveaway",
					  description=description,
					  colour=ctx.author.colour,
					  timestamp=datetime.utcnow())

		fields = [("End time", f"{datetime.utcnow()+timedelta(seconds=mins*60)} UTC", False)]

		for name, value, inline in fields:
			embed.add_field(name=name, value=value, inline=inline)

		message = await ctx.send(embed=embed)
		await message.add_reaction("✅")

		self.giveaways.append((message.channel.id, message.id))

		self.bot.scheduler.add_job(self.complete_giveaway, "date", run_date=datetime.now()+timedelta(seconds=mins),args=[message.channel.id, message.id])

	async def complete_poll(self, channel_id, message_id):
		message = await self.bot.get_channel(channel_id).fetch_message(message_id)

		most_voted = max(message.reactions, key=lambda r: r.count)

		await message.channel.send(f"The results are in and option {most_voted.emoji} was the most popular with {most_voted.count-1:,} votes!")
		self.polls.remove((message.channel.id, message.id))

	async def complete_giveaway(self, channel_id, message_id):
		message = await self.bot.get_channel(channel_id).fetch_message(message_id)

		if len((entrants := [u for u in await message.reactions[0].users().flatten() if not u.bot])) > 0:
			winner = choice(entrants)
			await message.channel.send(f"Congratulations {winner.mention} - you won the giveaway!")
			self.giveaways.remove((message.channel.id, message.id))

		else:
			await message.channel.send("Giveaway ended - no one entered!")
			self.giveaways.remove((message.channel.id, message.id))

	@Cog.listener()
	async def on_raw_reaction_add(self, payload):
		if payload.message_id == self.reaction_message.id:
			current_colours = filter(lambda r: r in self.colours.values(), payload.member.roles)
			await payload.member.remove_roles(*current_colours, reason="Colour role reaction.")
			await payload.member.add_roles(self.colours[payload.emoji.name], reason="Colour role reaction.")
			await self.reaction_message.remove_reaction(payload.emoji, payload.member)

		elif payload.message_id in (poll[1] for poll in self.polls):
			message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

			for reaction in message.reactions:
				if (not payload.member.bot
					and payload.member in await reaction.users().flatten()
					and reaction.emoji != payload.emoji.name):
					await message.remove_reaction(reaction.emoji, payload.member)

		elif payload.emoji.name == "⭐":
			message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

			if not message.author.bot and payload.member.id != message.author.id:
				msg_id, stars = db.record("SELECT StarMessageID, Stars FROM starboard WHERE RootMessageID = ?",message.id) or (None, 0)

				embed = Embed(title="Starred message",
							  colour=message.author.colour,
							  timestamp=datetime.utcnow())

				fields = [("Author", message.author.mention, False),
						  ("Content", message.content or "See attachment", False),
						  ("Stars", stars+1, False)]

				for name, value, inline in fields:
					embed.add_field(name=name, value=value, inline=inline)

				if len(message.attachments):
					embed.set_image(url=message.attachments[0].url)

				if not stars:
					star_message = await self.starboard_channel.send(embed=embed)
					#db.execute("INSERT INTO starboard (RootMessageID, StarMessageID) VALUES (?, ?)",message.id, star_message.id)

				else:
					star_message = await self.starboard_channel.fetch_message(msg_id)
					await star_message.edit(embed=embed)
					#db.execute("UPDATE starboard SET Stars = Stars + 1 WHERE RootMessageID = ?", message.id)

			else:
				await message.remove_reaction(payload.emoji, payload.member)


def setup(bot):
	bot.add_cog(Reactions(bot))
	print("reaction.py successfully loaded. Status OK")