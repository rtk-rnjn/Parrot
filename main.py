import jishaku
from keep_alive import keep_alive
from utilities.config import TOKEN
from core.bot import Parrot

bot = Parrot()

keep_alive()
bot.run(TOKEN)

#  REGEX FOR TIME