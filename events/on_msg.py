from core import Parrot, Cog
from database.msg_count import increment


class OnMsg(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message):
        await increment(message.guild.id, message.author.id)

    @Cog.listener()
    async def on_message_delete(self, message):
        pass

    @Cog.listener()
    async def on_bulk_message_delete(self, messages):
        pass

    @Cog.listener()
    async def on_raw_message_delete(self, payload):
        pass

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        pass

    @Cog.listener()
    async def on_message_edit(self, before, after):
        pass

    @Cog.listener()
    async def on_raw_message_edit(self, payload):
        pass


def setup(bot):
    bot.add_cog(OnMsg(bot))
