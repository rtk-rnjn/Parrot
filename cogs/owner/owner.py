from __future__ import annotations

import datetime
import hashlib
import json
import os
import random
import re
import string
import traceback
import typing
import urllib.parse
from collections import Counter
from typing import Literal, Annotated, Optional

from aiofile import async_open

import discord
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.converters import convert_bool
from utilities.paginator import PaginationView
from utilities.robopages import SimplePages
from utilities.time import ShortTime

from . import fuzzy
from .flags import AuditFlag, BanFlag, SubscriptionFlag
from .utils import SphinxObjectFileReader
from .views import MongoCollectionView, MongoView, MongoViewSelect, NitroView


class Owner(Cog, command_attrs={"hidden": True}):
    """You can not use these commands."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.count = 0

        self.bot.get_user_data = self.get_user_data

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="early_verified_bot_developer", id=892433993537032262)

    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    @Context.with_type
    async def gitload(self, ctx: Context, *, link: str) -> None:
        """To load the cog extension from github."""
        ctx.author.display_name
        r = await self.bot.http_session.get(link)
        data = await r.read()
        name = f"temp/temp{self.count}"
        name_cog = f"temp.temp{self.count}"
        try:
            async with async_open(f"{name}.py", "wb") as f:
                await f.write(data)
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not create file `{name}.py`: ```py\n{tbe}\n```")
        else:
            await ctx.send(f"[SUCCESS] file `{name}.py` created")

        try:
            await self.bot.load_extension(f"{name_cog}")
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not load extension {name_cog}.py: ```py\n{tbe}\n```")
        else:
            await ctx.send(f"[SUCCESS] Extension loaded `{name_cog}.py`")

        self.count += 1

    @commands.command()
    @Context.with_type
    async def makefile(self, ctx: Context, name: str, *, text: str) -> None:
        """To make a file in ./temp/ directly."""
        try:
            async with async_open(f"temp/{name}", "w+") as f:
                await f.write(text)
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await ctx.send(f"[ERROR] Could not create file `{name}`: ```py\n{tbe}\n```")
        else:
            await ctx.send(f"[SUCCESS] File `{name}` created")

    @commands.command(aliases=["nitroscam", "nitro-scam"])
    async def nitro_scam(
        self,
        ctx: Context,
        *,
        target: discord.User | discord.TextChannel | discord.Thread | None = None,
    ):
        """Fun command."""
        await ctx.message.delete(delay=0)
        target = target or ctx.channel  # type: ignore
        await target.send(  # type: ignore
            embed=discord.Embed(
                title="You've been gifted a subscription!",
                description="You've been gifted Nitro for **1 month!**\nExpires in **24 hours**",
                timestamp=discord.utils.utcnow(),
            ).set_thumbnail(url="https://i.imgur.com/w9aiD6F.png"),
            view=NitroView(ctx),
        )

    @commands.command()
    @Context.with_type
    async def leave_guild(self, ctx: Context, *, guild: discord.Guild):
        """To leave the guild."""
        await ctx.send("Leaving Guild in a second!")
        await guild.leave()

    @commands.command()
    @Context.with_type
    async def ban_user(
        self,
        ctx: Context,
        user: discord.User,
        *,
        args: BanFlag,
    ):
        """To ban the user."""
        reason = args.reason or "No reason provided"
        payload = {"reason": reason, "command": args.command, "global": args._global}
        await self.bot.extra_collections.insert_one(
            {"_id": "banned_users"},
            {"$addToSet": {"users": {"user_id": user.id, **payload}}},
        )
        await self.bot.update_banned_members.start()
        try:
            await user.send(
                f"{user.mention} you are banned from using Parrot bot. Reason: {reason}\n\nContact `{self.bot.author_name}` for unban.",
                view=ctx.send_view(),
            )
            await ctx.send("User banned and DM-ed")
        except discord.Forbidden:
            await ctx.send("User banned, unable to DM as their DMs are locked")

    @commands.command()
    @Context.with_type
    async def unban_user(
        self,
        ctx: Context,
        *,
        user: discord.User,
    ):
        """To ban the user."""
        await self.bot.extra_collections.update_one(
            {
                "_id": "banned_users",
            },
            {
                "$pull": {"users": {"user_id": user.id}},
            },
        )
        await self.bot.update_banned_members.start()
        try:
            await user.send(
                f"{user.mention} you are unbanned. You can now use Parrot bot.",
                view=ctx.send_view(),
            )
            await ctx.send("User unbanned and DM-ed")
        except discord.Forbidden:
            await ctx.send("User unbanned, unable to DM as their DMs are locked")

    @commands.group(
        name="image-search",
        aliases=["imagesearch", "imgs"],
        hidden=True,
        invoke_without_command=True,
    )
    @Context.with_type
    async def imgsearch(self, ctx: Context, *, text: str):
        """Image Search. Anything."""
        if ctx.invoked_subcommand is None:
            text = urllib.parse.quote(text)
            params = {
                "key": os.environ["GOOGLE_KEY"],
                "cx": os.environ["GOOGLE_CX"],
                "q": text,
                "searchType": "image",
            }
            url = "https://www.googleapis.com/customsearch/v1"
            res = await self.bot.http_session.get(url, params=params)
            data = await res.json()
            ls = []
            for i in data["items"]:
                embed = discord.Embed(
                    title=i["title"],
                    description=f"```\n{i['snippet']}```",
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_footer(text=f"Requester: {ctx.author}")
                embed.set_image(url=i["link"])
                ls.append(embed)
            page = PaginationView(embed_list=ls)
            await page.start(ctx)

    @commands.command(name="delete-reference", aliases=["dr"])
    async def dr(self, ctx: Context):
        """To delete the message reference."""
        await ctx.message.delete(delay=0)
        await ctx.message.reference.resolved.delete(delay=0)  # type: ignore

    @commands.command()
    async def spy_server(
        self,
        ctx: Context,
        guild: discord.Guild | int | None = None,
        channel_member: str | None = None,
    ):
        """This is not really a spy command."""
        guild = guild or ctx.guild
        channel_member = channel_member or "members"
        URL = f"https://discord.com/api/guilds/{guild.id if isinstance(guild, discord.Guild) else guild}/widget.json"
        data = await self.bot.http_session.get(URL)
        json: dict[str, typing.Any] = await data.json()
        if "message" in json:
            return await ctx.reply(f"{ctx.author.mention} can not spy that server")
        name = json["name"]
        _id = json["id"]
        instant_invite = json["instant_invite"]
        presence_count = json["presence_count"]

        embed_first = discord.Embed(
            title=name,
            color=ctx.author.color,
            timestamp=discord.utils.utcnow(),
        )
        if instant_invite:
            embed_first.url = instant_invite
        embed_first.set_footer(text=f"{_id}")
        embed_first.description = f"**Presence Count:** {presence_count}"
        em_list = [embed_first]

        for channel in json["channels"]:
            em_chan = discord.Embed(
                title=channel["name"],
                description=f"**Position:** {channel['position']}",
                color=ctx.author.color,
                timestamp=discord.utils.utcnow(),
            ).set_footer(text=channel["id"])

            em_list.append(em_chan)

        em_list_member = [embed_first]

        for member in json["members"]:
            _id = member["id"]
            username = member["username"]
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
                    title=f"Username: {username}",
                    color=ctx.author.color,
                    timestamp=discord.utils.utcnow(),
                )
                .set_footer(text=f"{_id}")
                .set_thumbnail(url=avatar_url)
            )
            em.description = f"**Status:** {status.upper()}\n**In VC?** {bool(vc)} ({f'<#{str(vc)}>' if vc else None})"

            if vc:
                em.add_field(name="VC Channel ID", value=str(vc), inline=True).add_field(
                    name="Suppress?",
                    value=suppress,
                    inline=True,
                ).add_field(name="Self Mute?", value=self_mute, inline=True).add_field(
                    name="Self Deaf?",
                    value=self_deaf,
                    inline=True,
                ).add_field(
                    name="Deaf?",
                    value=deaf,
                    inline=True,
                ).add_field(
                    name="Mute?",
                    value=mute,
                    inline=True,
                )
            em_list_member.append(em)

        if channel_member.lower() in ("channels",):
            await PaginationView(em_list).start(ctx=ctx)
        elif channel_member.lower() in ("members",):
            await PaginationView(em_list_member).start(ctx=ctx)

    @commands.command(aliases=["auditlogs"])
    @commands.bot_has_permissions(view_audit_log=True, attach_files=True)
    async def auditlog(self, ctx: Context, *, args: AuditFlag):
        """To get the audit log of the server, in nice format."""
        ls = []
        guild = args.guild or ctx.guild

        kwargs = {}

        if args.user:
            kwargs["user"] = args.user

        kwargs["limit"] = args.limit or 100
        if args.action:
            kwargs["action"] = getattr(discord.AuditLogAction, str(args.action).lower().replace(" ", "_"), None)

        if args.before:
            kwargs["before"] = args.before.dt

        if args.after:
            kwargs["after"] = args.after.dt

        if args.oldest_first:
            kwargs["oldest_first"] = args.oldest_first

        assert guild is not None

        async for entry in guild.audit_logs(**kwargs):
            st = f"""**{entry.action.name.replace('_', ' ').title()}** (`{entry.id}`)
