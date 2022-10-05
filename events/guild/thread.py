from __future__ import annotations

from contextlib import suppress

import discord
from core import Cog, Parrot
from discord import utils


class OnThread(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.collection = bot.mongo.parrot_db["logging"]
        self.ON_TESTING = False

    @Cog.listener()
    async def on_thread_join(self, thread: discord.Thread) -> None:
        await self.bot.wait_until_ready()
        if not thread.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": thread.guild.id, "on_thread_create": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_thread_create"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                async for entry in thread.guild.audit_logs(
                    action=discord.AuditLogAction.thread_create, limit=5
                ):
                    if entry.target.id == thread.id:
                        reason = entry.reason
                        user = entry.user or "UNKNOWN#0000"
                        entryID = entry.id

                        content = f"""**On Thread Create**

`Name      :` **{thread.name}** **(`{thread.id}`)**
`Created by:` **{user}**
`Created at:` **{utils.format_dt(utils.snowflake_time(thread.id))}**
`Reason    :` **{reason}**
`Entry ID  :` **{entryID}**
`Parent    :` **<#{thread.parent_id}>**
`Owner     :` **{thread.owner}** **(`{thread.owner_id}`)**
"""
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                        )
                        break

    @Cog.listener()
    async def on_thread_remove(self, thread: discord.Thread) -> None:
        await self.bot.wait_until_ready()
        if not thread.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": thread.guild.id, "on_thread_remove": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_thread_remove"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                content = f"""**On Thread Remove**

`Name      :` **{thread.name}** **(`{thread.id}`)**
`Created at:` **{utils.format_dt(utils.snowflake_time(thread.id))}**
`Parent    :` **<#{thread.parent_id}>**
`Owner     :` **{thread.owner}** **(`{thread.owner_id}`)**
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.display_avatar.url,
                    username=self.bot.user.name,
                )

    @Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        await self.bot.wait_until_ready()
        if not thread.guild.me.guild_permissions.view_audit_log:
            return
        if data := await self.collection.find_one(
            {"_id": thread.guild.id, "on_thread_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_thread_delete"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                async for entry in thread.guild.audit_logs(
                    action=discord.AuditLogAction.thread_delete, limit=5
                ):
                    if entry.target.id == thread.id:
                        reason = entry.reason
                        entryID = entry.id

                        content = f"""**On Thread Create**

`Name      :` **{thread.name}** **(`{thread.id}`)**
`Created at:` **{utils.format_dt(utils.snowflake_time(thread.id))}**
`Reason    :` **{reason}**
`Entry ID  :` **{entryID}**
`Parent    :` **<#{thread.parent_id}>**
`Owner     :` **{thread.owner}** **(`{thread.owner_id}`)**
"""
                        await webhook.send(
                            content=content,
                            avatar_url=self.bot.user.display_avatar.url,
                            username=self.bot.user.name,
                        )
                        break

    @Cog.listener()
    async def on_thread_member_join(self, member: discord.ThreadMember) -> None:
        await self.bot.wait_until_ready()
        if data := await self.collection.find_one(
            {"_id": member.thread.guild.id, "on_member_join_thread": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_member_join_thread"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                guild_member = await self.bot.get_or_fetch_member(
                    member.thread.guild, member.id
                )
                content = f"""**On Member Thread Join**

`Member    :` **{guild_member}** **(`{member.id}`)**
`Name      :` **{member.thread.name}** **(`{member.thread.id}`)**
`Created at:` **{utils.format_dt(utils.snowflake_time(member.thread.id))}**
`Joined at :` **{utils.format_dt(member.joined_at)}**
`Parent    :` **<#{member.thread.parent_id}>**
`Owner     :` **{member.thread.owner}** **(`{member.thread.owner_id}`)**
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.display_avatar.url,
                    username=self.bot.user.name,
                )

    @Cog.listener()
    async def on_thread_member_remove(self, member: discord.ThreadMember) -> None:
        await self.bot.wait_until_ready()
        if data := await self.collection.find_one(
            {"_id": member.thread.guild.id, "on_member_leave_thread": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_member_leave_thread"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                guild_member = await self.bot.get_or_fetch_member(
                    member.thread.guild, member.id
                )
                content = f"""**On Member Thread Leave**

`Member    :` **{guild_member}** **(`{member.id}`)**
`Name      :` **{member.thread.name}** **(`{member.thread.id}`)**
`Created at:` **{utils.format_dt(utils.snowflake_time(member.thread.id))}**
`Joined at :` **{utils.format_dt(member.joined_at)}**
`Parent    :` **<#{member.thread.parent_id}>**
`Owner     :` **{member.thread.owner}** **(`{member.thread.owner_id}`)**
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.display_avatar.url,
                    username=self.bot.user.name,
                )

    def difference_thread(self, before: discord.Thread, after: discord.Thread) -> list:
        ls = []
        if before.name != after.name:
            ls.append(["`Name        :`", f"**{before.name}**"])
        if before.member_count != after.member_count:
            ls.append(["`Member Count:`", f"**{before.member_count}**"])
        return ls

    @Cog.listener()
    async def on_thread_update(
        self, before: discord.Thread, after: discord.Thread
    ) -> None:
        await self.bot.wait_until_ready()
        if data := await self.collection.find_one(
            {"_id": after.guild.id, "on_thread_update": {"$exists": True}}
        ):
            thread = after
            webhook = discord.Webhook.from_url(
                data["on_thread_update"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                change = "\n".join(self.difference_thread(before, after))
                content = f"""**On Thread Update**

`Name      :` **{thread.name}** **(`{thread.id}`)**
`Created at:` **{utils.format_dt(utils.snowflake_time(thread.id))}**
`Parent    :` **<#{thread.parent_id}>**
`Owner     :` **{thread.owner}** **(`{thread.owner_id}`)**

**Change/Update (Before)**
{change}
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.display_avatar.url,
                    username=self.bot.user.name,
                )

    @Cog.listener()
    async def on_raw_thread_update(self, payload: discord.RawThreadUpdateEvent) -> None:
        pass

    @Cog.listener()
    async def on_raw_thread_delete(self, payload: discord.RawThreadDeleteEvent) -> None:
        pass

    @Cog.listener()
    async def on_raw_thread_member_remove(
        self, payload: discord.RawThreadMembersUpdate
    ) -> None:
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(OnThread(bot))
