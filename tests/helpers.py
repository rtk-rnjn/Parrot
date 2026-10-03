from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock

if TYPE_CHECKING:
    from discord import Interaction
    from discord.ext.commands import Context

    from core import Parrot

UTC = datetime.UTC
NOW = datetime.datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def make_ctx(reminder: Any = None, *, user_id: int = 42, created_at: datetime.datetime = NOW) -> Context[Parrot]:
    namespace = SimpleNamespace(
        bot=SimpleNamespace(reminder=reminder),
        author=SimpleNamespace(id=user_id),
        message=SimpleNamespace(created_at=created_at),
    )
    if TYPE_CHECKING:
        return cast(Context[Parrot], namespace)

    return namespace


def make_interaction(reminder: Any = None, *, user_id: int = 42, created_at: datetime.datetime = NOW) -> Interaction[Parrot]:
    namespace = SimpleNamespace(
        client=SimpleNamespace(reminder=reminder),
        user=SimpleNamespace(id=user_id),
        created_at=created_at,
    )
    if TYPE_CHECKING:
        return cast(Interaction[Parrot], namespace)

    return namespace


def reminder_with(tz: Any) -> SimpleNamespace:
    return SimpleNamespace(get_tzinfo=AsyncMock(return_value=tz))
