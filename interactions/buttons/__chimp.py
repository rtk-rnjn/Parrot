from __future__ import annotations

import asyncio
import random
from typing import List, Optional

import discord
from core import Context, Parrot

from .utils import chunk


class ChimpButton(discord.ui.Button["ChimpView"]):
    def __init__(self, num: int, *, style: discord.ButtonStyle) -> None:
        self.value = num

        super().__init__(
            label=str(self.value or "\u200b"),
            style=style,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view
        game = self.view.game

        if not game.first_clicked:
            game.first_clicked = True
            self.view.update_view(
                style=self.view.button_style,
                highlight=game.highlight_tiles,
            )

        idx = self.view.children.index(self)
        if idx == game.coordinates[game.step]:
            self.label = str(self.value)
            self.style = discord.ButtonStyle.green
            game.step += 1

            for button in game.wrong_guesses:
                button.style = self.view.button_style

            if game.step == len(game.coordinates):
                self.view.disable_all()
                self.view.stop()
                return await interaction.response.edit_message(content="Congratulations, you won!", view=self.view)
            else:
                await interaction.response.edit_message(
                    content=f"Click the buttons in order! **[Lives: {game.lives}]**",
                    view=self.view,
                )
        else:
            game.lives -= 1

            if game.lives == 0:
                self.view.update_view(
                    style=self.view.button_style,
                    show=True,
                )
                self.view.disable_all()
                self.style = discord.ButtonStyle.red

                await interaction.response.edit_message(content="You Lose!", view=self.view)
                return self.view.stop()
            else:
                self.style = discord.ButtonStyle.red

                game.wrong_guesses.append(self)
                await interaction.response.edit_message(
                    content=f"Click the buttons in order! **[Lives: `{game.lives}`]**",
                    view=self.view,
                )


class ChimpView(discord.ui.View):
    def __init__(
        self,
        game: ChimpTest,
        *,
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.button_style = button_style
        self.game = game

        for row in chunk(self.game.grid, count=5):
            for item in row:
                button = ChimpButton(item, style=discord.ButtonStyle.gray)
                button.disabled = not item
                self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.game.message.author.id:
            await interaction.response.send_message(
                "You cannot play this game as you are not the author of the message.",
                ephemeral=True,
            )
            return False
        return True

    def disable_all(self) -> None:
        for button in self.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True

    async def on_timeout(self) -> None:
        return self.stop()

    def update_view(
        self,
        style: discord.ButtonStyle,
        *,
        show: bool = False,
        highlight: bool = True,
    ) -> None:
        for num, button in zip(self.game.grid, self.children):
            if isinstance(button, ChimpButton):
                if num and highlight and button.style != discord.ButtonStyle.green:
                    button.style = style
                button.label = str(button.value or "\u200b") if show else "\u200b"


class ChimpTest:
    """
    ChimpTest Memory Game
    """

    def __init__(self, count: int = 9) -> None:
        self.lives: int = 0
        self.initial_sleep: Optional[float] = None
        self.highlight_tiles: bool = True

        if count not in range(1, 26):
            raise ValueError(f"the count must be between 1 and 26, not {count}")
        self.count = count

        self.coordinates = []
        self.grid = [0] * 25
        for i in range(self.count):
            j = random.randrange(25)
            while self.grid[j] != 0:
                j = random.randrange(25)

            self.coordinates.append(j)
            self.grid[j] = i + 1

        self.step: int = 0
        self.first_clicked: bool = False
        self.wrong_guesses: List[ChimpButton] = []

    async def start(
        self,
        ctx: Context[Parrot],
        *,
        lives: int = 1,
        highlight_tiles: bool = True,
        initial_sleep: Optional[float] = None,
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        timeout: Optional[float] = None,
    ) -> discord.Message:
        self.lives = lives
        self.initial_sleep = initial_sleep
        self.highlight_tiles = highlight_tiles
        self.view = ChimpView(
            game=self,
            button_style=button_style,
            timeout=timeout,
        )
        self.message = await ctx.send(
            content="Click the buttons in order!",
            view=self.view,
        )

        if self.initial_sleep is not None:
            await asyncio.sleep(self.initial_sleep)
            self.first_clicked = True

            if not self.view.is_finished():
                self.view.update_view(
                    style=self.view.button_style,
                    highlight=self.highlight_tiles,
                )
                await self.message.edit(
                    content=f"Click the buttons in order! **[Lives: {self.lives}]**",
                    view=self.view,
                )

        await asyncio.wait(
            [
                ctx.bot.loop.create_task(self.view.wait()),
                ctx.bot.loop.create_task(ctx.wait_for_delete(self.message)),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        return self.message
