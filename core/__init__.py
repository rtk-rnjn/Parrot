from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import Bot as Bot


def __getattr__(name: str):
    if name == "Bot":
        from .bot import Bot  # noqa: PLC0415

        return Bot

    from . import utils  # noqa: PLC0415

    try:
        return getattr(utils, name)
    except AttributeError:
        message = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(message) from None
