from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from discord.ext import commands

from ..models import ErrorResponse
from ..utils import Named, find_closest

if TYPE_CHECKING:
    from ..models import Context

type Pool = Callable[[Context], Sequence[Named]]


def _members(ctx: Context) -> Sequence[Named]:
    return ctx.guild.members if ctx.guild else []


def _channels(ctx: Context) -> Sequence[Named]:
    return [*ctx.guild.text_channels, *ctx.guild.voice_channels] if ctx.guild else []


def _roles(ctx: Context) -> Sequence[Named]:
    return ctx.guild.roles if ctx.guild else []


def _emojis(ctx: Context) -> Sequence[Named]:
    return ctx.guild.emojis if ctx.guild else []


@dataclass(slots=True, frozen=True)
class _ArgumentSpecification:
    title: str
    description: str
    pool: Pool | None = None  # candidates for the "Did you mean" hint


_DEFAULT_TITLE = "Bad Argument"

# First match wins.
_SPECS: tuple[tuple[type[commands.BadArgument], _ArgumentSpecification], ...] = (
    (
        commands.MessageNotFound,
        _ArgumentSpecification("Message Not Found", "Message ID/Link you provided is either invalid or deleted"),
    ),
    (
        commands.MemberNotFound,
        _ArgumentSpecification(
            "Member Not Found",
            "Member ID/Mention/Name you provided is invalid or bot can not see that Member",
            _members,
        ),
    ),
    (
        commands.UserNotFound,
        _ArgumentSpecification("User Not Found", "User ID/Mention/Name you provided is invalid or bot can not see that User"),
    ),
    (
        commands.ChannelNotFound,
        _ArgumentSpecification(
            "Channel Not Found",
            "Channel ID/Mention/Name you provided is invalid or bot can not see that Channel",
            _channels,
        ),
    ),
    (
        commands.RoleNotFound,
        _ArgumentSpecification(
            "Role Not Found",
            "Role ID/Mention/Name you provided is invalid or bot can not see that Role",
            _roles,
        ),
    ),
    (
        commands.EmojiNotFound,
        _ArgumentSpecification(
            "Emoji Not Found",
            "Emoji ID/Name you provided is invalid or bot can not see that Emoji",
            _emojis,
        ),
    ),
)


def _resolve_spec(error: commands.BadArgument) -> _ArgumentSpecification:
    if isinstance(error, commands.RangeError):
        return _ArgumentSpecification(
            "Value Out Of Range",
            f"Value you provided is out of range. Expected a value between {error.minimum} and {error.maximum}",
        )
    for error_type, spec in _SPECS:
        if isinstance(error, error_type):
            return spec
    return _ArgumentSpecification(_DEFAULT_TITLE, str(error))


def _with_hint(error: commands.BadArgument, ctx: Context, spec: _ArgumentSpecification) -> str:
    argument = getattr(error, "argument", None)
    if spec.pool is None or not isinstance(argument, str):
        return spec.description

    match = find_closest(argument, spec.pool(ctx))
    if match is None:
        return spec.description
    return f"{spec.description}\nDid you mean: `{match.name}`?\n-# Confidence: {match.score}%"


def bad_argument(ctx: Context, error: commands.BadArgument) -> ErrorResponse:
    spec = _resolve_spec(error)
    return ErrorResponse(
        title=spec.title,
        description=_with_hint(error, ctx, spec),
        reset_cooldown=True,
    )
