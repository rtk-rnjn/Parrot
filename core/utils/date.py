from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Literal

from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    import discord

    from core import Parrot

__all__ = ("MONTHS", "BadDateTransform", "DateTransformer", "HumanDate")

Prefer = Literal["current", "future", "past"]

MONTHS: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "febuary": 2, "february": 2,   # 'febuary' is the single most common typo
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}  # fmt: skip

# Longest-first so "march" wins over "mar" and "september" over "sep".
_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

_DAY = r"(?P<day>\d{1,2})(?:st|nd|rd|th)?"
_MONTH = rf"(?P<month>{_MONTH_ALT})\.?"
_YEAR = r"(?P<year>\d{4}|['\u2019]?\d{2})"  # 2004 | '04 | 04 | ’04
_SEP = r"[\s,]+"

# Every pattern is tried against the *start* of the string; the longest match
# wins. That resolves "March 2004" (month-year) vs "March 20" + "04" for free,
# while ties go to the earlier pattern, so "March 23" stays month-day.
_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # ISO: 2004-03-23
    re.compile(r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"),
    # DMY: 23 March 2004 / 23rd of March '04 / 23 Mar
    re.compile(rf"{_DAY}{_SEP}(?:of{_SEP})?{_MONTH}(?:{_SEP}{_YEAR})?", re.IGNORECASE),
    # MDY: May 13 '12 / March 23rd, 2004 / Mar 23
    re.compile(rf"{_MONTH}{_SEP}{_DAY}(?:{_SEP}{_YEAR})?", re.IGNORECASE),
    # MY:  March 2004 / May '12
    re.compile(rf"{_MONTH}{_SEP}{_YEAR}", re.IGNORECASE),
    # Numeric, genuinely ambiguous: 23/03/2004 / 3-23-04 / 23.03
    re.compile(r"(?P<first>\d{1,2})[-/.](?P<second>\d{1,2})(?:[-/.](?P<year>\d{4}|\d{2}))?"),
)

_TIME_RE = re.compile(
    r"""
    (?:(?P<at>at|@)\s*)?
    (?P<hour>\d{1,2})
    (?::(?P<minute>\d{2}))?
    (?::(?P<second>\d{2}))?
    \s*
    (?P<ampm>[ap]\.?m\.?)?
    """,
    re.VERBOSE | re.IGNORECASE,
)


class BadDateTransform(app_commands.AppCommandError):
    pass


def _expand_year(raw: str, *, pivot: int = 69) -> int:
    """'04 -> 2004, '99 -> 1999, 2004 -> 2004.

    Matches the POSIX/strptime pivot: 69-99 is 1900s, 00-68 is 2000s.
    """
    raw = raw.lstrip("'\u2019")
    if len(raw) >= 4:
        return int(raw)
    n = int(raw)
    return 1900 + n if n >= pivot else 2000 + n


def _shift_year(date: datetime.date, year: int) -> datetime.date:
    try:
        return date.replace(year=year)
    except ValueError:  # 29 Feb into a non-leap year
        return date.replace(year=year, day=28)


def _match_date(argument: str) -> re.Match[str] | None:
    best: re.Match[str] | None = None
    for pattern in _DATE_PATTERNS:
        m = pattern.match(argument)
        if m is not None and (best is None or m.end() > best.end()):
            best = m
    return best


def _resolve_month_day(data: dict[str, str | None], *, dayfirst: bool) -> tuple[int, int]:
    month_raw = data.get("month")

    if month_raw is None:
        # Purely numeric: 23/03 is unambiguous (23 can't be a month), 03/04 isn't.
        first, second = int(data["first"]), int(data["second"])  # type: ignore[arg-type]
        if first > 12:
            return second, first
        if second > 12:
            return first, second
        return (second, first) if dayfirst else (first, second)

    month = MONTHS.get(month_raw.lower())
    if month is None:
        month = int(month_raw)  # ISO branch, where month is digits

    day = int(data["day"] or 1) if data.get("day") else 1  # "March 2004" -> the 1st
    return month, day


