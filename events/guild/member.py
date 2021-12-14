from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db
import discord, time

collection = parrot_db['server_config']
log = parrot_db['logging']


class Member(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.muted = {}  # {GUILD_ID: {*MEMBER_IDS}}

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if data := await log.find_one({'_id': member.guild.id, 'on_member_join': {'$exists': True}}):
            webhook = discord.Webhook.from_url(data['on_member_join'], session=self.bot.session)
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
                await webhook.send(content=content, avatar_url=self.bot.user.avatar.url, username=self.bot.user.name)
            
        data = await collection.find_one({'_id': member.guild.id})
        if data:

            muted = member.guild.get_role(data['mute_role']) or discord.utils.get(
                member.guild.roles, name="Muted")
            if not muted:
                return

            if member.guild.id in self.muted:
                if member.id in self.muted[member.guild.id]:
                    self.muted[member.guild.id].remove(member.id)
                    try:
                        await member.add_roles(
                            muted,
                            reason=
                            f"Action auto performed | Reason: {member} attempted to mute bypass, by rejoining the server"
                        )
                    except discord.errors.Forbidden:
                        pass
        

    @Cog.listener()
    async def on_member_remove(self, member):
        if data := await log.find_one({'_id': member.guild.id, 'on_member_leave': {'$exists': True}}):
            webhook = discord.Webhook.from_url(data['on_member_leave'], session=self.bot.session)
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
                await webhook.send(content=content, avatar_url=self.bot.user.avatar.url, username=self.bot.user.name)
        
        if data := await collection.find_one({'_id': member.guild.id}):
            muted = member.guild.get_role(data['mute_role']) or discord.utils.get(
                member.guild.roles, name="Muted")
            if muted:
                if muted in member.roles:
                    if member.guild.id in self.muted:
                        self.muted[member.guild.id].add(member.id)
                    elif member.guild.id not in self.muted:
                        self.muted[member.guild.id] = {member.id}

    @Cog.listener()
    async def on_member_update(self, before, after):
        pass

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        pass

    @Cog.listener()
    async def on_presence_update(self, before, after):
        pass # nothing can be done, as discord dont gave use presence intent UwU


def setup(bot):
    bot.add_cog(Member(bot))
