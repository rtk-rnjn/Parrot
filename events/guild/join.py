from __future__ import annotations

from core import Parrot, Cog
from utilities.database import guild_join, guild_remove, parrot_db
from utilities.config import JOIN_LEAVE_CHANNEL_ID

import aiohttp, os, discord

CHANNEL_ID = JOIN_LEAVE_CHANNEL_ID
BASE_URL = f"https://discord.com/api/webhooks/{CHANNEL_ID}/"


class GuildJoin(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.url = BASE_URL + os.environ['CHANNEL_TOKEN1']
        self.collection = parrot_db['server_config']

    async def log_it(self, guild: discord.Guild):
        pass

    @Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild is None: return
        await self.bot.wait_until_ready()
        CONTENT = f"Joined {guild.name} ({guild.id}). Total member in {guild.name}: {len(guild.members)}. Server Owner: {guild.owner} ({guild.owner.id}). Server Region: {str(guild.region).replace('_', ' ').title()}. \n\nTotal server on count {len(self.bot.guilds)}. Total users on count: {len(self.bot.users)}"
        await guild_join(guild.id)
        data = {
            'username': "Parrot",
            'avatar_url': self.bot.user.display_avatar.url,
            'content': CONTENT,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=data) as res:
                if res in range(200, 300 + 1):
                    pass

    @Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        if guild is None: return
        await self.bot.wait_until_ready()
        CONTENT = f"Left {guild.name} ({guild.id}). Total member in {guild.name}: {len(guild.members)}. Server Owner: {guild.owner} ({guild.owner.id}). Server Region: {str(guild.region).replace('_', ' ').title()}. \n\nTotal server on count {len(self.bot.guilds)}. Total users on count: {len(self.bot.users)}"
        await guild_remove(guild.id)
        data = {
            'username': "Parrot",
            'avatar_url': self.bot.user.display_avatar.url,
            'content': CONTENT,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=data) as res:
                if res in range(200, 300 + 1):
                    pass

    @Cog.listener()
    async def on_guild_update(self, before, after):
        pass


def setup(bot):
    bot.add_cog(GuildJoin(bot))
