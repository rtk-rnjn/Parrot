
from core import Parrot, Context

bot = Parrot()


@bot.before_invoke
async def bot_before_invoke(ctx: Context):
    if ctx.guild:
        if not ctx.guild.chunked:
            await ctx.guild.chunk()


if __name__ == '__main__':
    bot.run()
