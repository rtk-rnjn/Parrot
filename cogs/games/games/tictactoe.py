from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import discord
from discord.ext import commands

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player, chunk, double_wait, wait_for_delete

if TYPE_CHECKING:
    from core.bot import Parrot


class Tictactoe:
    """Tic-Tac-Toe, reaction-based.

    Two players take turns placing marks on a 3x3 grid.
    """

    BLANK: ClassVar[str] = "\N{BLACK LARGE SQUARE}"
    CIRCLE: ClassVar[str] = "\N{HEAVY LARGE CIRCLE}"
    CROSS: ClassVar[str] = "\N{CROSS MARK}"
    _conversion: ClassVar[dict[str, tuple[int, int]]] = {
        "\N{DIGIT ONE}": (0, 0),
        "\N{DIGIT TWO}": (0, 1),
        "\N{DIGIT THREE}": (0, 2),
        "\N{DIGIT FOUR}": (1, 0),
        "\N{DIGIT FIVE}": (1, 1),
        "\N{DIGIT SIX}": (1, 2),
        "\N{DIGIT SEVEN}": (2, 0),
        "\N{DIGIT EIGHT}": (2, 1),
        "\N{DIGIT NINE}": (2, 2),
    }

    _WINNERS: ClassVar[tuple[tuple[tuple[int, int], ...], ...]] = (
        ((0, 0), (0, 1), (0, 2)),
        ((1, 0), (1, 1), (1, 2)),
        ((2, 0), (2, 1), (2, 2)),
        ((0, 0), (1, 0), (2, 0)),
        ((0, 1), (1, 1), (2, 1)),
        ((0, 2), (1, 2), (2, 2)),
        ((0, 0), (1, 1), (2, 2)),
        ((0, 2), (1, 1), (2, 0)),
    )

    def __init__(
        self,
        cross: Player,
        circle: Player,
    ) -> None:
        self.cross = cross
        self.circle = circle

        self.board: list[list[str]] = [[self.BLANK for _ in range(3)] for _ in range(3)]
        self.turn: Player = self.cross

        self.winner: Player | None = None
        self.winning_indexes: tuple[tuple[int, int], ...] = ()
        self.message: discord.Message | None = None

        self._controls: list[str] = [
            "\N{DIGIT ONE}",
            "\N{DIGIT TWO}",
            "\N{DIGIT THREE}",
            "\N{DIGIT FOUR}",
            "\N{DIGIT FIVE}",
            "\N{DIGIT SIX}",
            "\N{DIGIT SEVEN}",
            "\N{DIGIT EIGHT}",
            "\N{DIGIT NINE}",
        ]

        self.emoji_to_player: dict[str, Player] = {
            self.CIRCLE: self.circle,
            self.CROSS: self.cross,
        }
        self.player_to_emoji: dict[Player, str] = {v: k for k, v in self.emoji_to_player.items()}

    def board_string(self) -> str:
        board = ""
        for row in self.board:
            board += "".join(row) + "\n"
        return board

    def make_embed(self, *, game_over: bool = False) -> discord.Embed:
        embed = discord.Embed(color=self.embed_color)
        if game_over:
            status = f"{self.winner.mention} won!" if self.winner else "Tie"
            embed.description = f"**Game over**\n{status}"
        else:
            embed.description = f"**Turn:** {self.turn.mention}\n**Piece:** `{self.player_to_emoji[self.turn]}`"
        return embed

    def make_move(self, emoji: str, user: Player) -> list:
        if emoji not in self._controls:
            raise KeyError("Provided emoji is not one of the valid controls")
        else:
            x, y = self._conversion[emoji]
            piece = self.player_to_emoji[user]
            self.board[x][y] = piece

            self.turn = self.circle if user == self.cross else self.cross
            self._conversion.pop(emoji)
            self._controls.remove(emoji)
            return self.board

    def is_game_over(self, *, tie: bool = False) -> bool:
        for possibility in self._WINNERS:
            row = [self.board[r][c] for r, c in possibility]

            if len(set(row)) == 1 and row[0] != self.BLANK:
                self.winner = self.emoji_to_player[row[0]]
                self.winning_indexes = possibility
                return True

        if not self._controls or tie:
            return True

        return False

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        timeout: float | None = None,
        embed_color: DiscordColor = DEFAULT_COLOR,
        remove_reaction_after: bool = False,
        **kwargs,
    ) -> discord.Message:
        self.embed_color = embed_color

        embed = self.make_embed()
        self.message = await ctx.reply(self.board_string(), embed=embed, **kwargs)

        for button in self._controls:
            await self.message.add_reaction(button)

        while not ctx.bot.is_closed():

            def check(reaction: discord.Reaction, user: discord.User) -> bool:
                return (
                    str(reaction.emoji) in self._controls
                    and user == self.turn
                    and self.message is not None
                    and reaction.message.id == self.message.id
                )

            try:
                done, _ = await double_wait(
                    ctx.bot.wait_for("reaction_add", timeout=timeout, check=check),
                    ctx.bot.wait_for("reaction_remove", timeout=timeout, check=check),
                )
                reaction, user = done.pop().result()
            except TimeoutError:
                break

            emoji = str(reaction.emoji)
            self.make_move(emoji, user)
            embed = self.make_embed()

            if remove_reaction_after:
                await self.message.remove_reaction(emoji, user)

            if self.is_game_over():
                break

            await self.message.edit(content=self.board_string(), embed=embed)

        embed = self.make_embed(game_over=True)
        await self.message.edit(content=self.board_string(), embed=embed)

        return self.message


