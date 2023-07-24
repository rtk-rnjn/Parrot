# https://github.com/Tom-the-Bomb/Discord-Games/blob/master/discord_games/wordle.py

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from typing import TypeAlias

import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

import discord
from core import Context, Parrot
from utilities.converters import ToAsync

from .utils import DEFAULT_COLOR, BaseView

DiscordColor: TypeAlias = Union[discord.Color, int]


BORDER = 40
SQ = 100
SPACE = 10

WIDTH = BORDER * 2 + SQ * 5 + SPACE * 4
HEIGHT = BORDER * 2 + SQ * 6 + SPACE * 5

GRAY = (119, 123, 125)
ORANGE = (200, 179, 87)
GREEN = (105, 169, 99)
LGRAY = (198, 201, 205)

with open(r"extra/5_words.txt", encoding="utf-8", errors="ignore") as f:
    VALID_WORDS = tuple(f.read().splitlines())


class Wordle:
    def __init__(self, *, text_size: int = 55) -> None:
        self.embed_color: Optional[DiscordColor] = None

        self._valid_words = VALID_WORDS
        self._text_size = text_size
        self._font = ImageFont.truetype(r"extra/HelveticaNeuBold.ttf", self._text_size)

        self.guesses: list[list[dict[str, str]]] = []
        self.word: str = random.choice(self._valid_words)

    def parse_guess(self, guess: str) -> bool:
        self.guesses.append([])
        for ind, letter in enumerate(guess):
            if letter in self.word:
                color = GREEN if self.word[ind] == letter else ORANGE
            else:
                color = GRAY
            self.guesses[-1].append({"letter": letter, "color": color})

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

        message: discord.Message = await ctx.send(embed=embed, file=discord.File(buf, "wordle.png"))

        while True:

            def check(m: discord.Message) -> bool:
                return (len(m.content) == 5 and m.author == ctx.author and m.channel == ctx.channel) or (
                    m.content.lower() == "quit"
                )

            try:
                guess: discord.Message = await ctx.wait_for("message", check=check, timeout=900)
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

                message = await ctx.send(embed=embed, file=discord.File(buf, "wordle.png"))

                if won:
                    await ctx.database_game_update("wordle", win=True)
                    return await ctx.send("Game Over! You won!")
                if len(self.guesses) > 5:
                    await ctx.database_game_update("wordle", loss=True)
                    return await ctx.send(f"Game Over! You lose, the word was: **{self.word}**")


class WordInput(discord.ui.Modal, title="Word Input"):
    word: discord.ui.TextInput = discord.ui.TextInput(
        label="Input your guess",
        style=discord.TextStyle.short,
        required=True,
        min_length=5,
        max_length=5,
    )

    def __init__(self, view: WordleView) -> None:
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert interaction.message is not None

        content = str(self.word.value).lower()
        game = self.view.game

        if content not in game._valid_words:
            return await interaction.response.send_message("That is not a valid word!", ephemeral=True)
        won = game.parse_guess(content)
        buf = await game.render_image()

        embed = discord.Embed(title="Wordle!", color=self.view.game.embed_color)
        embed.set_image(url="attachment://wordle.png")
        file = discord.File(buf, "wordle.png")

        if won:
            await interaction.message.reply("Game Over! You won!", mention_author=True)
        elif lost := len(game.guesses) >= 6:
            await interaction.message.reply(
                f"Game Over! You lose, the word was: **{game.word}**",
                mention_author=True,
            )

        if won or lost:
            self.view.disable_all()
            self.view.stop()

        return await interaction.response.edit_message(embed=embed, attachments=[file], view=self.view)


class WordInputButton(discord.ui.Button["WordleView"]):
    def __init__(self, *, cancel_button: bool = False) -> None:
        super().__init__(
            label="Cancel" if cancel_button else "Make a guess!",
            style=discord.ButtonStyle.red if cancel_button else discord.ButtonStyle.blurple,
        )
        self.view.game: WordleView

    async def callback(self, interaction: discord.Interaction) -> None:
        assert interaction.message is not None

        game = self.view.game
        if interaction.user != game.player:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        if self.label != "Cancel":
            return await interaction.response.send_modal(WordInput(self.view))
        await interaction.response.send_message(f"Game Over! the word was: **{game.word}**")
        await interaction.message.delete()
        self.view.stop()
        return


class WordleView(BaseView):
    def __init__(self, game: BetaWordle, *, timeout: float) -> None:
        super().__init__(timeout=timeout)

        self.game = game
        self.add_item(WordInputButton())
        self.add_item(WordInputButton(cancel_button=True))


class BetaWordle(Wordle):
    player: discord.User
    """
    Wordle(buttons) game
    """

    async def start(
        self,
        ctx: Context[Parrot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: Optional[float] = None,
    ) -> discord.Message:
        """Starts the wordle(buttons) game.

        Parameters
        ----------
        ctx : Context
            the context of the invokation command
        embed_color : DiscordColor, optional
            the color of the game embed, by default DEFAULT_COLOR
        timeout : Optional[float], optional
            the timeout for the view, by default None

        Returns
        -------
        discord.Message
            returns the game message.
        """
        self.embed_color = embed_color
        self.player = ctx.author

        buf = await self.render_image()
        embed = discord.Embed(title="Wordle!", color=self.embed_color)
        embed.set_image(url="attachment://wordle.png")

        self.view = WordleView(self, timeout=timeout)
        self.message = await ctx.send(
            embed=embed,
            file=discord.File(buf, "wordle.png"),
            view=self.view,
        )
        await self.view.wait()
        return self.message
