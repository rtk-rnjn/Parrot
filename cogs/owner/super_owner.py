from core import Parrot, Context, Cog
from aiofile import async_open
import traceback

class Owner(Cog):
    """You can not use these commands"""
    def __init__(self, bot: Parrot):
            self.bot = bot
            self.count = 0

    @commands.command()
    @commands.is_owner()
    async def gitload(self, ctx: Context, *, link: str):
        """To load the cog extension from github"""
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                data = await r.read()
        name = f"temp/temp{self.count}.py"
        
        try:
            async with async_open(f'{name}', 'wb') as f:
                await f.write(data)
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not create file `{name}.py`: ```py\n{tbe}\n```")
        else:
            await ctx.send("[SUCCESS] file `{name}.py` created")
        
        self.count += 1

        try:
            self.bot.load_extension(name)
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not load extension {name}: ```py\n{tbe}\n```")
        else:
            await ctx.send("[SUCCESS] Extension loaded `{name}.py`")
            
    @commands.command()
    @commands.is_owner()
    async def makefile(self, ctx: Context, name: str, *, text: str):
        """To make a file in ./temp/ directly"""
        try:
            async with async_open(f'{name}', 'w+') as f:
                await f.write(text)
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not create file `{name}`: ```py\n{tbe}\n```")
        else:
            await ctx.send("[SUCCESS] File `{name}` created")
            
def setup(bot):
    bot.add_cog(Owner(bot))