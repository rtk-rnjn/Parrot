
from core import Parrot

bot = Parrot()

@bot.before_invoke
async def bot_before_invoke(ctx):
    if ctx.guild is not None:
        if not ctx.guild.chunked:
            await ctx.guild.chunk()

@bot.check
if __name__ == '__main__':
    bot.run()
