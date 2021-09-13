from .help import HelpCog
from core import Parrot

def setup(bot: Parrot):
    bot.add_cog(HelpCog(bot))