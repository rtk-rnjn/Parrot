from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db
import discord
import time

collection = parrot_db["server_config"]
log = parrot_db["logging"]


class Member(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.muted = {}  # {GUILD_ID: {*MEMBER_IDS}}

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.bot.wait_until_ready()
        if data := await log.find_one(
            {"_id": member.guild.id, "on_member_join": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_member_join"], session=self.bot.session
            )
            if webhook:
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
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                )

        data = await collection.find_one({"_id": member.guild.id})
        if data:

            muted = member.guild.get_role(data["mute_role"]) or discord.utils.get(
                member.guild.roles, name="Muted"
            )
            if not muted:
                return

            if (member.guild.id in self.muted) and (
                member.id in self.muted[member.guild.id]
            ):
                self.muted[member.guild.id].remove(member.id)
                try:
                    await member.add_roles(
                        muted,
                        reason=f"Action auto performed | Reason: {member} attempted to mute bypass, by rejoining the server",
                    )
                except discord.errors.Forbidden:
                    pass

    @Cog.listener()
    async def on_member_remove(self, member):
        await self.bot.wait_until_ready()
        if data := await log.find_one(
            {"_id": member.guild.id, "on_member_leave": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_member_leave"], session=self.bot.session
            )
            if webhook:
                content = f"""**Member Joined Event**

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
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                )

        if data := await collection.find_one({"_id": member.guild.id}):
            muted = member.guild.get_role(data["mute_role"]) or discord.utils.get(
                member.guild.roles, name="Muted"
            )
            if muted and (muted in member.roles):
                if member.guild.id in self.muted:
                    self.muted[member.guild.id].add(member.id)
                elif member.guild.id not in self.muted:
                    self.muted[member.guild.id] = {member.id}

    def difference_list(self, li1: list, li2: list) -> list:
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
    async def on_member_update(self, before, after):
        await self.bot.wait_until_ready()
        if data := await log.find_one(
            {"_id": after.guild.id, "on_member_update": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_member_update"], session=self.bot.session
            )
            ch = ""
            for i, j in self._member_change(before, after):
                ch += f"{i} {j}\n"
            if webhook:
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
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                )

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        await self.bot.wait_until_ready()
        if member.bot:
            return
        if before is None:
            # member joined VC
            if data := await log.find_one(
                {"_id": member.guild.id, "on_vc_join": {"$exists": True}}
            ):
                webhook = discord.Webhook.from_url(
                    data["on_vc_join"], session=self.bot.session
                )
                if webhook:
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
                        avatar_url=self.bot.user.avatar.url,
                        username=self.bot.user.name,
                    )
                    return

        if after is None:
            # Member left VC
            if data := await log.find_one(
                {"_id": member.guild.id, "on_vc_leave": {"$exists": True}}
            ):
                webhook = discord.Webhook.from_url(
                    data["on_vc_leave"], session=self.bot.session
                )
                if webhook:
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
                        avatar_url=self.bot.user.avatar.url,
                        username=self.bot.user.name,
                    )
                    return

        if before and after:
            # Member moved
            if data := await log.find_one(
                {"_id": member.guild.id, "on_vc_move": {"$exists": True}}
            ):
                webhook = discord.Webhook.from_url(
                    data["on_vc_move"], session=self.bot.session
                )
                if webhook:
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
                        avatar_url=self.bot.user.avatar.url,
                        username=self.bot.user.name,
                    )
                    return

    async def __notify_member(self, error: str, *, member: discord.Member):
        try:
            await member.send(error)
        except discord.Forbidden:
            pass

    async def _get_index(self, guild: discord.Guild) -> int:
        if data := await parrot_db.server_config.find_one({"_id": guild.id, "temp_channels": {"$exists": True}}):
            return len(data["temp_channels"]) + 1
        
        return 1

    async def __on_voice_channel_join(self, channel, member):
        try:
            self.bot.server_config[member.guild.id]["hub"]
        except KeyError:
            return
        else:
            perms = member.guild.me.guild_permissions
            if not all(perms.manage_permissions, perms.manage_channels, perms.move_members):
                await self.__notify_member(
                    f"{member.mention} can not proceed to make Hub channel. Bot need `Manage Roles`, `Manage Channels` and `Move Members` permissions",
                    member=member
                )
                return
            if channel.id == self.bot.server_config[member.guild.id]["hub"]:
                if channel.category:
                    hub_channel = await member.guild.create_voice_channel(
                        f"[#{self._get_index(member.guild)}] {member.name}"
                    )
                    await parrot_db.server_config.update_one(
                        {"_id": member.guild.id},
                        {"$addToSet": {"temp_channels": {"channel_id": hub_channel.id, "author": member.id}}}
                    )
                    await member.edit(voice_channel=hub_channel, reason=f"{member} ({member.id}) created their Hub")
                else:
                    await self.__notify_member(
                        f"{member.mention} falied to create Hub for you. As the base Category is unreachable by the bot",
                        member=member
                    )
    
    async def __on_voice_channel_remove(self, channel, member):
        if data := await parrot_db.server_config.find_one(
            {"_id": member.guild.id, "temp_channels.channel_id": channel.id, "temp_channels.author": member.id}
        ):
            perms = member.guild.me.guild_permissions
            if not all(perms.manage_permissions, perms.manage_channels, perms.move_members):
                await self.__notify_member(
                    f"{member.mention} can not proceed to make Hub channel. Bot need `Manage Roles`, `Manage Channels` and `Move Members` permissions",
                    member=member
                )
                return
            for ch in data["temp_channels"]:
                if ch["channel_id"] == channel.id:
                    hub_channel = await self.bot.getch(self.bot.get_channel, self.bot.fetch_channel, channel.id)
                    await parrot_db.server_config.update_one(
                        {"_id": member.guild.id},
                        {"$pull": {"temp_channels.channel_id": hub_channel.id, "temp_channels.author": member.id}}
                    )
                    await hub_channel.delete(reason=f"{member} ({member.id}) left their Hub")
                    return

    @Cog.listener(name="on_voice_state_update")
    async def hub_on_voice_state_update(self, member, before, after):
        await self.bot.wait_until_ready()
        if member.bot:
            return
        if member.guild is None:
            return
        
        if before and after:
            await self.__on_voice_channel_join(after.channel, member)
            await self.__on_voice_channel_remove(before.channel, member)
            return

        if before is None:
            return await self.__on_voice_channel_join(after.channel, member)
        if after is None:
            return await self.__on_voice_channel_remove(before.channel, member)
    @Cog.listener()
    async def on_presence_update(self, before, after):
        pass  # nothing can be done, as discord dont gave use presence intent UwU


def setup(bot):
    bot.add_cog(Member(bot))
