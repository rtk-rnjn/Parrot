from __future__ import annotations

from typing import Any

import discord
from discord.ext import commands

__all__ = ("Cog",)


class Cog(commands.Cog):
    """A custom implementation of commands.Cog class."""

    app_commands: discord.app_commands.Group | None
    description: str
    qualified_name: str
    ON_TESTING: bool = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.display_name: str = self.qualified_name

    def __str__(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"<Cog name={self.qualified_name} commands={len(self.__cog_commands__) + len(self.__cog_app_commands__)} listners={len(self.__cog_listeners__)}>"
