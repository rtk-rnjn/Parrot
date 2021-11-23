from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db

import discord, time

log = parrot_db['logging']


class GuildChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = log

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        if data := await self.collection.find_one({'_id': channel.guild.id, 'on_channel_delete': {'$exists': True}}):
            webhook = discord.Webhook(data['on_channel_delete'], session=self.bot.session, bot_token=self.bot.http.token)
            embed = discord.Embed(title='Channel Delete', color=self.bot.color)
            data = [
                ("Name", channel.name),
                ("Created at", f"<t:{int(channel.created_at.timestamp())}>"),
                ("Position", channel.position)
            ]
            await webhook.send(content=f"**Channel Delete Event at: <t:{int(time.time())}>**", avatar_url=self.bot.user.avatar.url, username=self.bot.user.name)

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
