from core import Cog


class GuildRoleEmoji(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_role_create(self, role):
        pass

    @Cog.listener()
    async def on_guild_role_delete(self, role):
        pass

    @Cog.listener()
    async def on_guild_role_update(self, before, after):
        pass

    @Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        pass


def setup(bot):
    bot.add_cog(GuildRoleEmoji(bot))
