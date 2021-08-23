from __future__ import annotations
from discord.ext import commands

__all__ = ("Context", )


class Context(commands.Context):
    """A custom implementation of commands.Context class."""
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
