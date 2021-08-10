from core import Parrot, Cog
from utilities.database import guild_join, guild_remove


class GuildJoin(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_join(self, guild):
        await guild_join(guild.id)
        

    @Cog.listener()
    async def on_guild_remove(self, guild):
        await guild_remove(guild.id)


    @Cog.listener()
    async def on_guild_update(self, before, after):
        pass


def setup(bot):
    bot.add_cog(GuildJoin(bot))
