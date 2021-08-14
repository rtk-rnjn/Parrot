
from core import Cog, Parrot
from utilities.database import parrot_db
import discord

collection = parrot_db['server_config']


class Member(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.mute = {}

    @Cog.listener()
    async def on_member_join(self, member):
        data = await collection.find_one({'_id': member.guild.id})
        if not data:
            return

        muted = member.guild.get_role(data['mute_role']) or discord.utils.get(member.guild.roles, name="Muted")
        if not muted:
            return 
        
        if self.mute[member.id]:
            await member.add_roles(muted, reason=f"Action auto performed | Reason: {member.name}#{member.discriminator} Attempt to mute bypass, by rejoining the server")

    @Cog.listener()
    async def on_member_remove(self, member):
        data = await collection.find_one({'_id': member.guild.id})
        if not data:
            return

        muted = member.guild.get_role(data['mute_role']) or discord.utils.get(member.guild.roles, name="Muted")
        if not muted:
            return
        
        if muted in member.roles: 
            self.mute[member.id] = True

    @Cog.listener()
    async def on_member_update(self, before, after):
        data = await collection.find_one({'_id': after.guild.id})
        if not data:
            return

        muted = after.guild.get_role(data['mute_role']) or discord.utils.get(after.guild.roles, name="Muted")
        if not muted:
            return
        
        if (muted in before.roles) and (muted not in after.roles):
            await after.add_roles(muted, reason=f"Action auto performed | Reason: {member.name}#{member.discriminator} Attempt to mute bypass.")

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        pass

    @Cog.listener()
    async def on_presence_update(self, before, after):
        pass

def setup(bot):
    bot.add_cog(Member(bot))
