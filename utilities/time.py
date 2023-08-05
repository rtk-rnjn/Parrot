from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing_extensions import Self

import parsedatetime as pdt
from dateutil.relativedelta import relativedelta

from core import Context
from discord.ext import commands

# Monkey patch mins and secs into the units
units = pdt.pdtLocales["en_US"].units
units["minutes"].append("mins")
units["seconds"].append("secs")


class ShortTime:
    compiled = re.compile(
        """
           (?:(?P<years>[0-9])(?:years?|y))?                    # e.g. 2y
           (?:(?P<months>[0-9]{1,2})(?:months?|mon?))?          # e.g. 2months
           (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?               # e.g. 10w
           (?:(?P<days>[0-9]{1,5})(?:days?|d))?                 # e.g. 14d
           (?:(?P<hours>[0-9]{1,5})(?:hours?|hr?))?             # e.g. 12h
           (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m(?:in)?))?    # e.g. 10m
           (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s(?:ec)?))?    # e.g. 15s
        """,
        re.VERBOSE,
    )

    discord_fmt = re.compile(r"<t:(?P<ts>[0-9]+)(?:\:?[RFfDdTt])?>")

    dt: datetime.datetime

    def __init__(
        self,
        argument: str,
        *,
        now: datetime.datetime | None = None,
        tzinfo: datetime.tzinfo = datetime.timezone.utc,
    ) -> None:
        match = self.compiled.fullmatch(argument)
        if match is None or not match.group(0):
            match = self.discord_fmt.fullmatch(argument)
            if match is not None:
                self.dt = datetime.datetime.fromtimestamp(int(match.group("ts")), tz=datetime.timezone.utc)
                if tzinfo is not datetime.timezone.utc:
                    self.dt = self.dt.astimezone(tzinfo)
                return
            else:
                msg = "invalid time provided"
                raise commands.BadArgument(msg)

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        now = now or datetime.datetime.now(datetime.timezone.utc)
        self.dt = now + relativedelta(**data)
        if tzinfo is not datetime.timezone.utc:
            self.dt = self.dt.astimezone(tzinfo)

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        tzinfo = datetime.timezone.utc
        return cls(argument, now=ctx.message.created_at, tzinfo=tzinfo)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} dt={self.dt}>"

    def __str__(self) -> str:
        return self.dt.isoformat()


class HumanTime:
    calendar = pdt.Calendar(version=pdt.VERSION_CONTEXT_STYLE)

    def __init__(
        self,
        argument: str,
        *,
        now: datetime.datetime | None = None,
        tzinfo: datetime.tzinfo = datetime.timezone.utc,
    ) -> None:
        now = now or datetime.datetime.now(tzinfo)
        dt, status = self.calendar.parseDT(argument, sourceTime=now, tzinfo=None)
        if not status.hasDateOrTime:
            msg = 'invalid time provided, try e.g. "tomorrow" or "3 days"'
            raise commands.BadArgument(msg)

        if not status.hasTime:
            # replace it with the current time
            dt = dt.replace(
                hour=now.hour,
                minute=now.minute,
                second=now.second,
                microsecond=now.microsecond,
            )

        self.dt: datetime.datetime = dt.replace(tzinfo=tzinfo)
        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)
        self._past: bool = self.dt < now

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        tzinfo = datetime.timezone.utc
        return cls(argument, now=ctx.message.created_at, tzinfo=tzinfo)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} dt={self.dt}>"

    def __str__(self) -> str:
        return self.dt.isoformat()


class Time(HumanTime):
    def __init__(
        self,
        argument: str,
        *,
        now: datetime.datetime | None = None,
        tzinfo: datetime.tzinfo = datetime.timezone.utc,
    ) -> None:
        try:
            o = ShortTime(argument, now=now, tzinfo=tzinfo)
        except Exception:
            super().__init__(argument, now=now, tzinfo=tzinfo)
        else:
            self.dt = o.dt
            self._past = False


class FutureTime(Time):
    def __init__(
        self,
        argument: str,
        *,
        now: datetime.datetime | None = None,
        tzinfo: datetime.tzinfo = datetime.timezone.utc,
    ) -> None:
        super().__init__(argument, now=now, tzinfo=tzinfo)

        if self._past:
            msg = "this time is in the past"
            raise commands.BadArgument(msg)


