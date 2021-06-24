from core.cog import Cog
from datetime import datetime


class OnConnect(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_connect(self):
        print(
            f"LOGGED IN AS {self.bot.user.name}#{self.bot.user.discriminator}. AT: {datetime.utcnow()}"
        )

    @Cog.listener()
    async def on_disconnect(self):
        print(
            f"{self.bot.user.name}#{self.bot.user.discriminator} DISCONNECTED FROM DISCORD. AT: {datetime.utcnow()}"
        )


def setup(bot):
    bot.add_cog(OnConnect(bot))
