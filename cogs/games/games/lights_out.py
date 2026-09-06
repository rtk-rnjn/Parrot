from __future__ import annotations

import random
from typing import TYPE_CHECKING, Final, Literal

import discord
from discord.ext import commands

from .number_slider import SlideView
from .utils import DEFAULT_COLOR, DiscordColor, Player, chunk, double_wait, wait_for_delete

if TYPE_CHECKING:
    from core.bot import Parrot

BULB = "\N{ELECTRIC LIGHT BULB}"

Board = list[list[Literal[BULB] | None]]


class LightsOutButton(discord.ui.Button["LightsOutView"]):
    def __init__(
        self,
        emoji: str | None,
        *,
        style: discord.ButtonStyle,
        row: int,
        col: int,
    ) -> None:
        super().__init__(
            emoji=emoji,
            style=style,
            row=row,
        )

        self.col = col

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        game = self.view.game

        if interaction.user != game.player:
            await interaction.response.send_message(
                "This is not your game!",
                ephemeral=True,
            )
            return
        else:
            assert self.row is not None
            row, col = self.row, self.col

            beside_item = game.beside_item(row, col)
            game.toggle(row, col)

            for i, j in beside_item:
                game.toggle(i, j)

            self.view.update_board(clear=True)

            game.moves += 1
            game.embed.set_field_at(0, name="\N{ZERO WIDTH SPACE}", value=f"Moves: `{game.moves}`")

            if game.tiles == game.completed:
                self.view.disable_all()
                self.view.stop()
                game.embed.description = "**Congrats! You won!**"

            await interaction.response.edit_message(embed=game.embed, view=self.view)


class LightsOutView(SlideView):
    game: LightsOut

    def __init__(self, game: LightsOut, *, timeout: float | None) -> None:
        super().__init__(game, timeout=timeout)  # type: ignore[arg-type]

    def update_board(self, *, clear: bool = False) -> None:
        if clear:
            idx = 0
            for _, row in enumerate(self.game.tiles):
                for _, tile in enumerate(row):
                    button = self.children[idx]
                    button.emoji = tile  # type: ignore[attr-defined]
                    button.label = "\N{ZERO WIDTH SPACE}"  # type: ignore[attr-defined]
                    button.style = self.game.button_style  # type: ignore[attr-defined]
                    idx += 1
        else:
            for i, row in enumerate(self.game.tiles):
                for j, tile in enumerate(row):
                    button = LightsOutButton(
                        emoji=tile,
                        style=self.game.button_style,
                        row=i,
                        col=j,
                    )
                    self.add_item(button)


class LightsOut:
    """Lights Out puzzle, button-based.

    Toggle lights on a grid \N{EM DASH} each toggle flips adjacent tiles too.
    Goal is to turn all lights off.
    """

    def __init__(self, count: Literal[1, 2, 3, 4, 5] = 4) -> None:
        if count not in range(1, 6):
            raise ValueError("Count must be an integer between 1 and 5")

        self.moves: int = 0
        self.count = count

        self.completed: Final[Board] = [[None] * self.count for _ in range(self.count)]
        self.tiles: Board = []

        self.player: Player | None = None
        self.button_style: discord.ButtonStyle = discord.ButtonStyle.green
        self.view: LightsOutView
        self.embed: discord.Embed
        self.message: discord.Message

    def toggle(self, row: int, col: int) -> None:
        self.tiles[row][col] = BULB if self.tiles[row][col] is None else None

    def beside_item(self, row: int, col: int) -> list[tuple[int, int]]:
        beside = [
            (row - 1, col),
            (row, col - 1),
            (row + 1, col),
            (row, col + 1),
        ]

        data = [(i, j) for i, j in beside if i in range(self.count) and j in range(self.count)]
        return data

    async def start(
        self,
        ctx: commands.Context[Parrot],
        *,
        button_style: discord.ButtonStyle = discord.ButtonStyle.green,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: float | None = None,
    ) -> discord.Message:
        self.button_style = button_style
        self.player = ctx.author

        flat_tiles = random.choices((None, BULB), k=self.count**2)
        self.tiles = chunk(flat_tiles, count=self.count)

        self.view = LightsOutView(self, timeout=timeout)
        self.embed = discord.Embed(
            description="Turn off all the tiles!",
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
