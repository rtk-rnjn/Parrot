from utilities.checks import _can_run
from utilities.database import parrot_db
collection = parrot_db['banned_users']

from core import Parrot

bot = Parrot()


@bot.before_invoke
async def bot_before_invoke(ctx):
    if ctx.guild is not None:
        if not ctx.guild.chunked:
            await ctx.guild.chunk()


@bot.check
async def bot_check(ctx):
    if ctx.command is not None:
        _true = await _can_run(ctx)
        return _true


@bot.check_once
async def check_once(ctx):
    if data := await collection.find_one({'_id': ctx.author.id}):
        return False
    return True

if __name__ == '__main__':
    bot.run()
