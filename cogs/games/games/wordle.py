from __future__ import annotations

import random
from io import BytesIO
from typing import TYPE_CHECKING, Final

import discord
from discord.ext import commands
from jishaku.functools import executor_function as executor
from PIL import Image, ImageDraw, ImageFont

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player

if TYPE_CHECKING:
    from core.bot import Parrot


BORDER: Final[int] = 40
SQ: Final[int] = 100
SPACE: Final[int] = 10

WIDTH: Final[int] = BORDER * 2 + SQ * 5 + SPACE * 4
HEIGHT: Final[int] = BORDER * 2 + SQ * 6 + SPACE * 5

GRAY: Final[tuple[int, int, int]] = (119, 123, 125)
ORANGE: Final[tuple[int, int, int]] = (200, 179, 87)
GREEN: Final[tuple[int, int, int]] = (105, 169, 99)
LGRAY: Final[tuple[int, int, int]] = (198, 201, 205)


class Guess:
    __slots__ = ("letter", "color")

    def __init__(self, letter: str, color: tuple[int, int, int]) -> None:
        self.letter = letter
        self.color = color


class Wordle:
    """Wordle game, message-based.

    Guess a five-letter word with color-coded feedback
    for each attempt.
    """

    word: str

    def __init__(self, word: str | None = None, *, text_size: int = 55) -> None:
        self.embed_color: DiscordColor | None = None

        with open("assets/words.txt") as f:
            self._valid_words = tuple(f.read().splitlines())
        self._text_size = text_size
        self._font = ImageFont.truetype("assets/HelveticaNeuBold.ttf", self._text_size)

        self.guesses: list[list[Guess | None]] = []

        if word:
            if len(word) != 5:
                raise ValueError("Word must be of length 5")

            if not word.isalpha():
                raise ValueError("Word must be an alphabetical string")

            self.word = word
        else:
            self.word = random.choice(self._valid_words)

    def parse_guess(self, guess: str) -> bool:
        assert (guess_len := len(guess)) == len(self.word)

        word: list[str | None] = list(self.word)
        curr_guess: list[Guess | None] = [None] * guess_len

        for i, letter in enumerate(guess):
            if word[i] == letter:
                word[i] = None
                curr_guess[i] = Guess(letter, GREEN)

        for i, letter in enumerate(guess):
            if word[i] is not None:
                curr_guess[i] = Guess(letter, ORANGE if letter in word else GRAY)

        self.guesses.append(curr_guess)
        return guess == self.word

    @executor
    def render_image(self) -> BytesIO:
        with Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255)) as img:
            cursor = ImageDraw.Draw(img)

            x = y = BORDER
            for i in range(6):
                for j in range(5):
                    try:
                        letter = self.guesses[i][j]
                        assert letter is not None
                        color = letter.color
                        literal_letter = letter.letter
                    except IndexError, KeyError:
                        cursor.rectangle((x, y, x + SQ, y + SQ), outline=LGRAY, width=4)
                    else:
                        cursor.rectangle((x, y, x + SQ, y + SQ), width=0, fill=color)
                        cursor.text(
                            (x + SQ / 2, y + SQ / 2),
                            literal_letter.upper(),
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
        ctx: commands.Context[Parrot],
        *,
        timeout: float | None = None,
        embed_color: DiscordColor = DEFAULT_COLOR,
    ) -> discord.Message:
        self.embed_color = embed_color

        buf = await self.render_image()

        embed = discord.Embed(title="Wordle!", color=self.embed_color)
        embed.set_image(url="attachment://wordle.png")
        embed.set_footer(text='Say "stop" to cancel the game!')

        self.message = await ctx.reply(embed=embed, file=discord.File(buf, "wordle.png"))

        while not ctx.bot.is_closed():

            def check(m: discord.Message) -> bool:
                return (len(m.content) == 5 or m.content.lower() == "stop") and m.author == ctx.author and m.channel == ctx.channel

            try:
                guess: discord.Message = await ctx.bot.wait_for("message", timeout=timeout, check=check)
            except TimeoutError:
                break

            content = guess.content.lower()

            if content == "stop":
                await ctx.reply(f"Game Over! cancelled, the word was: **{self.word}**")
                break

            if content != self.word and content not in self._valid_words:
                await ctx.reply("That is not a valid word!")
            else:
                won = self.parse_guess(content)
                buf = await self.render_image()

                await self.message.delete()

                embed = discord.Embed(title="Wordle!", color=self.embed_color)
                embed.set_image(url="attachment://wordle.png")

                self.message = await ctx.reply(embed=embed, file=discord.File(buf, "wordle.png"))

                if won:
                    await ctx.reply("Game Over! You won!")
                    break
                elif len(self.guesses) >= 6:
                    await ctx.reply(f"Game Over! You lose, the word was: **{self.word}**")
                    break

        return self.message


