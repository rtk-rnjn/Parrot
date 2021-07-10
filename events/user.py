from core import Cog


class User(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_member_ban(self, guild, user):
        pass

    @Cog.listener()
    async def on_member_unban(self, guild, user):
        pass

    @Cog.listener()
    async def on_user_update(self, before, after):
        pass


def setup(bot):
    bot.add_cog(User(bot))