> Reason: `{entry.reason or 'No reason was specified'}` at {discord.utils.format_dt(entry.created_at)}
`Responsible Moderator`: {f'<@{str(entry.user.id)}>' if entry.user else 'Can not determine the Moderator'}
`Action performed on  `: {entry.target or 'Can not determine the Target'}
"""

            ls.append(st)

        p = SimplePages(ls, ctx=ctx, per_page=5)
        await p.start()

    @commands.command()
    async def announce_global(self, ctx: Context, *, announcement: str):
        async for data in self.bot.guild_configurations.find():
            webhook = data["global_chat"]
            if (hook := webhook["webhook"]) and webhook["enable"]:
                if webhook := discord.Webhook.from_url(f"{hook}", session=self.bot.http_session):
                    await webhook.send(
                        content=announcement,
                        username="SERVER - SECTOR 17-29",
                        avatar_url=self.bot.user.display_avatar.url,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
        await ctx.tick()

    @commands.command()
    async def create_code(self, ctx: Context, *, args: SubscriptionFlag):
        """To create a code for the bot premium."""
        PAYLOAD = {}
        BASIC = list(string.ascii_letters + string.digits)
        random.shuffle(BASIC)

        if args.code:
            PAYLOAD["hash"] = hashlib.sha256(args.code.encode()).hexdigest()
        else:
            PAYLOAD["hash"] = hashlib.sha256("".join(BASIC).encode()).hexdigest()

        PAYLOAD["guild"] = args.guild.id if args.guild else ctx.guild.id
        PAYLOAD["expiry"] = args.expiry.dt.timestamp() if args.expiry else ShortTime("2d").dt.timestamp()
        PAYLOAD["uses"] = args.uses
        PAYLOAD["limit"] = args.limit
        await self.bot.mongo.extra.subscriptions.insert_one(PAYLOAD)
        await ctx.send(
            f"""**{ctx.author.mention} Code created successfully.**
