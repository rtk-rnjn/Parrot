from __future__ import annotations

import asyncio
import functools
import random
from asyncio import Lock
from collections.abc import Container, Iterable
from functools import wraps
from typing import Callable, Optional, Union
from weakref import WeakValueDictionary
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import CheckFailure, Command
from discord import Colour, Embed

from .constants import ERROR_REPLIES, Month, Day
from .checks import in_whitelist_check

from core import Context

ONE_DAY = 24 * 60 * 60


def resolve_current_month() -> Month:
    return Month(datetime.utcnow().month)


def resolve_current_day() -> Day:
    return Day(datetime.utcnow().day)


def resolve_current_time(*, _time: datetime) -> datetime:
    return _time or datetime.utcnow()


def human_months(months: Iterable[Month]) -> str:
    """Build a comma separated list of `months`."""
    return ", ".join(str(m) for m in months)


def human_days(days: Iterable[Day]) -> str:
    """Build a comma separated list of `days`."""
    return ", ".join(str(m) for m in days)


def human_time(past: datetime, future: datetime) -> str:
    return f"{discord.utils.format_dt(past)} and {discord.utils.format_dt(future)}"


class InChannelCheckFailure(CheckFailure):
    """Check failure when the user runs a command in a non-whitelisted channel."""


class InMonthCheckFailure(CheckFailure):
    """Check failure for when a command is invoked outside of its allowed month."""


class InDayCheckFailure(CheckFailure):
    """Check failure for when a command is invoked outside of its allowed day."""


class InTimeCheckFaliure(CheckFailure):
    """Check failure for when a command is invoked outside of its allowed time."""


