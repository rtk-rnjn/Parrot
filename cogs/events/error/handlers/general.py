from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ..models import ErrorResponse

if TYPE_CHECKING:
    from ..models import Context


def cooldown(_: Context, error: commands.CommandOnCooldown) -> ErrorResponse:
    retry_at = discord.utils.utcnow() + timedelta(seconds=error.retry_after)
    return ErrorResponse(
        title="Command On Cooldown",
        description=f"You are on command cooldown, please retry **{discord.utils.format_dt(retry_at, 'R')}**",
        delete_after=error.retry_after,
    )


def syntax(ctx: Context, _: commands.CommandError) -> ErrorResponse:
    command = ctx.command
    assert command is not None

    aliases = f"|{'|'.join(command.aliases)}" if command.aliases else ""
    usage = f"{ctx.clean_prefix}{command.qualified_name}{aliases} {command.signature}"
    return ErrorResponse(
        title="Invalid Syntax",
        description=f"Please use proper syntax.\n`{usage}`",
        reset_cooldown=True,
    )


def literal(_: Context, error: commands.BadLiteralArgument) -> ErrorResponse:
    literals = "`, `".join(str(value) for value in error.literals)
    return ErrorResponse(
        title="Invalid Literal(s)",
        description=f"Please use proper Literals. Literal should be any one of the following: `{literals}`",
    )


def concurrency(_: Context, __: commands.MaxConcurrencyReached) -> ErrorResponse:
    return ErrorResponse(
        title="Max Concurrency Reached",
        description="This command is already running in this server/channel by you. You have to wait for it to finish",
    )


def check_any(ctx: Context, error: commands.CheckAnyFailure) -> ErrorResponse:
    description = " or\n".join(str(exc).format(ctx=ctx) for exc in error.errors)
    return ErrorResponse(title="Unexpected Error", description=description, reset_cooldown=True)


def check(_: Context, __: commands.CheckFailure) -> ErrorResponse:
    return ErrorResponse(
        title="Unexpected Error",
        description="You don't have the required permissions to use this command.",
        reset_cooldown=True,
    )


def timeout(_: Context, __: TimeoutError) -> ErrorResponse:
    return ErrorResponse(title="Timeout Error", description="Command took too long to respond")


def quote(_: Context, error: commands.CommandError) -> ErrorResponse:
    if isinstance(error, commands.InvalidEndOfQuotedStringError):
        return ErrorResponse(
            title="Invalid End Of Quoted String Error",
            description="Invalid end of quoted string. Expected space after closing quotation mark. Did you forget to close the quotation mark?",
        )
    return ErrorResponse(
        title="Unexpected Quote Error",
        description="Unexpected quote mark. Did you forget to close the quotation mark?",
    )


def disabled(_: Context, __: commands.DisabledCommand) -> ErrorResponse:
    return ErrorResponse(
        title="Disabled Command",
        description="This command is disabled in this server, ask your server admin to enable it.",
    )


def fallback(ctx: Context, error: Exception) -> ErrorResponse:
    command = ctx.command
    assert command is not None

    return ErrorResponse(
        title="Well this is embarrassing!",
        description=f"For some reason **{command.qualified_name}** is not working. If possible report this error.\n-# {error}",
        should_raise=True,
    )
