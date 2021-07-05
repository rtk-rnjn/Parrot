
from mee6_py_api import API

mee6API = API(741614680652644382)

from core import Parrot, Cog

class Mee6Integration(Cog, name="MEE6 Integration"):
	"""MEE6 Inetration for level rewards"""
	
	def __init__(self, bot: Parrot):
		self.bot = bot
	
	@Cog.listener()
	async def on_message(self, message):
			
		if message.author.bot or (str(message.channel.type) == "private"): return
		if message.guild.id != 741614680652644382: return
		user_level = await mee6API.levels.get_user_level(message.author.id)
		
		if user_level is None: return
		
		if user_level >= 50: 
			if message.guild.get_role(842781615120711680) not in message.author.roles:
				await message.author.add_roles(message.guild.get_role(842781615120711680), reason="Auto Roles as per MEE6 Leveling System")
				await message.channel.send(f"**{message.author.name}** congrats, you are above 50+ level. GG!", delete_after=10)
			
		if user_level >= 40: 
			if message.guild.get_role(842781860127440906) not in message.author.roles:
				await message.author.add_roles(message.guild.get_role(842781860127440906), reason="Auto Roles as per MEE6 Leveling System")
				await message.channel.send(f"**{message.author.name}** congrats, you are above 40+ level. GG!", delete_after=10)
			
		if user_level >= 30: 
			if message.guild.get_role(842782110657413121) not in message.author.roles:
				await message.author.add_roles(message.guild.get_role(842782110657413121), reason="Auto Roles as per MEE6 Leveling System")
				await message.channel.send(f"**{message.author.name}** congrats, you are above 30+ level. GG!", delete_after=10)
			
		if user_level >= 20: 
			if message.guild.get_role(842782583954604042) not in message.author.roles:
				await message.author.add_roles(message.guild.get_role(842782583954604042), reason="Auto Roles as per MEE6 Leveling System")
				await message.channel.send(f"**{message.author.name}** congrats, you are above 20+ level. GG!", delete_after=10)
			
		if user_level >= 10: 
			if message.guild.get_role(842803963883814922) not in message.author.roles:
				await message.author.add_roles(message.guild.get_role(842803963883814922), reason="Auto Roles as per MEE6 Leveling System")
				await message.channel.send(f"**{message.author.name}** congrats, you are above 10+ level. GG!", delete_after=10)
			
		if user_level >= 5: 
			if message.guild.get_role(842782858061545562) not in message.author.roles:
				await message.author.add_roles(message.guild.get_role(842782858061545562), reason="Auto Roles as per MEE6 Leveling System")
				await message.channel.send(f"**{message.author.name}** congrats, you are above 05+ level. GG!", delete_after=10)
		return
		
def setup(bot):
	bot.add_cog(Mee6Integration(bot))
