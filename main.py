import jishaku

from keep_alive import keep_alive

from utilities.config import EXTENSIONS, TOKEN
from utilities.extra import load_ext

from core.bot import Parrot

bot = Parrot()

load_ext(bot, EXTENSIONS)

keep_alive()
bot.run(TOKEN)
