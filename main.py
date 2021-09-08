
VER = "v3.8.0"
from core import Parrot

bot = Parrot()

@bot.check
async def check_ban(ctx):
    if ctx.guild in None:
        return False
    else: 
        return True

if __name__ == '__main__':
    bot.run()
