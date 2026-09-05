from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord.ext.commands import Command

from core.constants import Day, Month

ONE_DAY = 86400  # faster response time if in seconds

__all__ = (
    "resolve_current_month",
    "resolve_current_day",
    "resolve_current_time",
    "human_months",
    "human_days",
    "human_time",
    "seasonal_task",
    "in_month_listener",
    "in_day_listener",
    "in_time_listener",
    "in_month_command",
    "in_day_command",
    "in_time_command",
    "in_month",
    "in_day",
    "in_time",
    "everyday_at",
)

def resolve_current_month() -> Month:
    return Month(discord.utils.utcnow().month)


def resolve_current_day() -> Day:
    return Day(discord.utils.utcnow().day)


def resolve_current_time(*, _time: datetime = None) -> datetime:
    return _time or discord.utils.utcnow()


def human_months(months: Iterable[Month]) -> str:
    """Build a comma separated list of `months`."""
    return ", ".join(str(m) for m in months)


def human_days(days: Iterable[Day]) -> str:
    """Build a comma separated list of `days`."""
    return ", ".join(str(m) for m in days)


def human_time(past: datetime, future: datetime) -> str:
    return f"{discord.utils.format_dt(past)} and {discord.utils.format_dt(future)}"


def seasonal_task(*allowed_months: Month, sleep_time: float | int = ONE_DAY) -> Callable:
    """Perform the decorated method periodically in `allowed_months`.
    This provides a convenience wrapper to avoid code repetition where some task shall
    perform an operation repeatedly in a constant interval, but only in specific months.
    The decorated function will be called once every `sleep_time` seconds while
    the current UTC month is in `allowed_months`. Sleep time defaults to 24 hours.
    The wrapped task is responsible for waiting for the bot to be ready, if necessary.
    """

    def decorator(task_body: Callable) -> Callable:
        @functools.wraps(task_body)
        async def decorated_task(*args, **kwargs) -> None:
            """Call `task_body` once every `sleep_time` seconds in `allowed_months`."""
            while True:
                current_month = resolve_current_month()

                if current_month in allowed_months:
                    await task_body(*args, **kwargs)

                await asyncio.sleep(sleep_time)

        return decorated_task

    return decorator


def in_month_listener(*allowed_months: Month) -> Callable:
    """Shield a listener from being invoked outside of `allowed_months`.
    The check is performed against current UTC month.
    """

    def decorator(listener: Callable) -> Callable:
        @functools.wraps(listener)
        async def guarded_listener(*args, **kwargs) -> None:
            """Wrapped listener will abort if not in allowed month."""
            current_month = resolve_current_month()

            if current_month in allowed_months:
                # Propagate return value although it should always be None
                return await listener(*args, **kwargs)

        return guarded_listener

    return decorator


def in_day_listener(*allowed_day: Day) -> Callable:
    """Shield a listener from being invoked outside of `allowed_day`.
    The check is performed against current UTC Day.
    """

    def decorator(listener: Callable) -> Callable:
        @functools.wraps(listener)
        async def guarded_listener(*args, **kwargs) -> None:
            """Wrapped listener will abort if not in allowed day."""
            current_day = resolve_current_day()

            if current_day in allowed_day:
                # Propagate return value although it should always be None
                return await listener(*args, **kwargs)

        return guarded_listener

    return decorator


def in_time_listener(*, past: datetime, future: datetime) -> Callable:
    """Shield a listener from being invoked outside of `allowed_time`.
    The check is performed against current UTC Day.
    """

    def decorator(listener: Callable) -> Callable:
        @functools.wraps(listener)
        async def guarded_listener(*args, **kwargs) -> None:
            """Wrapped listener will abort if not in allowed day."""
            current_time = discord.utils.utcnow()
            if past < current_time < future:
                # Propagate return value although it should always be None
                return await listener(*args, **kwargs)

        return guarded_listener

    return decorator


