from __future__ import annotations

import os

import discord
from core import Cog, Parrot
from utilities.config import WEBHOOK_JOIN_LEAVE_CHANNEL_ID

WEBHOOK_CHANNEL_ID = WEBHOOK_JOIN_LEAVE_CHANNEL_ID
BASE_URL = f"https://discord.com/api/webhooks/{WEBHOOK_CHANNEL_ID}/"

HEAD_MODERATOR = 861476968439611392
MODERATOR = 771025632184369152
STAFF = 793531029184708639


class GuildJoin(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.url = BASE_URL + os.environ["CHANNEL_TOKEN1"]
        self.collection = bot.mongo.parrot_db["server_config"]

    async def __check_guild_requirements(self, guild: discord.Guild):
        staff_roles = [HEAD_MODERATOR, MODERATOR, STAFF]

        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
                m = self.bot.server.get_member(entry.user.id)
                if (
                    (entry.target.id == self.bot.user.id)
                    and m
                    and any(m._roles.has(r) for r in staff_roles)
                ):
                    return

        bots = len([m for m in guild.members if m.bot])
        humans = guild.member_count - bots
        if bots > humans:
            return await guild.leave()
        if guild.member_count < 30:
            return await guild.leave()

    async def guild_join(self, guild_id: int):
        collection = self.bot.mongo.parrot_db["telephone"]
        post = {
            "channel": None,
            "pingrole": None,
            "is_line_busy": False,
            "memberping": None,
            "blocked": [],
        }
        await collection.update_one({"_id": guild_id}, {"$set": post}, upsert=True)

        collection = self.bot.mongo.parrot_db["ticket"]
        post = {
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
        await collection.update_one({"_id": guild_id}, {"$set": post}, upsert=True)

    async def guild_remove(self, guild_id: int):
        collection = self.bot.mongo.parrot_db["server_config"]

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

    @Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.wait_until_ready()
        try:
            CONTENT = f"""
`Joined       `: {guild.name} (`{guild.id}`)
`Total member `: {len(guild.members)}
`Server Owner `: `{guild.owner}` | {guild.owner.id}
`Bots         `: {len(guild.members) - len([m for m in guild.members if not m.bot])}

Total server on count **{len(self.bot.guilds)}**. Total users on count: **{len(self.bot.users)}**
"""
        except AttributeError:
            return
        await self.__check_guild_requirements(guild)

        await self.guild_join(guild.id)

        data = {
            "username": "Parrot",
            "avatar_url": self.bot.user.display_avatar.url,
            "content": CONTENT,
        }
        await self.bot.http_session.post(self.url, json=data)
        await self.bot.update_server_config_cache.start(guild.id)

    @Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.wait_until_ready()
        try:
            CONTENT = f"""
`Removed      `: {guild.name} (`{guild.id}`)
`Total member `: {len(guild.members)}
`Server Owner `: `{guild.owner}` | {guild.owner.id}
`Bots         `: {len(guild.members) - len([m for m in guild.members if not m.bot])}

Total server on count **{len(self.bot.guilds)}**. Total users on count: **{len(self.bot.users)}**
"""
        except AttributeError:
            return

        await self.guild_remove(guild.id)
        data = {
            "username": "Parrot",
            "avatar_url": self.bot.user.display_avatar.url,
            "content": CONTENT,
        }
        await self.bot.http_session.post(self.url, json=data)
        await self.bot.update_server_config_cache.start(guild.id)

    @Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        pass


async def setup(bot) -> None:
    await bot.add_cog(GuildJoin(bot))
