from __future__ import annotations

import asyncio
import random
import time
from typing import TYPE_CHECKING, Any, ClassVar, Coroutine, Final, List, Optional, Set, Tuple, TypeVar, Union

from pymongo.collection import Collection

import discord
from core import Context, Parrot

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, TypeAlias

    DiscordColor: TypeAlias = Union[discord.Color, int]

    P = ParamSpec("P")
    T = TypeVar("T")

    A = TypeVar("A", bool)
    B = TypeVar("B", bool)

DEFAULT_COLOR: Final[discord.Color] = discord.Color(0x2F3136)


def chunk(iterable: List[int], *, count: int) -> List[List[int]]:
    return [iterable[i : i + count] for i in range(0, len(iterable), count)]


async def wait_for_delete(
    ctx: Context[Parrot],
    message: discord.Message,
    *,
    emoji: str = "\N{BLACK SQUARE FOR STOP}",
    _bot: Optional[Parrot] = None,
    user: Optional[Union[discord.User, Tuple[discord.User, ...]]] = None,
    timeout: Optional[float] = None,
) -> bool:
    if not user:
        user = ctx.author
    try:
        await message.add_reaction(emoji)
    except discord.DiscordException:
        pass

    def check(reaction: discord.Reaction, _user: discord.User) -> bool:
        if reaction.emoji == emoji and reaction.message == message:
            return _user in user if isinstance(user, tuple) else _user == user
        return False

    bot: Parrot = _bot or ctx.bot
    try:
        await bot.wait_for("reaction_add", timeout=timeout, check=check)
    except asyncio.TimeoutError:
        return False
    else:
        await message.delete()
        return True


async def double_wait(
    task1: Coroutine[Any, Any, A],
    task2: Coroutine[Any, Any, B],
    *,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> Tuple[Set[asyncio.Task[Union[A, B]]], Set[asyncio.Task[Union[A, B]]],]:
    if not loop:
        loop = asyncio.get_event_loop()

    return await asyncio.wait(
        [
            loop.create_task(task1),
            loop.create_task(task2),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )


class BaseView(discord.ui.View):
    def disable_all(self) -> None:
        for button in self.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True

    async def on_timeout(self) -> None:
        return self.stop()


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

            return await interaction.message.edit(view=self.view, embed=game.embed)
        else:
            self.emoji = self.value
            self.view.opened = self
            self.disabled = True
            return await interaction.response.edit_message(view=self.view)

    async def update_to_db(self):
        time_taken = time.perf_counter() - self.view.ini

        bot: Parrot = self.view.ctx.bot
        col: Collection = bot.game_collections

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
    board: List[List[str]]
    DEFAULT_ITEMS: ClassVar[List[str]] = [
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
        items: List[str],
        *,
        button_style: discord.ButtonStyle,
        pause_time: float,
        ctx: Context,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        self.button_style = button_style
        self.pause_time = pause_time
        self.opened: Optional[MemoryButton] = None
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
    """
    Memory Game
    """

    def __init__(self) -> None:
        self.embed_color: Optional[DiscordColor] = None
        self.embed: Optional[discord.Embed] = None
        self.moves: int = 0

    async def start(
        self,
        ctx: Context[Parrot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        items: List[str] = None,
        pause_time: float = 0.7,
        button_style: discord.ButtonStyle = discord.ButtonStyle.gray,
        timeout: Optional[float] = None,
    ) -> discord.Message:
        """
        starts the memory game
        Parameters
        ----------
        ctx : Context
            the context of the invokation command
        embed_color : DiscordColor, optional
            the color of the game embed, by default DEFAULT_COLOR
        items : List[str], optional
            items to use for the game tiles, by default []
        pause_time : float, optional
            specifies the duration to pause for before hiding the tiles again, by default 0.7
        button_style : discord.ButtonStyle, optional
            the primary button style to use, by default discord.ButtonStyle.red
        timeout : Optional[float], optional
            the timeout for the view, by default None
        Returns
        -------
        discord.Message
            returns the game message
        """
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
