from core import Parrot, Cog
from database.msg_count import increment


class Msg(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message):
        await increment(message.guild.id, message.author.id)


def setup(bot):
    bot.add_cog(Msg(bot))
