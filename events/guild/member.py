from __future__ import annotations

import time
from contextlib import suppress
from typing import Dict, List, Optional, Set, Union

from pymongo import UpdateOne

import discord
from core import Cog, Parrot

from ._member import _MemberJoin as MemberJoin


class Member(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.muted: Dict[int, Set[int]] = {}  # {GUILD_ID: {*MEMBER_IDS}}

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.bot.wait_until_ready()
        if data := await self.bot.mongo.parrot_db.logging.find_one(
            {"_id": member.guild.id, "on_member_join": {"$exists": True}}
        ):
            webhook: discord.Webhook = discord.Webhook.from_url(
                data["on_member_join"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                content = f"""**Member Joined Event**

`Name (ID)  :` **{member} (`{member.id}`)**
`Account age:` **{discord.utils.format_dt(member.created_at)}**
`Joined at  :` **{discord.utils.format_dt(member.joined_at)}**
`Is Bot?    :` **{member.bot}**
`Verified?  :` **{not member.pending}**
`Badges     :` **{', '.join([str(i).replace('.', ':').split(':')[1].replace('_', ' ').title() if i else None for i in member.public_flags.all()])}**
`Premium Since:` **{discord.utils.format_dt(member.premium_since) if member.premium_since else None}**
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.display_avatar.url,
                    username=self.bot.user.name,
                )

        try:
            role = int(self.bot.server_config[member.guild.id]["mute_role"] or 0)
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
        await self.bot.wait_until_ready()
        if data := await self.bot.mongo.parrot_db.logging.find_one(
            {"_id": member.guild.id, "on_member_leave": {"$exists": True}}
        ):
            webhook: discord.Webhook = discord.Webhook.from_url(
                data["on_member_leave"], session=self.bot.http_session
            )
            with suppress(discord.HTTPException):
                content = f"""**Member Leave Event**

`Name (ID)  :` **{member} (`{member.id}`)**
`Account age:` **{discord.utils.format_dt(member.created_at)}**
`Joined at  :` **{discord.utils.format_dt(member.joined_at)}**
`Left at    :` **<t:{int(time.time())}>**
`Is Bot?    :` **{member.bot}**
`Verified?  :` **{not member.pending}**
`Badges     :` **{', '.join([str(i).replace('.', ':').split(':')[1].replace('_', ' ').title() if i else None for i in member.public_flags.all()])}**
`Premium Since:` **{discord.utils.format_dt(member.premium_since) if member.premium_since else None}**
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.display_avatar.url,
                    username=self.bot.user.name,
                )

    @Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        member = payload.user
        if isinstance(member, discord.User) or member.bot:
            return
        try:
            role = int(self.bot.server_config[payload.guild_id]["mute_role"] or 0)
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

    def difference_list(self, li1: List, li2: List) -> List:
        return [i for i in li1 + li2 if i not in li1 or i not in li2]

    def _member_change(self, before, after):
        ls = []
        if before.nick != after.nick:
            ls.append(["`Nickname Changed:`", before.nick])
        if before.name != after.name:
            ls.append(["`Name changed    :`", before.name])
        if before.discriminator != after.discriminator:
            ls.append(["`Discriminator   :`", before.discriminator])
        if before.display_avatar.url != after.display_avatar.url:
            ls.append(["`Avatar Changed  :`", f"<{before.display_avatar.url}>"])
        if before.roles != after.roles:
            ls.append(
                "`Role Update     :`",
                ", ".join(
                    [
                        role.name
                        for role in self.difference_list(before.roles, after.roles)
                    ]
                ),
            )
        return ls

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        await self.bot.wait_until_ready()
        if data := await self.bot.mongo.parrot_db.logging.find_one(
            {"_id": after.guild.id, "on_member_update": {"$exists": True}}
        ):
            webhook: discord.Webhook = discord.Webhook.from_url(
                data["on_member_update"], session=self.bot.http_session
            )
            ch = "".join(f"{i} {j}\n" for i, j in self._member_change(before, after))
            with suppress(discord.HTTPException):
                content = f"""**On Member Update**

`Name       :` **{after.name} (`{after.id}`)**
`Account age:` **{discord.utils.format_dt(after.created_at)}**
`Joined at  :` **{discord.utils.format_dt(after.joined_at)}**
`Badges     :` **{', '.join([str(i).replace('.', ':').split(':')[1].replace('_', ' ').title() if i else None for i in after.public_flags.all()])}**
`Premium Since:` **{discord.utils.format_dt(after.premium_since) if after.premium_since else None}**

**Change/Update (Before)**
{ch}
"""
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.display_avatar.url,
                    username=self.bot.user.name,
                )

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        await self.bot.wait_until_ready()
        if member.bot:
            return
        if before.channel is None:
            # member joined VC
            if data := await self.bot.mongo.parrot_db.logging.find_one(
                {"_id": member.guild.id, "on_vc_join": {"$exists": True}}
            ):
                webhook: discord.Webhook = discord.Webhook.from_url(
                    data["on_vc_join"], session=self.bot.http_session
                )
                with suppress(discord.HTTPException):
                    content = f"""**On VC Join Event**

`Member     :` **{member}** (`{member.id}`)
`Channel    :` **{after.channel.mention}** (`{after.channel.id}`)
`Server Mute:` **{after.mute}**
`Server Deaf:` **{after.deaf}**
`Self Mute  :` **{after.self_mute}**
`Self Deaf  :` **{after.self_deaf}**
"""
                    await webhook.send(
                        content=content,
                        avatar_url=self.bot.user.display_avatar.url,
                        username=self.bot.user.name,
                    )
                    return

        if after.channel is None:
            # Member left VC
            if data := await self.bot.mongo.parrot_db.logging.find_one(
                {"_id": member.guild.id, "on_vc_leave": {"$exists": True}}
            ):
                webhook: discord.Webhook = discord.Webhook.from_url(
                    data["on_vc_leave"], session=self.bot.http_session
                )
                with suppress(discord.HTTPException):
                    content = f"""**On VC Leave Event**

`Member     :` **{member}** (`{member.id}`)
`Channel    :` **{before.channel.mention}** (`{before.channel.id}`)
`Server Mute:` **{before.mute}**
`Server Deaf:` **{before.deaf}**
`Self Mute  :` **{before.self_mute}**
`Self Deaf  :` **{before.self_deaf}**
"""
                    await webhook.send(
                        content=content,
                        avatar_url=self.bot.user.display_avatar.url,
                        username=self.bot.user.name,
                    )
                    return

        if before.channel and after.channel:
            # Member moved
            if data := await self.bot.mongo.parrot_db.logging.find_one(
                {"_id": member.guild.id, "on_vc_move": {"$exists": True}}
            ):
                webhook: discord.Webhook = discord.Webhook.from_url(
                    data["on_vc_move"], session=self.bot.http_session
                )
                with suppress(discord.HTTPException):
                    content = f"""**On VC Move Event**

`Member     :` **{member}** (`{member.id}`)
`Channel (A):` **{after.channel.mention}** (`{after.channel.id}`) 
`Channel (B):` **{before.channel.mention}** (`{before.channel.id}`)
`Server Mute:` **A: {after.mute}** | **B: {before.mute}**
`Server Deaf:` **A: {after.deaf}** | **B: {before.deaf}**
`Self Mute  :` **A: {after.self_mute}** | **B: {after.self_mute}**
`Self Deaf  :` **A: {after.self_deaf}** | **B: {after.self_deaf}**
"""
                    await webhook.send(
                        content=content,
                        avatar_url=self.bot.user.display_avatar.url,
                        username=self.bot.user.name,
                    )
                    return

    async def __notify_member(self, error: str, *, member: discord.Member):
        with suppress(discord.Forbidden):
            await member.send(error)

    async def _get_index(self, guild: discord.Guild) -> int:
        if data := await self.bot.mongo.parrot_db.server_config.find_one(
            {"_id": guild.id, "temp_channels": {"$exists": True}}
        ):
            return len(data["temp_channels"]) + 1

        return 1

    async def __on_voice_channel_join(
        self,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
        member: discord.Member,
    ):
        try:
            self.bot.server_config[member.guild.id]["hub"]
        except KeyError:
            return
        else:
            perms = member.guild.me.guild_permissions
            if not all(
                [perms.manage_permissions, perms.manage_channels, perms.move_members]
            ):
                return
            if channel.id == self.bot.server_config[member.guild.id]["hub"]:
                if channel.category:
                    hub_channel = await member.guild.create_voice_channel(
                        f"[#{await self._get_index(member.guild)}] {member.name}",
                        category=channel.category,
                    )
                    await self.bot.mongo.parrot_db.server_config.update_one(
                        {"_id": member.guild.id},
                        {
                            "$addToSet": {
                                "temp_channels": {
                                    "channel_id": hub_channel.id,
                                    "author": member.id,
                                }
                            }
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
        if data := await self.bot.mongo.parrot_db.server_config.find_one(
            {
                "_id": member.guild.id,
                "temp_channels.channel_id": channel.id,
                "temp_channels.author": member.id,
            }
        ):
            perms = member.guild.me.guild_permissions
            if not all(
                [perms.manage_permissions, perms.manage_channels, perms.move_members]
            ):
                return
            for ch in data["temp_channels"]:
                if ch["channel_id"] == channel.id and ch["author"] == member.id:
                    hub_channel = await self.bot.getch(
                        self.bot.get_channel, self.bot.fetch_channel, channel.id
                    )
                    await self.bot.mongo.parrot_db.server_config.update_one(
                        {"_id": member.guild.id},
                        {"$pull": {"temp_channels": {"channel_id": hub_channel.id}}},
                    )
                    await hub_channel.delete(
                        reason=f"{member} ({member.id}) left their Hub"
                    )
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

        if before.channel is None:
            return await self.__on_voice_channel_join(after.channel, member)

        if after.channel is None:
            return await self.__on_voice_channel_remove(before.channel, member)

    @Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        pass  # nothing can be done, as discord dont gave use presence intent UwU

    async def cog_load(self):
        async for data in self.bot.mongo.parrot_db.server_config.find(
            {"muted": {"$exists": True}}
        ):
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

        await self.bot.mongo.parrot_db.server_config.write_bulk(operations)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Member(bot))
    await bot.add_cog(MemberJoin(bot))