class TTTButton(discord.ui.Button["TTTView"]):
    def __init__(self, label: str, style: discord.ButtonStyle, *, row: int, col: int):
        super().__init__(
            label=label,
            style=style,
            row=row,
        )

        self.col = col

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        user = interaction.user
        game = self.view.game

        if user not in (game.cross, game.circle):
            await interaction.response.send_message(
                "You are not part of this game!",
                ephemeral=True,
            )
            return

        if user != game.turn:
            await interaction.response.send_message(
                "it is not your turn!",
                ephemeral=True,
            )
            return

        self.label = game.player_to_emoji[user]
        self.disabled = True

        assert self.row is not None
        assert self.label is not None
        game.board[self.row][self.col] = self.label
        game.turn = game.circle if user == game.cross else game.cross

        tie = all(button.disabled for button in self.view.children if isinstance(button, discord.ui.Button))

        if game_over := game.is_game_over(tie=tie):
            if game.winning_indexes:
                self.view.disable_all()
                game.create_streak()
            self.view.stop()

        embed = game.make_embed(game_over=game_over or tie)
        await interaction.response.edit_message(embed=embed, view=self.view)


class TTTView(BaseView):
    def __init__(self, game: BetaTictactoe, *, timeout: float | None) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        for x, row in enumerate(game.board):
            for y, square in enumerate(row):
                button = TTTButton(
                    label=square,
                    style=self.game.button_style,
                    row=x,
                    col=y,
                )
                self.add_item(button)


class BetaTictactoe(Tictactoe):
    BLANK: ClassVar[str] = "\N{ZERO WIDTH SPACE}"
    CIRCLE: ClassVar[str] = "O"
    CROSS: ClassVar[str] = "X"

    def create_streak(self) -> None:
        assert self.view is not None
        chunked = chunk(self.view.children, count=3)
        for row, col in self.winning_indexes:
            button = chunked[row][col]
            assert isinstance(button, TTTButton)
            button.style = self.win_button_style

    async def start(
        self,
        ctx: commands.Context[Parrot],
        button_style: discord.ButtonStyle = discord.ButtonStyle.green,
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        win_button_style: discord.ButtonStyle = discord.ButtonStyle.red,
        timeout: float | None = None,
    ) -> discord.Message:
        self.embed_color = embed_color
        self.button_style = button_style
        self.win_button_style = win_button_style

        self.view = TTTView(self, timeout=timeout)
        self.message = await ctx.reply(embed=self.make_embed(), view=self.view)
        self.view.message = self.message

        await double_wait(
            wait_for_delete(ctx, self.message, user=(self.cross, self.circle)),
            self.view.wait(),
        )

        return self.message
