from .mod import moderation
from core import Parrot

def setup(bot: Parrot):
    bot.add_cog(moderation(bot))