from __future__ import annotations

import json
import random
from collections.abc import Iterable
from typing import TYPE_CHECKING

from discord.ext import commands
from discord.ext.commands import Converter
from rapidfuzz import fuzz

from .utils import SNAKE_RESOURCES

if TYPE_CHECKING:
    from core import Parrot

FIRST_EMOJI = "\u23ee"  # [:track_previous:]
LEFT_EMOJI = "\u2b05"  # [:arrow_left:]
RIGHT_EMOJI = "\u27a1"  # [:arrow_right:]
LAST_EMOJI = "\u23ed"  # [:track_next:]
DELETE_EMOJI = "\N{WASTEBASKET}"  # [:trashcan:]

PAGINATION_EMOJI = (FIRST_EMOJI, LEFT_EMOJI, RIGHT_EMOJI, LAST_EMOJI, DELETE_EMOJI)


class Snake(Converter):
    """Snake converter for the Snakes Cog."""

    snakes = None
    special_cases = None

    async def convert(self, ctx: commands.Context[Parrot], name: str) -> str:
        """Convert the input snake name to the closest matching Snake object."""
        await self.build_list()
        name = name.lower()

        if name == "python":
            return "Python (programming language)"

        def get_potential(iterable: Iterable[str], *, threshold: int = 80) -> list[str]:
            nonlocal name
            potential = []

            for item in iterable:
                original, current_item = item, item.lower()

                if name == current_item:
                    return [original]

                a, b = fuzz.ratio(name, current_item), fuzz.partial_ratio(name, current_item)
                if a >= threshold or b >= threshold:
                    potential.append(original)

            return potential

        # Handle special cases
        if self.special_cases and name.lower() in self.special_cases:
            return self.special_cases.get(name.lower(), name.lower())

        names = {snake["name"]: snake["scientific"] for snake in self.snakes or []}
        all_names = names.keys() | names.values()

        name = await ctx.bot.disambiguate(ctx, matches=get_potential(all_names), ephemeral=True)
        return names.get(name, name)

    @classmethod
    async def build_list(cls) -> None:
        """Build list of snakes from the static snake resources."""
        # Get all the snakes
        if cls.snakes is None:
            cls.snakes = json.loads((SNAKE_RESOURCES / "snake_names.json").read_text("utf8"))
        # Get the special cases
        if cls.special_cases is None:
            special_cases = json.loads((SNAKE_RESOURCES / "special_snakes.json").read_text("utf8"))
            cls.special_cases = {snake["name"].lower(): snake for snake in special_cases}

    @classmethod
    async def random(cls) -> str:
        """Get a random Snake from the loaded resources.
        This is stupid. We should find a way to somehow get the global session into a global context,
        so I can get it from here.
        """
        await cls.build_list()
        assert cls.snakes is not None, "Snakes list is not built yet."

        names = [snake["scientific"] for snake in cls.snakes]
        return random.choice(names)
