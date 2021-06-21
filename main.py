import jishaku

from keep_alive import keep_alive
from utilities.config import EXTENSIONS
from utilities.config import TOKEN
from core.bot import Parrot
from utils.extra import load_ext

bot = Parrot()

load_ext(bot, EXTENSIONS)

keep_alive()
bot.run(TOKEN)