class WordInput(discord.ui.Modal, title="Word Input"):
    word = discord.ui.TextInput(
        label="Input your guess",
        style=discord.TextStyle.short,
        required=True,
        min_length=5,
        max_length=5,
    )

    def __init__(self, view: WordleView) -> None:
        super().__init__()
        self.wordle_view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        content = self.word.value.lower()
        game = self.wordle_view.game

        if content not in game._valid_words:
            await interaction.response.send_message("That is not a valid word!", ephemeral=True)
            return
        else:
            won = game.parse_guess(content)
            buf = await game.render_image()

            embed = discord.Embed(title="Wordle!", color=self.wordle_view.game.embed_color)
            embed.set_image(url="attachment://wordle.png")
            file = discord.File(buf, "wordle.png")

            lost = False
            if won:
                assert interaction.message is not None
                await interaction.message.reply("Game Over! You won!", mention_author=True)
            elif lost := len(game.guesses) >= 6:
                assert interaction.message is not None
                await interaction.message.reply(
                    f"Game Over! You lose, the word was: **{game.word}**",
                    mention_author=True,
                )

            if won or lost:
                self.wordle_view.disable_all()
                self.wordle_view.stop()

            await interaction.response.edit_message(embed=embed, attachments=[file], view=self.wordle_view)


class WordInputButton(discord.ui.Button["WordleView"]):
    def __init__(self, *, cancel_button: bool = False):
        super().__init__(
            label="Cancel" if cancel_button else "Make a guess!",
            style=discord.ButtonStyle.red if cancel_button else discord.ButtonStyle.blurple,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        game = self.view.game
        if interaction.user != game.player:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        if self.label == "Cancel":
            await interaction.response.send_message(f"Game Over! the word was: **{game.word}**")
            assert interaction.message is not None
            await interaction.message.delete()
            self.view.stop()
            return
        else:
            await interaction.response.send_modal(WordInput(self.view))


class WordleView(BaseView):
    def __init__(self, game: BetaWordle, *, timeout: float | None):
        super().__init__(timeout=timeout)

        self.game = game
        self.add_item(WordInputButton())
        self.add_item(WordInputButton(cancel_button=True))


class BetaWordle(Wordle):
    """Wordle game, button-based.

    Same as :class:`Wordle` but uses a modal for word input.
    """

    player: Player

    async def start(
        self,
        ctx: commands.Context[Parrot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: float | None = None,
    ) -> discord.Message:
        self.embed_color = embed_color
        self.player = ctx.author

        buf = await self.render_image()
        embed = discord.Embed(title="Wordle!", color=self.embed_color)
        embed.set_image(url="attachment://wordle.png")

        self.view = WordleView(self, timeout=timeout)
        self.message = await ctx.reply(
            embed=embed,
            file=discord.File(buf, "wordle.png"),
            view=self.view,
        )
        self.view.message = self.message
        await self.view.wait()
        return self.message
