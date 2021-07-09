from discord.ext import tasks
from core import Cog, Parrot
from cogs.giveaway.method import collection, end_giveaway
from datetime import datetime


class GiveawayTask(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.GiveawayRefresher.start()

    def cog_unload(self):
        self.GiveawayRefresher.cancel()

    @tasks.loop(seconds=2.0)
    async def GiveawayRefresher(self):
        data = collection.find({})
        for data in data:
            if data['ends_at'] >= datetime.utcnow():
                break
        else:
            return

        await end_giveaway(self.bot, data['message_id'], None)


def setup(bot):
    bot.add_cog(GiveawayTask(bot))
