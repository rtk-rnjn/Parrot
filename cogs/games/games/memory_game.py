from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, ClassVar

import discord
from discord.ext import commands

from .utils import (
    DEFAULT_COLOR,
    BaseView,
    DiscordColor,
    chunk,
    double_wait,
    wait_for_delete,
)

if TYPE_CHECKING:
    from core import Parrot


class MemoryButton(discord.ui.Button["MemoryView"]):
    def __init__(self, emoji: str, *, style: discord.ButtonStyle, row: int = 0) -> None:
        self.value = emoji

        super().__init__(
            style=style,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        game = self.view.game

        if opened := self.view.opened:
            game.moves += 1
            assert game.embed is not None
            game.embed.set_field_at(0, name="\N{ZERO WIDTH SPACE}", value=f"Moves: `{game.moves}`")

            self.emoji = self.value
            self.disabled = True
            await interaction.response.edit_message(view=self.view)

            if opened.value != self.value:
                await asyncio.sleep(self.view.pause_time)

                opened.emoji = None
                opened.disabled = False

                self.emoji = None
                self.disabled = False
                self.view.opened = None
            else:
                self.view.opened = None

                if all(button.disabled for button in self.view.children if isinstance(button, discord.ui.Button)):
                    if interaction.message:
                        await interaction.message.edit(
                            content="Game Over, Congrats!",
                            view=self.view,
                        )
                    self.view.stop()
                    return

            if interaction.message:
                await interaction.message.edit(view=self.view, embed=game.embed)
        else:
            self.emoji = self.value
            self.view.opened = self
            self.disabled = True
            await interaction.response.edit_message(view=self.view)


class MemoryView(BaseView):
    board: list[list[str]]
    DEFAULT_ITEMS: ClassVar[list[str]] = [
        "\N{GRAPES}",
        "\N{WATERMELON}",
        "\N{TANGERINE}",
        "\N{LEMON}",
        "\N{PINEAPPLE}",
        "\N{RED APPLE}",
        "\N{PEACH}",
        "\N{STRAWBERRY}",
        "\N{TROPICAL DRINK}",
        "\N{KIWIFRUIT}",
        "\N{LEAFY GREEN}",
        "\N{MANGO}",
    ]

    def __init__(
        self,
        game: MemoryGame,
        items: list[str] | None = None,
        *,
        button_style: discord.ButtonStyle,
        pause_time: float,
        timeout: float | None = None,
    ) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        self.button_style = button_style
        self.pause_time = pause_time
        self.opened: MemoryButton | None = None

        if not items:
            items = self.DEFAULT_ITEMS[:]
        assert len(items) == 12

        items *= 2
        random.shuffle(items)
        random.shuffle(items)
        items.insert(12, None)  # type: ignore[arg-type]

        self.board = chunk(items, count=5)

        for i, row in enumerate(self.board):
            for item in row:
                button = MemoryButton(item, style=self.button_style, row=i)

                if not item:
                    button.disabled = True
                self.add_item(button)


class MemoryGame:
    """Memory card matching game, button-based.

    Flip pairs of emoji cards to find matches.
    Try to clear the board in as few moves as possible.
    """

    def __init__(self) -> None:
        self.embed_color: DiscordColor | None = None
        self.embed: discord.Embed | None = None
        self.moves: int = 0
        self.view: MemoryView
        self.message: discord.Message

    async def start(  # noqa: PLR0913
        self,
        ctx: commands.Context[Parrot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        items: list[str] | None = None,
        pause_time: float = 0.7,
        button_style: discord.ButtonStyle = discord.ButtonStyle.red,
        timeout: float | None = None,
    ) -> discord.Message:
        self.embed_color = embed_color
        self.embed = discord.Embed(
            description="**Memory Game**",
            color=self.embed_color,
        )
        self.embed.add_field(name="\N{ZERO WIDTH SPACE}", value="Moves: `0`")

        self.view = MemoryView(
            game=self,
            items=items,
            button_style=button_style,
            pause_time=pause_time,
            timeout=timeout,
        )
        self.message = await ctx.reply(embed=self.embed, view=self.view)
        self.view.message = self.message

        await double_wait(
            wait_for_delete(ctx, self.message),
            self.view.wait(),
        )
        return self.message
