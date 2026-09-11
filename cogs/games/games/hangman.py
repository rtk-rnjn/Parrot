from __future__ import annotations

import random
import string
from typing import TYPE_CHECKING, Final

import discord
from discord.ext import commands
from english_words import get_english_words_set

from .utils import DEFAULT_COLOR, BaseView, DiscordColor
from .wordle import WordInputButton

if TYPE_CHECKING:
    from core import Parrot

BLANK: Final[str] = "  \N{ZERO WIDTH SPACE}"

STAGES: Final[tuple[str, ...]] = (
    """
            _________\t
            |/      |\t
            |      \N{DIZZY FACE}\t
            |      \\|/\t
            |       |\t
            |      / \\\t
         ___|___
            """,
    """
            _________\t
            |/      |\t
            |      \N{FROWNING FACE WITH OPEN MOUTH}\t
            |      \\|/\t
            |       |\t
            |      /\t
         ___|___
            """,
    """
            _________\t
            |/      |\t
            |      \N{FROWNING FACE WITH OPEN MOUTH}\t
            |      \\|/\t
            |       |\t
            |
         ___|___
            """,
    """
            --------\t
            |/     |\t
            |     \N{FROWNING FACE WITH OPEN MOUTH}\t
            |     \\|\t
            |      |\t
            |
         ___|___
            """,
    """
            _________\t
            |/      |\t
            |      \N{FROWNING FACE WITH OPEN MOUTH}\t
            |       |\t
            |       |\t
            |
         ___|___
            """,
    """
            _________\t
            |/      |\t
            |      \N{FROWNING FACE WITH OPEN MOUTH}\t
            |
            |
            |
         ___|___
            """,
    """
            _________\t
            |/      |\t
            |
            |
            |
            |
         ___|___
            """,
    """
            _________\t
            |/
            |
            |
            |
            |
         ___|___
            """,
    """
            ___      \t
            |/
            |
            |
            |
            |
         ___|___
            """,
)


class Hangman:
    """Hangman game, message-based.

    Guess letters to reveal a hidden word before
    running out of attempts. Displayed as ASCII art.
    """

    def __init__(self, word: str | None = None) -> None:
        self._alpha: list[str] = list(string.ascii_lowercase)
        self._all_words = tuple(
            get_english_words_set(
                ["web2"],
                alpha=True,
                lower=True,
            ),
        )

        if word:
            if not word.isalpha():
                raise ValueError("Word must be an alphabetical string")

            self.word = word
        else:
            self.word = self.get_word()

        self.letters: tuple[str, ...] = tuple(self.word)

        self.correct: list[str] = [r"\_" for _ in self.word]
        self.wrong_letters: list[str] = []

        self.embed: discord.Embed = discord.Embed(title="HANGMAN")
        self.message: discord.Message | None = None
        self._counter: int = 8

        self.game_over: bool = False

    def get_word(self) -> str:
        word = random.choice(self._all_words).lower()
        if len(word) == 1:
            word = self.get_word()
        return word

    def lives(self) -> str:
        return f"`{('\N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16}' * self._counter) or '\N{SKULL}'} ({self._counter})`"

    async def make_guess(self, guess: str) -> None:
        assert self.message is not None
        if guess == self.word:
            self.game_over = True
            self.embed.set_field_at(0, name="Word", value=self.word)
            await self.message.edit(content="**YOU WON**", embed=self.embed)

        elif guess in self.letters:
            self._alpha.remove(guess)
            matches = [a for a, b in enumerate(self.letters) if b == guess]

            for match in matches:
                self.correct[match] = guess

            self.embed.set_field_at(0, name="Word", value=f"{' '.join(self.correct)}")
            await self.message.edit(embed=self.embed)
        else:
            if len(guess) == 1:
                self._alpha.remove(guess)
                self.wrong_letters.append(guess)

            self._counter -= 1

            self.embed.set_field_at(
                1,
                name="Wrong letters",
                value=f"{', '.join(self.wrong_letters) or BLANK}",
            )
            self.embed.set_field_at(
                2,
                name="Lives left",
                value=self.lives(),
                inline=False,
            )
            self.embed.description = f"```\n{STAGES[self._counter]}\n```"
            await self.message.edit(embed=self.embed)

    async def check_win(self) -> bool:
        assert self.message is not None
        if self._counter == 0:
            self.game_over = True
            self.embed.set_field_at(0, name="Word", value=self.word)
            await self.message.edit(content="**YOU LOST**", embed=self.embed)

        elif r"\_" not in self.correct:
            self.game_over = True
            self.embed.set_field_at(0, name="Word", value=self.word)
            await self.message.edit(content="**YOU WON**", embed=self.embed)

        return self.game_over

    def initialize_embed(self) -> discord.Embed:
        self.embed.description = f"```\n{STAGES[self._counter]}\n```"
        self.embed.color = self.embed_color
        self.embed.add_field(name="Word", value=f"{' '.join(self.correct)}")

        wrong_letters = ", ".join(self.wrong_letters) or BLANK
        self.embed.add_field(name="Wrong letters", value=wrong_letters)
        self.embed.add_field(name="Lives left", value=self.lives(), inline=False)
        return self.embed

    async def start(
        self,
        ctx: commands.Context[Parrot],
        *,
        timeout: float | None = None,
        embed_color: DiscordColor = DEFAULT_COLOR,
        delete_after_guess: bool = False,
        **kwargs,
    ) -> discord.Message:
        self.player = ctx.author
        self.embed_color = embed_color
        embed = self.initialize_embed()

        self.message = await ctx.reply(embed=embed, **kwargs)

        while not ctx.bot.is_closed():

            def check(m: discord.Message) -> bool:
                if m.channel == ctx.channel and m.author == self.player:
                    return (len(m.content) == 1 and m.content.lower() in self._alpha) or (m.content.lower() == self.word)
                return False

            try:
                message: discord.Message = await ctx.bot.wait_for(
                    "message",
                    timeout=timeout,
                    check=check,
                )
            except TimeoutError:
                break

            await self.make_guess(message.content.lower())
            gameover = await self.check_win()

            if gameover:
                break

            if delete_after_guess:
                try:
                    await message.delete()
                except discord.DiscordException:
                    pass
        return self.message


