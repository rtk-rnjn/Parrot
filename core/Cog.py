from __future__ import annotations

from typing import Any, Optional

import discord
from discord.ext import commands

__all__ = ("Cog",)


class Cog(commands.Cog):
    """A custom implementation of commands.Cog class."""

    app_commands: Optional[discord.app_commands.Group]
    description: str
    qualified_name: str
    ON_TESTING: bool = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.display_name: str = self.qualified_name

    def __str__(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return self.__str__()
