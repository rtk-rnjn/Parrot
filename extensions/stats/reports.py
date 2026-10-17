from __future__ import annotations

import asyncio
import hashlib
import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import discord

from core.utils.formats import format_count as fmt_count
from core.utils.formats import format_duration as fmt_duration
from core.utils.formats import safe_text

from . import charts
from .repository import DAY, Period, StatsRepository
from .schema import utcnow

ACCENT = 0x5865F2


@dataclass(slots=True)
class Report:
    title: str
    summary: str
    metrics: list[str]
    footer: str
    chart_png: bytes | None = None
    chart_name: str = "chart.png"
    chart_alt: str = ""
    accent: int = ACCENT

    def file(self) -> discord.File | None:
        """A *fresh* File each call (File objects are single-use once uploaded)."""
        if not self.chart_png:
            return None
        return discord.File(io.BytesIO(self.chart_png), filename=self.chart_name, description=self.chart_alt[:1024])


def fill_days(series: Sequence[tuple[datetime, int]], start: datetime | None, end: datetime) -> list[tuple[datetime, int]]:
    """Insert zero-valued days so trends are not visually compressed."""
    if not series:
        return []
    lookup = dict(series)
    first = start if start is not None else min(lookup)
    out, day = [], first
    while day < end:
        out.append((day, lookup.get(day, 0)))
        day += DAY
    return out


class _Base:
    tabs: Sequence[tuple[str, str]] = ()
    default_tab = ""

    def __init__(
        self,
        guild: discord.Guild,
        repo: StatsRepository,
        chart_service: charts.ChartService,
        *,
        clock: Callable[[], datetime] = utcnow,
        leaderboard_size: int = 10,
    ) -> None:
        self.guild, self.repo, self.charts, self._clock = guild, repo, chart_service, clock
        self.size = leaderboard_size
        self.gid = str(guild.id)

    def user_name(self, uid: str) -> str:
        m = self.guild.get_member(int(uid))
        return safe_text(m.display_name) if m else f"Unknown user \N{HORIZONTAL ELLIPSIS}{uid[-4:]}"

    def channel_name(self, cid: str) -> str:
        ch = self.guild.get_channel_or_thread(int(cid))
        return "#" + safe_text(ch.name) if ch else "#deleted-channel"

    def footer(self, period: Period, now: datetime) -> str:
        return f"{period.label} \N{MIDDLE DOT} all times UTC \N{MIDDLE DOT} generated {now:%Y-%m-%d %H:%M} UTC"

    async def _chart(self, scope: str, fn: Callable[..., bytes], data: Any, *args: Any, **kwargs: Any) -> bytes | None:
        """Render via the shared service; a rendering failure degrades to a text-only report."""
        try:
            return await self.charts.render(self.charts.key(self.gid, scope, (data, args, sorted(kwargs.items()))), fn, *args, **kwargs)
        except Exception:
            return None

    @staticmethod
    def _name(png: bytes | None) -> str:
        return f"stats-{hashlib.blake2b(png, digest_size=4).hexdigest()}.png" if png else "chart.png"