class FriendlyTimeResult:
    dt: datetime.datetime
    arg: str

    __slots__ = ("dt", "arg")

    def __init__(self, dt: datetime.datetime) -> None:
        self.dt = dt
        self.arg = ""

    async def ensure_constraints(
        self,
        ctx: Context,
        uft: UserFriendlyTime,
        now: datetime.datetime,
        remaining: str,
    ) -> None:
        if self.dt < now:
            msg = "This time is in the past."
            raise commands.BadArgument(msg)

        if not remaining:
            if uft.default is None:
                msg = "Missing argument after the time."
                raise commands.BadArgument(msg)
            remaining = uft.default

        if uft.converter is not None:
            self.arg = await uft.converter.convert(ctx, remaining)
        else:
            self.arg = remaining


class UserFriendlyTime(commands.Converter):
    """That way quotes aren't absolutely necessary."""

    def __init__(
        self,
        converter: type[commands.Converter] | commands.Converter | None = None,
        *,
        default: Any = None,
    ) -> None:
        if isinstance(converter, type) and issubclass(converter, commands.Converter):
            converter = converter()

        if converter is not None and not isinstance(converter, commands.Converter):
            msg = "commands.Converter subclass necessary."
            raise TypeError(msg)

        self.converter: commands.Converter = converter  # type: ignore  # It doesn't understand this narrowing
        self.default: Any = default

    async def convert(self, ctx: Context, argument: str) -> FriendlyTimeResult:
        calendar = HumanTime.calendar
        regex = ShortTime.compiled
        now = ctx.message.created_at

        tzinfo = datetime.timezone.utc

        match = regex.match(argument)
        if match is not None and match.group(0):
            data = {k: int(v) for k, v in match.groupdict(default=0).items()}
            remaining = argument[match.end() :].strip()
            dt = now + relativedelta(**data)
            result = FriendlyTimeResult(dt.astimezone(tzinfo))
            await result.ensure_constraints(ctx, self, now, remaining)
            return result

        if match is None or not match.group(0):
            match = ShortTime.discord_fmt.match(argument)
            if match is not None:
                result = FriendlyTimeResult(
                    datetime.datetime.fromtimestamp(int(match.group("ts")), tz=datetime.timezone.utc).astimezone(tzinfo),
                )
                remaining = argument[match.end() :].strip()
                await result.ensure_constraints(ctx, self, now, remaining)
                return result

        # apparently nlp does not like "from now"
        # it likes "from x" in other cases though so let me handle the 'now' case
        if argument.endswith("from now"):
            argument = argument[:-8].strip()

        if argument[:2] == "me" and argument[:6] in ("me to ", "me in ", "me at "):
            argument = argument[6:]

        # Have to adjust the timezone so pdt knows how to handle things like "tomorrow at 6pm" in an aware way
        now = now.astimezone(tzinfo)
        elements = calendar.nlp(argument, sourceTime=now)
        if elements is None or len(elements) == 0:
            msg = 'Invalid time provided, try e.g. "tomorrow" or "3 days".'
            raise commands.BadArgument(msg)

        # handle the following cases:
        # "date time" foo
        # date time foo
        # foo date time

        # first the first two cases:
        dt, status, begin, end, dt_string = elements[0]

        if not status.hasDateOrTime:
            msg = 'Invalid time provided, try e.g. "tomorrow" or "3 days".'
            raise commands.BadArgument(msg)

        if begin not in (0, 1) and end != len(argument):
            msg = "Time is either in an inappropriate location, which must be either at the end or beginning of your input, or I just flat out did not understand what you meant. Sorry."
            raise commands.BadArgument(
                msg,
            )

        if not status.hasTime:
            # replace it with the current time
            dt = dt.replace(
                hour=now.hour,
                minute=now.minute,
                second=now.second,
                microsecond=now.microsecond,
            )

        # if midnight is provided, just default to next day
        if status.accuracy == pdt.pdtContext.ACU_HALFDAY:
            dt = dt.replace(day=now.day + 1)

        result = FriendlyTimeResult(dt.replace(tzinfo=tzinfo))
        remaining = ""

        if begin in (0, 1):
            if begin == 1:
                # check if it's quoted:
                if argument[0] != '"':
                    msg = "Expected quote before time input..."
                    raise commands.BadArgument(msg)

                if end >= len(argument) or argument[end] != '"':
                    msg = "If the time is quoted, you must unquote it."
                    raise commands.BadArgument(msg)

                remaining = argument[end + 1 :].lstrip(" ,.!")
            else:
                remaining = argument[end:].lstrip(" ,.!")
        elif len(argument) == end:
            remaining = argument[:begin].strip()

        await result.ensure_constraints(ctx, self, now, remaining)
        return result
