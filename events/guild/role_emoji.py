from core import Cog, Parrot


class GuildRoleEmoji(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
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
