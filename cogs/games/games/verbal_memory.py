from __future__ import annotations

import random

import discord
from discord.ext import commands
from english_words import get_english_words_set

from .utils import DEFAULT_COLOR, BaseView, DiscordColor


class VerbalButton(discord.ui.Button["VerbalView"]):
    def __init__(self, label: str, style: discord.ButtonStyle) -> None:
        super().__init__(
            label=label,
            style=style,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view
        game = self.view.game
        assert game.embed

        score_incr = False
        lives_decr = False

        if self.label == "Cancel" and interaction.message:
            await interaction.message.delete()
            self.view.stop()
            return

        if self.label == "Seen" and game.word in game.seen or self.label == "New" and game.word not in game.seen:
            game.score += 1
            score_incr = True
        else:
            game.lives -= 1
            lives_decr = True
            game.update_description(score_incr, lives_decr)

            if game.lives == 0:
                game.embed.title = "You Lost!"
                self.view.disable_all()
                await interaction.response.edit_message(
                    embed=game.embed,
                    view=self.view,
                )
                self.view.stop()
                return

        if game.word not in game.seen:
            game.seen.append(game.word)

        game.word = game.choose_word()
        game.embed.title = game.word
        game.update_description(score_incr, lives_decr)
        await interaction.response.edit_message(embed=game.embed, view=self.view)


class VerbalView(BaseView):
    def __init__(
        self,
        game: VerbalMemory,
        *,
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        timeout: float | None = None,
    ) -> None:
        super().__init__(timeout=timeout)

        self.game = game
        self.button_style = button_style

        self.add_item(VerbalButton(label="Seen", style=self.button_style))
        self.add_item(VerbalButton(label="New", style=self.button_style))
        self.add_item(VerbalButton(label="Cancel", style=discord.ButtonStyle.red))


class VerbalMemory:
    """Verbal memory test, button-based.

    Words are shown one at a time \N{EM DASH} indicate whether
    each word is new or was already seen.
    """

    def __init__(
        self,
        word_set: list[str] | None = None,
        sample_size: int | None = 300,
    ) -> None:
        self.lives: int = 0
        self.embed: discord.Embed | None = None

        english_words = list(
            get_english_words_set(
                ["web2"],
                alpha=True,
                lower=True,
            ),
        )

        if sample_size:
            self.word_set = word_set or random.choices(
                english_words,
                k=sample_size,
            )
        else:
            self.word_set = word_set or english_words

        assert self.word_set

        self.score: int = 0
        self.seen: list[str] = []
        self.word = self.choose_word()

    def choose_word(self) -> str:
        new = random.choice(self.word_set)
        if self.seen:
            seen = random.choice(self.seen)
            word = random.choices([new, seen], weights=self.weights)[0]
        else:
            word = new
        if word in self.word_set:
            self.word_set.remove(word)
        return word

    def update_description(
        self,
        score_incr: bool = False,
        lives_decr: bool = False,
    ) -> None:
        assert self.embed
        s = "+" if score_incr else "\N{BULLET}"
        label = "-" if lives_decr else "\N{BULLET}"
        self.embed.description = f"```diff\n{s} Score | {self.score}\n{label} Lives | {self.lives}\n```"

    async def start(  # noqa: PLR0913
        self,
        ctx: commands.Context[commands.Bot],
        *,
        lives: int = 3,
        weights: tuple[float, float] = (0.7, 0.3),
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: float | None = None,
    ) -> discord.Message:
        self.weights = weights
        self.lives = lives
        self.embed = discord.Embed(
            title=self.word,
            color=embed_color,
        )
        self.update_description()
        self.view = VerbalView(
            game=self,
            button_style=button_style,
            timeout=timeout,
        )
        self.message = await ctx.reply(embed=self.embed, view=self.view)
        self.view.message = self.message

        await self.view.wait()
        return self.message
