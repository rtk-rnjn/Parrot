from __future__ import annotations

from core import Parrot, Cog
from utilities.config import JOIN_LEAVE_CHANNEL_ID

import aiohttp
import os
import discord

CHANNEL_ID = JOIN_LEAVE_CHANNEL_ID
BASE_URL = f"https://discord.com/api/webhooks/{CHANNEL_ID}/"


class GuildJoin(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.url = BASE_URL + os.environ["CHANNEL_TOKEN1"]
        self.collection = bot.mongo.parrot_db["server_config"]

    @Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.wait_until_ready()
        try:
            CONTENT = f"""
`Joined       `: {guild.name} (`{guild.id}`)
`Total member `: {guild.member_count}
`Server Owner `: `{guild.owner}` | {guild.owner.id}
`Server Region`: {str(guild.region).replace('_', ' ').title()}.

Total server on count **{len(self.bot.guilds)}**. Total users on count: **{len(self.bot.users)}**
"""
        except AttributeError:
            return

        
        async def guild_join(guild_id: int):
            collection = self.bot.mongo.parrot_db["global_chat"]
            post = {
                "_id": guild_id,
                "channel_id": None,
                "webhook": None,
                "ignore-role": None,
            }
            await collection.insert_one(post)

            collection = self.bot.mongo.parrot_db["telephone"]
            post = {
                "_id": guild_id,
                "channel": None,
                "pingrole": None,
                "is_line_busy": False,
                "memberping": None,
                "blocked": [],
            }
            await collection.insert_one(post)

            collection = self.bot.mongo.parrot_db["ticket"]
            post = {
                "_id": guild_id,
                "ticket_counter": 0,
                "valid_roles": [],
                "pinged_roles": [],
                "ticket_channel_ids": [],
                "verified_roles": [],
                "message_id": None,
                "log": None,
                "category": None,
                "channel_id": None,
            }
            await collection.insert_one(post)

        await guild_join(guild.id)

        data = {
            "username": "Parrot",
            "avatar_url": self.bot.user.display_avatar.url,
            "content": CONTENT,
        }
        await self.bot.http_session.post(self.url, json=data)

    @Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.wait_until_ready()
        try:
            CONTENT = f"""
`Removed      `: {guild.name} (`{guild.id}`)
`Total member `: {guild.member_count}
`Server Owner `: `{guild.owner}` | {guild.owner.id}
`Server Region`: {str(guild.region).replace('_', ' ').title()}.

Total server on count **{len(self.bot.guilds)}**. Total users on count: **{len(self.bot.users)}**
"""
        except AttributeError:
            return

        async def guild_remove(guild_id: int):
            collection = self.bot.mongo.parrot_db["server_config"]
            await collection.delete_one({"_id": guild_id})

            collection = self.bot.mongo.parrot_db[f"{guild_id}"]
            await collection.drop()

            collection = self.bot.mongo.parrot_db["global_chat"]
            await collection.delete_one({"_id": guild_id})

            collection = self.bot.mongo.parrot_db["telephone"]
            await collection.delete_one({"_id": guild_id})

            collection = self.bot.mongo.parrot_db["ticket"]
            await collection.delete_one({"_id": guild_id})

            collection = self.bot.mongo.enable_disable[f"{guild_id}"]
            await collection.drop()

        await guild_remove(guild.id)
        data = {
            "username": "Parrot",
            "avatar_url": self.bot.user.display_avatar.url,
            "content": CONTENT,
        }
        await self.bot.http_session.post(self.url, json=data)

    @Cog.listener()
    async def on_guild_update(self, before, after):
        pass


async def setup(bot):
    await bot.add_cog(GuildJoin(bot))
