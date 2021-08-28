from core import Cog, Parrot

class GuildChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_channel_delete(self, channel):
        db = await self.bot.db('parrot_db')
        
        if data := await db['global_chat'].find_one({'_id': channel.guild.id}):
            if data['channel_id'] == channel.id:
                await db['global_chat'].delete_one({'_id': channel.guild.id})
        
        if data := await parrot_db["telephone"].find_one({'_id': channel.guild.id}):
            if data['channel'] == channel.id:
                await parrot_db["telephone"].update_one({'_id': channel.guild.id}, {'$set': {'channel': None}})
        
        if data := await parrot_db["ticket"].find_one({'_id': channel.guild.id}):
            if data['channel_id'] == channel.id:
                await parrot_db["ticket"].update_one({'_id': channel.guild.id}, {'$set': {'message_id': None, 'channel_id': None}})
            if data['log'] == channel.id:
                await parrot_db["ticket"].update_one({'_id': channel.guild.id}, {'$set': {'log': None}})
            if data['category'] == channel.id:
                await parrot_db["ticket"].update_one({'_id': channel.guild.id}, {'$set': {'category': None}})
            if channel.id in data['ticket-channel-ids']:
                await parrot_db["ticket"].update_one({'_id': channel.guild.id}, {'$pull': {'ticket-channel-ids': channel.id}})

        if data := await parrot_db["server_config"].find_one({'_id': channel.guild.id}):
            await parrot_db["server_config"].update_one({'_id': channel.guild.id}, {'$set': {'action_log': None}})

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
        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            return
        
        webhooks = await channel.webhooks()
        db = await self.bot.db('parrot_db')
        if not webhooks:
            return await db['global_chat'].delete_one({'_id': channel.guild.id})
        for webhook in webhooks:
            if data := await db['global_chat'].find_one({'_id': channel.guild.id}):
                if webhook.url == data['webhook']:
                    return await db['global_chat'].delete_one({'_id': channel.guild.id})

    @Cog.listener()
    async def on_reaction_clear_emoji(self, reaction):
        pass

    @Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload):
        pass


def setup(bot):
    bot.add_cog(GuildChannel(bot))
