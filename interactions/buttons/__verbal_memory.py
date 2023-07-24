from __future__ import annotations

import random
from typing import Optional

from english_words import get_english_words_set

import discord
from core import Context, Parrot

from .utils import BaseView


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
            return self.view.stop()

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
                await interaction.response.edit_message(embed=game.embed, view=self.view)
                return self.view.stop()

        if game.word not in game.seen:
            game.seen.append(game.word)

        game.word = game.choose_word()
        game.embed.title = game.word
        game.update_description(score_incr, lives_decr)
        return await interaction.response.edit_message(embed=game.embed, view=self.view)


class VerbalView(BaseView):
    def __init__(
        self,
        game: VerbalMemory,
        *,
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(timeout=timeout)

        self.game = game
        self.button_style = button_style

        self.add_item(VerbalButton(label="Seen", style=self.button_style))
        self.add_item(VerbalButton(label="New", style=self.button_style))
        self.add_item(VerbalButton(label="Cancel", style=discord.ButtonStyle.red))


class VerbalMemory:
    def __init__(self, word_set: Optional[list[str]] = None, sample_size: Optional[int] = 300) -> None:
        self.lives: int = 0
        self.embed: Optional[discord.Embed] = None

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

    def update_description(self, score_incr: bool = False, lives_decr: bool = False) -> None:
        assert self.embed
        s = "+" if score_incr else "•"
        l = "-" if lives_decr else "•"
        self.embed.description = f"```diff\n{s} Score | {self.score}\n{l} Lives | {self.lives}\n```"

    async def start(
        self,
        ctx: Context[Parrot],
        *,
        lives: int = 3,
        weights: tuple[float, float] = (0.7, 0.3),
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        timeout: Optional[float] = None,
    ) -> Optional[discord.Message]:
        self.weights = weights
        self.lives = lives
        self.embed = discord.Embed(
            title=self.word,
        )
        self.update_description()
        self.view = VerbalView(
            game=self,
            button_style=button_style,
            timeout=timeout,
        )
        self.message = await ctx.send(embed=self.embed, view=self.view)

        await self.view.wait()
        return self.message
