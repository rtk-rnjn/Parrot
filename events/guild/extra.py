from __future__ import annotations

from utilities.database import parrot_db
import discord

from core import Cog, Parrot

log = parrot_db["logging"]


class Extra(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db["logging"]

    @Cog.listener()
    async def on_guild_available(self, guild):
        pass

    @Cog.listener()
    async def on_guild_unavailable(self, guild):
        pass

    @Cog.listener()
    async def on_invite_create(self, invite):
        if not invite.guild:
            return
        if not invite.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": invite.guild.id, "on_invite_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_invite_create"], session=self.bot.session
            )
            if webhook:
                try:
                    async for entry in invite.guild.audit_logs(
                        action=discord.AuditLogAction.invite_delete, limit=5
                    ):
                        if entry.extra.id == invite.id:
                            reason = entry.reason or None
                            break
                except Exception:
                    reason = None

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
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                )

    @Cog.listener()
    async def on_invite_delete(self, invite):
        if not invite.guild:
            return
        if data := await self.collection.find_one(
            {"_id": invite.guild.id, "on_invite_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_invite_create"], session=self.bot.session
            )
            if webhook:
                try:
                    async for entry in invite.guild.audit_logs(
                        action=discord.AuditLogAction.invite_delete, limit=5
                    ):
                        if entry.extra.id == invite.id:
                            reason = entry.reason or None
                            user = entry.user or "UNKNOWN#0000"
                            break
                except Exception:
                    reason = None
                    user = "UNKNOWN#0000"

                content = f"""**On Invite Create**

`Member Count?  :` **{invite.approximate_member_count}**
`Presence Count?:` **{invite.approximate_presence_count}**
`Channel     :` **<#{invite.channel.id}>**
`Created At  :` **<t:{int(invite.created_at.timestamp())}>**
`Temporary?  :` **{invite.temporary}**
`Uses        :` **{invite.uses}**
`Link        :` **{invite.url}**
`Inviter?    :` **{invite.inviter}**
`Reason?     :` **{reason}**
`Deleted By? :` **{user}**
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                )


def setup(bot):
    bot.add_cog(Extra(bot))
