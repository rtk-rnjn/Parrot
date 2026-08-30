from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Any, Self

import arrow
import dateparser
from dateutil.relativedelta import relativedelta
from discord import app_commands
from discord.ext import commands

from .formats import human_join, plural

if TYPE_CHECKING:
    from core.bot import Parrot

__all__ = (
    "ShortTime",
    "RelativeDelta",
    "HumanTime",
    "Time",
    "FutureTime",
    "FriendlyTimeResult",
    "UserFriendlyTime",
    "human_timedelta",
)

SHORT_RE = re.compile(
    r"""
    (?:(?P<years>\d+)(?:years?|y))?
    (?:(?P<months>\d+)(?:months?|mon?))?
    (?:(?P<weeks>\d+)(?:weeks?|w))?
    (?:(?P<days>\d+)(?:days?|d))?
    (?:(?P<hours>\d+)(?:hours?|hr?s?))?
    (?:(?P<minutes>\d+)(?:minutes?|m(?:ins?)?))?
    (?:(?P<seconds>\d+)(?:seconds?|s(?:ecs?)?))?
    """,
    re.VERBOSE | re.IGNORECASE,
)

DISCORD_TS_RE = re.compile(r"<t:(?P<ts>\d+)(?:\:[RFfDdTt])?>")


def _as_arrow_now(now: datetime.datetime | None, tzinfo: datetime.tzinfo) -> arrow.Arrow:
    if now is None:
        return arrow.now(tzinfo)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.UTC)
    return arrow.get(now).to(tzinfo)


def _parse_short(argument: str, now: arrow.Arrow) -> arrow.Arrow | None:
    m = SHORT_RE.fullmatch(argument.strip())
    if not m or not m.group(0):
        return None
    data = {k: int(v or 0) for k, v in m.groupdict().items()}
    if not any(data.values()):
        return None
    return now.shift(**data)


def _parse_discord_ts(argument: str, tzinfo: datetime.tzinfo) -> arrow.Arrow | None:
    m = DISCORD_TS_RE.fullmatch(argument.strip())
    if not m:
        return None
    return arrow.get(int(m.group("ts"))).to(tzinfo)


def _parse_human(argument: str, now: arrow.Arrow, tzinfo: datetime.tzinfo) -> arrow.Arrow | None:
    dt = dateparser.parse(
        argument,
        settings={
            "RELATIVE_BASE": now.datetime,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": str(getattr(tzinfo, "key", "UTC")),
            "TO_TIMEZONE": str(getattr(tzinfo, "key", "UTC")),
            "PREFER_DATES_FROM": "future",
        },
    )
    return arrow.get(dt).to(tzinfo) if dt else None


class ShortTime:
    compiled = SHORT_RE
    discord_fmt = DISCORD_TS_RE
    dt: datetime.datetime

    def __init__(self, argument: str, *, now: datetime.datetime | None = None, tzinfo: datetime.tzinfo = datetime.UTC):
        base = _as_arrow_now(now, tzinfo)
        parsed = _parse_short(argument, base) or _parse_discord_ts(argument, tzinfo)
        if parsed is None:
            raise commands.BadArgument("invalid time provided")
        self.dt = parsed.datetime

    @classmethod
    async def convert(cls, ctx: commands.Context[Parrot], argument: str) -> Self:
        tzinfo = datetime.UTC
        reminder = ctx.bot.reminder
        if reminder is not None:
            tzinfo = await reminder.get_tzinfo(ctx.author.id)
        return cls(argument, now=ctx.message.created_at, tzinfo=tzinfo)


class RelativeDelta(app_commands.Transformer, commands.Converter):
    @classmethod
    def __do_conversion(cls, argument: str) -> relativedelta:
        m = ShortTime.compiled.fullmatch(argument.strip())
        if m is None or not m.group(0):
            raise ValueError("invalid time provided")
        data = {k: int(v or 0) for k, v in m.groupdict().items()}
        return relativedelta(**data)

    async def convert(self, ctx: commands.Context[Parrot], argument: str) -> relativedelta:
        try:
            return self.__do_conversion(argument)
        except ValueError as e:
            raise commands.BadArgument(str(e)) from None

    async def transform(self, interaction, value: str) -> relativedelta:
        try:
            return self.__do_conversion(value)
        except ValueError as e:
            raise app_commands.AppCommandError(str(e)) from None


class HumanTime:
    def __init__(self, argument: str, *, now: datetime.datetime | None = None, tzinfo: datetime.tzinfo = datetime.UTC):
        base = _as_arrow_now(now, tzinfo)
        parsed = _parse_human(argument, base, tzinfo)
        if parsed is None:
            raise commands.BadArgument('invalid time provided, try e.g. "tomorrow" or "3 days"')
        self.dt = parsed.datetime
        self._past = parsed <= base

    @classmethod
    async def convert(cls, ctx: commands.Context[Parrot], argument: str) -> Self:
        tzinfo = datetime.UTC
        reminder = ctx.bot.reminder
        if reminder is not None:
            tzinfo = await reminder.get_tzinfo(ctx.author.id)
        return cls(argument, now=ctx.message.created_at, tzinfo=tzinfo)


