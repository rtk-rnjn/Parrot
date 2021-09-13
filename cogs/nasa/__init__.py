from core import Parrot
from .nasa import nasa

def setup(bot: Parrot):
    bot.add_cog(nasa(bot))