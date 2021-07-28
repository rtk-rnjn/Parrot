from mee6_py_api import API
from core import Parrot, Cog
from database.mee6 import collection


class Mee6Integration(Cog, name="MEE6 Integration"):
    """MEE6 Inetration for level rewards"""
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if not message.guild: return
        mee6API = API(message.guild.id)
        data = collection.find_one({'_id': message.guild.id})

        if (not data): return
        user_level = await mee6API.levels.get_user_level(message.author.id)
        if not user_level: return
        
        for rolid in data.keys():
            try:
              if int(rolid) <= user_level:
                role = message.guild.get_role(int(rolid))
                if role not in message.author.roles:
                      await message.author.add_roles(role, reason="Auto Roles as per MEE6 Leveling System")
            except Exception: 
              pass

def setup(bot):
    bot.add_cog(Mee6Integration(bot))
