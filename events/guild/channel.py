from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db

import discord, time, io, json

log = parrot_db['logging']


class GuildChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = log

    @staticmethod
    def _overwrite_to_json(overwrites):
        try:
            over = {
                f"{str(target.name)} ({'Role' if type(target) is discord.Role else 'Member'})": overwrite._values for target, overwrite in overwrites.items()
            }
            return json.dumps(over, indent=4)
        except Exception:
            return "{}"
    
    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        if data := await self.collection.find_one({'_id': channel.guild.id, 'on_channel_delete': {'$exists': True}}):
            webhook = discord.Webhook(data['on_channel_delete'], session=self.bot.session, bot_token=self.bot.http.token)
            embed = discord.Embed(title='Channel Delete Event', color=self.bot.color)
            data = [
                ("Name", channel.name),
                ("Created at", f"<t:{int(channel.created_at.timestamp())}>"),
                ("Position", channel.position)
            ]
            for name, value in data: embed.add_field(name=name, value=value, inline=True)
            embed.set_footer(text=f"ID: {channel.id}")
            fp = io.BytesIO(self._overwrite_to_dict(channel.overwrites).encode())
            await webhook.send(
                content=f"**Channel Deleted at: <t:{int(time.time())}>**", 
                avatar_url=self.bot.user.avatar.url, 
                username=self.bot.user.name,
                file=discord.File(fp, filename='overwrites.json')
            )

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
