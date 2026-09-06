from __future__ import annotations

import random
from copy import deepcopy
from typing import TYPE_CHECKING, Literal

import discord
from discord.ext import commands

from .utils import (
    DEFAULT_COLOR,
    BaseView,
    DiscordColor,
    Player,
    chunk,
    double_wait,
    wait_for_delete,
)

if TYPE_CHECKING:
    from core.bot import Parrot

Board = list[list[int | None]]


class SlideButton(discord.ui.Button["SlideView"]):
    def __init__(self, label: str, *, style: discord.ButtonStyle, row: int) -> None:
        super().__init__(
            label=label,
            style=style,
            row=row,
        )

        if label == "\N{ZERO WIDTH SPACE}":
            self.disabled = True

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        assert self.label is not None
        game = self.view.game

        if interaction.user != game.player:
            await interaction.response.send_message(
                "This is not your game!",
                ephemeral=True,
            )
            return
        else:
            num = int(self.label)

            if num not in game.beside_blank():
                await interaction.response.defer()
                return
            else:
                pressed = game.get_item(num)
                blank = game.get_item()

                game.swap(pressed, blank)

                self.view.update_board(clear=True)

                game.moves += 1
                game.embed.set_field_at(
                    0,
                    name="\N{ZERO WIDTH SPACE}",
                    value=f"Moves: `{game.moves}`",
                )

                if game.numbers == game.completed:
                    self.view.disable_all()
                    self.view.stop()
                    game.embed.description = "**Congrats! You won!**"

                await interaction.response.edit_message(
                    embed=game.embed,
                    view=self.view,
                )


class SlideView(BaseView):
    def __init__(self, game: NumberSlider, *, timeout: float | None) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        self.update_board()

    def update_board(self, *, clear: bool = False) -> None:
        if clear:
            idx = 0
            for i, row in enumerate(self.game.numbers):
                for j, number in enumerate(row):
                    button = self.children[idx]
                    button.label = str(number) if number else "\N{ZERO WIDTH SPACE}"  # type: ignore[attr-defined]
                    button.disabled = not number  # type: ignore[attr-defined]
                    button.style = (  # type: ignore[attr-defined]
                        self.game.correct_style if number == self.game.completed[i][j] else self.game.wrong_style
                    )
                    idx += 1
        else:
            for i, row in enumerate(self.game.numbers):
                for j, number in enumerate(row):
                    if number == self.game.completed[i][j]:
                        style = self.game.correct_style
                    else:
                        style = self.game.wrong_style

                    button = SlideButton(
                        label=str(number) if number else "\N{ZERO WIDTH SPACE}",
                        style=style,
                        row=i,
                    )
                    self.add_item(button)


class NumberSlider:
    """Number slider puzzle, button-based.

    Rearrange numbered tiles into order by sliding
    them into the empty space.
    """

    def __init__(self, count: Literal[1, 2, 3, 4, 5] = 4) -> None:
        if count not in range(1, 6):
            raise ValueError("Count must be an integer between 1 and 5")

        self.all_numbers = list(range(1, count**2))

        self.player: Player | None = None

        self.moves: int = 0
        self.count = count
        self.numbers: Board = []
        self.completed: Board = []

        self.wrong_style: discord.ButtonStyle = discord.ButtonStyle.gray
        self.correct_style: discord.ButtonStyle = discord.ButtonStyle.green
        self.view: SlideView
        self.embed: discord.Embed
        self.message: discord.Message

    def get_item(self, obj: int | None = None) -> tuple[int, int]:
        return next((x, y) for x, row in enumerate(self.numbers) for y, item in enumerate(row) if item == obj)

    def beside_blank(self) -> list[int | None]:
        nx, ny = self.get_item()

        beside_item = [
            (nx - 1, ny),
            (nx, ny - 1),
            (nx + 1, ny),
            (nx, ny + 1),
        ]

        data = [self.numbers[i][j] for i, j in beside_item if i in range(self.count) and j in range(self.count)]
        return data

    def swap(self, pressed: tuple[int, int], blank: tuple[int, int]) -> None:
        ix, iy = pressed
        nx, ny = blank

        self.numbers[nx][ny], self.numbers[ix][iy] = (
            self.numbers[ix][iy],
            self.numbers[nx][ny],
        )

    def shuffle(self, count: int) -> None:
        blank = self.get_item()

        for _ in range(count):
            neighbors = self.beside_blank()
            try:
                row, col = blank
                neighbors.remove(self.numbers[row][col])
            except ValueError:
                pass
            move = random.choice(neighbors)
            self.swap(self.get_item(move), blank)

            blank = self.get_item()

    async def start(
        self,
        ctx: commands.Context[Parrot],
        *,
        wrong_style: discord.ButtonStyle = discord.ButtonStyle.gray,
        correct_style: discord.ButtonStyle = discord.ButtonStyle.green,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: float | None = None,
    ) -> discord.Message:
        self.player = ctx.author
        self.wrong_style = wrong_style
        self.correct_style = correct_style

        self.completed = chunk(self.all_numbers + [None], count=self.count)

        self.numbers = deepcopy(self.completed)
        self.shuffle(self.count**6)

        self.view = SlideView(self, timeout=timeout)
        self.embed = discord.Embed(
            description="Slide the tiles back in ascending order!",
            color=embed_color,
        )
        self.embed.add_field(name="\N{ZERO WIDTH SPACE}", value="Moves: `0`")

        self.message = await ctx.reply(embed=self.embed, view=self.view)
        self.view.message = self.message

        await double_wait(
            wait_for_delete(ctx, self.message),
            self.view.wait(),
        )
        return self.message
