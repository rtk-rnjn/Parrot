from .mod import mod
from core import Parrot

def setup(bot: Parrot):
    bot.add_cog(mod(bot))