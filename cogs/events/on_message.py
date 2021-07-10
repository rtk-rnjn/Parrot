from core import Parrot, Cog
from database.msg_count import if_not_exists, increment, collection


class Msg(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            if not collection.find_one({'_id': message.guild.id}):
                return await if_not_exists(message.guild.id, message.author.id, 1)
            return await increment(message.guild.id, message.author.id)
        return

def setup(bot):
    bot.add_cog(Msg(bot))
