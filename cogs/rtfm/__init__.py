from .rtfm import rtfm 
from core import Parrot

def setup(bot: Parrot):
    bot.add_cog(rtfm(bot))