class ActivityProvider(_Base):
    """Guild, single-user or single-channel activity (overview / messages / voice / commands)."""

    def __init__(
        self,
        guild: discord.Guild,
        repo: StatsRepository,
        chart_service: charts.ChartService,
        *,
        user_id: int | None = None,
        channel_id: int | None = None,
        subject: str | None = None,
        clock: Callable[[], datetime] = utcnow,
        leaderboard_size: int = 10,
    ) -> None:
        super().__init__(guild, repo, chart_service, clock=clock, leaderboard_size=leaderboard_size)
        self.uid = str(user_id) if user_id else None
        self.cid = str(channel_id) if channel_id else None
        self.subject = subject or safe_text(getattr(guild, "name", "Server"))
        self.scope = f"u{self.uid}" if self.uid else f"c{self.cid}" if self.cid else "g"
        if self.cid:
            self.tabs, self.default_tab = (("messages", "Messages"), ("voice", "Voice")), "messages"
        else:
            self.tabs = (("overview", "Overview"), ("messages", "Messages"), ("voice", "Voice"), ("commands", "Commands"))
            self.default_tab = "overview"

    async def build(self, tab: str, period: Period) -> Report:
        now = self._clock()
        start, end = period.bounds(now)
        kw = {"user_id": self.uid, "channel_id": self.cid}
        footer = self.footer(period, now)
        builder = {"overview": self._overview, "messages": self._messages, "voice": self._voice, "commands": self._commands}[tab]
        return await builder(period, start, end, kw, footer, now)

    async def _tops(self, metric: str, start, end, kw) -> list[str]:
        """'Top \N{HORIZONTAL ELLIPSIS}' lines appropriate for the scope (users in guild/channel, channels for a user)."""
        by = "channel_id" if self.uid else "user_id"
        rows = await self.repo.top(self.gid, metric, by, start, end, limit=3, **kw)
        fmt = (lambda v: f"{fmt_count(v)} msgs") if metric == "messages" else (lambda v: fmt_duration(v / 1000))
        label = self.channel_name if by == "channel_id" else self.user_name
        return [f"{i}. **{label(k)}** - {fmt(v)}" for i, (k, v) in enumerate(rows, 1)]

    def _days(self, period: Period, start, end, series) -> int:
        return period.days or max(1, ((end - (start or (series[0][0] if series else end))) // DAY))

    async def _time_chart(
        self,
        tab: str,
        period: Period,
        start: datetime | None,
        end: datetime,
        raw: Sequence[tuple[datetime, int]],
        kind: str,
        title: str,
        now: datetime,
        footer: str,
    ):
        series = fill_days(raw, start, end)
        data = [(d, v / 3_600_000 if kind == "hours" else v) for d, v in series]
        data = [(d, round(v, 2)) for d, v in data]
        return await self._chart(
            f"{self.scope}:{tab}:{period.key}",
            charts.render_time_series,
            data,
            title,
            f"{self.subject} \N{MIDDLE DOT} {period.label}",
            data,
            kind=kind,
            footer=f"{self.subject[:30]} \N{MIDDLE DOT} UTC",
        )

    def _report(
        self,
        title: str,
        summary: str,
        metrics: list[str],
        footer: str,
        png: bytes | None,
        alt: str,
    ) -> Report:
        return Report(
            title=title,
            summary=summary,
            metrics=metrics or ["No data recorded for this period yet."],
            footer=footer,
            chart_png=png,
            chart_name=self._name(png),
            chart_alt=alt,
        )

    async def _overview(self, period: Period, start: datetime | None, end: datetime, kw, footer: str, now: datetime) -> Report:
        totals, series, users_or_ch = await asyncio.gather(
            self.repo.totals(self.gid, start, end, **kw),
            self.repo.series(self.gid, "messages", start, end, **kw),
            self._tops("messages", start, end, kw),
        )
        png = await self._time_chart("overview", period, start, end, series, "count", "Message activity", now, footer)
        metrics = [
            f"**Messages** {fmt_count(totals['messages'])}   \N{MIDDLE DOT}   **Voice** {fmt_duration(totals['voice_ms'] / 1000)}"
            + (f"   \N{MIDDLE DOT}   **Commands** {fmt_count(totals.get('commands', 0))}" if not self.cid else "")
        ]
        if users_or_ch:
            metrics.append("**Most active " + ("channels" if self.uid else "members") + "**\n" + "\n".join(users_or_ch))
        if not totals["messages"] and not totals["voice_ms"] and not totals.get("commands"):
            metrics = []
        return self._report(
            f"{self.subject} - Overview", period.label, metrics, footer, png, f"Daily message counts for {self.subject}, {period.label}"
        )

    async def _messages(
        self,
        period: Period,
        start: datetime | None,
        end: datetime,
        kw,
        footer: str,
        now: datetime,
    ) -> Report:
        totals, series, tops = await asyncio.gather(
            self.repo.totals(self.gid, start, end, **kw),
            self.repo.series(self.gid, "messages", start, end, **kw),
            self._tops("messages", start, end, kw),
        )
        png = await self._time_chart("messages", period, start, end, series, "count", "Messages per day", now, footer)
        metrics: list[str] = []
        if totals["messages"]:
            best = max(series, key=lambda s: s[1])
            avg = totals["messages"] / self._days(period, start, end, series)
            metrics = [
                (
                    f"**Total** {fmt_count(totals['messages'])}   \N{MIDDLE DOT}   **Avg/day** {fmt_count(round(avg, 1))}"
                    f"   \N{MIDDLE DOT}   **Busiest day** {best[0]:%b %d} ({fmt_count(best[1])})"
                )
            ]
            if tops:
                metrics.append("\n".join(tops))
        return self._report(f"{self.subject} - Messages", period.label, metrics, footer, png, f"Messages per day, {period.label}")

    async def _voice(
        self,
        period: Period,
        start: datetime | None,
        end: datetime,
        kw,
        footer: str,
        now: datetime,
    ) -> Report:
        totals, series, tops = await asyncio.gather(
            self.repo.totals(self.gid, start, end, **kw), self.repo.series(self.gid, "voice", start, end, **kw), self._tops("voice", start, end, kw)
        )
        png = await self._time_chart("voice", period, start, end, series, "hours", "Voice hours per day", now, footer)
        metrics: list[str] = []
        if totals["voice_ms"]:
            secs = totals["voice_ms"] / 1000
            metrics = [
                (f"**Total** {fmt_duration(secs)}   \N{MIDDLE DOT}   **Avg/day** {fmt_duration(secs / self._days(period, start, end, series))}")
            ]
            if tops:
                metrics.append("\n".join(tops))
        return self._report(f"{self.subject} - Voice", period.label, metrics, footer, png, f"Voice hours per day, {period.label}")

    async def _commands(
        self,
        period: Period,
        start: datetime | None,
        end: datetime,
        kw,
        footer: str,
        now: datetime,
    ) -> Report:
        if self.cid:  # commands are not channel-scoped
            return self._report(f"{self.subject} - Commands", period.label, ["Commands are not tracked per channel."], footer, None, "")
        rows = await self.repo.top_commands(self.gid, start, end, limit=8, user_id=self.uid)
        png = await self._chart(
            f"{self.scope}:commands:{period.key}",
            charts.render_ranking,
            rows,
            "Most-used commands",
            f"{self.subject} \N{MIDDLE DOT} {period.label}",
            [r["command"] for r in rows],
            [r["attempts"] for r in rows],
            footer=f"{self.subject[:30]} \N{MIDDLE DOT} UTC",
        )
        metrics: list[str] = []
        if rows:
            att = sum(r["attempts"] for r in rows)
            ok, bad, rej = (sum(r[k] for r in rows) for k in ("success", "failed", "rejected"))
            timed, dur = sum(r["timed"] for r in rows), sum(r["duration_ms"] for r in rows)
            metrics = [
                f"**Invocations** {fmt_count(att)}   \N{MIDDLE DOT}   **Succeeded** {fmt_count(ok)}   \N{MIDDLE DOT}   "
                f"**Failed** {fmt_count(bad)}   \N{MIDDLE DOT}   **Rejected** {fmt_count(rej)}"
                + (f"   \N{MIDDLE DOT}   **Avg runtime** {dur / timed:.0f} ms" if timed else ""),
                "\n".join(f"{i}. `{safe_text(r['command'], 30)}` - {fmt_count(r['attempts'])}" for i, r in enumerate(rows[:5], 1)),
            ]
        return self._report(f"{self.subject} - Commands", period.label, metrics, footer, png, f"Most-used commands, {period.label}")


LEADERBOARD_TABS = (("messages", "Members: Messages"), ("voice", "Members: Voice"), ("channels", "Channels"), ("commands", "Commands"))


class LeaderboardProvider(_Base):
    tabs, default_tab = LEADERBOARD_TABS, "messages"

    def __init__(self, guild: discord.Guild, repo, chart_service, *, page: int = 0, **kw) -> None:
        super().__init__(guild, repo, chart_service, **kw)
        self.page = max(0, page)

    async def build(self, tab: str, period: Period) -> Report:
        now = self._clock()
        start, end = period.bounds(now)
        skip = self.page * self.size
        footer = self.footer(period, now) + (f" \N{MIDDLE DOT} page {self.page + 1}" if self.page else "")
        title = dict(self.tabs)[tab]

        if tab == "commands":
            rows = await self.repo.top_commands(self.gid, start, end, limit=self.size, skip=skip)
            labels, values = [r["command"] for r in rows], [r["attempts"] for r in rows]
            texts = [fmt_count(v) for v in values]
        else:
            metric, by = {"messages": ("messages", "user_id"), "voice": ("voice", "user_id"), "channels": ("messages", "channel_id")}[tab]
            rows = await self.repo.top(self.gid, metric, by, start, end, limit=self.size, skip=skip)
            name = self.channel_name if by == "channel_id" else self.user_name
            labels = [name(k) for k, _ in rows]
            values = [v / 3_600_000 if metric == "voice" else v for _, v in rows]
            texts = [fmt_duration(v * 3600) if metric == "voice" else fmt_count(v) for v in values]

        png = await self._chart(
            f"lb:{tab}:{period.key}:{self.page}",
            charts.render_ranking,
            (labels, values),
            f"Top - {title}",
            period.label,
            labels,
            values,
            value_labels=texts,
            footer=f"{safe_text(self.guild.name, 30)} \N{MIDDLE DOT} UTC",
        )
        lines = [f"`#{skip + i}` **{label}** - {text}" for i, (label, text) in enumerate(zip(labels, texts, strict=False), 1)]

        return Report(
            f"Leaderboard - {title}",
            period.label,
            lines or ["No data recorded for this period yet."],
            footer,
            png,
            self._name(png),
            f"Leaderboard: {title}, {period.label}",
        )
