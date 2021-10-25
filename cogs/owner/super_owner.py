from __future__ import annotations

from core import Parrot, Context, Cog
from aiofile import async_open

from discord.ext import commands
import discord, aiohttp, datetime, os, traceback, typing

from utilities.database import ban
import re, io, zlib

from . import fuzzy

class nitro(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.bot = ctx.bot

    @discord.ui.button(custom_id="fun (nitro)", label="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀Claim⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀", style=discord.ButtonStyle.green)
    async def func(self, button: discord.ui.Button, interaction: discord.Interaction):

        i = discord.Embed()
        i.set_image(url="https://c.tenor.com/x8v1oNUOmg4AAAAd/rickroll-roll.gif")
        await interaction.response.send_message(f"https://imgur.com/NQinKJB", ephemeral=True)

        
        button.disabled = True
        button.style = discord.ButtonStyle.grey
        button.label = "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀Claimed⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"

        ni = discord.Embed(title=f"You received a gift, but...", description=f"The gift link has either expired or has been\nrevoked.")
        ni.set_thumbnail(url="https://i.imgur.com/w9aiD6F.png")
        try:
          await interaction.message.edit(embed=ni,view=self)
        except:
          pass


class Owner(Cog):
    """You can not use these commands"""
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.count = 0
        self.owner = None

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='early_verified_bot_developer', id=892433993537032262)

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
            await ctx.send(
                f"[ERROR] Could not create file `{name}.py`: ```py\n{tbe}\n```"
            )
        else:
            await ctx.send(f"[SUCCESS] file `{name}.py` created")

        try:
            self.bot.load_extension(f'{name_cog}')
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(
                f"[ERROR] Could not load extension {name_cog}.py: ```py\n{tbe}\n```"
            )
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
            await ctx.send(
                f"[ERROR] Could not create file `{name}`: ```py\n{tbe}\n```")
        else:
            await ctx.send(f"[SUCCESS] File `{name}` created")
    
    @commands.command()
    @commands.is_owner()
    async def nitro_scam(self, 
                         ctx: Context, 
                         *, 
                         target: typing.Union[discord.User, 
                                              discord.TextChannel, 
                                              discord.Thread]=None):
        """Fun command"""
        await target.send(embed=discord.Embed(
                            title="You've been gifted a subscription!", 
                            description="You've been gifted Nitro for **1 month!**\nExpires in **24 hours**",
                            timestamp=datetime.datetime.utcnow()).set_thumbnail(url="https://i.imgur.com/w9aiD6F.png"), 
                       view=nitro(ctx))

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
    async def ban_user(self,
                       ctx: Context,
                       user: discord.User,
                       cmd: bool = True,
                       chat: bool = True,
                       global_: bool = True,
                       *,
                       reason: str = None):
        """To ban the user"""
        reason = reason or "No reason provided"
        await ban(user.id, cmd, chat, global_, reason)
        try:
            await user.send(
                f"{user.mention} you are banned from using Parrot bot. Reason: {reason}\n\nContact `!! Ritik Ranjan [*.*]#9230` (741614468546560092) for unban."
            )
        except Exception:
            pass

    @commands.command(name='image-search',
                      aliases=['imagesearch', 'imgs'],
                      hidden=True)
    @commands.is_owner()
    @Context.with_type
    async def imgsearch(self, ctx: Context, *, text: str):
        """Image Search. Anything"""
        try:
            async with aiohttp.ClientSession() as session:
                res = await session.get(
                    f"https://normal-api.ml/image-search?query={text}",
                    timeout=aiohttp.ClientTimeout(total=60))
        except Exception as e:
            return await ctx.reply(
                f"{ctx.author.mention} something not right. Error raised {e}")
        json = await res.json()
        if str(json['status']) != str(200):
            return await ctx.reply(f"{ctx.author.mention} something not right."
                                   )
        img = json['image']
        await ctx.reply(embed=discord.Embed(
            color=ctx.author.color, timestamp=datetime.datetime.utcnow()).
                        set_image(url=img).set_footer(text=f"{ctx.author}"))

    @commands.command(name='ss', hidden=True)
    @commands.is_owner()
    @Context.with_type
    async def ss(self, ctx: Context, *, site: str):
        """To take the ss"""
        link = f"https://api.apiflash.com/v1/urltoimage?access_key={os.environ['SCREEN_SHOT']}&delay=1&format=png&no_ads=true&no_cookie_banners=true&no_tracking=true&response_type=image&transparent=true&url={site}&wait_until=page_loaded"
        return await ctx.reply(embed=discord.Embed(
            color=ctx.author.color,
            timestamp=datetime.datetime.utcnow()).set_image(url=link))


    @commands.command()
    @commands.is_owner()
    @Context.with_type
    async def dr(self, ctx: Context):
        """To delete the message reference"""
        await ctx.message.referece.resolved.delete()

