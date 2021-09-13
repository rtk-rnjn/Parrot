from core import Parrot, Context, Cog
from aiofile import async_open
import traceback
from discord.ext import commands
import discord, aiohttp
from utilities.database import ban
import datetime
import os

class Owner(Cog):
    """You can not use these commands"""
    def __init__(self, bot: Parrot):
            self.bot = bot
            self.count = 0
            self.owner = None

    @commands.command()
    @commands.is_owner()
    @Context.with_type
    async def gitload(self, ctx: Context, *, link: str):
        """To load the cog extension from github"""
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                data = await r.read()
        name = f"temp/temp{self.count}"
        name_cog = f"temp.temp{self.count}"
        try:
            async with async_open(f'{name}.py', 'wb') as f:
                await f.write(data)
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not create file `{name}.py`: ```py\n{tbe}\n```")
        else:
            await ctx.send(f"[SUCCESS] file `{name}.py` created")
        
        try:
            self.bot.load_extension(f'{name_cog}')
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not load extension {name_cog}.py: ```py\n{tbe}\n```")
        else:
            await ctx.send(f"[SUCCESS] Extension loaded `{name_cog}.py`")
        
        self.count += 1

    @commands.command()
    @commands.is_owner()
    @Context.with_type
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
            await ctx.send(f"[SUCCESS] File `{name}` created")
            
    @commands.command()
    @commands.is_owner()
    @Context.with_type
    async def leave_guild(self, ctx: Context, *, guild: discord.Guild):
        """To leave the guild"""
        await ctx.send(f"Leaving Guild in a second!")
        await guild.leave()
    
    @commands.command()
    @commands.is_owner()
    @Context.with_type
    async def ban_user(self, ctx: Context, user: discord.User, cmd: bool=True, chat: bool=True, global_: bool=True, *, reason: str=None):
        """To ban the user"""
        reason = reason or "No reason provided"
        await ban(user.id, cmd, chat, globals_, reason)
        try:
            await user.send(f"{user.mention} you are banned from Parrot bot. From now you can not use any command neither you can chat on #global-chat. Reason: {reason}\n\nContact `!! Ritik Ranjan [*.*]#9230` (741614468546560092) for unban.")
        except Exception:
            pass
    
    @commands.command(aliases=['report-user', 'report', 'report_user', 'ru'])
    @Context.with_type
    async def reportuser(self, ctx: Context, *, text: str):
        """To report someone"""
        if self.owner is None:
            self.owner = self.bot.get_user(741614468546560092)
        await ctx.send(f"{ctx.author.mention} are you sure? Abuse of this command will result in ban from parrot commands. Type `YES` to continue (case sensitive)")
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        try:
            msg = await self.bot.wait_for('message', timeout=60, check=check)
        except Exception:
            return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
        if msg.content.upper() == "YES":
            await ctx.send(f"{ctx.author.mention} reported")
            await self.owner.send(f"{ctx.author.mention} {text[:1000:]}")

    @commands.command(name='image-search', aliases=['imagesearch', 'imgs'], hidden=True)
    @commands.is_owner()
    @Context.with_type
    async def imgsearch(self, ctx: Context, *, text: str):
        """Image Search. Anything"""
        try:
            async with aiohttp.ClientSession() as session:
                res = await session.get(f"https://normal-api.ml/image-search?query={text}", timeout=aiohttp.ClientTimeout(total=60))
        except Exception as e: 
            return await ctx.reply(f"{ctx.author.mention} something not right. Error raised {e}")
        json = await res.json()
        if str(json['status']) != str(200): return await ctx.reply(f"{ctx.author.mention} something not right.")
        img = json['image']
        await ctx.reply(embed=discord.Embed(color=ctx.author.color, timestamp=datetime.datetime.utcnow()).set_image(url=img).set_footer(text=f"{ctx.author}"))

    @commands.command(name='ss', hidden=True)
    @commands.is_owner()
    @Context.with_type
    async def ss(self, ctx: Context, *, site: str):
        """To take the ss"""
        link = f"https://api.apiflash.com/v1/urltoimage?access_key={os.environ['SCREEN_SHOT']}&delay=1&format=png&no_ads=true&no_cookie_banners=true&no_tracking=true&response_type=image&transparent=true&url={site}&wait_until=page_loaded"
        return await ctx.reply(embed=discord.Embed(color=ctx.author.color, timestamp=datetime.datetime.utcnow()).set_image(url=link))
        
