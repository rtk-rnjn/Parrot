from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Annotated, Any

import discord
from core import Cog, Context, Parrot
from discord.ext import commands, tasks
from utilities.robopages import SimplePages
from utilities.time import ShortTime

from .constants import ACTION_EMOJIS, ACTION_NAMES
from .flags import AfkFlags, AuditFlag
from .methods import get_action_color, get_change_value, resolve_target

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

        self._audit_log_cache: dict[int, deque[discord.AuditLogEntry]] = {}
        # guild_id: deque

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{SLEEPING SYMBOL}")

    @Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if entry.guild.id not in self._audit_log_cache:
            self._audit_log_cache[entry.guild.id] = deque(maxlen=100)

        self._audit_log_cache[entry.guild.id].appendleft(entry)

    @commands.command(aliases=["auditlogs"], hidden=True)
    @commands.bot_has_permissions(view_audit_log=True)
    @commands.has_permissions(view_audit_log=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def auditlog(self, ctx: Context, *, args: AuditFlag):
        """To get the audit log of the server, in nice format."""
        ls = []
        if await ctx.bot.is_owner(ctx.author):
            guild = args.guild or ctx.guild
        else:
            guild = ctx.guild

        kwargs = {}

        if args.user:
            kwargs["user"] = args.user

        kwargs["limit"] = max(args.limit or 0, 100)
        if args.action:
            kwargs["action"] = getattr(discord.AuditLogAction, str(args.action).lower().replace(" ", "_"), None)

        if args.before:
            kwargs["before"] = args.before.dt

        if args.after:
            kwargs["after"] = args.after.dt

        if args.oldest_first:
            kwargs["oldest_first"] = args.oldest_first

        def fmt(entry: discord.AuditLogEntry) -> str:
            return f"""**{entry.action.name.replace('_', ' ').title()}** (`{entry.id}`)
> Reason: `{entry.reason or 'No reason was specified'}` at {discord.utils.format_dt(entry.created_at)}
`Responsible Moderator`: {f'<@{str(entry.user.id)}>' if entry.user else 'Can not determine the Moderator'}
`Action performed on  `: {resolve_target(entry.target)}
"""

        def finder(entry: discord.AuditLogEntry) -> bool:
            ls = []
            if kwargs.get("action"):
                ls.append(entry.action == kwargs["action"])
            if kwargs.get("user"):
                ls.append(entry.user == kwargs["user"])
            if kwargs.get("before"):
                ls.append(entry.created_at < kwargs["before"])
            if kwargs.get("after"):
                ls.append(entry.created_at > kwargs["after"])

            if kwargs.get("oldest_first"):
                ls = ls[::-1]
            if kwargs.get("limit"):
                ls = ls[: kwargs["limit"]]

            return all(ls) if ls else True

        if self._audit_log_cache.get(guild.id) and len(self._audit_log_cache[guild.id]) == 100:
            entries = self._audit_log_cache[guild.id]
            for entry in entries:
                if finder(entry):
                    st = fmt(entry)
                    ls.append(st)
        else:
            async for entry in guild.audit_logs(**kwargs):
                st = fmt(entry)
                ls.append(st)

        p = SimplePages(ls, ctx=ctx, per_page=5)
        await p.start()

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

    @Cog.listener("on_audit_log_entry_create")
    async def on_audit_log_entry(self, entry: discord.AuditLogEntry) -> None:
        guild_id = entry.guild.id
        try:
            webhook = self.bot.guild_configurations_cache[guild_id]["auditlog"]
        except KeyError:
            return
        else:
            if not webhook:
                return

        action_name = ACTION_NAMES.get(entry.action)

        emoji = ACTION_EMOJIS.get(entry.action)
        color = get_action_color(entry.action)

        target_type = entry.action.target_type.title()
        action_event_type = entry.action.name.replace("_", " ").title()  # noqa

        message = []
        for value in vars(entry.changes.before):
            if changed := get_change_value(entry, value):
                message.append(changed)

        if not message:
            message.append("*Nothing Mentionable*")

        target = resolve_target(entry.target)
        by = getattr(entry, "user", None) or "N/A"

        embed = (
            discord.Embed(
                title=f"{emoji} {action_event_type}",
                description="## Changes\n\n" + "\n".join(message),
                colour=color,
            )
            .add_field(name="Performed by", value=by, inline=True)
            .add_field(name="Target", value=target, inline=True)
            .add_field(name="Reason", value=entry.reason, inline=False)
            .add_field(name="Category", value=f"{action_name} (Type: {target_type})", inline=False)
            .set_footer(text=f"Log: [{entry.id}]", icon_url=entry.user.display_avatar.url if entry.user else None)
        )
        embed.timestamp = entry.created_at

        await self.bot._execute_webhook_from_scratch(webhook, embeds=[embed])