def _parse_time(text: str) -> tuple[datetime.time, int] | None:
    m = _TIME_RE.match(text)
    if m is None:
        return None

    # A bare number is too dangerous to treat as a time -- require a colon,
    # an am/pm, or an explicit "at"/"@".
    if not (m.group("at") or m.group("minute") or m.group("ampm")):
        return None

    hour = int(m.group("hour"))
    minute = int(m.group("minute") or 0)
    second = int(m.group("second") or 0)

    ampm = m.group("ampm")
    if ampm:
        if not 1 <= hour <= 12:
            return None
        if ampm[0].lower() == "p":
            hour = hour if hour == 12 else hour + 12
        elif hour == 12:
            hour = 0

    if hour > 23 or minute > 59 or second > 59:
        return None
    return datetime.time(hour, minute, second), m.end()


class HumanDate:
    """Parses an explicit calendar date, optionally followed by a time.

    Understands, among others::

        23 March 2004        23rd of March, 2004      23 Mar 04
        May 13 '12           March 23rd, 2004         Mar 23
        March 2004           May '12                  2004-03-23
        23/03/2004           3-23-04                  23 March 2004 at 5pm

    Parameters
    ----------
    dayfirst:
        How to read an ambiguous all-numeric date like ``03/04/05``. ``True``
        (the default) reads it day-first; pass ``False`` for US ordering. Dates
        with a named month are never ambiguous, so this doesn't touch them.
    prefer:
        What to do when no year was given. ``"current"`` uses the current year,
        ``"future"`` rolls forward if the date has already passed, ``"past"``
        rolls back if it hasn't. Use ``"past"`` for birthdays, ``"future"`` for
        reminders.

    Attributes
    ----------
    date: :class:`datetime.date`
    dt: :class:`datetime.datetime`
        Timezone-aware, midnight local unless a time was supplied.
    has_year: :class:`bool`
        ``False`` if the year was inferred rather than written.
    has_time: :class:`bool`
    remaining: :class:`str`
        Whatever followed the date, for commands like ``!remind 23 March 2004 ...``.
    """

    __slots__ = ("date", "datetime", "has_time", "has_year", "remaining")

    def __init__(
        self,
        argument: str,
        *,
        now: datetime.datetime | None = None,
        tzinfo: datetime.tzinfo | None = None,
        dayfirst: bool = True,
        prefer: Prefer = "current",
    ) -> None:
        argument = argument.strip()
        m = _match_date(argument)
        if m is None:
            msg = "Couldn't find a date in that. Try something like `23 March 2004`, `May 13 '12` or `2004-03-23`."
            raise commands.BadArgument(msg)

        data = m.groupdict()
        month, day = _resolve_month_day(data, dayfirst=dayfirst)

        if tzinfo is None:
            tzinfo = datetime.UTC

        if now is None:
            now = datetime.datetime.now(tzinfo)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=datetime.UTC)
        today = now.astimezone(tzinfo).date()

        year_raw = data.get("year")
        self.has_year = year_raw is not None
        year = _expand_year(year_raw) if year_raw else today.year

        try:
            date = datetime.date(year, month, day)
        except ValueError:
            message = f"`{m.group(0)}` isn't a real date."
            raise commands.BadArgument(message) from None

        if not self.has_year:
            if prefer == "future" and date < today:
                date = _shift_year(date, year + 1)
            elif prefer == "past" and date > today:
                date = _shift_year(date, year - 1)

        rest = argument[m.end() :].strip()
        parsed_time = _parse_time(rest)
        if parsed_time is not None:
            time, end = parsed_time
            rest = rest[end:].strip()
        else:
            time = datetime.time(0, 0)

        self.date = date
        self.has_time = parsed_time is not None
        self.remaining = rest
        self.datetime = datetime.datetime.combine(date, time, tzinfo=tzinfo)

    def __repr__(self) -> str:
        return f"<HumanDate date={self.date!r} has_year={self.has_year} remaining={self.remaining!r}>"

    @classmethod
    async def convert(cls, ctx: commands.Context[Parrot], argument: str) -> HumanDate:
        tzinfo = datetime.UTC
        reminder = ctx.bot.reminder
        if reminder is not None:
            tzinfo = await reminder.get_tzinfo(ctx.author.id)
        return cls(argument, now=ctx.message.created_at, tzinfo=tzinfo)


class DateTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction[Parrot], value: str) -> datetime.datetime:
        tzinfo = datetime.UTC
        reminder = interaction.client.reminder
        if reminder is not None:
            tzinfo = await reminder.get_tzinfo(interaction.user.id)
        try:
            return HumanDate(value, now=interaction.created_at, tzinfo=tzinfo).datetime
        except commands.BadArgument as e:
            raise BadDateTransform(str(e)) from None
