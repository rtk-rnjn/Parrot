from __future__ import annotations

import urllib
from core import Parrot, Context, Cog
from aiofile import async_open

from discord.ext import commands
import discord

import aiohttp
import datetime
import os
import traceback
import typing

from utilities.database import ban
import re
import io
import zlib
import json

from . import fuzzy
from collections import Counter
from utilities.paginator import PaginationView
from utilities.time import ShortTime
from utilities.converters import convert_bool
from cogs.meta.robopage import SimplePages


class auditFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    guild: typing.Optional[discord.Guild]
    limit: typing.Optional[int] = 100
    action: typing.Optional[str]
    before: typing.Optional[ShortTime]
    after: typing.Optional[ShortTime]
    oldest_first: typing.Optional[convert_bool] = False
    user: typing.Optional[int]
    action: typing.Optional[str]


act = {
    "channel_create": discord.AuditLogAction.channel_create,
    "channel_delete": discord.AuditLogAction.channel_delete,
    "channel_update": discord.AuditLogAction.channel_update,
    "overwrite_create": discord.AuditLogAction.overwrite_create,
    "overwrite_update": discord.AuditLogAction.overwrite_update,
    "overwrite_delete": discord.AuditLogAction.overwrite_delete,
    "kick": discord.AuditLogAction.kick,
    "member_prune": discord.AuditLogAction.member_prune,
    "ban": discord.AuditLogAction.ban,
    "unban": discord.AuditLogAction.unban,
    "member_update": discord.AuditLogAction.member_update,
    "member_role_update": discord.AuditLogAction.member_role_update,
    "member_disconnect": discord.AuditLogAction.member_disconnect,
    "bot_add": discord.AuditLogAction.bot_add,
    "role_create": discord.AuditLogAction.role_create,
    "role_update": discord.AuditLogAction.role_update,
    "role_delete": discord.AuditLogAction.role_delete,
    "invite_create": discord.AuditLogAction.invite_create,
    "invite_delete": discord.AuditLogAction.invite_delete,
    "invite_update": discord.AuditLogAction.invite_update,
    "webhook_create": discord.AuditLogAction.webhook_create,
    "webhook_delete": discord.AuditLogAction.webhook_delete,
    "webhook_update": discord.AuditLogAction.webhook_update,
    "emoji_create": discord.AuditLogAction.emoji_create,
    "emoji_delete": discord.AuditLogAction.emoji_delete,
    "emoji_update": discord.AuditLogAction.emoji_update,
    "message_delete": discord.AuditLogAction.message_delete,
    "message_bulk_delete": discord.AuditLogAction.message_bulk_delete,
    "message_pin": discord.AuditLogAction.message_pin,
    "message_unpin": discord.AuditLogAction.message_unpin,
    "integration_create": discord.AuditLogAction.integration_create,
    "integration_delete": discord.AuditLogAction.integration_delete,
    "integration_update": discord.AuditLogAction.integration_update,
}


