from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
from PIL import Image, ImageDraw, ImageFont

from core.utils.formats import format_count as fmt_count
from core.utils.formats import truncate

log = logging.getLogger(__name__)

FIG_W, FIG_H, DPI = 7.5, 4.0, 120
MAX_PIXEL_WIDTH = 1200


@dataclass(frozen=True, slots=True)
class Theme:
    bg: str = "#1e2230"
    outer: str = "#14161f"
    text: str = "#e8eaf2"
    muted: str = "#9aa1b9"
    grid: str = "#343a52"
    accent: str = "#5865f2"
    accent2: str = "#57f287"
    border: str = "#2f3550"


THEME = Theme()


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path("assets/DejaVuSansMNerdFontMono-Regular.ttf")
    try:
        return ImageFont.truetype(path, size)
    except OSError:  # pragma: no cover - fallback
        return ImageFont.load_default()


def _style_axes(ax: Any, theme: Theme) -> None:
    ax.set_facecolor(theme.bg)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(theme.grid)
    ax.tick_params(colors=theme.muted, labelsize=13, length=0, pad=6)
    ax.grid(axis="y", color=theme.grid, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)


def _axis_formatter(kind: str) -> FuncFormatter:
    if kind == "hours":
        return FuncFormatter(lambda v, _: f"{v:g}h")
    return FuncFormatter(lambda v, _: fmt_count(v))


def _to_png(fig: Figure, theme: Theme) -> bytes:
    buf = io.BytesIO()
    try:
        FigureCanvasAgg(fig)
        fig.savefig(buf, format="png", dpi=DPI, facecolor=theme.bg)
        return buf.getvalue()
    finally:
        buf.close()
        fig.clear()


def _compose(png: bytes, footer: str, theme: Theme) -> bytes:
    """Pillow stage: outer padding, border, consistent footer; bounded output size."""
    pad, foot = 14, 30
    with Image.open(io.BytesIO(png)) as src:
        chart = src.convert("RGB")
    canvas = Image.new("RGB", (chart.width + 2 * pad, chart.height + 2 * pad + foot), theme.outer)
    canvas.paste(chart, (pad, pad))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((pad - 1, pad - 1, pad + chart.width, pad + chart.height), outline=theme.border, width=2)
    draw.text((pad + 4, pad + chart.height + 8), truncate(footer, 90), fill=theme.muted, font=_font(14))
    if canvas.width > MAX_PIXEL_WIDTH:
        ratio = MAX_PIXEL_WIDTH / canvas.width
        canvas = canvas.resize((MAX_PIXEL_WIDTH, int(canvas.height * ratio)), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    try:
        canvas.save(out, format="PNG", optimize=True)
        return out.getvalue()
    finally:
        out.close()
        chart.close()
        canvas.close()


def _title(fig: Figure, title: str, subtitle: str, theme: Theme) -> None:
    fig.text(0.04, 0.95, truncate(title, 48), color=theme.text, fontsize=19, fontweight="bold", va="top")
    if subtitle:
        fig.text(0.04, 0.875, truncate(subtitle, 70), color=theme.muted, fontsize=12.5, va="top")


def render_time_series(
    title: str,
    subtitle: str,
    series: Sequence[tuple[datetime, float]],
    *,
    kind: str = "count",
    footer: str = "UTC",
    theme: Theme = THEME,
) -> bytes:
    """Line + area chart for daily trends. Empty input yields an empty-state image."""
    if not series or not any(v for _, v in series):
        return render_empty(title, "No activity recorded for this period yet.", footer=footer, theme=theme)
    fig = Figure(figsize=(FIG_W, FIG_H), facecolor=theme.bg)
    try:
        ax = fig.add_axes((0.11, 0.17, 0.85, 0.60))
        _style_axes(ax, theme)
        xs = [d.replace(tzinfo=None) for d, _ in series]  # naive-UTC for matplotlib date handling
        ys = [float(v) for _, v in series]
        ax.plot(xs, ys, color=theme.accent, linewidth=2.6, marker="o" if len(xs) <= 31 else None, markersize=4.5)
        ax.fill_between(xs, ys, color=theme.accent, alpha=0.18)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=(kind == "count")))
        ax.yaxis.set_major_formatter(_axis_formatter(kind))
        loc = AutoDateLocator(minticks=3, maxticks=6)
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(ConciseDateFormatter(loc))
        if len(xs) == 1:
            ax.set_xlim(xs[0] - timedelta(days=1), xs[0] + timedelta(days=1))
        _title(fig, title, subtitle, theme)
        return _compose(_to_png(fig, theme), footer, theme)
    finally:
        fig.clear()


