# -*- coding: utf-8 -*-

from __future__ import annotations

from discord.ext import commands
import discord

from typing import Optional

__all__ = ("Cog",)


class Cog(commands.Cog):
    app_commands: Optional[discord.app_commands.Group]
    description: str
    qualified_name: str

    """A custom implementation of commands.Cog class."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        return "{0.__class__.__name__}".format(self)
    
    def __repr__(self) -> str:
        return self.__str__()
