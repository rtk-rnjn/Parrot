from __future__ import annotations

import asyncio
import random
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from rapidfuzz import fuzz

from .utils import DEFAULT_COLOR, DiscordColor, Player

if TYPE_CHECKING:
    from core.bot import Parrot


with open("assets/random_sentences.txt", encoding="utf-8") as file:
    random_sentences = [line.strip() for line in file]


class TypingTest:
    """Typing speed test.

    Measures how quickly players type a randomly generated sentence while
    also reporting their typing accuracy.
    """

    def __init__(self) -> None:
        self.sentence = random.choice(random_sentences)

    async def wait_for_message(
        self,
        ctx: commands.Context[Parrot],
        *,
        start_time: float,
        completed: set[int],
        required_accuracy: float = 50.0,
    ) -> tuple[Player, float, float]:

        def check(message: discord.Message) -> bool:
            return (
                message.channel.id == self.message.channel.id
                and message.author.id not in completed
                and not message.author.bot
                and fuzz.ratio(self.sentence, message.content) >= required_accuracy
            )

        message = await ctx.bot.wait_for(
            "message",
            check=check,
        )

        elapsed = time.perf_counter() - start_time
        accuracy = fuzz.ratio(self.sentence, message.content)

        return message.author, elapsed, accuracy

    def _add_hidden_space(self, text: str) -> str:
        """Adds N random hidden spaces to ``text``, where N is its length.

        The hidden space is U+200B (ZERO WIDTH SPACE). If ``text`` is empty,
        it is returned unchanged.
        """
        if not text:
            return text

        positions = sorted(random.randrange(len(text) + 1) for _ in range(len(text)))

        result: list[str] = []
        previous = 0

        for position in positions:
            result.append(text[previous:position])
            result.append("\u200b")
            previous = position

        result.append(text[previous:])
        return "".join(result)

    async def start(
        self,
        ctx: commands.Context[Parrot],
        *,
        timeout: float | None = 60.0,
        embed_color: DiscordColor = DEFAULT_COLOR,
    ) -> discord.Message:
        embed = discord.Embed(
            title="Typing Test",
            description=f"Type the following sentence as accurately as possible:\n```css\n{self._add_hidden_space(self.sentence)}\n```",
            color=embed_color,
        )

        self.message = await ctx.reply(embed=embed)

        results: list[str] = []
        completed: set[int] = set()
        start_time = time.perf_counter()

        try:
            async with asyncio.timeout(timeout):
                while not ctx.bot.is_closed():
                    user, elapsed, accuracy = await self.wait_for_message(
                        ctx,
                        start_time=start_time,
                        completed=completed,
                    )

                    completed.add(user.id)

                    # Characters typed per minute, based on the submitted text.
                    cpm = len(self.sentence) / elapsed * 60

                    place = len(results) + 1
                    results.append(
                        f"**{place}.** {user.mention} — `{elapsed:.2f}s` · `{accuracy:.1f}%` · `{cpm:.0f} CPM`",
                    )

                    embed.description = embed.description + "\n" + "\n".join(results)  # type: ignore[operator]
                    await self.message.edit(embed=embed)

        except TimeoutError:
            if not results:
                embed.description = "No one completed the typing test in time!"
                await self.message.edit(embed=embed)

            await self.message.add_reaction("\N{HOURGLASS}")

        return self.message
