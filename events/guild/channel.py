from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db

import discord
import io
import json

log = parrot_db["logging"]
server_config = parrot_db["server_config"]


class GuildChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = log

    def _overwrite_to_json(self, overwrites) -> str:
        try:
            over = {
                f"{str(target.name)} ({'Role' if type(target) is discord.Role else 'Member'})": overwrite._values
                for target, overwrite in overwrites.items()
            }
            return json.dumps(over, indent=4)
        except Exception:
            return "{}"

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not channel.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": channel.guild.id, "on_channel_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_delete"], session=self.bot.session
            )
            if webhook:
                channel_type = str(channel.type)
                TYPE = channel_type.replace("_", " ").title() + " Channel"
                async for entry in channel.guild.audit_logs(
                    action=discord.AuditLogAction.channel_delete, limit=5
                ):
                    if entry.target.id == channel.id:

                        reason = (
                            entry.reason or None
                        )  # Fact is this thing has to be implemented
                        user = entry.user or "UNKNOWN#0000"  # If the action is too old
                        deleted_at = (
                            entry.created_at
                        )  # The logs can't be proceeded. I dont know why
                        content = f"""**Channel Delete Event**

`Name (ID) :` **{channel.name} [`{TYPE}`] ({channel.id})**
`Created at:` **<t:{int(channel.created_at.timestamp())}>**
`Position  :` **{channel.position}**
`Category  :` **{channel.category.mention if channel.category else None}**
`Caterogy Synced?:` **{channel.permissions_synced}**
`Reason    :` **{reason if reason else 'No reason provided'}**
`Deleted at:` **{discord.utils.format_dt(deleted_at) if deleted_at else 'Not available'}**
`Deleted by:` **{user}**
"""
                        break
                fp = io.BytesIO(self._overwrite_to_json(channel.overwrites).encode())
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="overwrites.json"),
                )

    @Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if not channel.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": channel.guild.id, "on_channel_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_create"], session=self.bot.session
            )
            if webhook:
                channel_type = str(channel.type)
                TYPE = channel_type.replace("_", " ").title() + " Channel"
                async for entry in channel.guild.audit_logs(
                    action=discord.AuditLogAction.channel_delete, limit=5
                ):
                    if entry.target.id == channel.id:
                        reason = entry.reason or None
                        user = entry.user or "UNKNOWN#0000"
                        entryID = entry.id
                        content = f"""**Channel Create Event**

`Name (ID) :` **{channel.name} [`{TYPE}`] ({channel.id})**
`Created at:` **<t:{int(channel.created_at.timestamp())}>**
`Position  :` **{channel.position}**
`Category  :` **{channel.category.mention if channel.category else None}**
`Caterogy Synced?:` **{channel.permissions_synced}**
`Reason    :` **{reason if reason else 'No reason provided'}**
`Entry ID  :` **{entryID if entryID else None}**
`Deleted by:` **{user}**
"""
                        break
                fp = io.BytesIO(self._overwrite_to_json(channel.overwrites).encode())
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="overwrites.json"),
                )
            if (
                channel.permissions_for(channel.guild.me).manage_channels
                and channel.permissions_for(channel.guild.default_role).send_messages
                and channel.permissions_for(channel.guild.me).manage_roles
            ):
                if data := await server_config.find_one({"_id": channel.guild.id}):
                    if data["muted_role"]:
                        if role := channel.guild.get_role(data["muted_role"]):
                            await channel.edit(
                                role, send_messages=False, add_reactions=False
                            )
                    else:
                        if role := discord.utils.get(channel.guild.roles, name="Muted"):
                            await channel.edit(
                                role, send_messages=False, add_reactions=False
                            )

    @Cog.listener()
    async def on_guild_channel_update(self, before, after):
        channel = after
        if not channel.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": before.guild.id, "on_channel_update": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_update"], session=self.bot.session
            )
            if webhook:
                channel_type = str(channel.type)
                TYPE = channel_type.replace("_", " ").title() + " Channel"
                async for entry in channel.guild.audit_logs(
                    action=discord.AuditLogAction.channel_update, limit=5
                ):
                    if entry.target.id == channel.id:
                        reason = entry.reason or None
                        user = entry.user or "UNKNOWN#0000"
                        entryID = entry.id
                        ls = self._channel_change(before, after, TYPE=channel_type)
                        ext = ""
                        for i, j in ls:
                            ext += f"{i} **{j}**\n"
                        content = f"""**Channel Update Event**

`Name (ID) :` **{channel.name} [`{TYPE}`] ({channel.id})**
`Created at:` **<t:{int(channel.created_at.timestamp())}>**
`Reason    :` **{reason if reason else 'No reason provided'}**
`Entry ID  :` **{entryID if entryID else None}**
`Updated by:` **{user}**

**Change/Update (Before)**
{ext}
"""
                        break

                fp = io.BytesIO(self._overwrite_to_json(channel.overwrites).encode())
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="overwrites.json"),
                )

    def _channel_change(self, before, after, *, TYPE: str) -> tuple:
        ls = []
        if before.name != after.name:
            ls.append(("`Name Changed     :`", before.name))
        if before.position != after.position:
            ls.append(("`Position Changed :`", before.position))
        if before.overwrites != after.overwrites:
            ls.append(
                ("`Overwrite Changed:`", self._overwrite_to_json(before.overwrites))
            )
        if before.category.id != after.category.id:
            ls.append(
                (
                    "`Category Changed :`"
                    if after.category
                    else "`Category Removed :`",
                    f"{before.category.name} ({before.category.id})",
                )
            )
        if before.permissions_synced is not after.permissions_synced:
            ls.append(("`Toggled Permissions Sync:`", after.permissions_synced))

        if "text" in TYPE.lower():
            if before.nsfw is not after.nsfw:
                ls.append(("`NSFW Toggled     :`", after.nsfw))
            if before.topic != after.topic:
                ls.append(("`Topic Changed    :`", after.topic))
            if before.slowmode_delay != after.slowmode_delay:
                ls.append(
                    (
                        "`Slowmode Delay Changed:`"
                        if after.slowmode_delay
                        else "`Slowmode Delay Removed:`",
                        after.slowmode_delay if after.slowmode_delay else None,
                    )
                )
        if "vc" in TYPE.lower():
            if before.user_limit != after.user_limit:
                ls.append(
                    (
                        "`Limit Updated    :`",
                        before.user_limit if before.user_limit else None,
                    )
                )
            if before.rtc_region != after.rtc_region:
                ls.append(
                    (
                        "`Region Updated   :`",
                        before.rtc_region if after.rtc_region is not None else "Auto",
                    )
                )
            if before.bitrate != after.bitrate:
                ls.append(("`Bitrate Updated  :`", before.bitrate))

    @Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        if not channel.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": channel.guild.id, "on_message_pin": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_pin"], session=self.bot.session
            )
            if webhook:
                async for entry in channel.guild.audit_logs(
                    action=discord.AuditLogAction.message_pin, limit=5
                ):
                    if entry.target.channel.id == channel.id:
                        user = entry.user or "UNKNOWN#0000"
                        entryID = entry.id
                        content = f"""**Message Pinned**

`ID       :` **{entry.extra.message_id}**
`Channel  :` **{channel.mention} ({channel.id})**
`Author   :` **{entry.target}**
`Pinned at:` **{discord.utils.format_dt(last_pin)}**
`Pinned by:` **{user}**
`Entry ID :` **{entryID}**
`Jump URL :` **<https://discord.com/channels/{channel.guild.id}/{channel.id}/{entry.extra.message_id}>**
"""
                        break
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                )

        if data := await self.collection.find_one(
            {"_id": channel.guild.id, "on_message_unpin": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_unpin"], session=self.bot.session
            )
            if webhook:
                async for entry in channel.guild.audit_logs(
                    action=discord.AuditLogAction.message_unpin, limit=5
                ):
                    if entry.target.channel.id == channel.id:
                        user = entry.user or "UNKNOWN#0000"
                        entryID = entry.id
                        content = f"""**Message Unpinned**

`ID         :` **{entry.extra.message_id}**
`Channel    :` **{channel.mention} ({channel.id})**
`Author     :` **{entry.target}**
`Unpinned at:` **{discord.utils.format_dt(last_pin)}**
`Unpinned by:` **{user}**
`Entry ID   :` **{entryID}**
`Jump URL   :` **<https://discord.com/channels/{channel.guild.id}/{channel.id}/{entry.extra.message_id}>**
"""
                        break
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                )

    @Cog.listener()
    async def on_guild_integrations_update(self, guild):
        pass

    @Cog.listener()
    async def on_webhooks_update(self, channel):
        pass


def setup(bot):
    bot.add_cog(GuildChannel(bot))