`Hash  `: `{PAYLOAD["hash"]}`
`Code  `: `{args.code or "".join(BASIC)}`
`Guild `: `{args.guild.name if args.guild else ctx.guild.name}`
`Expiry`: {discord.utils.format_dt(args.expiry.dt if args.expiry else ShortTime("2d").dt, 'R')}
`Uses  `: `{args.uses}`
`Limit `: `{args.limit}`
""",
        )

    @commands.command(hidden=True)
    async def gateway(self, ctx: Context):
        """Gateway related stats."""
        yesterday = discord.utils.utcnow() - datetime.timedelta(days=1)

        # fmt: off
        identifies = {
            shard_id: sum(dt > yesterday for dt in dates)
            for shard_id, dates in self.bot.identifies.items()
        }

        resumes = {
            shard_id: sum(dt > yesterday for dt in dates)
            for shard_id, dates in self.bot.resumes.items()
        }

        # fmt: on

        total_identifies = sum(identifies.values())

        builder = [
            f"Total RESUMEs: {sum(resumes.values())}",
            f"Total IDENTIFYs: {total_identifies}",
        ]

        shard_count = len(self.bot.shards)
        if total_identifies > (shard_count * 10):
            issues = 2 + (total_identifies // 10) - shard_count
        else:
            issues = 0

        for shard_id, shard in self.bot.shards.items():
            badge = None
            # Shard WS closed
            # Shard Task failure
            # Shard Task complete (no failure)
            if shard.is_closed():
                badge = "\N{MEDIUM BLACK CIRCLE}"
                issues += 1
            elif shard._parent._task and shard._parent._task.done():
                exc = shard._parent._task.exception()
                if exc is not None:
                    badge = "\N{FIRE}"
                    issues += 1
                else:
                    badge = "\U0001f504"

            if badge is None:
                badge = "\N{LARGE GREEN CIRCLE}"

            stats = []
            identify = identifies.get(shard_id, 0)
            resume = resumes.get(shard_id, 0)
            if resume != 0:
                stats.append(f"R: {resume}")
            if identify != 0:
                stats.append(f"ID: {identify}")

            if stats:
                builder.append(f'Shard ID {shard_id}: {badge} ({", ".join(stats)})')
            else:
                builder.append(f"Shard ID {shard_id}: {badge}")

        if issues == 0:
            colour = 0x43B581
        elif issues < len(self.bot.shards) // 4:
            colour = 0xF09E47
        else:
            colour = 0xF04947

        embed = discord.Embed(colour=colour, title="Gateway (last 24 hours)")
        embed.description = "\n".join(builder)
        embed.set_footer(text=f"{issues} warnings")
        await ctx.send(embed=embed)

    @commands.command()
    async def maintenance(
        self,
        ctx: Context,
        till: ShortTime | None = None,
        *,
        reason: str | None = None,
    ):
        """To toggle the bot maintenance."""
        ctx.bot.UNDER_MAINTENANCE = not ctx.bot.UNDER_MAINTENANCE
        ctx.bot.UNDER_MAINTENANCE_OVER = till.dt if till is not None else till
        ctx.bot.UNDER_MAINTENANCE_REASON = reason
        await ctx.tick()

    @commands.command()
    async def member_count(self, ctx: Context, guild: discord.Object | None = None):
        """Returns member count of the guild.

        This is equivalent to:
        ```py
        return ctx.bot.get_guild(GUILD or ctx.guild.id).member_count
        ```
        """

        GUILD_ID = getattr(guild, "id", ctx.guild.id)
        await ctx.send(
            getattr(
                ctx.bot.get_guild(GUILD_ID),
                "member_count",
                "Member count not available",
            ),
        )

    @commands.command(aliases=["streaming", "listening", "watching"], hidden=True)
    async def playing(
        self,
        ctx: Context[Parrot],
        shard: int | None,
        status: Literal["online", "dnd", "offline", "idle"] | None = "dnd",
        *,
        media: str,
    ):
        """Update bot presence accordingly to invoke command.

        This is equivalent to:
        ```py
        p_types = {'playing': 0, 'streaming': 1, 'listening': 2, 'watching': 3}
        await ctx.bot.change_presence(discord.Activity(name=media, type=p_types[ctx.invoked_with]))
        ```
        """
        p_types = {"playing": 0, "streaming": 1, "listening": 2, "watching": 3, None: 0}
        await ctx.bot.change_presence(
            activity=discord.Activity(name=media, type=p_types[ctx.invoked_with]),
            shard_id=shard,
            status=discord.Status(status),
        )
        await ctx.tick()

    @commands.command()
    async def toggle_testing(self, ctx: Context, cog: str, toggle: Annotated[bool, Optional[convert_bool]] = None) -> None:  # type: ignore
        """Update the cog setting to toggle testing mode.

        ```py
        if hasattr(cog, "ON_TESTING"):
            cog.ON_TESTING = not cog.ON_TESTING
        ```
        """
        cog: Cog | None = self.bot.get_cog(cog)  # type: ignore
        assert cog is not None
        if hasattr(cog, "ON_TESTING"):
            true_false = toggle if toggle is not None else not cog.ON_TESTING
            cog.ON_TESTING = true_false
            await ctx.send(f"{ctx.author.mention} successfully toggled cog ({cog.qualified_name}) to {toggle}")
            return
        if cog is not None:
            await ctx.send(f"{ctx.author.mention} cog ({cog.qualified_name}) does not have testing mode")
        else:
            await ctx.send(f"{ctx.author.mention} cog ({cog}) does not exist")

    async def get_user_data(self, *, user: discord.Object) -> typing.Any:
        """Illegal way to get presence of a user."""
        from utilities.object import objectify

        url = f"https://japi.rest/discord/v1/user/{user.id}"
        async with self.bot.http_session.get(url) as resp:
            data = await resp.json()

        return objectify(data)

    @commands.command()
    async def mongo(
        self,
        ctx: Context,
        db: str | None = None,
        collection: str | None = None,
    ):
        """MongoDB query."""
        if db and collection:
            view = MongoCollectionView(db=db, collection=collection, ctx=ctx)
            embed = await MongoViewSelect.build_embed(ctx, db, collection)
            view.message = await ctx.send(embed=embed, view=view)
            return

        view = MongoView(ctx)
        await view.init()


class DiscordPy(Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        with open("extra/docs_links.json", encoding="utf-8", errors="ignore") as f:
            self.page_types = json.load(f)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="dpy", id=596577034537402378)

    async def cog_load(self) -> None:
        self.bot.loop.create_task(self.build_rtfm_lookup_table(self.page_types))

    def parse_object_inv(self, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()
        _ = stream.readline().rstrip()[11:]

        if inv_version != "# Sphinx inventory version 2":
            msg = "Invalid objects.inv file version."
            raise RuntimeError(msg)

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]

        # next line says if it's a zlib header
        line = stream.readline()
        if "zlib" not in line:
            msg = "Invalid objects.inv file, not z-lib compatible."
            raise RuntimeError(msg)

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
            cache[key] = {}
            resp = await self.bot.http_session.get(f"{page}/objects.inv")
            if resp.status != 200:
                msg = "Cannot build rtfm lookup table, try again later."
                raise RuntimeError(msg)

            stream = SphinxObjectFileReader(await resp.read())
            cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx: Context, key: str, obj):
        if obj is None:
            await ctx.send(self.page_types[key])
            return

        if not hasattr(self, "_rtfm_cache"):
            await ctx.typing()
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

        matches = (await ctx.bot.func(fuzzy.finder, obj, cache, key=lambda t: t[0], lazy=False))[:8]

        e = discord.Embed(title="Read the Fucking Documentation", timestamp=discord.utils.utcnow())
        if len(matches) == 0:
            return await ctx.send("Could not find anything. Sorry.")

        e.description = "\n".join(f"[`{key}`]({url})" for key, url in matches)

        e.set_footer(
            text=f"Request by {ctx.author}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=e)

    @commands.group(invoke_without_command=True)
    async def rtfd(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a specified entity.
        Events, objects, and functions are all supported through
        a cruddy fuzzy algorithm.
        """
        if not ctx.invoked_subcommand:
            return await self.do_rtfm(ctx, "discord", obj)

    @rtfd.command(name="python", aliases=["py"])
    async def rtfm_python(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a Python entity."""
        await self.do_rtfm(ctx, "python", obj)

    @rtfd.command(name="aiohttp")
    async def rtfd_aiohttp(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a aiohttp entity."""
        await self.do_rtfm(ctx, "aiohttp", obj)

    @rtfd.command(name="requests", aliases=["request", "req"])
    async def rtfd_request(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a request entity."""
        await self.do_rtfm(ctx, "requests", obj)

    @rtfd.command(name="flask")
    async def rtfd_flask(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a flask entity."""
        await self.do_rtfm(ctx, "flask", obj)

    @rtfd.command(name="numpy", aliases=["np"])
    async def rtfd_numpy(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a numpy entity."""
        await self.do_rtfm(ctx, "numpy", obj)

    @rtfd.command(name="pil")
    async def rtfd_pil(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a PIL entity."""
        await self.do_rtfm(ctx, "pil", obj)

    @rtfd.command(name="matplotlib", aliases=["matlab", "plt", "mat"])
    async def rtfd_matplotlib(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a matplotlib entity."""
        await self.do_rtfm(ctx, "matplotlib", obj)

    @rtfd.command(name="pandas", aliases=["pd"])
    async def rtfd_pandas(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a pandas entity."""
        await self.do_rtfm(ctx, "pandas", obj)

    @rtfd.command(name="pymongo", aliases=["mongo", "pym"])
    async def rtfd_pymongo(self, ctx: Context, *, obj: str | None = None):
        """Gives you a documentation link for a pymongo entity."""
        await self.do_rtfm(ctx, "pymongo", obj)

    @rtfd.command(name="showall", aliases=["show"])
    async def rtfd_showall(
        self,
        ctx: Context,
    ):
        """Show all the docs links."""
        async with async_open(r"extra/docs_links.json") as f:
            data = json.loads(await f.read())

        await ctx.send(f"```json\n{json.dumps(data, indent=4)}```")

    @rtfd.command(name="add")
    async def rtfd_add(self, ctx: Context, name: str, *, link: str):
        """To add the links in docs."""
        async with async_open(r"extra/docs_links.json") as f:
            data = json.loads(await f.read())

        data[name] = link

        async with async_open(r"extra/docs_links.json") as f:
            await f.write(data)

        await ctx.send(f"{ctx.author.mention} done!")

    @rtfd.command(name="del")
    async def rtfd_del(
        self,
        ctx: Context,
        name: str,
    ):
        """To add the links in docs."""
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
        assert isinstance(ctx.author, discord.Member) and isinstance(ctx.me, discord.Member)
        is_mod = ctx.channel.permissions_for(ctx.author).manage_messages
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            if is_mod:
                strategy = self._complex_cleanup_strategy
            else:
                strategy = self._regular_user_cleanup_strategy

        search = min(max(2, search), 1000) if is_mod else min(max(2, search), 25)
        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append("")
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"- **{author}**: {count}" for author, count in spammers)

        await ctx.send("\n".join(messages), delete_after=10)

    async def _basic_cleanup_strategy(self, ctx: Context, search: int):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me and not msg.mentions and not msg.role_mentions:
                await msg.delete()
                count += 1
        return {"Bot": count}

    async def _complex_cleanup_strategy(self, ctx: Context, search: int):
        prefixes = tuple(await self.bot.get_guild_prefixes(ctx.guild))  # thanks startswith

        def check(m: discord.Message):
            return m.author == ctx.me or m.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    async def _regular_user_cleanup_strategy(self, ctx: Context, search: int):
        prefixes = tuple(await self.bot.get_guild_prefixes(ctx.guild))

        def check(m: discord.Message):
            return (m.author == ctx.me or m.content.startswith(prefixes)) and not m.mentions and not m.role_mentions

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)
