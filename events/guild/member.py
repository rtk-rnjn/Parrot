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
        [i for i in li1 + li2 if i not in li1 or i not in li2]

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
                f"`Role Update     :`",
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
        if member.bot:
            return
        if before is None:
            if data := await log.find_one(
                {"_id": member.guild.id, "on_vc_join": {"$exists": True}}
            ):
                webhook = discord.Webhook.from_url(
                    data["on_vc_join"], session=self.bot.session
                )
            if webhook:
                content = f"""**On VC Join Event**

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

        if after is None:
            if data := await log.find_one(
                {"_id": member.guild.id, "on_vc_leave": {"$exists": True}}
            ):
                webhook = discord.Webhook.from_url(
                    data["on_vc_leave"], session=self.bot.session
                )
            if webhook:
                content = f"""**On VC Leave Event**

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

        if before and after:
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

    @Cog.listener()
    async def on_presence_update(self, before, after):
        pass  # nothing can be done, as discord dont gave use presence intent UwU


def setup(bot):
    bot.add_cog(Member(bot))
