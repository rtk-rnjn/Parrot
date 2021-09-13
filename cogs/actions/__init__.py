from .actions import actions
from core import Parrot

def setup(bot: Parrot):
    bot.add_cog(actions(bot))