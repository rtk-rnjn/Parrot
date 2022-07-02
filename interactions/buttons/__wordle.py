# https://github.com/Tom-the-Bomb/Discord-Games/blob/master/discord_games/wordle.py

from __future__ import annotations
import asyncio
from typing import Any, Optional, Union, List, Dict, Final, TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

import random
from io import BytesIO

import discord
from PIL import Image, ImageDraw, ImageFont

from utilities.converters import ToAsync
from core import Context

DiscordColor: TypeAlias = Union[discord.Color, int]
DEFAULT_COLOR: Final[discord.Color] = discord.Color(0x2F3136)

BORDER = 40
SQ = 100
SPACE = 10

WIDTH = BORDER * 2 + SQ * 5 + SPACE * 4
HEIGHT = BORDER * 2 + SQ * 6 + SPACE * 5

GRAY = (119, 123, 125)
ORANGE = (200, 179, 87)
GREEN = (105, 169, 99)
LGRAY = (198, 201, 205)


class Wordle:
    def __init__(self, *, text_size: int = 55) -> None:
        self.embed_color: Optional[DiscordColor] = None

        self._valid_words = tuple(open(r"extra/5_words.txt", "r").read().splitlines())
        self._text_size = text_size
        self._font = ImageFont.truetype(r"extra/HelveticaNeuBold.ttf", self._text_size)

        self.guesses: List[List[Dict[str, str]]] = []
        self.word: str = random.choice(self._valid_words)

    def parse_guess(self, guess: str) -> bool:
        self.guesses.append([])
        for ind, l in enumerate(guess):
            if l in self.word:
                color = GREEN if self.word[ind] == l else ORANGE
            else:
                color = GRAY
            self.guesses[-1].append({"letter": l, "color": color})

        return guess == self.word

    @ToAsync()
    def render_image(self) -> BytesIO:
        with Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255)) as img:
            cursor = ImageDraw.Draw(img)

            x = y = BORDER
            for i in range(6):
                for j in range(5):
                    try:
                        letter = self.guesses[i][j]
                        color = letter["color"]
                        act_letter = letter["letter"]
                    except (IndexError, KeyError):
                        cursor.rectangle((x, y, x + SQ, y + SQ), outline=LGRAY, width=4)
                    else:
                        cursor.rectangle((x, y, x + SQ, y + SQ), width=0, fill=color)
                        cursor.text(
                            (x + SQ / 2, y + SQ / 2),
                            act_letter.upper(),
                            font=self._font,
                            anchor="mm",
                            fill=(255, 255, 255),
                        )

                    x += SQ + SPACE
                x = BORDER
                y += SQ + SPACE

            buf = BytesIO()
            img.save(buf, "PNG")
        buf.seek(0)
        return buf

    async def start(
        self,
        ctx: Context,
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        **kwargs: Any,
    ) -> Optional[discord.Message]:

        self.embed_color = embed_color

        buf = await self.render_image()

        embed = discord.Embed(title="Wordle!", color=self.embed_color)
        embed.description = "`QUIT` to end the game"
        embed.set_image(url="attachment://wordle.png")

        message = await ctx.send(embed=embed, file=discord.File(buf, "wordle.png"))

        while True:

            def check(m):
                return (
                    len(m.content) == 5
                    and m.author == ctx.author
                    and m.channel == ctx.channel
                ) or (m.content.lower() == "quit")

            try:
                guess: discord.Message = await ctx.bot.wait_for(
                    "message", check=check, timeout=900
                )
            except asyncio.TimeoutError:
                return await ctx.send("You took too long to guess the word!")
            content = guess.content.lower()

            if content.upper() == "QUIT":
                return await ctx.send(f"Game over! You quit! Word was: {self.word}")

            if content not in self._valid_words:
                await ctx.send(
                    "That is not a valid word!",
                )
            else:
                won = self.parse_guess(content)
                buf = await self.render_image()

                await message.delete()

                embed = discord.Embed(
                    title="Wordle!",
                    color=self.embed_color,
                    description="`QUIT` to end the game",
                    timestamp=ctx.message.created_at,
                )
                embed.set_footer(text=f"{ctx.author}")
                embed.set_image(url="attachment://wordle.png")

                message = await ctx.send(
                    embed=embed, file=discord.File(buf, "wordle.png")
                )

                if won:
                    return await ctx.send("Game Over! You won!")
                if len(self.guesses) >= 6:
                    return await ctx.send(
                        f"Game Over! You lose, the word was: **{self.word}**"
                    )
