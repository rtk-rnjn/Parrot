from __future__ import annotations

import asyncio
import random
import time
from typing import TYPE_CHECKING, ClassVar, TypeVar

import discord
from core import Context, Parrot

if TYPE_CHECKING:
    from typing import TypeAlias

    from typing_extensions import ParamSpec

    DiscordColor: TypeAlias = discord.Color | int

    P = ParamSpec("P")
    T = TypeVar("T")


from .utils import DEFAULT_COLOR, BaseView, chunk, double_wait, wait_for_delete


class MemoryButton(discord.ui.Button["MemoryView"]):
    def __init__(self, emoji: str, *, style: discord.ButtonStyle, row: int = 0) -> None:
        self.value = emoji

        super().__init__(
            label="\u200b",
            style=style,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None

        game = self.view.game

        if opened := self.view.opened:
            game.moves += 1
            game.embed.set_field_at(0, name="\u200b", value=f"Moves: `{game.moves}`")

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
                    await interaction.message.edit(content="Game Over, Congrats!", view=self.view)
                    await self.update_to_db()
                    return self.view.stop()

            if interaction.message:
                await interaction.message.edit(view=self.view, embed=game.embed)
                return
        else:
            self.emoji = self.value
            self.view.opened = self
            self.disabled = True
            return await interaction.response.edit_message(view=self.view)

    async def update_to_db(self):
        assert self.view is not None

        time_taken = time.perf_counter() - self.view.ini

        bot: Parrot = self.view.ctx.bot
        col = bot.game_collections

        await col.update_one(
            {
                "_id": self.view.ctx.author.id,
                "game_memory_test_time": {"$gt": time_taken},
            },
            {
                "$set": {"game_memory_test_time": time_taken},
                "$inc": {"game_memory_test_played": 1},
            },
        )


class MemoryView(BaseView):
    board: list[list[str]]
    DEFAULT_ITEMS: ClassVar[list[str]] = [
        "\N{KIWIFRUIT}",
        "\N{STRAWBERRY}",
        "\N{TROPICAL DRINK}",
        "\N{LEMON}",
        "\N{MANGO}",
        "\N{RED APPLE}",
        "\N{TANGERINE}",
        "\N{PINEAPPLE}",
        "\N{PEACH}",
        "\N{GRAPES}",
        "\N{WATERMELON}",
        "\N{LEAFY GREEN}",
    ]

    def __init__(
        self,
        game: MemoryGame,
        items: list[str],
        *,
        button_style: discord.ButtonStyle,
        pause_time: float,
        ctx: Context,
        timeout: float | None = None,
    ) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        self.button_style = button_style
        self.pause_time = pause_time
        self.opened: MemoryButton | None = None
        self.ctx = ctx

        if not items:
            items = self.DEFAULT_ITEMS[:]
        assert len(items) == 12

        items *= 2
        random.shuffle(items)
        random.shuffle(items)
        items.insert(12, None)

        self.board = chunk(items, count=5)
        self.ini = time.perf_counter()

        for i, row in enumerate(self.board):
            for item in row:
                button = MemoryButton(item, style=self.button_style, row=i)

                if not item:
                    button.disabled = True
                self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You can't interact with this game!", ephemeral=True)
            return False
        return True


class MemoryGame:
    """Memory Game."""

    def __init__(self) -> None:
        self.embed_color: DiscordColor | None = None
        self.embed: discord.Embed | None = None
        self.moves: int = 0

    async def start(
        self,
        ctx: Context[Parrot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        items: list[str] = None,
        pause_time: float = 0.7,
        button_style: discord.ButtonStyle = discord.ButtonStyle.gray,
        timeout: float | None = None,
    ) -> discord.Message | None:
        if items is None:
            items = []
        self.embed_color = embed_color
        self.embed = discord.Embed(description="**Memory Game**", color=self.embed_color)
        self.embed.add_field(name="\u200b", value="Moves: `0`")

        self.view = MemoryView(
            game=self,
            items=items,
            button_style=button_style,
            pause_time=pause_time,
            timeout=timeout,
            ctx=ctx,
        )
        self.message = await ctx.send(embed=self.embed, view=self.view)

        await double_wait(
            wait_for_delete(ctx, self.message),
            self.view.wait(),
        )
        return self.message
