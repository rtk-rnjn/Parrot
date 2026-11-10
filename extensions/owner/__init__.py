from __future__ import annotations

import asyncio
import io
import logging
import traceback
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatchcase
from functools import partial
from typing import TYPE_CHECKING, Any

import discord
import psutil
from colorama import Fore
from discord.ext import commands, tasks
from humanfriendly import InvalidTimespan, parse_timespan
from rapidfuzz import fuzz, process
lazy import aiohttp
lazy import matplotlib.dates as mdates
lazy from jishaku.codeblocks import Codeblock
lazy from matplotlib.backends.backend_agg import FigureCanvasAgg
lazy from matplotlib.figure import Figure

from .panel import OwnerPanel

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from core import Bot


RETENTION_MINUTES = 24 * 60  # 1 sample/min -> 24h. ~1440 tiny objects.
DEFAULT_WINDOW = "1h"


_log = logging.getLogger(__name__)

REDIS_RESULT_LIMIT = 1980


def pool_snapshot(session: aiohttp.ClientSession | None) -> tuple[int, int, bool]:
    """Returns (connections in use, idle keep-alive connections, session closed).

    Uses private connector attributes (no public API for this), so it is defensive.
    """
    if session is None:
        return 0, 0, True
    connector = session.connector
    if connector is None:
        return 0, 0, session.closed
    in_use = len(connector._acquired)
    idle = sum(len(v) for v in connector._conns.values())
    return in_use, idle, session.closed


@dataclass(slots=True)
class Sample:
    ts: datetime
    proc_cpu: float  # % of ONE core (can exceed 100 on multi-core)
    sys_cpu: float  # % of whole machine
    rss_mb: float
    sys_mem_pct: float
    threads: int
    tasks: int
    latency_ms: float
    loop_lag_ms: float  # worst event-loop stall seen during the minute
    guilds: int
    http_requests: int  # per-minute deltas
    http_errors: int
    http_new_conns: int
    http_reused_conns: int
    http_queued: int
    http_in_use: int  # gauges
    http_idle: int
    socket_delta: dict[str, int] = field(default_factory=dict)

    @property
    def socket_total(self) -> int:
        return sum(self.socket_delta.values())


BG = "#2b2d31"
PANEL = "#1e1f22"
FG = "#dbdee1"
GRID = "#3f4147"
PALETTE = [
    "#5865f2",
    "#57f287",
    "#fee75c",
    "#eb459e",
    "#ed4245",
    "#3ba5ff",
    "#f59e0b",
    "#a78bfa",
    "#2dd4bf",
    "#94a3b8",
]


def _style(ax: Axes, title: str, ylabel: str | None = None) -> None:
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=FG, fontsize=11, loc="left", pad=8)
    ax.tick_params(colors=FG, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=UTC))
    if ylabel:
        ax.set_ylabel(ylabel, color=FG, fontsize=8)


def _legend(ax: Axes, **kw: Any) -> None:
    ax.legend(fontsize=7, facecolor=BG, edgecolor=GRID, labelcolor=FG, **kw)


def _annotate_peak(ax: Axes, xs: list[datetime], ys: list[int], color: str) -> None:
    peak = max(ys, default=0)
    if peak <= 0:
        return
    idx = ys.index(peak)
    right = idx > len(ys) / 2  # keep the label inside the plot
    ax.plot([xs[idx]], [peak], marker="o", color=color)
    ax.annotate(
        f"peak {peak:,} @ {xs[idx]:%H:%M} UTC",
        xy=(xs[idx], peak),
        xytext=(-10 if right else 10, -16),
        textcoords="offset points",
        ha="right" if right else "left",
        color=FG,
        fontsize=8,
        arrowprops={"arrowstyle": "-", "color": color},
    )


