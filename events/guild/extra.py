from __future__ import annotations

from contextlib import suppress

import discord
from core import Cog, Parrot


class Extra(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = bot.mongo.parrot_db["logging"]

    @Cog.listener()
    async def on_guild_available(self, guild: discord.Guild):
        pass

    @Cog.listener()
    async def on_guild_unavailable(self, guild: discord.Guild):
        pass

    @Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        await self.bot.wait_until_ready()
        if not invite.guild:
            return
        if not invite.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": invite.guild.id, "on_invite_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_invite_create"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                async for entry in invite.guild.audit_logs(
                    action=discord.AuditLogAction.invite_create, limit=5
                ):
                    if entry.after.code == invite.code:
                        reason = entry.reason or None
                        content = f"""**On Invite Create**

`Member Count?  :` **{invite.approximate_member_count}**
`Presence Count?:` **{invite.approximate_presence_count}**
`Channel     :` **<#{invite.channel.id}>**
`Created At  :` **<t:{int(invite.created_at.timestamp())}>**
`Temporary?  :` **{invite.temporary}**
`Max Uses    :` **{invite.max_uses if invite.max_uses else 'Infinte'}**
`Link        :` **{invite.url}**
`Inviter?    :` **{invite.inviter}**
`Reason?     :` **{reason}**
`Created By  :` **{entry.user}**
"""
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                        )
                        break

    @Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        await self.bot.wait_until_ready()
        if not invite.guild:
            return
        if not invite.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": invite.guild.id, "on_invite_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_invite_create"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                async for entry in invite.guild.audit_logs(
                    action=discord.AuditLogAction.invite_delete, limit=5
                ):
                    if entry.after.code == invite.code:
                        reason = entry.reason or None
                        user = entry.user or "UNKNOWN#0000"

                        content = f"""**On Invite Create**

`Member Count?  :` **{invite.approximate_member_count}**
`Presence Count?:` **{invite.approximate_presence_count}**
`Channel     :` **<#{invite.channel.id}>**
`Created At  :` **{discord.utils.format_dt(invite.created_at)}**
`Temporary?  :` **{invite.temporary}**
`Uses        :` **{invite.uses}**
`Link        :` **{invite.url}**
`Inviter?    :` **{invite.inviter}**
`Reason?     :` **{reason}**
`Deleted By? :` **{user}**
"""
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                        )
                        break


async def setup(bot: Parrot):
    await bot.add_cog(Extra(bot))
