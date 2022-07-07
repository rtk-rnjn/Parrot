from __future__ import annotations

from contextlib import suppress

import discord
from core import Cog, Parrot
from pymongo.collection import Collection


class User(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = bot.mongo.parrot_db["logging"]

    @Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self.bot.wait_until_ready()
        if not guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": guild.id, "on_member_ban": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_member_ban"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                async for entry in guild.audit_logs(
                    action=discord.AuditLogAction.ban, limit=5
                ):
                    if entry.target.id == user.id:
                        content = f"""**Member Banned**

`Name (ID)  :` **{user} [`{user.id}`]**
`Created At :` **{discord.utils.format_dt(user.created_at)}**
`Reason     :` **{entry.reason if entry.reason else None}**
`Banned by  :` **{entry.user}**
"""
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.avatar.url,
                            username=self.bot.user.name,
                        )
                        break

    @Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self.bot.wait_until_ready()
        if not guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": guild.id, "on_member_unban": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_member_unban"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                async for entry in guild.audit_logs(
                    action=discord.AuditLogAction.ban, limit=5
                ):
                    if entry.target.id == user.id:
                        content = f"""**Member Unbanned**

`Name (ID)  :` **{user} [`{user.id}`]**
`Created At :` **{discord.utils.format_dt(user.created_at)}**
`Reason     :` **{entry.reason if entry.reason else None}**
`Unbanned by:` **{entry.user}**
"""
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.avatar.url,
                            username=self.bot.user.name,
                        )
                        break

    @Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.bot:
            return

        collection: Collection = self.bot.mongo.extra.user_misc
        try:
            before_avatar = await before.display_avatar.read()
            after_avatar = await after.display_avatar.read()
        except (discord.NotFound, discord.DiscordException):
            return

        PAYLOAD = {}
        if before_avatar != after_avatar:
            PAYLOAD["before_avatar"] = before_avatar
            PAYLOAD["after_avatar"] = after_avatar
        if before.name != after.name:
            PAYLOAD["before_name"] = before.name
            PAYLOAD["after_name"] = after.name
        if before.discriminator != after.discriminator:
            PAYLOAD["before_discriminator"] = before.discriminator
            PAYLOAD["after_discriminator"] = after.discriminator

        await collection.update_one(
            {"_id": before.id},
            {
                "$addToSet": {
                    "change": {
                        "at": discord.utils.utcnow().timestamp(),
                        **PAYLOAD,
                    }
                }
            },
            upsert=True,
        )


async def setup(bot):
    await bot.add_cog(User(bot))
