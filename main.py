import jishaku

from keep_alive import keep_alive
from utils.config import EXTENSIONS, TOKEN
from core.bot import Parrot
from utils.extra import load_ext

bot = Parrot()

load_ext(bot, EXTENSIONS)

keep_alive()
bot.run(TOKEN)
