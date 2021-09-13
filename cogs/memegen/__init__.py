from core import Parrot
from .memegen import memegen

def setup(bot: Parrot):
    bot.add_cog(memegen(bot))