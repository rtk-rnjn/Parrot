from __future__ import annotations

import io
import json
from contextlib import suppress
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import discord
from core import Cog, Parrot


class GuildChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = bot.mongo.parrot_db["logging"]

    def _overwrite_to_json(
        self,
        overwrites: Dict[
            Union[discord.Role, discord.User], discord.PermissionOverwrite
        ],
    ) -> str:
        try:
            over = {
                f"{str(target.name)} ({'Role' if isinstance(target, discord.Role) else 'Member'})": overwrite._values
                for target, overwrite in overwrites.items()
            }
            return json.dumps(over, indent=4)
        except TypeError:
            return "{}"

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self.bot.wait_until_ready()
        if not channel.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": channel.guild.id, "on_channel_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_delete"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
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
`Created at:` **{discord.utils.format_dt(channel.created_at)}**
`Position  :` **{channel.position}**
`Category  :` **{channel.category.mention if channel.category else None}**
`Caterogy Synced?:` **{channel.permissions_synced}**
`Reason    :` **{reason or 'No reason provided'}**
`Deleted at:` **{discord.utils.format_dt(deleted_at) if deleted_at else 'Not available'}**
`Deleted by:` **{user}**
"""

                        fp = io.BytesIO(
                            self._overwrite_to_json(channel.overwrites).encode()
                        )
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                            file=discord.File(fp, filename="overwrites.json"),
                        )
                        break

    @Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await self.bot.wait_until_ready()
        if not channel.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": channel.guild.id, "on_channel_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_create"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
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
`Created at:` **{discord.utils.format_dt(channel.created_at)}**
`Position  :` **{channel.position}**
`Category  :` **{channel.category.mention if channel.category else None}**
`Caterogy Synced?:` **{channel.permissions_synced}**
`Reason    :` **{reason or 'No reason provided'}**
`Entry ID  :` **{entryID or None}**
`Deleted by:` **{user}**
"""

                        fp = io.BytesIO(
                            self._overwrite_to_json(channel.overwrites).encode()
                        )
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                            file=discord.File(fp, filename="overwrites.json"),
                        )
                        break

            if (
                channel.permissions_for(channel.guild.me).manage_channels
                and channel.permissions_for(channel.guild.default_role).send_messages
                and channel.permissions_for(channel.guild.me).manage_roles
            ):
                if role_id := self.bot.guild_configurations[channel.guild.id][
                    "mute_role"
                ]:
                    if role := channel.guild.get_role(role_id):
                        await channel.set_permissions(
                            role, send_messages=False, add_reactions=False
                        )
                elif role := discord.utils.get(channel.guild.roles, name="Muted"):
                    await channel.set_permissions(
                        role, send_messages=False, add_reactions=False
                    )

    @Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        await self.bot.wait_until_ready()
        channel = after
        if not channel.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": before.guild.id, "on_channel_update": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_update"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
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
                        ext = "".join(f"{i} **{j}**\n" for i, j in ls)
                        content = f"""**Channel Update Event**

`Name (ID) :` **{channel.name} [`{TYPE}`] ({channel.id})**
`Created at:` **{discord.utils.format_dt(channel.created_at)}**
`Reason    :` **{reason or 'No reason provided'}**
`Entry ID  :` **{entryID or None}**
`Updated by:` **{user}**

**Change/Update (Before)**
{ext}
"""

                        fp = io.BytesIO(
                            self._overwrite_to_json(channel.overwrites).encode()
                        )
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                            file=discord.File(fp, filename="overwrites.json"),
                        )
                        break

    def _channel_change(
        self,
        before: discord.abc.GuildChannel,
        after: discord.abc.GuildChannel,
        *,
        TYPE: str,
    ) -> List[Tuple[str, Any]]:
        ls = []
        if before.name != after.name:
            ls.append(("`Name Changed     :`", before.name))
        if before.position != after.position:
            ls.append(("`Position Changed :`", before.position))
        if before.overwrites != after.overwrites:
            ls.append(
                ("`Overwrite Changed:`", self._overwrite_to_json(before.overwrites))
            )
        if (
            before.category
            and after.category
            and before.category.id != after.category.id
        ):
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
                        after.slowmode_delay or None,
                    )
                )

        if "vc" in TYPE.lower():
            if before.user_limit != after.user_limit:
                ls.append(("`Limit Updated    :`", before.user_limit or None))
            if before.rtc_region != after.rtc_region:
                ls.append(
                    (
                        "`Region Updated   :`",
                        before.rtc_region if after.rtc_region is not None else "Auto",
                    )
                )
            if before.bitrate != after.bitrate:
                ls.append(("`Bitrate Updated  :`", before.bitrate))
        return ls

    @Cog.listener()
    async def on_guild_channel_pins_update(
        self,
        channel: Union[discord.abc.GuildChannel, discord.Thread],
        last_pin: Optional[datetime],
    ):
        await self.bot.wait_until_ready()
        if not channel.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": channel.guild.id, "on_message_pin": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_pin"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
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
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                        )
                        break

        if data := await self.collection.find_one(
            {"_id": channel.guild.id, "on_message_unpin": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_channel_unpin"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
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
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                        )
                        break

    @Cog.listener()
    async def on_guild_integrations_update(self, guild: discord.Guild):
        pass

    @Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        pass

    @Cog.listener()
    async def on_integration_create(self, integration: discord.Integration):
        pass

    @Cog.listener()
    async def on_integration_update(self, integration: discord.Integration):
        pass

    @Cog.listener()
    async def on_raw_integration_delete(
        self, payload: discord.RawIntegrationDeleteEvent
    ):
        pass


async def setup(bot):
    await bot.add_cog(GuildChannel(bot))
