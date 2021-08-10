
from core import Cog, Parrot

class Member(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member):
        pass

    @Cog.listener()
    async def on_member_remove(self, member):
        pass

    @Cog.listener()
    async def on_member_update(self, before, after):
        pass

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        pass

    @Cog.listener()
    async def on_presence_update(self, before, after):
        pass

def setup(bot):
    bot.add_cog(Member(bot))
