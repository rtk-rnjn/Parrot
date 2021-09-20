from utilities.database import enable_disable
from core import Parrot

bot = Parrot()

@bot.before_invoke
async def bot_before_invoke(ctx):
    if ctx.guild is not None:
        if not ctx.guild.chunked:
            await ctx.guild.chunk()

@bot.check
async def can_run(ctx):
    if ctx.guild is not None:
        # is_owner = await bot.is_owner(ctx.author)
        # if is_owner: return True
        collection = enable_disable[f'{ctx.guild.id}']
        if data := await collection.find_one({'_id': ctx.command.qualified_name}):
            if ctx.channel.id in data['channel_in']: 
                print(1)
                return True
            for role in ctx.author.roles:
                if role.id in data['role_in']: 
                    print(2)
                    return True
                if role.id in data['role_out']: 
                    print(3)
                    return False
            if ctx.channel.id in data['channel_out']: return False
            if data['server']: return False
            if not data['server']: return True
        if data := await collection.find_one({'_id': ctx.command.cog.qualified_name}):
            if ctx.channel.id in data['channel_in']: return True
            for role in ctx.author.roles:
                if role.id in data['role_in']: return True
                if role.id in data['role_out']: return False
            if ctx.channel.id in data['channel_out']: return False
            if data['server']: return False
            if not data['server']: return True
        return True
    return False

if __name__ == '__main__':
    bot.run()