def in_month_command(*allowed_months: Month) -> Callable:
    """Check whether the command was invoked in one of `enabled_months`.
    Uses the current UTC month at the time of running the predicate.
    """

    async def predicate(ctx: commands.Context[commands.Bot]) -> bool:
        current_month = resolve_current_month()
        can_run = current_month in allowed_months

        if can_run:
            return True
        msg = f"Command can only be used in {human_months(allowed_months)}"
        raise commands.CheckFailure(msg)

    return commands.check(predicate)


def in_day_command(*allowed_day: Day) -> Callable:
    """Check whether the command was invoked in one of `enabled_days`.
    Uses the current UTC day at the time of running the predicate.
    """

    async def predicate(ctx: commands.Context[commands.Bot]) -> bool:
        current_day = resolve_current_month()
        can_run = current_day in allowed_day

        if can_run:
            return True
        msg = f"Command can only be used in {human_days(allowed_day)}"
        raise commands.CheckFailure(msg)

    return commands.check(predicate)


def in_time_command(*, past: datetime, future: datetime) -> Callable:
    async def predicate(ctx: commands.Context[commands.Bot]) -> bool:
        current_time = resolve_current_time()
        can_run = past < current_time < future

        if can_run:
            return True
        msg = f"Command can only be used during {human_time(past, future)}"
        raise commands.CheckFailure(msg)

    return commands.check(predicate)


def in_month(*allowed_months: Month) -> Callable:
    def decorator(callable_: Callable) -> Callable:
        # Functions decorated as commands are turned into instances of `Command`
        if isinstance(callable_, Command):
            actual_deco = in_month_command(*allowed_months)

        # D.py will assign this attribute when `callable_` is registered as a listener
        elif hasattr(callable_, "__cog_listener__"):
            actual_deco = in_month_listener(*allowed_months)

        # Otherwise we're unsure exactly what has been decorated
        # This happens before the bot starts, so let's just raise
        else:
            msg = f"Decorated object {callable_} is neither a command nor a listener"
            raise TypeError(msg)

        return actual_deco(callable_)

    return decorator


def in_day(*allowed_days: Day) -> Callable:
    def decorator(callable_: Callable) -> Callable:
        # Functions decorated as commands are turned into instances of `Command`
        if isinstance(callable_, Command):
            actual_deco = in_day_command(*allowed_days)

        # D.py will assign this attribute when `callable_` is registered as a listener
        elif hasattr(callable_, "__cog_listener__"):
            actual_deco = in_day_listener(*allowed_days)

        # Otherwise we're unsure exactly what has been decorated
        # This happens before the bot starts, so let's just raise
        else:
            msg = f"Decorated object {callable_} is neither a command nor a listener"
            raise TypeError(msg)

        return actual_deco(callable_)

    return decorator


def in_time(*, past: datetime, future: datetime) -> Callable:
    def decorator(callable_: Callable) -> Callable:
        # Functions decorated as commands are turned into instances of `Command`
        if isinstance(callable_, Command):
            actual_deco = in_time_command(past=past, future=future)

        # D.py will assign this attribute when `callable_` is registered as a listener
        elif hasattr(callable_, "__cog_listener__"):
            actual_deco = in_time_listener(past=past, future=future)

        # Otherwise we're unsure exactly what has been decorated
        # This happens before the bot starts, so let's just raise
        else:
            msg = f"Decorated object {callable_} is neither a command nor a listener"
            raise TypeError(msg)

        return actual_deco(callable_)

    return decorator


def everyday_at(*, hour: int = 0, minute: int = 0, second: int = 0) -> Callable:
    """Decorator to run a task every day at a specific time.
    The decorated task will be called at the specified time every day.
    """

    def decorator(task: Callable) -> Callable:
        async def wrapped_task(*args, **kwargs) -> None:
            """Call `task` every day at the specified time."""
            while True:
                now = resolve_current_time()
                target = now.replace(hour=hour, minute=minute, second=second)

                if now >= target:
                    target += timedelta(days=1)

                await asyncio.sleep((target - now).total_seconds())
                await task(*args, **kwargs)

        return wrapped_task

    return decorator
