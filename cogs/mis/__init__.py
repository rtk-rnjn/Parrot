from .mis import misc
from core import Parrot

def setup(bot: Parrot):
    bot.add_cog(misc(bot))