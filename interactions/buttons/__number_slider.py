# https://github.com/Tom-the-Bomb/Discord-Games/blob/master/discord_games/button_games/number_slider.py

from __future__ import annotations

import asyncio
import random
from typing import (
    TYPE_CHECKING,
    Any,
    Coroutine,
    Final,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import discord
from core import Context, Parrot

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    A = TypeVar("A", bool)
    B = TypeVar("B", bool)

    Board: TypeAlias = List[List[Optional[int]]]


DiscordColor: TypeAlias = Union[discord.Color, int]
DEFAULT_COLOR: Final[discord.Color] = discord.Color(0x2F3136)


def chunk(iterable: List[Optional[int]], *, count: int) -> List[List[Optional[int]]]:
    return [iterable[i : i + count] for i in range(0, len(iterable), count)]


async def wait_for_delete(
    ctx: Context,
    message: discord.Message,
    *,
    emoji: str = "\N{BLACK SQUARE FOR STOP}",
    bot: Optional[Parrot] = None,
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

    bot: Parrot = bot or ctx.bot
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
) -> Tuple[Set[asyncio.Task[Union[A, B]]], Set[asyncio.Task[Union[A, B]]]]:

    if not loop:
        loop = asyncio.get_event_loop()

    return await asyncio.wait(
        [loop.create_task(task1), loop.create_task(task2)],
        return_when=asyncio.FIRST_COMPLETED,
    )


class BaseView(discord.ui.View):
    def disable_all(self) -> None:
        for button in self.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True

    async def on_timeout(self) -> None:
        return self.stop()


class SlideButton(discord.ui.Button["SlideView"]):
    def __init__(
        self, label: Union[int, str], *, style: discord.ButtonStyle, row: int
    ) -> None:
        super().__init__(
            label=str(label),
            style=style,
            row=row,
        )

        if label == "\u200b":
            self.disabled = True

    async def callback(self, interaction: discord.Interaction) -> None:

        assert self.view is not None

        game = self.view.game

        if interaction.user != game.player:
            return await interaction.response.send_message(
                "This is not your game!", ephemeral=True
            )
        num = int(self.label)

        if num not in game.beside_blank():
            return await interaction.response.defer()
        ix, iy = game.get_item(num)
        nx, ny = game.get_item()

        game.numbers[nx][ny], game.numbers[ix][iy] = (
            game.numbers[ix][iy],
            game.numbers[nx][ny],
        )

        self.view.update_board(clear=True)

        game.moves += 1
        game.embed.set_field_at(0, name="\u200b", value=f"Moves: `{game.moves}`")

        if game.numbers == game.completed:
            self.view.disable_all()
            self.view.stop()
            game.embed.description = "**Congrats! You won!**"

        return await interaction.response.edit_message(embed=game.embed, view=self.view)


class NumberSlider:
    """
    Number Slider Game
    """

    def __init__(self, count: Literal[1, 2, 3, 4, 5] = 4) -> None:

        if count not in range(1, 6):
            raise ValueError("Count must be an integer between 1 and 5")

        self.all_numbers: List[Optional[int]] = list(range(1, count**2))

        self.player: Optional[discord.Member] = None

        self.moves: int = 0
        self.count = count
        self.numbers: Board = []
        self.completed: Board = []

        self.wrong_style: discord.ButtonStyle = discord.ButtonStyle.gray
        self.correct_style: discord.ButtonStyle = discord.ButtonStyle.green

    def get_item(self, obj: Optional[int] = None) -> Tuple[int, int]:
        return next(
            (x, y)
            for x, row in enumerate(self.numbers)
            for y, item in enumerate(row)
            if item == obj
        )

    def beside_blank(self) -> List[Optional[int]]:
        nx, ny = self.get_item()

        beside_item = [
            (nx - 1, ny),
            (nx, ny - 1),
            (nx + 1, ny),
            (nx, ny + 1),
        ]

        return [
            self.numbers[i][j]
            for i, j in beside_item
            if i in range(self.count) and j in range(self.count)
        ]

    async def start(
        self,
        ctx: Context,
        *,
        wrong_style: discord.ButtonStyle = discord.ButtonStyle.gray,
        correct_style: discord.ButtonStyle = discord.ButtonStyle.green,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: Optional[float] = None,
    ) -> discord.Message:
        """
        starts the number slider game
        Parameters
        ----------
        ctx : Context
            the context of the invokation command
        wrong_style : discord.ButtonStyle, optional
            the button style to use for tiles that are in the wrong spot, by default discord.ButtonStyle.gray
        correct_style : discord.ButtonStyle, optional
            the button style to use for tiles that are in the right spot, by default discord.ButtonStyle.green
        embed_color : DiscordColor, optional
            the game embedd color, by default DEFAULT_COLOR
        timeout : Optional[float], optional
            the timeout for the view, by default None
        Returns
        -------
        discord.Message
            returns the game message
        """
        self.player = ctx.author
        self.wrong_style = wrong_style
        self.correct_style = correct_style

        numbers = self.all_numbers[:]
        random.shuffle(numbers)
        random.shuffle(numbers)

        numbers.append(None)
        self.numbers = chunk(numbers, count=self.count)

        self.completed = chunk(self.all_numbers + [None], count=self.count)

        self.view = SlideView(self, timeout=timeout)
        self.embed = discord.Embed(
            description="Slide the tiles back in ascending order!", color=embed_color
        )
        self.embed.add_field(name="\u200b", value="Moves: `0`")

        self.message: discord.Message = await ctx.send(embed=self.embed, view=self.view)

        await double_wait(
            wait_for_delete(ctx, self.message),
            self.view.wait(),
        )
        return self.message


class SlideView(BaseView):
    def __init__(self, game: NumberSlider, *, timeout: float) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        self.update_board()

    def update_board(self, *, clear: bool = False) -> None:

        if clear:
            self.clear_items()

        for i, row in enumerate(self.game.numbers):
            for j, number in enumerate(row):
                if number == self.game.completed[i][j]:
                    style = self.game.correct_style
                else:
                    style = self.game.wrong_style

                button = SlideButton(
                    label=number or "\u200b",
                    style=style,
                    row=i,
                )
                self.add_item(button)
