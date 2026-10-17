from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from discord.ext import commands

from ..models import ErrorResponse
from . import arguments, general, permissions

if TYPE_CHECKING:
    from ..models import Context

type ErrorType = commands.CommandError

ErrorHandler = Callable[
    [commands.Context, ErrorType],
    ErrorResponse,
]

HANDLERS = (
    # permissions
    (commands.BotMissingPermissions, permissions.bot_missing_permissions),
    (commands.MissingPermissions, permissions.missing_permissions),
    (commands.MissingRole, permissions.missing_role),
    (commands.MissingAnyRole, permissions.missing_any_role),
    (commands.NSFWChannelRequired, permissions.nsfw_channel_required),
    # arguments
    (commands.BadArgument, arguments.bad_argument),
    # general
    (commands.CommandOnCooldown, general.cooldown),
    (commands.MissingRequiredArgument, general.syntax),
    (commands.BadUnionArgument, general.syntax),
    (commands.TooManyArguments, general.syntax),
    (commands.BadLiteralArgument, general.literal),
    (commands.MaxConcurrencyReached, general.concurrency),
    (commands.CheckAnyFailure, general.check_any),
    (commands.CheckFailure, general.check),
    (TimeoutError, general.timeout),
    (commands.InvalidEndOfQuotedStringError, general.quote),
    (commands.UnexpectedQuoteError, general.quote),
    (commands.DisabledCommand, general.disabled),
)


def resolve(ctx: Context, error: ErrorType) -> ErrorResponse:
    """Map an error to a response. Always returns one (falls back to a generic message)."""
    for error_type, handler in HANDLERS:
        if isinstance(error, error_type):
            return handler(ctx, error)  # pyright: ignore[reportArgumentType]
    return general.fallback(ctx, error)
