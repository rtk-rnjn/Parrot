from __future__ import annotations
from discord.ext import commands
import functools

__all__ = ("Context", )


class Context(commands.Context):
    """A custom implementation of commands.Context class."""
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

    def with_type(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            context = args[0] if isinstance(args[0], commands.Context) else args[1]
            async with context.typing():
                await func(*args, **kwargs)
        return wrapped