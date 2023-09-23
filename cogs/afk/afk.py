from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

import discord
from core import Cog, Context, Parrot
from discord.ext import commands, tasks
from utilities.time import ShortTime

from .flags import AfkFlags

log = logging.getLogger("cogs.utils.utils")


class AFK(Cog):
    """AFK Management"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.collection = bot.timers
        self.lock = asyncio.Lock()

        self.ON_TESTING = False
        self.server_stats_updater.start()

        self.create_timer = self.bot.create_timer
        self.delete_timer = self.bot.delete_timer

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{SLEEPING SYMBOL}")

    def build_afk_post(self, ctx: Context, text: str, **kw) -> dict[str, Any]:
        if text.lower() in {"global", "till", "ignore", "after", "custom"}:
            msg = "You can't set afk reason with reserved words."
            raise commands.BadArgument(msg)
        _global = kw.pop("global", False)
        return {
            "_id": ctx.message.id,
            "messageURL": ctx.message.jump_url,
            "messageAuthor": ctx.author.id,
            "guild": ctx.guild.id,
            "channel": ctx.channel.id,
            "at": ctx.message.created_at.timestamp(),
            "text": text,
            "global": _global,
            "ignoredChannel": [],
            **kw,
        }

    @commands.group(invoke_without_command=True)
    async def afk(self, ctx: Context, *, text: Annotated[str, commands.clean_content] = "AFK"):
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
            post = self.build_afk_post(ctx, text)
            await ctx.send(f"{ctx.author.mention} AFK: {text}", delete_after=5)
            await self.bot.afk_collection.insert_one(post)
            self.bot.afk_users.add(ctx.author.id)

    @afk.command(name="global")
    async def _global(self, ctx: Context, *, text: Annotated[str, commands.clean_content] = "AFK"):
        """To set the AFK globally (works only if the bot can see you)."""
        post = self.build_afk_post(ctx, text, **{"global": True})
        await self.bot.afk_collection.insert_one(post)

        await ctx.send(f"{ctx.author.mention} AFK: {text or 'AFK'}")

        self.bot.afk_users.add(ctx.author.id)

    @afk.command(name="for")
    async def afk_till(self, ctx: Context, till: ShortTime, *, text: Annotated[str, commands.clean_content] = "AFK"):
        """To set the AFK time."""
        if till.dt.timestamp() - ctx.message.created_at.timestamp() <= 120:
            return await ctx.send(f"{ctx.author.mention} time must be above 120s")

        post = self.build_afk_post(ctx, text, **{"global": True})
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
    async def afk_after(self, ctx: Context, after: ShortTime, *, text: Annotated[str, commands.clean_content] = "AFK"):
        """To set the AFK future time."""
        if after.dt.timestamp() - ctx.message.created_at.timestamp() <= 120:
            return await ctx.send(f"{ctx.author.mention} time must be above 120s")

        await ctx.send(
            f"{ctx.author.mention} AFK: {text or 'AFK'}\n> Your AFK status will be set {discord.utils.format_dt(after.dt, 'R')}",
        )

        post = self.build_afk_post(ctx, text, **{"global": True})
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

    @tasks.loop(seconds=1500)
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
                continue
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
