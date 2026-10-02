from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from core import human_join

from ..models import ErrorResponse
from ..utils import format_permissions

if TYPE_CHECKING:
    from ..models import Context


def bot_missing_permissions(_: Context, error: commands.BotMissingPermissions) -> ErrorResponse:
    fmt = format_permissions(error.missing_permissions)
    return ErrorResponse(
        title="Bot Missing Permissions",
        description=f"Please provide the following permission(s) to the bot.\nPermission(s) missing: {fmt}",
        reset_cooldown=True,
    )


def missing_permissions(_: Context, error: commands.MissingPermissions) -> ErrorResponse:
    fmt = format_permissions(error.missing_permissions)
    return ErrorResponse(
        title="Missing permissions",
        description=f"You need the following permission(s) to run the command.\nPermission(s) missing: {fmt}",
        reset_cooldown=True,
    )


def missing_role(_: Context, error: commands.MissingRole) -> ErrorResponse:
    return ErrorResponse(
        title="Missing Role",
        description=f"You need the role `{error.missing_role}` to run this command.",
        reset_cooldown=True,
    )


def missing_any_role(_: Context, error: commands.MissingAnyRole) -> ErrorResponse:
    fmt = human_join(list(error.missing_roles), delim="`, `", final="or")
    return ErrorResponse(
        title="Missing Role",
        description=f"You need any of the following role(s) to use the command.\nRole(s) missing: {fmt}",
        reset_cooldown=True,
    )


def nsfw_channel_required(_: Context, error: commands.NSFWChannelRequired) -> ErrorResponse:
    return ErrorResponse(
        title="NSFW Channel Required",
        description="This command will only run in an NSFW-marked channel. [View example](https://i.imgur.com/oe4iK5i.gif)",
        reset_cooldown=True,
    )
