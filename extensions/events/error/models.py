from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from core import Bot

type Context = commands.Context[Bot]

# Every handler has the same shape: pure, synchronous, always returns a response.
# `Any` lets each handler annotate the concrete error type it expects.
type ErrorHandler = Callable[[Context, commands.CommandError], ErrorResponse]


@dataclass(slots=True, frozen=True)
class ErrorResponse:
    title: str
    description: str
    reset_cooldown: bool = False
    delete_after: float | None = None
    should_raise: bool = False
    media_url: str | None = None
