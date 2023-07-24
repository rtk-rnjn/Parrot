from __future__ import annotations

from contextlib import suppress
from typing import Optional, Union

from pymongo import UpdateOne

import discord
from core import Cog, Parrot

from ._member import _MemberJoin as MemberJoin


class Member(Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.muted: dict[int, set[int]] = {}  # {GUILD_ID: {*MEMBER_IDS}}

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            role = int(self.bot.guild_configurations_cache[member.guild.id]["mute_role"] or 0)
            role: Optional[discord.Role] = member.guild.get_role(role)
        except KeyError:
            role = discord.utils.get(member.guild.roles, name="Muted")

        if role is None:
            role = discord.utils.get(member.guild.roles, name="Muted")

        if member.id in self.muted.get(member.guild.id, []) and role is not None:
            self.muted[member.guild.id].remove(member.id)
            with suppress(discord.Forbidden):
                await member.add_roles(
                    role,
                    reason=f"Action auto performed | Reason: {member} attempted to mute bypass, by rejoining the server",
                )

    @Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pass

    @Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        member = payload.user
        if isinstance(member, discord.User) or member.bot:
            return
        try:
            role = int(self.bot.guild_configurations_cache[payload.guild_id]["mute_role"] or 0)
            role = member.guild.get_role(role)
        except KeyError:
            role = discord.utils.find(lambda m: "muted" in m.name.lower(), member.roles)
        if role is None:
            role = discord.utils.find(lambda m: "muted" in m.name.lower(), member.roles)

        if role in member.roles:
            if guild_set := self.muted.get(member.guild.id):
                guild_set.add(member.id)
            else:
                self.muted[member.guild.id] = {member.id}

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        pass

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        pass

    async def __notify_member(self, error: str, *, member: discord.Member):
        with suppress(discord.Forbidden):
            await member.send(error)

    async def _get_index(self, guild: discord.Guild) -> int:
        if data := await self.bot.guild_configurations.find_one({"_id": guild.id, "hub_temp_channels": {"$exists": True}}):
            return len(data["hub_temp_channels"]) + 1

        return 1

    async def __on_voice_channel_join(
        self,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
        member: discord.Member,
    ):
        try:
            self.bot.guild_configurations_cache[member.guild.id]["hub"]
        except KeyError:
            return
        else:
            perms = member.guild.me.guild_permissions
            if not all([perms.manage_permissions, perms.manage_channels, perms.move_members]):
                return
            if channel.id == self.bot.guild_configurations_cache[member.guild.id]["hub"]:
                if channel.category:
                    hub_channel = await member.guild.create_voice_channel(
                        f"[#{await self._get_index(member.guild)}] {member.name}",
                        category=channel.category,
                    )
                    await self.bot.guild_configurations.update_one(
                        {"_id": member.guild.id},
                        {
                            "$addToSet": {
                                "hub_temp_channels": {
                                    "channel_id": hub_channel.id,
                                    "author": member.id,
                                },
                            },
                        },
                    )
                    await member.edit(
                        voice_channel=hub_channel,
                        reason=f"{member} ({member.id}) created their Hub",
                    )
                else:
                    await self.__notify_member(
                        f"{member.mention} falied to create Hub for you. As the base Category is unreachable by the bot",
                        member=member,
                    )

    async def __on_voice_channel_remove(
        self,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
        member: discord.Member,
    ):
        if data := await self.bot.guild_configurations.find_one(
            {
                "_id": member.guild.id,
                "hub_temp_channels.channel_id": channel.id,
                "hub_temp_channels.author": member.id,
            },
        ):
            perms = member.guild.me.guild_permissions
            if not all([perms.manage_permissions, perms.manage_channels, perms.move_members]):
                return
            for ch in data["hub_temp_channels"]:
                if ch["channel_id"] == channel.id and ch["author"] == member.id:
                    hub_channel = await self.bot.getch(self.bot.get_channel, self.bot.fetch_channel, channel.id)
                    await self.bot.guild_configurations.update_one(
                        {"_id": member.guild.id},
                        {"$pull": {"hub_temp_channels": {"channel_id": hub_channel.id}}},
                    )
                    await hub_channel.delete(reason=f"{member} ({member.id}) left their Hub")
                    return

    @Cog.listener(name="on_voice_state_update")
    async def hub_on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        await self.bot.wait_until_ready()
        if member.bot:
            return

        if member.guild is None:
            return

        __channel = before.channel or after.channel
        if isinstance(__channel, discord.StageChannel) or __channel is None:
            return

        if before.channel and after.channel:
            await self.__on_voice_channel_join(after.channel, member)
            await self.__on_voice_channel_remove(before.channel, member)
            return

        if before.channel is None and after.channel is not None:
            return await self.__on_voice_channel_join(after.channel, member)

        if after.channel is None and before.channel is not None:
            return await self.__on_voice_channel_remove(before.channel, member)

    @Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        pass  # nothing can be done, as discord dont gave use presence intent UwU

    async def cog_load(self):
        async for data in self.bot.guild_configurations.find({"muted": {"$exists": True}}):
            self.muted[data["_id"]] = set(data["muted"])

    async def cog_unload(self):
        operations = [
            UpdateOne(
                {"_id": guild_id},
                {"$set": {"muted": list(set_member_muted)}},
                upsert=True,
            )
            for guild_id, set_member_muted in self.muted.items()
        ]

        await self.bot.guild_configurations.write_bulk(operations)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Member(bot))
    await bot.add_cog(MemberJoin(bot))