class SphinxObjectFileReader:
    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode("utf-8")

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b""
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b"\n")
            while pos != -1:
                yield buf[:pos].decode("utf-8")
                buf = buf[pos + 1:]
                pos = buf.find(b"\n")


class DiscordPy(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
    
    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='dpy', id=596577034537402378)
    
    def parse_object_inv(self, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]

        # next line says if it's a zlib header
        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError(
                "Invalid objects.inv file, not z-lib compatible.")

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(
            r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(":")
            if directive == "py:module" and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == "std:doc":
                subdirective = "label"

            if location.endswith("$"):
                location = location[:-1] + name

            key = name if dispname == "-" else dispname
            prefix = f"{subdirective}:" if domain == "std" else ""

            if projname == "discord.py":
                key = key.replace("discord.ext.commands.",
                                  "").replace("discord.", "")

            result[f"{prefix}{key}"] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self, page_types):
        cache = {}
        for key, page in page_types.items():
            sub = cache[key] = {}
            async with aiohttp.ClientSession() as session:
                async with session.get(page + "/objects.inv") as resp:
                    if resp.status != 200:
                        raise RuntimeError(
                            "Cannot build rtfm lookup table, try again later.")

                    stream = SphinxObjectFileReader(await resp.read())
                    cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx, key, obj):
        page_types = {
            "latest": "https://discordpy.readthedocs.io/en/latest",
            "python": "https://docs.python.org/3",
            "master": "https://discordpy.readthedocs.io/en/master",
            "stable": "https://discordpy.readthedocs.io/en/stable"
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not hasattr(self, "_rtfm_cache"):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1",
                     obj)

        if key.startswith("latest"):
            # point the abc.Messageable types properly:
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == "_":
                    continue
                if q == name:
                    obj = f"abc.Messageable.{name}"
                    break

        cache = list(self._rtfm_cache[key].items())

        def transform(tup):
            return tup[0]

        matches = fuzzy.finder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

        e = discord.Embed(title="Read the Fine Manual",
                          timestamp=datetime.datetime.utcnow())
        if len(matches) == 0:
            return await ctx.send("Could not find anything. Sorry.")

        e.set_thumbnail(
            url='https://cdn.discordapp.com/attachments/894938379697913916/894938401294401576/3aa641b21acded468308a37eef43d7b3.png'
        )
        e.description = "\n".join(f"[`{key}`]({url})" for key, url in matches)

        e.set_footer(
            text=f"Request by {ctx.author.name}#{ctx.author.discriminator}",
            icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=e)

    @commands.group(invoke_without_command=True)
    async def rtfd(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity.
        Events, objects, and functions are all supported through
        a cruddy fuzzy algorithm.
        """
        await self.do_rtfm(ctx, "latest", obj)

    @rtfd.command(name="python", aliases=["py"])
    async def rtfm_python(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity."""
        await self.do_rtfm(ctx, "python", obj)

    @rtfd.command(name="master", aliases=["2.0"])
    async def rtfm_master(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (master branch)"""
        await self.do_rtfm(ctx, "master", obj)

    @rtfd.command(name="stable")
    async def rtfm_stable(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (stable branch)"""
        await self.do_rtfm(ctx, "stable", obj)

