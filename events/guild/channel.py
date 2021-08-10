from core import Cog, Parrot
# from database.global_chat import collection as cgc
# from database.server_config import cluster
class GuildChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_channel_delete(self, channel):
        # data = cgc.find_one({'_id': channel.guild.id})
        # if not data: return
        # if data['channel_id'] == channel.id:
        #     cgc.update_one({'_id': channel.guild.id}, {'$set': {'channel_id': None, 'webhook': None}})
        pass
    @Cog.listener()
    async def on_guild_channel_create(self, channel):
        pass

    @Cog.listener()
    async def on_guild_channel_update(self, before, after):
        pass

    @Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        pass

    @Cog.listener()
    async def on_guild_integrations_update(self, guild):
        pass

    @Cog.listener()
    async def on_webhooks_update(self, channel):
        pass

    @Cog.listener()
    async def on_reaction_clear_emoji(self, reaction):
        pass

    @Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload):
        pass


def setup(bot):
    bot.add_cog(GuildChannel(bot))