class Time(HumanTime):
    def __init__(self, argument: str, *, now: datetime.datetime | None = None, tzinfo: datetime.tzinfo = datetime.UTC):
        try:
            s = ShortTime(argument, now=now, tzinfo=tzinfo)
        except commands.BadArgument:
            super().__init__(argument, now=now, tzinfo=tzinfo)
        else:
            self.dt = s.dt
            self._past = False


class FutureTime(Time):
    def __init__(self, argument: str, *, now: datetime.datetime | None = None, tzinfo: datetime.tzinfo = datetime.UTC):
        super().__init__(argument, now=now, tzinfo=tzinfo)
        if self._past:
            raise commands.BadArgument("this time is in the past")


class BadTimeTransform(app_commands.AppCommandError):
    pass


class TimeTransformer(app_commands.Transformer):
    async def transform(self, interaction, value: str) -> datetime.datetime:
        tzinfo = datetime.UTC
        reminder = interaction.client.get_cog("Reminder")
        if reminder is not None:
            tzinfo = await reminder.get_tzinfo(interaction.user.id)

        now = interaction.created_at.astimezone(tzinfo)
        try:
            short = ShortTime(value, now=now, tzinfo=tzinfo)
            return short.dt
        except commands.BadArgument:
            try:
                human = FutureTime(value, now=now, tzinfo=tzinfo)
                return human.dt
            except commands.BadArgument as e:
                raise BadTimeTransform(str(e)) from None


class FriendlyTimeResult:
    dt: datetime.datetime
    arg: str
    __slots__ = ("dt", "arg")

    def __init__(self, dt: datetime.datetime):
        self.dt = dt
        self.arg = ""

    async def ensure_constraints(self, ctx: commands.Context[Parrot], uft: UserFriendlyTime, now: datetime.datetime, remaining: str) -> None:
        if self.dt < now:
            raise commands.BadArgument("This time is in the past.")
        if not remaining:
            if uft.default is None:
                raise commands.BadArgument("Missing argument after the time.")
            remaining = uft.default
        if uft.converter is not None:
            self.arg = await uft.converter.convert(ctx, remaining)
        else:
            self.arg = remaining


class UserFriendlyTime(commands.Converter):
    def __init__(self, converter: type[commands.Converter] | commands.Converter | None = None, *, default: Any = None):
        if isinstance(converter, type) and issubclass(converter, commands.Converter):
            converter = converter()
        if converter is not None and not isinstance(converter, commands.Converter):
            raise TypeError("commands.Converter subclass necessary.")
        self.converter: commands.Converter = converter  # type: ignore
        self.default: Any = default

    async def convert(self, ctx: commands.Context[Parrot], argument: str) -> FriendlyTimeResult:
        now = ctx.message.created_at
        tzinfo = datetime.UTC
        reminder = ctx.bot.reminder
        if reminder is not None:
            tzinfo = await reminder.get_tzinfo(ctx.author.id)

        # 1) leading short-time
        m = ShortTime.compiled.match(argument)
        if m and m.group(0):
            data = {k: int(v or 0) for k, v in m.groupdict().items()}
            if any(data.values()):
                dt = arrow.get(now).to(tzinfo).shift(**data).datetime
                remaining = argument[m.end() :].strip()
                r = FriendlyTimeResult(dt)
                await r.ensure_constraints(ctx, self, now, remaining)
                return r

        # 2) leading discord timestamp
        m = ShortTime.discord_fmt.match(argument)
        if m:
            dt = arrow.get(int(m.group("ts"))).to(tzinfo).datetime
            remaining = argument[m.end() :].strip()
            r = FriendlyTimeResult(dt)
            await r.ensure_constraints(ctx, self, now, remaining)
            return r

        # 3) fallback natural language (whole argument as time)
        parsed = _parse_human(argument, arrow.get(now).to(tzinfo), tzinfo)
        if parsed is None:
            raise commands.BadArgument('Invalid time provided, try e.g. "tomorrow" or "3 days".')

        r = FriendlyTimeResult(parsed.datetime)
        await r.ensure_constraints(ctx, self, now, self.default if self.default is not None else "")
        return r


def human_timedelta(
    dt: datetime.datetime,
    *,
    source: datetime.datetime | None = None,
    accuracy: int | None = 3,
    brief: bool = False,
    suffix: bool = True,
) -> str:
    now = arrow.get(source or datetime.datetime.now(datetime.UTC))
    target = arrow.get(dt if dt.tzinfo else dt.replace(tzinfo=datetime.UTC))
    rel = relativedelta(target.datetime, now.datetime) if target >= now else relativedelta(now.datetime, target.datetime)

    attrs = [("year", "y"), ("month", "mo"), ("day", "d"), ("hour", "h"), ("minute", "m"), ("second", "s")]
    out: list[str] = []
    for attr, short in attrs:
        n = getattr(rel, f"{attr}s")
        if not n:
            continue
        if attr == "day" and rel.weeks:
            n -= rel.weeks * 7
            if rel.weeks:
                out.append(f"{rel.weeks}w" if brief else format(plural(rel.weeks), "week"))
        if n <= 0:
            continue
        out.append(f"{n}{short}" if brief else format(plural(n), attr))

    if accuracy is not None:
        out = out[:accuracy]
    if not out:
        return "now"

    text = " ".join(out) if brief else human_join(out, final="and")
    if suffix and target < now:
        text += " ago"
    return text
