"""Event collection + prefix commands. Wires pipeline, voice tracker, repository and views."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal

import discord
from discord.ext import commands, tasks
from pymongo.asynchronous.database import AsyncDatabase

from . import charts
from .config import StatsConfig
from .events import command_event, message_event
from .pipeline import EventPipeline
from .reports import ActivityProvider, LeaderboardProvider
from .repository import DEFAULT_PERIOD, PERIODS, Period, StatsRepository
from .schema import Collections, ensure_indexes, ensure_utc, utcnow
from .views import NO_MENTIONS, StatsView, notice_view
from .voice import ActiveSession, VoiceTracker

if TYPE_CHECKING:
    from core import Bot

log = logging.getLogger(__name__)

_REJECTED = (commands.CheckFailure, commands.UserInputError, commands.DisabledCommand, commands.CommandOnCooldown, commands.MaxConcurrencyReached)
_COUNTED_TYPES = (discord.MessageType.default, discord.MessageType.reply)


class StatsConfigError(RuntimeError):
    pass


class InvalidPeriod(commands.BadArgument):
    pass


class PeriodConverter(commands.Converter):
    ALIASES: ClassVar[dict[str, str]] = {
        "7": "7d",
        "7d": "7d",
        "week": "7d",
        "1w": "7d",
        "30": "30d",
        "30d": "30d",
        "month": "30d",
        "all": "all",
        "alltime": "all",
        "lifetime": "all",
    }

    async def convert(self, ctx: commands.Context, argument: str) -> Period:
        key = self.ALIASES.get(argument.lower())
        if key is None:
            msg = "Unknown period. Use `7d`, `30d` or `all`."
            raise InvalidPeriod(msg)
        return PERIODS[key]


def classify_error(error: commands.CommandError) -> str:
    """'failed' = the command body raised (or an unexpected error); 'rejected' = never ran."""
    if isinstance(error, commands.CommandInvokeError):
        return "failed"
    return "rejected" if isinstance(error, _REJECTED) else "failed"


def resolve_database(bot: Bot, cfg: StatsConfig) -> AsyncDatabase:
    wrapper = bot.database
    client = wrapper.mongo_client
    return client[cfg.database_name]


class StatisticsCog(commands.Cog, name="Statistics"):
    """Server statistics: messages, voice time and command usage."""

    help_emoji = "\N{BAR CHART}"

    def __init__(self, bot: Bot, cfg: StatsConfig | None = None) -> None:
        self.bot = bot
        self.cfg = cfg or StatsConfig.from_bot(bot)

        self.cols = Collections(self.cfg.collection_prefix)
        self.db: AsyncDatabase = resolve_database(self.bot, self.cfg)
        self.pipeline: EventPipeline | None = None
        self.repo = StatsRepository(self.db, self.cols)
        self.tracker = VoiceTracker()
        self.charts = charts.ChartService(self.cfg.max_concurrent_renders, self.cfg.chart_cache_size, self.cfg.chart_cache_ttl_seconds)

        self._accepting = False  # event intake gate (False before load / after unload)
        self._voice_ready = False  # voice listeners wait for recovery
        self._recovery_task: asyncio.Task | None = None
        self._flush_loop = tasks.loop(seconds=self.cfg.flush_interval_seconds)(self._flush_tick)
        self._heartbeat_loop = tasks.loop(seconds=self.cfg.heartbeat_interval_seconds)(self._heartbeat_tick)

    async def cog_load(self) -> None:
        await ensure_indexes(self.db, self.cols, self.cfg)
        self.pipeline = EventPipeline(self.db, self.cols, self.cfg)

        self._accepting = True
        self._flush_loop.start()
        self._heartbeat_loop.start()
        if self.cfg.track_voice:
            self._recovery_task = asyncio.create_task(self._recover_voice(), name="stats-voice-recovery")

    async def cog_unload(self) -> None:
        self._accepting = False
        self._flush_loop.stop()  # let an in-flight flush finish
        self._heartbeat_loop.stop()
        if self._recovery_task:
            self._recovery_task.cancel()
        if self.pipeline is None:
            return
        if self._voice_ready:  # close open intervals at "now"
            self._enqueue_all(self.tracker.close_all(utcnow()))
            self._voice_ready = False
        left = await self.pipeline.drain(self.cfg.shutdown_drain_timeout)
        self._flush_loop.cancel()
        self._heartbeat_loop.cancel()
        log.info("statistics unloaded (%d events left unflushed)", left)

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            msg = "Server statistics are only available inside a server."
            raise commands.NoPrivateMessage(msg)
        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        # Only our own period errors are handled here; everything else flows to the bot's handler.
        if isinstance(error, InvalidPeriod):
            await ctx.send(view=notice_view(str(error), title="Invalid period"), allowed_mentions=NO_MENTIONS)

    def _enqueue(self, event) -> None:
        if self._accepting and self.pipeline is not None:
            self.pipeline.enqueue(event)

    def _enqueue_all(self, events) -> None:
        for e in events:
            if self.pipeline and not self.pipeline.enqueue(e):
                log.error("voice event dropped (queue exhausted): %s", e.key)

    async def _flush_tick(self) -> None:
        try:
            if self.pipeline:
                await self.pipeline.flush()
        except Exception:
            log.exception("stats flush tick failed")

    async def _heartbeat_tick(self) -> None:
        try:
            if self._voice_ready:
                await self.reconcile_voice()
        except Exception:
            log.exception("voice heartbeat failed")

    def _present_voice(self, guild: discord.Guild) -> dict[str, str]:
        """user_id -> channel_id for humans in voice, read from the gateway cache (no API calls)."""
        present: dict[str, str] = {}
        for ch in (*guild.voice_channels, *guild.stage_channels):
            for uid in ch.voice_states:
                member = guild.get_member(uid)
                if member is not None and member.bot and not self.cfg.include_bots:
                    continue
                present[str(uid)] = str(ch.id)
        return present

    async def reconcile_voice(self, only: discord.Guild | None = None) -> None:
        now = utcnow()
        max_gap = timedelta(seconds=self.cfg.heartbeat_interval_seconds * 2.5)
        touched: list[str] = []
        for i, guild in enumerate([only] if only else list(self.bot.guilds)):
            if guild.unavailable:
                continue  # unknown != gone: never guess
            events, ids = self.tracker.reconcile(str(guild.id), self._present_voice(guild), now, max_gap)
            self._enqueue_all(events)
            touched += ids
            if i % 100 == 100 - 1:
                await asyncio.sleep(0)
        for i in range(0, len(touched), 1000):
            try:
                await self.db[self.cols.voice_sessions].update_many(
                    {"session_id": {"$in": touched[i : i + 1000]}, "state": "active"}, {"$set": {"last_seen_at": now}}
                )
            except Exception:
                log.warning("could not persist voice heartbeat", exc_info=True)

    async def _recover_voice(self) -> None:
        try:
            await self.bot.wait_until_ready()
            ids = [str(g.id) for g in self.bot.guilds]
            for i in range(0, len(ids), 500):
                rows = await StatsRepository._rows(self.db[self.cols.voice_sessions].find({"state": "active", "guild_id": {"$in": ids[i : i + 500]}}))
                for r in rows:
                    self.tracker.adopt(
                        ActiveSession(
                            r["session_id"],
                            r["guild_id"],
                            r["user_id"],
                            r["channel_id"],
                            ensure_utc(r["started_at"]),
                            ensure_utc(r.get("last_seen_at", r["started_at"])),
                        )
                    )
            self._voice_ready = True
            await self.reconcile_voice()
            log.info("voice recovery complete (%d sessions restored)", len(self.tracker))
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("voice recovery failed; continuing with an empty tracker")
            self._voice_ready = True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if (
            not self.cfg.track_messages
            or message.guild is None
            or message.type not in _COUNTED_TYPES
            or (message.author.bot and not self.cfg.include_bots)
        ):
            return
        self._enqueue(
            message_event(
                message_id=message.id,
                guild_id=message.guild.id,
                user_id=message.author.id,
                channel_id=message.channel.id,
                ts=ensure_utc(message.created_at),
            )
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        if not (self.cfg.track_voice and self._voice_ready and self._accepting):
            return
        if member.bot and not self.cfg.include_bots:
            return
        events = self.tracker.transition(
            str(member.guild.id),
            str(member.id),
            str(before.channel.id) if before.channel else None,
            str(after.channel.id) if after.channel else None,
            utcnow(),
        )
        self._enqueue_all(events)

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild) -> None:
        if self.cfg.track_voice and self._voice_ready:
            await self.reconcile_voice(only=guild)

    on_guild_join = on_guild_available

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        if self.cfg.track_voice and self._voice_ready:
            self._enqueue_all(self.tracker.close_guild(str(guild.id), utcnow()))

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context) -> None:
        ctx._stats_started = time.perf_counter()  # fires before checks: duration includes check/parse time

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        self._record_command(ctx, "success")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if ctx.command is None or isinstance(error, commands.CommandNotFound):
            return  # not an invocation of a real command
        self._record_command(ctx, classify_error(error))

    def _record_command(self, ctx: commands.Context, outcome: str) -> None:
        """``ctx.command`` is the *resolved leaf* here (``stats user``), so groups never double count.

        Raw arguments are intentionally never read.
        """
        if not self.cfg.track_commands or ctx.interaction is not None or ctx.command is None:
            return
        started = getattr(ctx, "_stats_started", None)
        duration = int((time.perf_counter() - started) * 1000) if started is not None else 0
        msg = ctx.message
        self._enqueue(
            command_event(
                message_id=msg.id,
                edited_ts=msg.edited_at.timestamp() if msg.edited_at else 0,
                guild_id=ctx.guild.id if ctx.guild else None,
                user_id=ctx.author.id,
                channel_id=ctx.channel.id if ctx.channel else None,
                command_name=ctx.command.qualified_name,
                outcome=outcome,
                duration_ms=duration,
                ts=utcnow(),
            )
        )

    async def _present(self, ctx: commands.Context, provider: Any, tab: str, period: Period) -> None:
        try:
            async with ctx.typing():
                report = await provider.build(tab, period)
        except Exception:
            log.exception("stats command failed")
            await ctx.send(view=notice_view("Bot could not load those statistics right now. Try again shortly."), allowed_mentions=NO_MENTIONS)
            return
        view = StatsView(provider, invoker_id=ctx.author.id, tab=tab, period=period, timeout=self.cfg.view_timeout_seconds)
        view.set_report(report)
        file = report.file()
        kwargs: dict[str, Any] = {"file": file} if file else {}
        view.message = await ctx.send(view=view, allowed_mentions=NO_MENTIONS, **kwargs)

    def _activity(self, ctx: commands.Context[Bot], **kw) -> ActivityProvider:
        assert ctx.guild is not None

        return ActivityProvider(ctx.guild, self.repo, self.charts, leaderboard_size=self.cfg.leaderboard_size, **kw)

    @commands.group(
        name="stats",
        aliases=["statistics", "metrics"],
        invoke_without_command=True,
    )
    async def stats(
        self,
        ctx: commands.Context[Bot],
        period: Annotated[Period, PeriodConverter] = commands.parameter(default=DEFAULT_PERIOD, description="7d, 30d or all"),  # noqa: B008
    ) -> None:
        """Show an overview of server statistics (messages, voice time, commands) for the given period."""
        await self._present(ctx, self._activity(ctx), "overview", period)

    @stats.command(name="messages", brief="Message trends")
    async def stats_messages(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member | None = commands.parameter(description="Optional member to show message trends for", default=None),  # noqa: B008
        period: Annotated[Period, PeriodConverter] = commands.parameter(default=DEFAULT_PERIOD, description="7d, 30d or all"),  # noqa: B008
    ) -> None:
        """Show message volume over time for the server."""
        provider = self._activity(ctx, user_id=member.id, subject=member.display_name) if member else self._activity(ctx)
        await self._present(ctx, provider, "messages", period)

    @stats.command(name="voice", brief="Voice time (server, or one member)")
    async def stats_voice(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member | None = commands.parameter(description="Optional member to show voice time for", default=None),  # noqa: B008
        period: Annotated[Period, PeriodConverter] = commands.parameter(default=DEFAULT_PERIOD, description="7d, 30d or all"),  # noqa: B008
    ) -> None:
        """Show time spent in voice channels, for the whole server or for one member."""
        provider = self._activity(ctx, user_id=member.id, subject=member.display_name) if member else self._activity(ctx)
        await self._present(ctx, provider, "voice", period)

    @stats.command(name="commands", brief="Command usage")
    async def stats_commands(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member | None = commands.parameter(description="Optional member to show command usage for", default=None),  # noqa: B008
        period: Annotated[Period, PeriodConverter] = commands.parameter(default=DEFAULT_PERIOD, description="7d, 30d or all"),  # noqa: B008
    ) -> None:
        """Show how often bot commands are used in the server."""
        provider = self._activity(ctx, user_id=member.id, subject=member.display_name) if member else self._activity(ctx)
        await self._present(ctx, provider, "commands", period)

    @stats.command(name="user", aliases=["member"], brief="Statistics for one member")
    async def stats_user(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member | None = commands.parameter(description="The member to show statistics for", default=None),  # noqa: B008
        period: Annotated[Period, PeriodConverter] = commands.parameter(default=DEFAULT_PERIOD, description="7d, 30d or all"),  # noqa: B008
    ) -> None:
        """Show one member's messages, voice time and command usage."""
        provider = self._activity(ctx, user_id=member.id, subject=member.display_name) if member else self._activity(ctx)
        await self._present(ctx, provider, "overview", period)

    @stats.command(name="channel", brief="Statistics for one channel")
    async def stats_channel(
        self,
        ctx: commands.Context[Bot],
        channel: discord.abc.GuildChannel | discord.Thread = commands.parameter(  # noqa: B008
            description="The channel to show statistics for",
            default=lambda ctx: ctx.channel,
        ),
        period: Annotated[Period, PeriodConverter] = commands.parameter(default=DEFAULT_PERIOD, description="7d, 30d or all"),  # noqa: B008
    ) -> None:
        """Show message trends for one channel or thread."""
        if getattr(channel, "guild", None) != ctx.guild:
            msg = "That channel is not in this server."
            raise commands.BadArgument(msg)
        await self._present(ctx, self._activity(ctx, channel_id=channel.id, subject="#" + channel.name), "messages", period)

    @stats.command(name="leaderboard", aliases=["top", "lb"], brief="Top members / channels / commands")
    async def stats_leaderboard(
        self,
        ctx: commands.Context[Bot],
        category: Literal["messages", "voice", "channels", "commands"] = commands.parameter(
            default="messages", description="messages, voice, channels or commands"
        ),
        period: Annotated[Period, PeriodConverter] = commands.parameter(default=DEFAULT_PERIOD, description="7d, 30d or all"),  # noqa: B008
        page: int = commands.parameter(default=1, description="The page of the leaderboard to show"),
    ) -> None:
        """Rank members, channels or commands by activity. Use the page argument to see further down the list."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        provider = LeaderboardProvider(ctx.guild, self.repo, self.charts, page=max(0, page - 1), leaderboard_size=self.cfg.leaderboard_size)
        await self._present(ctx, provider, category, period)

    @stats.command(name="commandleaderboard", aliases=["cmdtop"], brief="Most-used commands")
    async def stats_commandleaderboard(
        self,
        ctx: commands.Context[Bot],
        period: Annotated[Period, PeriodConverter] = commands.parameter(default=DEFAULT_PERIOD, description="7d, 30d or all"),  # noqa: B008
    ) -> None:
        """Show the most-used bot commands in the server."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        provider = LeaderboardProvider(ctx.guild, self.repo, self.charts, leaderboard_size=self.cfg.leaderboard_size)
        await self._present(ctx, provider, "commands", period)

    @stats.command(name="refresh", hidden=True)
    @commands.is_owner()
    async def stats_refresh(self, ctx: commands.Context[Bot]) -> None:
        """Flush buffered statistics to the database immediately."""
        if self.pipeline is None:
            await ctx.send(view=notice_view("The statistics pipeline is not running."), allowed_mentions=NO_MENTIONS)
            return

        flushed = await self.pipeline.flush()
        if self._voice_ready:
            await self.reconcile_voice(only=ctx.guild)
        snap = self.pipeline.snapshot()
        lines = [
            f"Flushed **{flushed}** events just now.",
            *(f"- `{k}`: {v}" for k, v in snap.items()),
            f"- `voice_sessions_tracked`: {len(self.tracker)}",
            f"- `chart_cache`: {self.charts.hits} hits / {self.charts.misses} misses",
        ]
        await ctx.send(view=notice_view("\n".join(lines), title="Statistics pipeline"), allowed_mentions=NO_MENTIONS)