class HangmanInput(discord.ui.Modal, title="Make a guess!"):
    def __init__(self, view: HangmanView) -> None:
        super().__init__()
        self.view = view

        self.word = discord.ui.TextInput(
            label="Input your guess",
            style=discord.TextStyle.short,
            required=True,
            min_length=1,
            max_length=len(self.view.game.word),
        )

        self.add_item(self.word)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        content = self.word.value.lower()
        game = self.view.game

        if len(content) == 1 and content not in game._alpha:
            await interaction.response.send_message(
                "This is not a valid letter to guess (or you've guessed it before)",
                ephemeral=True,
            )
            return

        elif len(content) > 1 and content not in game._all_words:
            await interaction.response.send_message(
                "This is not a valid word!",
                ephemeral=True,
            )
            return

        else:
            await game.make_guess(content)

            if await game.check_win():
                self.view.disable_all()
                await interaction.response.edit_message(view=self.view)
                self.view.stop()
            else:
                await interaction.response.defer()


class HangmanButton(WordInputButton):
    view: HangmanView

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        game = self.view.game
        if interaction.user != game.player:
            await interaction.response.send_message(
                "This isn't your game!",
                ephemeral=True,
            )
            return
        elif self.label == "Cancel":
            await interaction.response.send_message(
                f"Game Over! the word was: **{game.word}**",
            )
            assert interaction.message is not None
            await interaction.message.delete()
            self.view.stop()
        else:
            await interaction.response.send_modal(HangmanInput(self.view))


class HangmanView(BaseView):
    def __init__(self, game: BetaHangman, *, timeout: float | None) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        self.add_item(HangmanButton())
        self.add_item(HangmanButton(cancel_button=True))


class BetaHangman(Hangman):
    """Hangman game, button-based.

    Same as :class:`Hangman` but uses a modal for letter input.
    """

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: float | None = None,
        **kwargs,
    ) -> discord.Message:
        self.player = ctx.author
        self.embed_color = embed_color

        embed = self.initialize_embed()
        self.view = HangmanView(self, timeout=timeout)
        self.message = await ctx.reply(embed=embed, view=self.view, **kwargs)
        self.view.message = self.message

        await self.view.wait()
        return self.message
