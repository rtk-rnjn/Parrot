from __future__ import annotations

from contextlib import suppress

import discord
from cogs.meta.robopage import SimplePages
from core import Cog, Context, Parrot
from discord.ext import commands, tasks
from pymongo.collection import Collection


class User(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection: Collection = bot.mongo.parrot_db["logging"]
        self.clear_user_misc.start()

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
                            avatar_url=self.bot.user.display_avatar.url,
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
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                        )
                        break

    @Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.bot:
            return

        collection: Collection = self.bot.mongo.extra.user_misc

        PAYLOAD = {}
        if before.name != after.name:
            PAYLOAD["before_name"] = before.name
            PAYLOAD["after_name"] = after.name
        if before.discriminator != after.discriminator:
            PAYLOAD["before_discriminator"] = before.discriminator
            PAYLOAD["after_discriminator"] = after.discriminator

        if PAYLOAD:
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

    @commands.command(aliases=["userchange"])
    @commands.is_owner()
    async def user_change(self, ctx: Context, *, user: discord.User):
        """To set the update of users"""
        data: dict = await self.bot.mongo.extra.user_misc.find_one({"_id": user.id})
        if not data:
            await ctx.send("User didn't updated since a while")
        entries = []
        for index, change in enumerate(data["change"]):
            if index % 10 == 0:
                break
            entries.append(
                f"""{discord.utils.format_dt(change['at'])}
Name: {change.get('before_name')} -> {change('after_name')}
Discriminator: {change.get('before_discriminator')} -> {change('after_discriminator')}
"""
            )
        p = SimplePages(
            entries,
            ctx=ctx,
        )
        await p.start()

    @tasks.loop(hours=1)
    async def clear_user_misc(self):
        await self.bot.mongo.extra.user_misc.update_many(
            {},
            {
                "$pull": {
                    "change": {
                        "at": {"$lt": discord.utils.utcnow().timestamp() - 43200}
                    }
                }
            },
        )

    async def cog_unload(self) -> None:
        self.clear_user_misc.cancel()

async def setup(bot: Parrot):
    await bot.add_cog(User(bot))
