from core.cog import Cog
from datetime import datetime


class OnReady(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        print(
            f"{self.bot.user.name}#{self.bot.user.discriminator} IS READY TO TAKE COMMAND. AT: {datetime.utcnow()}"
        )
        print(f"TOTAL GUILD ON COUNT: {len(self.bot.guilds)}")
        print(f"TOTAL USERS ON COUNT: {len(self.bot.users)}")

    @Cog.listener()
    async def on_resumed(self):
        print(
            f"{self.bot.user.name}#{self.bot.user.discriminator} RESUMED. AT: {datetime.utcnow()}"
        )


def setup(bot):
    bot.add_cog(OnReady(bot))