def seasonal_task(
    *allowed_months: Month, sleep_time: Union[float, int] = ONE_DAY
) -> Callable:
    """
    Perform the decorated method periodically in `allowed_months`.
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
    """
    Shield a listener from being invoked outside of `allowed_months`.
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
    """
    Shield a listener from being invoked outside of `allowed_day`.
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
    """
    Shield a listener from being invoked outside of `allowed_time`.
    The check is performed against current UTC Day.
    """

    def decorator(listener: Callable) -> Callable:
        @functools.wraps(listener)
        async def guarded_listener(*args, **kwargs) -> None:
            """Wrapped listener will abort if not in allowed day."""
            current_time = resolve_current_time()
            if past < current_time < future:
                # Propagate return value although it should always be None
                return await listener(*args, **kwargs)

        return guarded_listener

    return decorator


def in_month_command(*allowed_months: Month) -> Callable:
    """
    Check whether the command was invoked in one of `enabled_months`.
    Uses the current UTC month at the time of running the predicate.
    """

    async def predicate(ctx: Context) -> bool:
        current_month = resolve_current_month()
        can_run = current_month in allowed_months

        if can_run:
            return True
        raise InMonthCheckFailure(
            f"Command can only be used in {human_months(allowed_months)}"
        )

    return commands.check(predicate)


def in_day_command(*allowed_day: Day) -> Callable:
    """
    Check whether the command was invoked in one of `enabled_days`.
    Uses the current UTC day at the time of running the predicate.
    """

    async def predicate(ctx: Context) -> bool:
        current_day = resolve_current_month()
        can_run = current_day in allowed_day

        if can_run:
            return True
        raise InDayCheckFailure(
            f"Command can only be used in {human_days(allowed_day)}"
        )

    return commands.check(predicate)


def in_time_command(*, past: datetime, future: datetime) -> Callable:
    async def predicate(ctx: Context) -> bool:
        current_time = resolve_current_month()
        can_run = past < current_time < future

        if can_run:
            return True
        raise InTimeCheckFaliure(
            f"Command can only be used during {human_time(past, future)}"
        )

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
            raise TypeError(
                f"Decorated object {callable_} is neither a command nor a listener"
            )

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
            raise TypeError(
                f"Decorated object {callable_} is neither a command nor a listener"
            )

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
            raise TypeError(
                f"Decorated object {callable_} is neither a command nor a listener"
            )

        return actual_deco(callable_)

    return decorator


def with_role(*role_ids: int) -> Callable:
    """Check to see whether the invoking user has any of the roles specified in role_ids."""

    async def predicate(ctx: Context) -> bool:
        if not ctx.guild:  # Return False in a DM
            return False

        for role in ctx.author.roles:
            if role.id in role_ids:
                return True

        return False

    return commands.check(predicate)


def without_role(*role_ids: int) -> Callable:
    """Check whether the invoking user does not have all of the roles specified in role_ids."""

    async def predicate(ctx: Context) -> bool:
        if not ctx.guild:  # Return False in a DM
            return False

        author_roles = [role.id for role in ctx.author.roles]
        check = all(role not in author_roles for role in role_ids)

        return check

    return commands.check(predicate)


def whitelist_check(**default_kwargs: Container[int]) -> Callable[[Context], bool]:
    """
    Checks if a message is sent in a whitelisted context.
    All arguments from `in_whitelist_check` are supported, with the exception of "fail_silently".
    If `whitelist_override` is present, it is added to the global whitelist.
    """

    def predicate(ctx: Context) -> bool:
        kwargs = default_kwargs.copy()
        allow_dms = False

        # Update kwargs based on override
        if hasattr(ctx.command.callback, "override"):
            # Handle DM invocations
            allow_dms = ctx.command.callback.override_dm

            # Remove default kwargs if reset is True
            if ctx.command.callback.override_reset:
                kwargs = {}

            # Merge overwrites and defaults
            for arg in ctx.command.callback.override:
                default_value = kwargs.get(arg)
                new_value = ctx.command.callback.override[arg]

                # Skip values that don't need merging, or can't be merged
                if default_value is None or isinstance(arg, int):
                    kwargs[arg] = new_value

                # Merge containers
                elif isinstance(default_value, Container):
                    if isinstance(new_value, Container):
                        kwargs[arg] = (*default_value, *new_value)
                    else:
                        kwargs[arg] = new_value

        if ctx.guild is None:
            result = allow_dms
        else:
            result = in_whitelist_check(ctx, fail_silently=True, **kwargs)

        # Return if check passed
        if result:
            return result

        # Raise error if the check did not pass
        channels = set(kwargs.get("channels") or {})
        categories = kwargs.get("categories")

        # Only output override channels + community_bot_commands

        # Add all whitelisted category channels, but skip if we're in DMs
        if categories and ctx.guild is not None:
            for category_id in categories:
                category = ctx.guild.get_channel(category_id)
                if category is None:
                    continue

                channels.update(channel.id for channel in category.text_channels)

        if channels:
            channels_str = ", ".join(f"<#{c_id}>" for c_id in channels)
            message = f"Sorry, but you may only use this command within {channels_str}."
        else:
            message = "Sorry, but you may not use this command."

        raise InChannelCheckFailure(message)

    return predicate


def whitelist_override(
    bypass_defaults: bool = False, allow_dm: bool = False, **kwargs: Container[int]
) -> Callable:
    """
    Override global whitelist context, with the kwargs specified.
    All arguments from `in_whitelist_check` are supported, with the exception of `fail_silently`.
    Set `bypass_defaults` to True if you want to completely bypass global checks.
    Set `allow_dm` to True if you want to allow the command to be invoked from within direct messages.
    Note that you have to be careful with any references to the guild.
    This decorator has to go before (below) below the `command` decorator.
    """

    def inner(func: Callable) -> Callable:
        func.override = kwargs
        func.override_reset = bypass_defaults
        func.override_dm = allow_dm
        return func

    return inner


def locked() -> Optional[Callable]:
    """
    Allows the user to only run one instance of the decorated command at a time.
    Subsequent calls to the command from the same author are ignored until the command has completed invocation.
    This decorator has to go before (below) the `command` decorator.
    """

    def wrap(func: Callable) -> Optional[Callable]:
        func.__locks = WeakValueDictionary()

        @wraps(func)
        async def inner(
            self: Callable, ctx: Context, *args, **kwargs
        ) -> Optional[Callable]:
            lock = func.__locks.setdefault(ctx.author.id, Lock())
            if lock.locked():
                embed = Embed()
                embed.colour = Colour.red()

                embed.description = (
                    "You're already using this command. Please wait until "
                    "it is done before you use it again."
                )
                embed.title = random.choice(ERROR_REPLIES)
                await ctx.send(embed=embed)
                return

            async with func.__locks.setdefault(ctx.author.id, Lock()):
                return await func(self, ctx, *args, **kwargs)

        return inner

    return wrap