def _plot_socket(ax: Axes, samples: list[Sample], top_n: int, events: list[str] | None = None) -> None:
    """One line per event type. `events` selects specific ones, otherwise the busiest `top_n`."""
    xs = [s.ts for s in samples]
    totals: Counter[str] = Counter()
    for s in samples:
        totals.update(s.socket_delta)

    names = list(events) if events else [name for name, _ in totals.most_common(top_n)]
    ceiling = 1
    for i, name in enumerate(names):
        ys = [s.socket_delta.get(name, 0) for s in samples]
        ceiling = max(ceiling, *ys)
        color = PALETTE[i % len(PALETTE)]
        ax.plot(xs, ys, color=color, linewidth=1.4, label=f"{name} ({totals[name]:,})")
        if len(names) == 1:
            ax.fill_between(xs, ys, color=color, alpha=0.15)
            _annotate_peak(ax, xs, ys, color)

    if names:
        # headroom so the legend sits above the lines instead of on top of them
        rows = -(-len(names) // 2) if len(names) > 4 else len(names)
        ax.set_ylim(0, ceiling * (1.12 + 0.045 * rows))
        _legend(ax, loc="upper left", ncol=2 if len(names) > 4 else 1)


def _event_summary(samples: list[Sample], names: list[str]) -> str:
    """Text table: total / average / peak minute per event."""
    width = max(len(n) for n in names)
    lines = []
    for name in names:
        ys = [s.socket_delta.get(name, 0) for s in samples]
        total, peak = sum(ys), max(ys)
        at = samples[ys.index(peak)].ts
        lines.append(f"{name:<{width}}  total {total:>9,}  avg {total / len(ys):>8.1f}/min  peak {peak:>6,} @ {at:%H:%M} UTC")
    return "```\n" + "\n".join(lines) + "\n```"


def _finish(fig: Figure, title: str) -> io.BytesIO:
    fig.suptitle(title, color=FG, fontsize=13, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    buf = io.BytesIO()
    FigureCanvasAgg(fig)
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf


DrawFn = Callable[[Any, "list[Sample]"], None]


def _draw_cpu(ax: Axes, samples: list[Sample]) -> None:
    xs = [s.ts for s in samples]
    _style(ax, "CPU", "%")
    ax.plot(xs, [s.proc_cpu for s in samples], color=PALETTE[0], label="bot (% of 1 core)")
    ax.plot(xs, [s.sys_cpu for s in samples], color=PALETTE[1], label="system (% total)")
    _legend(ax, loc="upper left")


def _draw_memory(ax: Axes, samples: list[Sample]) -> None:
    xs = [s.ts for s in samples]
    _style(ax, "Memory", "bot RSS (MB)")
    ax.plot(xs, [s.rss_mb for s in samples], color=PALETTE[0], label="bot RSS")
    ax2 = ax.twinx()
    ax2.plot(xs, [s.sys_mem_pct for s in samples], color=PALETTE[2], label="system %", linestyle="--")
    ax2.set_ylabel("system used (%)", color=FG, fontsize=8)
    ax2.tick_params(colors=FG, labelsize=8)
    for spine in ax2.spines.values():
        spine.set_color(GRID)
    _legend(ax, loc="upper left")
    _legend(ax2, loc="upper right")


def _draw_latency(ax: Axes, samples: list[Sample]) -> None:
    xs = [s.ts for s in samples]
    _style(ax, "Latency & event-loop lag", "ms")
    ax.plot(xs, [s.latency_ms for s in samples], color=PALETTE[5], label="gateway latency")
    ax.plot(xs, [s.loop_lag_ms for s in samples], color=PALETTE[4], label="worst loop lag")
    _legend(ax, loc="upper left")


def _draw_socket(ax: Axes, samples: list[Sample], top_n: int = 6) -> None:
    _style(ax, "Gateway events / min", "events")
    _plot_socket(ax, samples, top_n=top_n)


def _draw_http(ax: Axes, samples: list[Sample]) -> None:
    xs = [s.ts for s in samples]
    _style(ax, "aiohttp / min", "count")
    ax.plot(xs, [s.http_requests for s in samples], color=PALETTE[0], label="requests")
    ax.plot(xs, [s.http_new_conns for s in samples], color=PALETTE[1], label="new conns")
    ax.plot(xs, [s.http_reused_conns for s in samples], color=PALETTE[2], label="reused conns")
    ax.plot(xs, [s.http_errors for s in samples], color=PALETTE[4], label="errors")
    ax.plot(xs, [s.http_queued for s in samples], color=PALETTE[6], label="queued (pool full)")
    _legend(ax, loc="upper left", ncol=2)


def _draw_runtime(ax: Axes, samples: list[Sample]) -> None:
    xs = [s.ts for s in samples]
    _style(ax, "Runtime gauges", "count")
    ax.plot(xs, [s.tasks for s in samples], color=PALETTE[3], label="asyncio tasks")
    ax.plot(xs, [s.threads for s in samples], color=PALETTE[6], label="threads")
    ax.plot(xs, [s.http_in_use + s.http_idle for s in samples], color=PALETTE[8], label="http pool conns")
    _legend(ax, loc="upper left")


def render_dashboard(samples: list[Sample], title: str) -> io.BytesIO:
    fig = Figure(figsize=(13, 9), dpi=100, facecolor=BG)
    axes = fig.subplots(3, 2)

    _draw_cpu(axes[0][0], samples)
    _draw_memory(axes[0][1], samples)
    _draw_latency(axes[1][0], samples)
    _draw_socket(axes[1][1], samples, top_n=6)
    _draw_http(axes[2][0], samples)
    _draw_runtime(axes[2][1], samples)

    return _finish(fig, title)


def render_panel(draw: DrawFn, samples: list[Sample], title: str) -> io.BytesIO:
    """Render a single graph full-size."""
    fig = Figure(figsize=(13, 6), dpi=100, facecolor=BG)
    ax = fig.subplots(1, 1)
    draw(ax, samples)
    return _finish(fig, title)


def render_socket_chart(samples: list[Sample], title: str, events: list[str] | None = None) -> io.BytesIO:
    fig = Figure(figsize=(13, 6), dpi=100, facecolor=BG)
    ax = fig.subplots(1, 1)
    _style(ax, "Gateway events / min" + ("" if events else " (top 9)"), "events")
    _plot_socket(ax, samples, top_n=9, events=events)
    return _finish(fig, title)


class Owner(commands.Cog, command_attrs={"hidden": True}):
    """Bot owner tools for extensions, evaluation and maintenance."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        self.samples: deque[Sample] = deque(maxlen=RETENTION_MINUTES)

        self._process = psutil.Process()
        self._process.cpu_percent(None)  # prime; first call always returns 0.0
        psutil.cpu_percent(None)

        self._prev_socket: Counter[str] = Counter()
        self._prev_http: dict[str, int] = {}
        self._max_lag = 0.0
        self._lag_task: asyncio.Task[None] | None = None
        self._render_lock = asyncio.Lock()

        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def cog_load(self) -> None:
        self._lag_task = asyncio.create_task(self._lag_monitor())
        self.sample_loop.start()

    async def cog_unload(self) -> None:
        self.sample_loop.cancel()
        if self._lag_task:
            self._lag_task.cancel()

    async def _lag_monitor(self) -> None:
        """Sleeps 1s repeatedly; anything beyond 1s is time the loop was blocked."""
        loop = asyncio.get_running_loop()
        while True:
            start = loop.time()
            await asyncio.sleep(1.0)
            self._max_lag = max(self._max_lag, loop.time() - start - 1.0)

    @tasks.loop(minutes=1)
    async def sample_loop(self) -> None:
        try:
            self.samples.append(self._collect())
        except Exception:
            _log.exception("Metrics sampling failed")

    @sample_loop.before_loop
    async def _before_sample_loop(self) -> None:
        await self.bot.wait_until_ready()
        # Baselines so the first delta isn't "everything since boot".
        self._prev_socket = Counter(self.bot.socket_stats)
        stats = self.bot.http_stats
        self._prev_http = stats.snapshot() if stats else {}

    def _collect(self) -> Sample:
        with self._process.oneshot():
            proc_cpu = self._process.cpu_percent(None)
            rss_mb = self._process.memory_info().rss / 1024**2
            threads = self._process.num_threads()

        # Counter subtraction keeps only positive deltas.
        current_socket = Counter(self.bot.socket_stats)
        socket_delta = dict(current_socket - self._prev_socket)
        self._prev_socket = current_socket

        stats = self.bot.http_stats
        http_now = stats.snapshot() if stats else {}
        d = {k: http_now[k] - self._prev_http.get(k, 0) for k in http_now}
        self._prev_http = http_now

        in_use, idle, _ = pool_snapshot(self.bot.http_session)

        lag_ms = self._max_lag * 1000
        self._max_lag = 0.0

        latency = self.bot.latency
        return Sample(
            ts=datetime.now(UTC),
            proc_cpu=proc_cpu,
            sys_cpu=psutil.cpu_percent(None),
            rss_mb=rss_mb,
            sys_mem_pct=psutil.virtual_memory().percent,
            threads=threads,
            tasks=len(asyncio.all_tasks()),
            latency_ms=0.0 if latency != latency else latency * 1000,  # NaN before connect  # noqa: PLR0124
            loop_lag_ms=lag_ms,
            guilds=len(self.bot.guilds),
            http_requests=d.get("requests", 0),
            http_errors=d.get("errors", 0),
            http_new_conns=d.get("created", 0),
            http_reused_conns=d.get("reused", 0),
            http_queued=d.get("queued", 0),
            http_in_use=in_use,
            http_idle=idle,
            socket_delta=socket_delta,
        )

    def _window(self, text: str) -> tuple[list[Sample], str]:
        try:
            seconds = parse_timespan(text)
        except InvalidTimespan:
            msg = "Use a window like `15m`, `1h`, `6h` or `24h`."
            raise commands.BadArgument(msg) from None

        cutoff = datetime.now(UTC) - timedelta(seconds=seconds)
        picked = [s for s in self.samples if s.ts >= cutoff]
        if len(picked) < 2:
            msg = "Not enough samples yet, give it a couple of minutes."
            raise commands.BadArgument(msg)
        return picked, text

    async def _render(self, fn, samples: list[Sample], title: str) -> discord.File:
        async with self._render_lock:
            buf = await asyncio.to_thread(fn, samples, title)
        return discord.File(buf, filename="metrics.png")

    async def _send_panel(self, ctx: commands.Context[Bot], draw: DrawFn, name: str, window: str) -> None:
        """Shared body for every single-graph subcommand."""
        samples, label = self._window(window)
        async with ctx.typing():
            file = await self._render(partial(render_panel, draw), samples, f"{name}, last {label} (UTC)")
        await ctx.reply(file=file)

    @commands.group(name="perf", aliases=["vitals"], invoke_without_command=True)
    async def metrics(self, ctx: commands.Context[Bot], window: str = DEFAULT_WINDOW) -> None:
        """Runtime dashboard (CPU, RAM, latency, loop lag, gateway events, aiohttp)."""
        samples, label = self._window(window)
        last = samples[-1]
        in_use, idle, closed = pool_snapshot(self.bot.http_session)

        async with ctx.typing():
            file = await self._render(render_dashboard, samples, f"Bot metrics, last {label} ({len(samples)} samples, UTC)")

        embed = discord.Embed(color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
        embed.add_field(name="CPU", value=f"{last.proc_cpu:.1f}% bot / {last.sys_cpu:.1f}% sys")
        embed.add_field(name="RAM", value=f"{last.rss_mb:.0f} MB / {last.sys_mem_pct:.0f}% sys")
        embed.add_field(name="Latency", value=f"{last.latency_ms:.0f} ms (lag {last.loop_lag_ms:.0f} ms)")
        embed.add_field(name="Tasks / threads", value=f"{last.tasks} / {last.threads}")
        embed.add_field(name="Gateway", value=f"{last.socket_total} events/min")
        embed.add_field(
            name="HTTP pool",
            value=f"{in_use} busy, {idle} idle, session {'closed' if closed else 'open'}",
        )
        embed.set_image(url="attachment://metrics.png")
        embed.set_footer(text=f"{len(self.samples)}/{RETENTION_MINUTES} samples held in memory")
        await ctx.reply(embed=embed, file=file)

    @metrics.command(name="cpu")
    async def metrics_cpu(self, ctx: commands.Context[Bot], window: str = DEFAULT_WINDOW) -> None:
        """Bot and system CPU usage."""
        await self._send_panel(ctx, _draw_cpu, "CPU", window)

    @metrics.command(name="memory", aliases=["ram", "mem"])
    async def metrics_memory(self, ctx: commands.Context[Bot], window: str = DEFAULT_WINDOW) -> None:
        """Bot RSS and system memory usage."""
        await self._send_panel(ctx, _draw_memory, "Memory", window)

    @metrics.command(name="latency", aliases=["lag", "ping"])
    async def metrics_latency(self, ctx: commands.Context[Bot], window: str = DEFAULT_WINDOW) -> None:
        """Gateway latency and worst event-loop lag."""
        await self._send_panel(ctx, _draw_latency, "Latency & loop lag", window)

    @metrics.command(name="http", aliases=["aiohttp", "net"])
    async def metrics_http(self, ctx: commands.Context[Bot], window: str = DEFAULT_WINDOW) -> None:
        """aiohttp requests, connections and errors per minute."""
        await self._send_panel(ctx, _draw_http, "aiohttp", window)

    @metrics.command(name="runtime", aliases=["tasks", "gauges"])
    async def metrics_runtime(self, ctx: commands.Context[Bot], window: str = DEFAULT_WINDOW) -> None:
        """asyncio tasks, threads and HTTP pool size."""
        await self._send_panel(ctx, _draw_runtime, "Runtime gauges", window)

    def _resolve_events(self, queries: tuple[str, ...]) -> tuple[list[str], list[str]]:
        """Map user input to known event names. Returns (resolved, problem messages).

        Case-insensitive, supports globs (`MESSAGE_*`), and fuzzy-suggests for unknown names.
        """
        known = list(self.bot.socket_stats)
        resolved: list[str] = []
        problems: list[str] = []

        for raw in queries:
            query = raw.upper().replace("-", "_")
            if "*" in query or "?" in query:
                matches = sorted(n for n in known if fnmatchcase(n, query))
            else:
                matches = [query] if query in self.bot.socket_stats else []

            if matches:
                for name in matches:
                    if name not in resolved:
                        resolved.append(name)
                continue

            close = process.extract(query, known, scorer=fuzz.WRatio, limit=3, score_cutoff=60)
            if close:
                options = " or ".join(f"`{name}`" for name, _, _ in close)
                problems.append(f"`{query}` hasn't been received since startup. Did you mean {options}?")
            else:
                problems.append(f"`{query}` hasn't been received since startup, and nothing similar is known.")

        return resolved, problems

    @metrics.command(name="socket", aliases=["sockets", "gateway"])
    async def metrics_socket(self, ctx: commands.Context[Bot], window: str = DEFAULT_WINDOW, *events: str) -> None:
        """Gateway events per minute as lines, optionally filtered.

        Examples: `socket`, `socket 6h`, `socket 1h MESSAGE_CREATE`,
        `socket 1h MESSAGE_CREATE TYPING_START`, `socket 1h MESSAGE_*`.
        """
        # Be forgiving: `socket MESSAGE_CREATE` (no window) works too.
        try:
            parse_timespan(window)
        except InvalidTimespan:
            events = (window, *events)
            window = DEFAULT_WINDOW

        samples, label = self._window(window)

        if not events:
            async with ctx.typing():
                file = await self._render(render_socket_chart, samples, f"Gateway events, last {label} (UTC)")
            await ctx.reply(file=file)
            return

        if not self.bot.socket_stats:
            await ctx.reply("No socket events have been recorded yet.")
            return

        resolved, notes = self._resolve_events(events)

        totals: Counter[str] = Counter()
        for s in samples:
            totals.update(s.socket_delta)

        active = [n for n in resolved if totals[n]]
        notes += [f"`{n}` was received since startup, but not in the last {label}." for n in resolved if not totals[n]]

        if not active:
            await ctx.reply("\n".join(notes))
            return

        if len(active) > len(PALETTE):
            active = sorted(active, key=totals.__getitem__, reverse=True)[: len(PALETTE)]
            notes.append(f"Showing the {len(PALETTE)} busiest matches.")

        title = f"{', '.join(active) if len(active) <= 3 else f'{len(active)} events'}, last {label} (UTC)"
        async with ctx.typing():
            file = await self._render(partial(render_socket_chart, events=active), samples, title)

        await ctx.reply("\n".join([_event_summary(samples, active), *notes]), file=file)

    async def cog_check(self, ctx: commands.Context[Bot]) -> bool:
        if await self.bot.is_owner(ctx.author):
            return True

        raise commands.NotOwner()

    def _format_traceback(self, error: Exception) -> str:
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = "".join(tb)
        return f"```ansi\n{Fore.RED}{tb_str}{Fore.RESET}\n```"

    @commands.command(name="redis-repl", aliases=["redis-cli", "redis"])
    async def redis_repl(self, ctx: commands.Context[Bot]) -> None:
        """Run raw Redis commands from chat until `exit`. Monitoring lives in the owner panel."""
        await ctx.reply("\N{VIDEO GAME} Redis REPL session started. Type `exit` to quit.")

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        love = ...  # idk what is love, so just a placeholder

        while love is not True or False:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=300)
            except TimeoutError:
                await ctx.reply("\N{ALARM CLOCK} Redis REPL session timed out.")
                break

            if msg.content.lower() == "exit":
                await msg.reply("\N{WAVING HAND SIGN} Exiting Redis REPL session.")
                break

            codeblock = Codeblock.convert_raw(msg.content)
            try:
                result = await self.bot.database.redis_client.execute_command(codeblock.content)
                if len(str(result)) > REDIS_RESULT_LIMIT:
                    await msg.reply("\N{WARNING SIGN} Result is too long to display.")
                else:
                    await msg.reply(f"```py\n{result}```")
            except Exception as e:
                tb_fmt = self._format_traceback(e)
                await msg.reply(tb_fmt)

    @commands.command(name="owner", aliases=["panel", "dev"])
    async def owner(self, ctx: commands.Context[Bot]) -> None:
        """Open the owner panel: bot runtime, Redis, MongoDB, Lavalink and asyncio tasks in one tabbed message."""
        panel = OwnerPanel(ctx.author, bot=self.bot)
        await panel.start(ctx)

    @commands.command(name="echo", rest_is_raw=True)
    async def echo(self, ctx: commands.Context[Bot], *, message: str) -> None:
        """Echo a message."""
        await ctx.reply(message)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Owner(bot))
