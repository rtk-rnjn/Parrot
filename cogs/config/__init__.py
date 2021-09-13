from .config import botConfig
from core import Parrot

def setup(bot: Parrot):
    bot.add_cog(botConfig(bot))