def render_ranking(
    title: str,
    subtitle: str,
    labels: Sequence[str],
    values: Sequence[float],
    *,
    value_labels: Sequence[str] | None = None,
    footer: str = "UTC",
    theme: Theme = THEME,
) -> bytes:
    """Horizontal bars, largest on top. Long labels are truncated; height grows with rows."""
    if not labels or not any(values):
        return render_empty(title, "Nothing to rank for this period yet.", footer=footer, theme=theme)

    n = len(labels)
    height = max(3.2, 1.35 + 0.46 * n)
    head = 1.05 / height
    fig = Figure(figsize=(FIG_W, height), facecolor=theme.bg)
    try:
        ax = fig.add_axes((0.34, 0.05, 0.57, 1 - head - 0.05))
        _style_axes(ax, theme)
        ax.grid(False)
        ypos = list(range(n))
        ax.barh(ypos, list(values), color=theme.accent, height=0.62)
        ax.set_yticks(ypos)
        ax.set_yticklabels([truncate(label, 19) for label in labels], color=theme.text, fontsize=13)
        ax.invert_yaxis()
        ax.set_xticks([])
        ax.spines["bottom"].set_visible(False)
        top_val = max(values) or 1
        ax.set_xlim(0, top_val * 1.32)
        texts = value_labels or [fmt_count(v) for v in values]
        for y, v, text in zip(ypos, values, texts, strict=False):
            ax.text(v + top_val * 0.02, y, text, va="center", color=theme.text, fontsize=12.5)
        fig.text(0.04, 1 - 0.18 / height, truncate(title, 48), color=theme.text, fontsize=19, fontweight="bold", va="top")
        if subtitle:
            fig.text(0.04, 1 - 0.58 / height, truncate(subtitle, 70), color=theme.muted, fontsize=12.5, va="top")
        return _compose(_to_png(fig, theme), footer, theme)
    finally:
        fig.clear()


def render_empty(title: str, message: str, *, footer: str = "UTC", theme: Theme = THEME) -> bytes:
    fig = Figure(figsize=(FIG_W, 2.6), facecolor=theme.bg)
    try:
        fig.text(0.04, 0.88, truncate(title, 48), color=theme.text, fontsize=19, fontweight="bold", va="top")
        fig.text(0.5, 0.42, truncate(message, 70), color=theme.muted, fontsize=15, ha="center", va="center")
        return _compose(_to_png(fig, theme), footer, theme)
    finally:
        fig.clear()


class ChartService:
    """Async facade: thread offload, bounded concurrency, bounded TTL cache.

    Cache keys are built by the caller from ``(guild, scope, subject, tab, period)`` plus a
    digest of the *data itself*, so a hit can only ever serve identical input for the same guild.
    Nothing interaction-related is cached.
    """

    def __init__(self, max_concurrent: int = 2, cache_size: int = 64, ttl: float = 120.0, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._sem = asyncio.Semaphore(max_concurrent)
        self._cache: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
        self._size, self._ttl, self._clock = cache_size, ttl, clock
        self.hits = self.misses = 0

    @staticmethod
    def key(guild_id: str, scope: str, data: Any) -> str:
        digest = hashlib.blake2b(repr(data).encode(), digest_size=8).hexdigest()
        return f"{guild_id}|{scope}|{digest}"

    async def render(self, key: str, fn: Callable[..., bytes], *args: Any, **kwargs: Any) -> bytes:
        now = self._clock()
        hit = self._cache.get(key)
        if hit and now - hit[0] <= self._ttl:
            self._cache.move_to_end(key)
            self.hits += 1
            return hit[1]
        self.misses += 1
        async with self._sem:  # at most N renders in flight
            png = await asyncio.to_thread(fn, *args, **kwargs)  # CPU work off the event loop
        self._cache[key] = (self._clock(), png)
        self._cache.move_to_end(key)
        while len(self._cache) > self._size:
            self._cache.popitem(last=False)
        return png

    def clear(self) -> None:
        self._cache.clear()
