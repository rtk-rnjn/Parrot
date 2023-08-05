from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

import discord
from core import Cog, Context, Parrot
from discord.ext import commands, tasks
from utilities.converters import convert_bool
from utilities.rankcard import rank_card
from utilities.robopages import SimplePages
from utilities.time import ShortTime

log = logging.getLogger("cogs.utils.utils")

Collection = type[AsyncIOMotorCollection]


class AfkFlags(commands.FlagConverter, prefix="--", delimiter=" "):
    ignore_channel: tuple[discord.TextChannel, ...] = []
    _global: Annotated[bool | None, convert_bool] = commands.flag(name="global", default=False)
    _for: ShortTime | None = commands.flag(name="for", default=None)
    text: str | None = None
    after: ShortTime | None = None


class Utils(Cog):
    """Utilities for server, UwU."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.collection: Collection = bot.timers
        self.lock = asyncio.Lock()

        self.ON_TESTING = False
        self.server_stats_updater.start()

        self.create_timer = self.bot.create_timer
        self.delete_timer = self.bot.delete_timer

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="sparkles_", id=892435276264259665)

    @commands.group(invoke_without_command=True)
    async def afk(self, ctx: Context, *, text: Annotated[str, commands.clean_content | None] = None):
        """To set AFK.

        AFK will be removed once you message.
        If provided permissions, bot will add `[AFK]` as the prefix in nickname.
        The deafult AFK is on Server Basis
        """
        # Thanks `sourcandy_zz` (Sour Candy#8301 - 966599206880030760)
        await ctx.message.delete(delay=5)
        try:
            nick = f"[AFK] {ctx.author.display_name}"
            if len(nick) <= 32:  # discord limitation
                await ctx.author.edit(nick=nick, reason=f"{ctx.author} set their AFK")
        except discord.Forbidden:
            pass
        if not ctx.invoked_subcommand:
            if text and text.split(" ")[0].lower() in (
                "global",
                "till",
                "ignore",
                "after",
                "custom",
            ):
                return await ctx.send(f"{ctx.author.mention} you can't set afk reason reserved words.")
            post = {
                "_id": ctx.message.id,
                "messageURL": ctx.message.jump_url,
                "messageAuthor": ctx.author.id,
                "guild": ctx.guild.id,
                "channel": ctx.channel.id,
                "at": ctx.message.created_at.timestamp(),
                "global": False,
                "text": text or "AFK",
                "ignoredChannel": [],
            }
            await ctx.send(f"{ctx.author.mention} AFK: {text or 'AFK'}", delete_after=5)
            await self.bot.afk_collection.insert_one(post)
            self.bot.afk_users.add(ctx.author.id)

    @afk.command(name="global")
    async def _global(self, ctx: Context, *, text: commands.clean_content = None):
        """To set the AFK globally (works only if the bot can see you)."""
        post = {
            "_id": ctx.message.id,
            "messageURL": ctx.message.jump_url,
            "messageAuthor": ctx.author.id,
            "guild": ctx.guild.id,
            "channel": ctx.channel.id,
            "pings": [],
            "at": ctx.message.created_at.timestamp(),
            "global": True,
            "text": text or "AFK",
            "ignoredChannel": [],
        }
        await self.bot.afk_collection.insert_one(post)
        await ctx.send(f"{ctx.author.mention} AFK: {text or 'AFK'}")
        self.bot.afk_users.add(ctx.author.id)

    @afk.command(name="for")
    async def afk_till(self, ctx: Context, till: ShortTime, *, text: commands.clean_content = None):
        """To set the AFK time."""
        if till.dt.timestamp() - ctx.message.created_at.timestamp() <= 120:
            return await ctx.send(f"{ctx.author.mention} time must be above 120s")
        post = {
            "_id": ctx.message.id,
            "messageURL": ctx.message.jump_url,
            "messageAuthor": ctx.author.id,
            "guild": ctx.guild.id,
            "channel": ctx.channel.id,
            "pings": [],
            "at": ctx.message.created_at.timestamp(),
            "global": True,
            "text": text or "AFK",
            "ignoredChannel": [],
        }
        await self.bot.afk_collection.insert_one(post)
        self.bot.afk_users.add(ctx.author.id)
        await ctx.send(
            f"{ctx.author.mention} AFK: {text or 'AFK'}\n> Your AFK status will be removed {discord.utils.format_dt(till.dt, 'R')}",
        )
        await self.create_timer(
            _event_name="remove_afk",
            expires_at=till.dt.timestamp(),
            created_at=ctx.message.created_at.timestamp(),
            extra={"name": "REMOVE_AFK", "main": {**post}},
            message=ctx.message,
        )

    @afk.command(name="after")
    async def afk_after(self, ctx: Context, after: ShortTime, *, text: commands.clean_content = None):
        """To set the AFK future time."""
        if after.dt.timestamp() - ctx.message.created_at.timestamp() <= 120:
            return await ctx.send(f"{ctx.author.mention} time must be above 120s")
        post = {
            "_id": ctx.message.id,
            "messageURL": ctx.message.jump_url,
            "messageAuthor": ctx.author.id,
            "guild": ctx.guild.id,
            "channel": ctx.channel.id,
            "pings": [],
            "at": ctx.message.created_at.timestamp(),
            "global": True,
            "text": text or "AFK",
            "ignoredChannel": [],
        }
        await ctx.send(
            f"{ctx.author.mention} AFK: {text or 'AFK'}\n> Your AFK status will be set {discord.utils.format_dt(after.dt, 'R')}",
        )
        await self.create_timer(
            _event_name="set_afk",
            expires_at=after.dt.timestamp(),
            created_at=ctx.message.created_at.timestamp(),
            extra={"name": "SET_AFK", "main": {**post}},
            message=ctx.message,
        )

    @afk.command(name="custom")
    async def custom_afk(self, ctx: Context, *, flags: AfkFlags):
        """To set the custom AFK."""
        payload = {
            "_id": ctx.message.id,
            "text": flags.text or "AFK",
            "ignoredChannel": ([c.id for c in flags.ignore_channel] if flags.ignore_channel else []),
            "global": flags._global,
            "at": ctx.message.created_at.timestamp(),
            "guild": ctx.guild.id,
            "messageAuthor": ctx.author.id,
            "messageURL": ctx.message.jump_url,
            "channel": ctx.channel.id,
            "pings": [],
        }

        if flags.after and flags._for:
            return await ctx.send(f"{ctx.author.mention} can not have both `after` and `for` argument")

        if flags.after:
            await self.create_timer(
                _event_name="set_afk",
                expires_at=flags.after.dt.timestamp(),
                created_at=ctx.message.created_at.timestamp(),
                extra={"name": "SET_AFK", "main": {**payload}},
                message=ctx.message,
            )
            await ctx.send(
                f"{ctx.author.mention} AFK: {flags.text or 'AFK'}\n> Your AFK status will be set {discord.utils.format_dt(flags.after.dt, 'R')}",
            )
            return
        if flags._for:
            await self.create_timer(
                _event_name="remove_afk",
                expires_at=flags._for.dt.timestamp(),
                created_at=ctx.message.created_at.timestamp(),
                extra={"name": "REMOVE_AFK", "main": {**payload}},
                message=ctx.message,
            )
            await self.bot.afk_collection.insert_one(payload)
            self.bot.afk_users.add(ctx.author.id)
            await ctx.send(
                f"{ctx.author.mention} AFK: {flags.text or 'AFK'}\n> Your AFK status will be removed {discord.utils.format_dt(flags._for.dt, 'R')}",
            )
            return
        await self.bot.afk_collection.insert_one(payload)
        self.bot.afk_users.add(ctx.author.id)
        await ctx.send(f"{ctx.author.mention} AFK: {flags.text or 'AFK'}")

    async def cog_unload(self):
        self.server_stats_updater.cancel()

    @commands.command(aliases=["level"])
    @commands.bot_has_permissions(attach_files=True)
    async def rank(self, ctx: Context, *, member: discord.Member = None):
        """To get the level of the user."""
        member = member or ctx.author
        try:
            enable = self.bot.guild_configurations_cache[ctx.guild.id]["leveling"]["enable"]
            if not enable:
                return await ctx.send(f"{ctx.author.mention} leveling system is disabled in this server")
        except KeyError:
            return await ctx.send(f"{ctx.author.mention} leveling system is disabled in this server")
        else:
            collection: Collection = self.bot.guild_level_db[f"{member.guild.id}"]
            if data := await collection.find_one_and_update(
                {"_id": member.id},
                {"$inc": {"xp": 0}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            ):
                level = int((data["xp"] // 42) ** 0.55)
                xp = await self.__get_required_xp(level + 1)
                rank = await self.__get_rank(collection=collection, member=member) or 0
                file = await asyncio.to_thread(
                    rank_card,
                    level,
                    rank,
                    member,
                    current_xp=data["xp"],
                    custom_background="#000000",
                    xp_color="#FFFFFF",
                    next_level_xp=xp,
                )
                await ctx.reply(file=file)
                return
            if ctx.author.id == member.id:
                return await ctx.reply(f"{ctx.author.mention} you don't have any xp yet. Consider sending some messages")
            return await ctx.reply(f"{ctx.author.mention} **{member}** don't have any xp yet.")

    @commands.command(aliases=["leaderboard"])
    @commands.bot_has_permissions(embed_links=True)
    async def lb(self, ctx: Context, *, limit: int | None = None):
        """To display the Leaderboard."""
        limit = limit or 10
        collection = self.bot.guild_level_db[f"{ctx.guild.id}"]
        entries = await self.__get_entries(collection=collection, limit=limit, guild=ctx.guild)
        if not entries:
            return await ctx.send(f"{ctx.author.mention} there is no one in the leaderboard")
        pages = SimplePages(entries, ctx=ctx, per_page=10)
        await pages.start()

    async def __get_required_xp(self, level: int) -> int:
        xp = 0
        while True:
            xp += 12
            lvl = int((xp // 42) ** 0.55)
            if lvl == level:
                return xp
            await asyncio.sleep(0)

    async def __get_rank(self, *, collection: Collection, member: discord.Member):
        countr = 0

        # you can't use `enumerate`
        async for data in collection.find({}, sort=[("xp", -1)]):
            countr += 1
            if data["_id"] == member.id:
                return countr

    async def __get_entries(self, *, collection: Collection, limit: int, guild: discord.Guild):
        ls = []
        async for data in collection.find({}, limit=limit, sort=[("xp", -1)]):
            if member := await self.bot.get_or_fetch_member(guild, data["_id"]):
                ls.append(f"{member} (`{member.id}`)")
        return ls

    @tasks.loop(seconds=600)
    async def server_stats_updater(self):
        for guild in self.bot.guilds:
            PAYLOAD = {
                "bots": len([m for m in guild.members if m.bot]),
                "members": len(guild.members),
                "channels": len(guild.channels),
                "roles": len(guild.roles),
                "emojis": len(guild.emojis),
                "text": guild.text_channels,
                "voice": guild.voice_channels,
                "categories": len(guild.categories),
            }
            try:
                stats_channels: dict[str, Any] = self.bot.guild_configurations_cache[guild.id]["stats_channels"]
            except KeyError:
                pass
            else:
                for k, v in stats_channels.items():
                    if k != "role":
                        v: dict[str, Any]
                        if channel := guild.get_channel(v["channel_id"]):
                            await channel.edit(
                                name=v["template"].format(PAYLOAD[k]),
                                reason="Updating server stats",
                            )

                if roles := stats_channels.get("role", []):
                    for role in roles:
                        r = guild.get_role(role["role_id"])
                        channel = guild.get_channel(role["channel_id"])
                        if channel and role:
                            await channel.edit(
                                name=role["template"].format(len(r.members)),
                                reason="Updating server stats",
                            )

    @server_stats_updater.before_loop
    async def before_server_stats_updater(self) -> None:
        await self.bot.wait_until_ready()
