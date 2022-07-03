# -*- coding: utf-8 -*-

from __future__ import annotations

from discord.ext import commands
import discord

from typing import Any, Optional

__all__ = ("Cog",)


class Cog(commands.Cog):
    """A custom implementation of commands.Cog class."""

    app_commands: Optional[discord.app_commands.Group]
    description: str
    qualified_name: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        return "{0.__class__.__name__}".format(self)

    def __repr__(self) -> str:
        return self.__str__()
