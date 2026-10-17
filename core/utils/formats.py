# core/utils/formats.py

from __future__ import annotations

import datetime
from collections.abc import Sequence

import discord
import humanfriendly
import humanize
from dateutil.relativedelta import relativedelta

__all__ = (
    "format_clock_duration",
    "format_compact_duration",
    "format_count",
    "format_duration",
    "format_friendly_duration",
    "human_join",
    "human_timedelta",
    "natural_time",
    "plural",
    "safe_text",
    "truncate",
)

_UTC = datetime.UTC


class plural:
    """Format a number together with its singular or plural noun.

    Intended for use in format strings::

        f"{plural(1):apple}"  # "1 apple"
        f"{plural(2):apple}"  # "2 apples"
        f"{plural(2):child|children}"  # "2 children"
        f"{plural(2):apple!}"  # "apples" (number omitted)
    """

    def __init__(self, value: int):
        self.value = value

    def __format__(self, format_spec: str) -> str:
        """Format as ``singular[|plural][!]``.

        Only an absolute value of exactly one is singular (so ``0`` and ``-2``
        are plural). Without ``|plural``, an ``s`` is appended. A trailing
        ``!`` omits the number.
        """
        skip_value = format_spec.endswith("!")
        if skip_value:
            format_spec = format_spec[:-1]

        singular, _, plural_form = format_spec.partition("|")
        word = singular if abs(self.value) == 1 else (plural_form or f"{singular}s")
        return word if skip_value else f"{self.value} {word}"


def format_count(value: float) -> str:
    """Format a count compactly, e.g. ``1234`` -> ``1.2K``, ``2_500_000`` -> ``2.5M``."""
    value = float(value)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= limit:
            return f"{value / limit:.1f}".rstrip("0").rstrip(".") + suffix
    return f"{int(value):,}" if value == int(value) else f"{value:.1f}"


def format_duration(seconds: float) -> str:
    """Format a duration using its two largest units, e.g. ``2d 3h``, ``5m``, ``42s``.

    Negative values are treated as zero.
    """
    days, rem = divmod(int(max(0, seconds)), 86_400)
    hours, rem = divmod(rem, 3_600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{secs}s"


def format_clock_duration(milliseconds: float) -> str:
    """Format a media duration as ``m:ss`` or ``h:mm:ss``."""
    hours, rem = divmod(max(0, int(milliseconds // 1000)), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    return f"{minutes}:{secs:02}"


def format_compact_duration(seconds: float) -> str:
    """Format a duration in short units, e.g. ``1d 2h 30m``.

    Note: this is computed from a fixed reference date, so spans over a month
    use calendar months and weeks. A zero duration returns ``"now"``.
    """
    epoch = datetime.datetime(2000, 1, 1, tzinfo=_UTC)
    return human_timedelta(
        epoch + datetime.timedelta(seconds=max(0, seconds)),
        source=epoch,
        brief=True,
        suffix=False,
        accuracy=None,
    )


def format_friendly_duration(seconds: float) -> str:
    """Format a duration with humanfriendly's unit names, e.g. ``1 hour and 2 minutes``."""
    return humanfriendly.format_timespan(seconds)


def natural_time(value: datetime.datetime, *, when: datetime.datetime | None = None) -> str:
    """Format a datetime relative to ``when`` (default: now) using humanize."""
    return humanize.naturaltime(value, when=when)


def safe_text(text: str, limit: int = 40) -> str:
    """Escape mentions and markdown in user-controlled text, then truncate.

    Truncation happens after escaping, so the result is at most ``limit``
    characters but may end in the middle of an escape sequence.
    """
    return truncate(discord.utils.escape_markdown(discord.utils.escape_mentions(text)), limit)


def _as_utc(dt: datetime.datetime) -> datetime.datetime:
    """Treat naive datetimes as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=_UTC)


def human_timedelta(
    dt: datetime.datetime,
    *,
    source: datetime.datetime | None = None,
    accuracy: int | None = 3,
    brief: bool = False,
    suffix: bool = True,
) -> str:
    """Describe the difference between ``dt`` and ``source`` in words.

    Parameters
    ----------
    dt
        The datetime to describe. Naive values are assumed to be UTC.
    source
        The reference point. Defaults to the current UTC time.
    accuracy
        Maximum number of units to show (largest first); ``None`` for all.
    brief
        Use short units (``1y 2mo 3d``) instead of words.
    suffix
        Append ``" ago"`` when ``dt`` is before ``source``. Future times get
        no prefix or suffix.

    Returns
    -------
    str
        The description, or ``"now"`` if there is no difference.
    """
    now = _as_utc(source or datetime.datetime.now(_UTC))
    target = _as_utc(dt)
    rel = relativedelta(target, now) if target >= now else relativedelta(now, target)

    units = [("year", "y"), ("month", "mo"), ("day", "d"), ("hour", "h"), ("minute", "m"), ("second", "s")]
    output: list[str] = []
    for name, short in units:
        amount = getattr(rel, f"{name}s")
        if not amount:
            continue
        if name == "day" and rel.weeks:
            amount -= rel.weeks * 7
            output.append(f"{rel.weeks}w" if brief else format(plural(rel.weeks), "week"))
        if amount > 0:
            output.append(f"{amount}{short}" if brief else format(plural(amount), name))

    if accuracy is not None:
        output = output[:accuracy]
    if not output:
        return "now"

    text = " ".join(output) if brief else human_join(output, final="and")
    return f"{text} ago" if suffix and target < now else text


def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or") -> str:
    """Join strings as natural-language lists.

    ``["a"]`` -> ``"a"``, ``["a", "b"]`` -> ``"a or b"``,
    ``["a", "b", "c"]`` -> ``"a, b or c"``. Use ``final="and"`` for
    ``"a, b and c"``.
    """
    if len(seq) <= 1:
        return "".join(seq)
    if len(seq) == 2:
        return f"{seq[0]} {final} {seq[1]}"
    return f"{delim.join(seq[:-1])} {final} {seq[-1]}"


def truncate(text: str, limit: int, *, suffix: str = "\N{HORIZONTAL ELLIPSIS}") -> str:
    """Shorten ``text`` to at most ``limit`` characters, ending with ``suffix`` if cut."""
    if len(text) <= limit:
        return text
    if limit <= len(suffix):
        return suffix[: max(limit, 0)]
    return text[: limit - len(suffix)] + suffix
