from __future__ import annotations

import re
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from core import Context

__all__ = (
    "Cell",
    "Column",
    "Row",
)


class Column(commands.Converter[int]):
    """Returns the index of a column."""

    @classmethod
    def from_char(cls, argument: str) -> int:
        return ord(argument.upper()) - ord("A")

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> int:
        if len(argument) != 1 or not argument.isalpha():
            msg = "Column must be a single letter."
            raise commands.BadArgument(msg)
        return cls.from_char(argument)


class Row(commands.Converter[int]):
    """Returns the index of a row."""

    @classmethod
    def from_char(cls, argument: str) -> int:
        return int(argument) - 1

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> int:
        if not argument.isdigit():
            msg = "Row must be a number."
            raise commands.BadArgument(msg)
        return cls.from_char(argument)


class Cell(commands.Converter[tuple[int, int]]):
    """Returns the index of a row and column."""

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> tuple[int, int]:
        if re.match(r"[A-z]:?\d+", argument):
            return (Row.from_char(argument[1:]), Column.from_char(argument[0]))

        msg = "Could not determine cell!"
        raise commands.BadArgument(msg)
