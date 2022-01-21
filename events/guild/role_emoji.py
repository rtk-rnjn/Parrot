from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db
import discord
import io
import json


class GuildRoleEmoji(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db["logging"]

    def permissions_to_json(self, permissions) -> str:
        return json.dumps(dict(permissions), indent=4) if permissions else "{}"

    @Cog.listener()
    async def on_guild_role_create(self, role):
        if not role.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": role.guild.id, "on_role_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_role_create"], session=self.bot.session
            )
            if webhook:
                async for entry in role.guild.audit_logs(
                    action=discord.AuditLogAction.role_create, limit=5
                ):
                    if entry.target.id == role.id:
                        content = f"""**Role Create**

`Name (ID)  :` **{role.name} [`{role.id}`]**
`Created At :` **{discord.utils.format_dt(role.created_at)}**
`Position   :` **{role.position}**
`Colour     :` **{role.color.to_rgb()} (RGB)**
`Mentionable:` **{role.mentionable}**
`Hoisted    :` **{role.hoist}**
`Bot Managed:` **{role.is_bot_managed()}**
`Integrated :` **{role.is_integration()}**
"""
                        fp = io.ByteIO(
                            self.permissions_to_json(role.permissions).encode()
                        )
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.avatar.url,
                            username=self.bot.user.name,
                            file=discord.File(fp, filename="permissions.json"),
                        )
                        break

    @Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if not role.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": role.guild.id, "on_role_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_role_delete"], session=self.bot.session
            )
            if webhook:
                async for entry in role.guild.audit_logs(
                    action=discord.AuditLogAction.role_create, limit=5
                ):
                    if entry.target.id == role.id:
                        content = f"""**Role Create**

`Name (ID)  :` **{role.name} [`{role.id}`]**
`Created At :` **{discord.utils.format_dt(role.created_at)}**
`Position   :` **{role.position}**
`Colour     :` **{role.color.to_rgb()} (RGB)**
`Mentionable:` **{role.mentionable}**
`Hoisted    :` **{role.hoist}**
`Bot Managed:` **{role.is_bot_managed()}**
`Integrated :` **{role.is_integration()}**
"""
                        fp = io.ByteIO(
                            self.permissions_to_json(role.permissions).encode()
                        )
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.avatar.url,
                            username=self.bot.user.name,
                            file=discord.File(fp, filename="permissions.json"),
                        )
                        break

        parrot_db = await self.bot.db("parrot_db")

        if data := await parrot_db["server_config"].find_one({"_id": role.guild.id}):
            if data["mod_role"] == role.id:
                await parrot_db["server_config"].update_one(
                    {"_id": role.guild.id}, {"$set": {"mod_role": None}}
                )
            if data["mute_role"] == role.id:
                await parrot_db["server_config"].update_one(
                    {"_id": role.guild.id}, {"$set": {"mute_role": None}}
                )

        if data := await parrot_db["global_chat"].find_one({"_id": role.guild.id}):
            if data["ignore-role"] == role.id:
                await parrot_db["global_chat"].update_one(
                    {"_id": role.guild.id}, {"$set": {"ignore_role": None}}
                )

        if data := await parrot_db["telephone"].find_one({"_id": role.guild.id}):
            if data["pingrole"] == role.id:
                await parrot_db["telephone"].update_one(
                    {"_id": role.guild.id}, {"$set": {"pingrole": None}}
                )

        if data := await parrot_db["ticket"].find_one({"_id": role.guild.id}):
            await parrot_db["ticket"].update_one(
                {"_id": role.guild.id},
                {
                    "$pull": {
                        "valid_roles": role.id,
                        "pinged_roles": role.id,
                        "verified_roles": role.id,
                    }
                },
            )

    async def _update_role(
        self,
        before,
        after,
    ):
        ls = []
        if before.name != after.name:
            ls.append(("`Name Changed      :`", after.name))
        if before.position != after.position:
            ls.append(("`Position Changed  :`", after.position))
        if not before.hoist is after.hoist:
            ls.append(("`Hoist Toggled     :`", after.hoist))
        if before.color != after.color:
            ls.append(("`Color Changed     :`", after.color.to_rgb()))
        return ls

    @Cog.listener()
    async def on_guild_role_update(self, before, after):
        if not after.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": before.guild.id, "on_role_update": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_role_update"], session=self.bot.session
            )
            if webhook:
                async for entry in after.guild.audit_logs(
                    action=discord.AuditLogAction.role_update, limit=5
                ):
                    if entry.extra.id == after.id:
                        reason = entry.reason or None
                        user = entry.user or "UNKNOWN#0000"
                        entryID = entry.id
                        ls = self._update_change(before, after)
                        ext = ""
                        for i, j in ls:
                            ext += f"{i} **{j}**\n"
                        content = f"""**Role Update Event**

`Name (ID) :` **{after.name} ({after.id})**
`Created at:` **<t:{int(after.created_at.timestamp())}>**
`Reason    :` **{reason if reason else 'No reason provided'}**
`Entry ID  :` **{entryID if entryID else None}**
`Updated by:` **{user}**

**Change/Update**
{ext}
"""
                        break
                fp = io.BytesIO(self.permissions_to_json(after.permissions).encode())
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="permissions.json"),
                )

    @Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        if not guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": guild.id, "on_emoji_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_emoji_create"], session=self.bot.session
            )
            if webhook:
                async for entry in guild.audit_logs(
                    action=discord.AuditLogAction.emoji_create, limit=1
                ):
                    emoji_name = entry.name
                    if isinstance(entry.target, discord.Emoji):
                        animated = entry.target.animated
                        _id = entry.target.id
                        url = entry.target.url
                    else:
                        animated = None
                        _id = entry.target.id
                        url = None
                content = f"""**On Emoji Create**

`Name    `: **{emoji_name}**
`Raw     `: **`{entry.target if isinstance(entry.target, discord.Emoji) else None}`**
`ID      `: **{_id}**
`URL     `: **<{url}>**
`Animated`: **{animated}**
"""
            await webhook.send(
                content=content,
                avatar_url=self.bot.user.avatar.url,
                username=self.bot.user.name,
            )

        if data := await self.collection.find_one(
            {"_id": guild.id, "on_emoji_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_emoji_delete"], session=self.bot.session
            )
            if webhook:
                async for entry in guild.audit_logs(
                    action=discord.AuditLogAction.emoji_delete, limit=1
                ):
                    emoji_name = entry.name
                    if isinstance(entry.target, discord.Emoji):
                        animated = entry.target.animated
                        _id = entry.target.id
                        url = entry.target.url
                    else:
                        animated = None
                        _id = entry.target.id
                        url = None
                content = f"""**On Emoji Create**

`Raw     `: **`{entry.target if isinstance(entry.target, discord.Emoji) else None}`**
`ID      `: **{_id}**
`URL     `: **<{url}>**
"""
            await webhook.send(
                content=content,
                avatar_url=self.bot.user.avatar.url,
                username=self.bot.user.name,
            )

        if data := await self.collection.find_one(
            {"_id": guild.id, "on_emoji_update": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_emoji_update"], session=self.bot.session
            )
            if webhook:
                async for entry in guild.audit_logs(
                    action=discord.AuditLogAction.emoji_update, limit=1
                ):
                    emoji_name = entry.name
                    if isinstance(entry.target, discord.Emoji):
                        animated = entry.target.animated
                        _id = entry.target.id
                        url = entry.target.url
                    else:
                        animated = None
                        _id = entry.target.id
                        url = None
                content = f"""**On Emoji Create**

`Raw     `: **`{entry.target if isinstance(entry.target, discord.Emoji) else None}`**
`ID      `: **{_id}**
`URL     `: **<{url}>**
"""
            await webhook.send(
                content=content,
                avatar_url=self.bot.user.avatar.url,
                username=self.bot.user.name,
            )


def setup(bot):
    bot.add_cog(GuildRoleEmoji(bot))