class nitro(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.bot = ctx.bot

    @discord.ui.button(
        custom_id="fun (nitro)",
        label="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀Claim⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
        style=discord.ButtonStyle.green,
    )
    async def func(self, button: discord.ui.Button, interaction: discord.Interaction):

        i = discord.Embed()
        i.set_image(url="https://c.tenor.com/x8v1oNUOmg4AAAAd/rickroll-roll.gif")
        await interaction.response.send_message(
            "https://imgur.com/NQinKJB", ephemeral=True
        )

        button.disabled = True
        button.style = discord.ButtonStyle.grey
        button.label = "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀Claimed⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"

        ni = discord.Embed(
            title="You received a gift, but...",
            description="The gift link has either expired or has been\nrevoked.",
        )
        ni.set_thumbnail(url="https://i.imgur.com/w9aiD6F.png")
        try:
            await interaction.message.edit(embed=ni, view=self)
        except Exception:
            pass


class Owner(Cog, command_attrs=dict(hidden=True)):
    """You can not use these commands"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.count = 0
        self.owner = None

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            name="early_verified_bot_developer", id=892433993537032262
        )

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
            async with async_open(f"{name}.py", "wb") as f:
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
            self.bot.load_extension(f"{name_cog}")
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
            async with async_open(f"{name}", "w+") as f:
                await f.write(text)
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not create file `{name}`: ```py\n{tbe}\n```")
        else:
            await ctx.send(f"[SUCCESS] File `{name}` created")

    @commands.command(aliases=["nitroscam", "nitro-scam"])
    @commands.is_owner()
    async def nitro_scam(
        self,
        ctx: Context,
        *,
        target: typing.Union[discord.User, discord.TextChannel, discord.Thread] = None,
    ):
        """Fun command"""
        await ctx.message.delete(delay=0)
        target = target or ctx.channel
        await target.send(
            embed=discord.Embed(
                title="You've been gifted a subscription!",
                description="You've been gifted Nitro for **1 month!**\nExpires in **24 hours**",
                timestamp=datetime.datetime.utcnow(),
            ).set_thumbnail(url="https://i.imgur.com/w9aiD6F.png"),
            view=nitro(ctx),
        )

    @commands.command()
    @commands.is_owner()
    @Context.with_type
    async def leave_guild(self, ctx: Context, *, guild: discord.Guild):
        """To leave the guild"""
        await ctx.send("Leaving Guild in a second!")
        await guild.leave()

    @commands.command()
    @commands.is_owner()
    @Context.with_type
    async def ban_user(
        self,
        ctx: Context,
        user: discord.User,
        cmd: bool = True,
        chat: bool = True,
        global_: bool = True,
        *,
        reason: str = None,
    ):
        """To ban the user"""
        reason = reason or "No reason provided"
        await ban(user.id, cmd, chat, global_, reason)
        try:
            await user.send(
                f"{user.mention} you are banned from using Parrot bot. Reason: {reason}\n\nContact `{self.bot.author_name}` for unban."
            )
        except Exception:
            pass

    @commands.command(name="image-search", aliases=["imagesearch", "imgs"], hidden=True)
    @commands.is_owner()
    @Context.with_type
    async def imgsearch(self, ctx: Context, *, text: str):
        """Image Search. Anything"""
        text = urllib.parse.quote(text)
        url = f"https://www.googleapis.com/customsearch/v1?key={os.environ['GOOGLE_KEY']}&cx={os.environ['GOOGLE_CX']}&q={text}&searchType=image"
        res = await self.bot.session.get(url)
        data = await res.json()
        ls = []
        for i in data["items"]:
            embed = discord.Embed(
                title=i["title"],
                description=f"```\n{i['snippet']}```",
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_footer(text=f"Requester: {ctx.author}")
            embed.set_image(url=i["link"])
            ls.append(embed)
        page = PaginationView(embed_list=ls)
        await page.start(ctx)

    @commands.command(name="ss", hidden=True)
    @commands.is_owner()
    @Context.with_type
    async def ss(self, ctx: Context, *, site: str):
        """To take the ss"""
        link = f"https://api.apiflash.com/v1/urltoimage?access_key={os.environ['SCREEN_SHOT']}&delay=1&format=png&no_ads=true&no_cookie_banners=true&no_tracking=true&response_type=image&transparent=true&url={site}&wait_until=page_loaded"
        return await ctx.reply(
            embed=discord.Embed(
                color=ctx.author.color, timestamp=datetime.datetime.utcnow()
            ).set_image(url=link)
        )

    @commands.command()
    @commands.is_owner()
    async def dr(self, ctx: Context):
        """To delete the message reference"""
        await ctx.message.delete(delay=0)
        await ctx.message.reference.resolved.delete(delay=0)

    @commands.command()
    @commands.is_owner()
    async def spy_server(
        self, ctx: Context, guild: discord.Guild = None, channel_member: str = None
    ):
        """This is not really a spy command"""
        guild = guild or ctx.guild
        URL = f"https://discord.com/api/guilds/{guild.id}/widget.json"
        data = await self.bot.session.get(URL)
        json = await data.json()
        if "message" in json:
            return await ctx.reply(f"{ctx.author.mention} can not spy that server")
        name = json["name"]
        id_ = json["id"]
        instant_invite = json["instant_invite"]
        presence_count = json["presence_count"]

        embed_first = discord.Embed(
            title=name,
            color=ctx.author.color,
            timestamp=datetime.datetime.utcnow(),
        )
        if instant_invite:
            embed_first.url = instant_invite
        embed_first.set_footer(text=f"{id_}")
        embed_first.description = f"**Presence Count:** {presence_count}"
        em_list = [embed_first]

        for channel in json["channels"]:
            em_chan = discord.Embed(
                title=channel["name"],
                description=f"**Position:** {channel['position']}",
                color=ctx.author.color,
                timestamp=datetime.datetime.utcnow(),
            ).set_footer(text=channel["id"])

            em_list.append(em_chan)

        em_list_member = [embed_first]

        for member in json["members"]:
            id_ = member["id"]
            username = member["username"]
            discriminator = member["discriminator"]
            avatar_url = member["avatar_url"]
            status = member["status"]
            vc = member["channel_id"] if "channel_id" in member else None
            suppress = member["suppress"] if "suppress" in member else None
            self_mute = member["self_mute"] if "self_mute" in member else None
            self_deaf = member["self_deaf"] if "self_deaf" in member else None
            deaf = member["deaf"] if "deaf" in member else None
            mute = member["mute"] if "mute" in member else None

            em = (
                discord.Embed(
                    title=f"Username: {username}#{discriminator}",
                    color=ctx.author.color,
                    timestamp=datetime.datetime.utcnow(),
                )
                .set_footer(text=f"{id_}")
                .set_thumbnail(url=avatar_url)
            )
            em.description = f"**Status:** {status.upper()}\n**In VC?** {bool(vc)} ({'<#'+str(vc)+'>' if vc else None})"
            if vc:
                em.add_field(name="VC Channel ID", value=str(vc), inline=True)
                em.add_field(name="Suppress?", value=suppress, inline=True)
                em.add_field(name="Self Mute?", value=self_mute, inline=True)
                em.add_field(name="Self Deaf?", value=self_deaf, inline=True)
                em.add_field(name="Deaf?", value=deaf, inline=True)
                em.add_field(name="Mute?", value=mute, inline=True)
            em_list_member.append(em)

        if channel_member.lower() in ("channels",):
            await PaginationView(em_list).start(ctx=ctx)
        elif channel_member.lower() in ("members",):
            await PaginationView(em_list_member).start(ctx=ctx)

    @commands.command()
    @commands.is_owner()
    async def removebg(self, ctx: Context, *, url):
        """To remove the background from image"""
        async with self.bot.session.get(url) as img:
            imgdata = io.BytesIO(await img.read())

        response = await self.bot.session.post(
            "https://api.remove.bg/v1.0/removebg",
            data={"size": "auto", "image_file": imgdata},
            headers={"X-Api-Key": f'{os.environ["REMOVE_BG"]}'},
        )
        async with async_open("no-bg.png", "wb") as out:
            await out.write(await response.read())
        await ctx.send(file=discord.File("no-bg.png"))

    @commands.command(aliases=["auditlogs"])
    @commands.bot_has_permissions(view_audit_log=True, attach_files=True)
    @commands.is_owner()
    async def auditlog(self, ctx: Context, *, args: auditFlag):
        """To get the audit log of the server, in nice format"""
        ls = []
        guild = args.guild or ctx.guild
        async for entry in guild.audit_logs(
            limit=args.limit if args.limit else 100,
            user=discord.Object(id=args.user) if args.user else None,
            action=act.get(args.action.lower().replace(" ", "_"))
            if args.action
            else None,
            before=discord.Object(id=int(args.before.dt.timestamp()))
            if args.before
            else None,
            after=discord.Object(id=int(args.after.dt.timestamp()))
            if args.after
            else None,
            oldest_first=args.oldest_first,
        ):
            st = f"""**{entry.action.name.replace('_', ' ').title()}** (`{entry.id}`)
> Reason: `{entry.reason or 'No reason was specified'}` at {discord.utils.format_dt(entry.created_at)}
`Responsible Moderator`: <@{entry.user.id if entry.user else 'Can not determine the Moderator'}>
`Action performed on  `: {entry.target or 'Can not determine the Target'}
"""
            ls.append(st)

        p = SimplePages(ls, ctx=ctx, per_page=5)
        await p.start()


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
                buf = buf[pos + 1 :]
                pos = buf.find(b"\n")


class DiscordPy(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        with open("extra/docs_links.json") as f:
            self.page_types = json.load(f)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="dpy", id=596577034537402378)

    def parse_object_inv(self, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()
        _ = stream.readline().rstrip()[11:]

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]

        # next line says if it's a zlib header
        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, _, location, dispname = match.groups()
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
                key = key.replace("discord.ext.commands.", "").replace("discord.", "")

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
                            "Cannot build rtfm lookup table, try again later."
                        )

                    stream = SphinxObjectFileReader(await resp.read())
                    cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx, key, obj):
        if obj is None:
            await ctx.send(self.page_types[key])
            return

        if not hasattr(self, "_rtfm_cache"):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(self.page_types)

        obj = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", obj)

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

        e = discord.Embed(
            title="Read the Fine Manual", timestamp=datetime.datetime.utcnow()
        )
        if len(matches) == 0:
            return await ctx.send("Could not find anything. Sorry.")

        e.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/894938379697913916/894938401294401576/3aa641b21acded468308a37eef43d7b3.png"
        )
        e.description = "\n".join(f"[`{key}`]({url})" for key, url in matches)

        e.set_footer(
            text=f"Request by {ctx.author.name}#{ctx.author.discriminator}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=e)

    @commands.group(invoke_without_command=True)
    async def rtfd(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a specified entity.
        Events, objects, and functions are all supported through
        a cruddy fuzzy algorithm.
        """
        if not ctx.invoked_subcommand:
            return await self.do_rtfm(ctx, "discord", obj)

    @rtfd.command(name="python", aliases=["py"])
    async def rtfm_python(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a Python entity."""
        await self.do_rtfm(ctx, "python", obj)

    @rtfd.command(name="aiohttp")
    async def rtfd_aiohttp(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a aiohttp entity"""
        await self.do_rtfm(ctx, "aiohttp", obj)

    @rtfd.command(name="requests", aliases=["request", "req"])
    async def rtfd_request(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a request entity"""
        await self.do_rtfm(ctx, "requests", obj)

    @rtfd.command(name="flask")
    async def rtfd_flask(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a flask entity"""
        await self.do_rtfm(ctx, "flask", obj)

    @rtfd.command(name="numpy", aliases=["np"])
    async def rtfd_numpy(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a numpy entity"""
        await self.do_rtfm(ctx, "numpy", obj)

    @rtfd.command(name="pil")
    async def rtfd_pil(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a PIL entity"""
        await self.do_rtfm(ctx, "pil", obj)

    @rtfd.command(name="matplotlib", aliases=["matlab", "plt", "mat"])
    async def rtfd_matplotlib(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a matplotlib entity"""
        await self.do_rtfm(ctx, "matplotlib", obj)

    @rtfd.command(name="pandas", aliases=["pd"])
    async def rtfd_pandas(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a pandas entity"""
        await self.do_rtfm(ctx, "pandas", obj)

    @rtfd.command(name="pymongo", aliases=["mongo", "pym"])
    async def rtfd_pymongo(self, ctx: Context, *, obj: str = None):
        """Gives you a documentation link for a pymongo entity"""
        await self.do_rtfm(ctx, "pymongo", obj)

    @rtfd.command(name="showall")
    @commands.is_owner()
    async def rtfd_showall(
        self,
        ctx: Context,
    ):
        """Show all the docs links"""
        async with async_open(r"extra/docs_links.json") as f:
            data = json.loads(await f.read())

        await ctx.send(json.dumps(data, indent=4))

    @rtfd.command(name="add")
    @commands.is_owner()
    async def rtfd_add(self, ctx: Context, name: str, *, link: str):
        """To add the links in docs"""
        async with async_open(r"extra/docs_links.json") as f:
            data = json.loads(await f.read())

        data[name] = link

        async with async_open(r"extra/docs_links.json") as f:
            await f.write(data)

        await ctx.send(f"{ctx.author.mention} done!")

    @rtfd.command(name="del")
    @commands.is_owner()
    async def rtfd_del(
        self,
        ctx: Context,
        name: str,
    ):
        """To add the links in docs"""
        async with async_open(r"extra/docs_links.json") as f:
            data: dict = json.loads(await f.read())

        data.pop(name)

        async with async_open(r"extra/docs_links.json") as f:
            await f.write(data)

        await ctx.send(f"{ctx.author.mention} done!")

    @commands.command()
    async def cleanup(self, ctx: Context, search: int = 100):
        """Cleans up the bot's messages from the channel.
        If a search number is specified, it searches that many messages to delete.

        If the bot has Manage Messages permissions then it will try to delete
        messages that look like they invoked the bot as well.

        After the cleanup is completed, the bot will send you a message with
        which people got their messages deleted and their count. This is useful
        to see which users are spammers.
        Members with Manage Messages can search up to 1000 messages.
        Members without can search up to 25 messages.
        """
        strategy = self._basic_cleanup_strategy
        is_mod = ctx.channel.permissions_for(ctx.author).manage_messages
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            if is_mod:
                strategy = self._complex_cleanup_strategy
            else:
                strategy = self._regular_user_cleanup_strategy

        if is_mod:
            search = min(max(2, search), 1000)
        else:
            search = min(max(2, search), 25)

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append("")
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"- **{author}**: {count}" for author, count in spammers)

        await ctx.send("\n".join(messages), delete_after=10)

    async def _basic_cleanup_strategy(self, ctx, search):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me and not (msg.mentions or msg.role_mentions):
                await msg.delete()
                count += 1
        return {"Bot": count}

    async def _complex_cleanup_strategy(self, ctx, search):
        prefixes = tuple(
            await self.bot.get_guild_prefixes(ctx.guild)
        )  # thanks startswith

        def check(m):
            return m.author == ctx.me or m.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    async def _regular_user_cleanup_strategy(self, ctx, search):
        prefixes = tuple(await self.bot.get_guild_prefixes(ctx.guild))

        def check(m):
            return (m.author == ctx.me or m.content.startswith(prefixes)) and not (
                m.mentions or m.role_mentions
            )

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)
