from __future__ import annotations

import asyncio
import random
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .utils import DEFAULT_COLOR, DiscordColor, Player

if TYPE_CHECKING:
    from core.bot import Parrot


class ReactionGame:
    """Reaction time test, reaction-based.

    Measures how quickly a player reacts to an emoji change.
    """

    def __init__(self, emoji: str = "🖱️") -> None:
        self.emoji = emoji

    async def wait_for_reaction(
        self,
        ctx: commands.Context[Parrot],
        *,
        timeout: float | None,
        start_time: float,
        reacted: set[int],
    ) -> tuple[Player, float]:

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return str(reaction.emoji) == self.emoji and reaction.message.id == self.message.id and user.id not in reacted and not user.bot

        _, user = await ctx.bot.wait_for("reaction_add", timeout=timeout, check=check)
        elapsed = time.perf_counter() - start_time

        return user, elapsed

    async def start(
        self,
        ctx: commands.Context[Parrot],
        *,
        timeout: float | None = None,
        embed_color: DiscordColor = DEFAULT_COLOR,
    ) -> discord.Message:
        embed = discord.Embed(
            title="Reaction Game",
            description=f"React with {self.emoji} when the embed is edited!",
            color=embed_color,
        )

        self.message = await ctx.reply(embed=embed)
        await self.message.add_reaction(self.emoji)

        pause = random.uniform(1.0, 5.0)
        await asyncio.sleep(pause)

        embed.description = f"React with {self.emoji} now!"
        await self.message.edit(embed=embed)

        results: list[str] = []
        reacted: set[int] = set()

        start_time = time.perf_counter()

        while not ctx.bot.is_closed():
            try:
                user, reaction_time = await self.wait_for_reaction(
                    ctx,
                    timeout=timeout,
                    start_time=start_time,
                    reacted=reacted,
                )
            except TimeoutError:
                break

            reacted.add(user.id)
            place = len(results) + 1
            results.append(f"**{place}.** {user.mention} — `{reaction_time:.2f}s`")

            embed.description = "\n".join(results)
            await self.message.edit(embed=embed)

        if not results:
            embed.description = "No one reacted in time!"
            await self.message.edit(embed=embed)

        return self.message
