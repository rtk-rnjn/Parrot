from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player, double_wait

if TYPE_CHECKING:
    from core.bot import Parrot


RED = "\N{LARGE RED CIRCLE}"
BLUE = "\N{LARGE BLUE CIRCLE}"
BLANK = "\N{BLACK LARGE SQUARE}"


class ConnectFour:
    """Connect Four, reaction-based.

    Two players drop pieces into columns, trying to
    connect four in a row in any direction.
    """

    def __init__(
        self,
        *,
        red: Player,
        blue: Player,
    ) -> None:
        self.red_player = red
        self.blue_player = blue

        self.board: list[list[str]] = [[BLANK for _ in range(7)] for _ in range(6)]
        self._controls: tuple[str, ...] = (
            "\N{DIGIT ONE}",
            "\N{DIGIT TWO}",
            "\N{DIGIT THREE}",
            "\N{DIGIT FOUR}",
            "\N{DIGIT FIVE}",
            "\N{DIGIT SIX}",
            "\N{DIGIT SEVEN}",
        )

        self.turn = self.red_player
        self.message: discord.Message | None = None
        self.winner: Player | None = None

        self._conversion: dict[str, int] = {emoji: i for i, emoji in enumerate(self._controls)}
        self.player_to_emoji: dict[Player, str] = {
            self.red_player: RED,
            self.blue_player: BLUE,
        }
        self.emoji_to_player: dict[str, Player] = {v: k for k, v in self.player_to_emoji.items()}

    def board_string(self) -> str:
        board = "".join(self._controls) + "\n"
        for row in self.board:
            board += "".join(row) + "\n"
        return board

    def make_embed(self, *, status: bool) -> discord.Embed:
        embed = discord.Embed(color=self.embed_color)
        if not status:
            embed.description = f"**Turn:** {self.turn.name}\n**Piece:** `{self.player_to_emoji[self.turn]}`"
        else:
            status_ = f"{self.winner} won!" if self.winner else "Tie"
            embed.description = f"**Game over**\n{status_}"
        return embed

    def place_move(self, column: str | int, user) -> list[list[str]]:
        if isinstance(column, str):
            if column not in self._controls:
                raise KeyError("Provided emoji is not one of the valid controls")

            column = self._conversion[column]

        for x in range(5, -1, -1):
            if self.board[x][column] == BLANK:
                self.board[x][column] = self.player_to_emoji[user]
                break

        self.turn = self.red_player if user == self.blue_player else self.blue_player
        return self.board

    def is_game_over(self) -> bool:  # noqa: PLR0912, C901
        if all(i != BLANK for i in self.board[0]):
            return True

        for x in range(6):
            for i in range(4):
                if self.board[x][i] == self.board[x][i + 1] == self.board[x][i + 2] == self.board[x][i + 3] and self.board[x][i] != BLANK:
                    self.winner = self.emoji_to_player[self.board[x][i]]
                    return True

        for x in range(3):
            for i in range(7):
                if self.board[x][i] == self.board[x + 1][i] == self.board[x + 2][i] == self.board[x + 3][i] and self.board[x][i] != BLANK:
                    self.winner = self.emoji_to_player[self.board[x][i]]
                    return True

        for x in range(3):
            for i in range(4):
                if self.board[x][i] == self.board[x + 1][i + 1] == self.board[x + 2][i + 2] == self.board[x + 3][i + 3] and self.board[x][i] != BLANK:
                    self.winner = self.emoji_to_player[self.board[x][i]]
                    return True

        for x in range(5, 2, -1):
            for i in range(4):
                if self.board[x][i] == self.board[x - 1][i + 1] == self.board[x - 2][i + 2] == self.board[x - 3][i + 3] and self.board[x][i] != BLANK:
                    self.winner = self.emoji_to_player[self.board[x][i]]
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

        embed = self.make_embed(status=False)
        self.message = await ctx.reply(self.board_string(), embed=embed, **kwargs)

        for button in self._controls:
            await self.message.add_reaction(button)

        status = False
        while not ctx.bot.is_closed():

            def check(reaction: discord.Reaction, user: discord.User) -> bool:
                return (
                    str(reaction.emoji) in self._controls
                    and user == self.turn
                    and self.message is not None
                    and reaction.message.id == self.message.id
                    and self.board[0][self._conversion[str(reaction.emoji)]] == BLANK
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
            self.place_move(emoji, user)

            if status := self.is_game_over():
                break

            if remove_reaction_after:
                await self.message.remove_reaction(emoji, user)

            embed = self.make_embed(status=False)
            await self.message.edit(content=self.board_string(), embed=embed)

        embed = self.make_embed(status=status)
        await self.message.edit(content=self.board_string(), embed=embed)

        return self.message


class ConnectFourButton(discord.ui.Button["ConnectFourView"]):
    def __init__(self, number: int, style: discord.ButtonStyle) -> None:
        self.number = number

        super().__init__(
            label=str(self.number),
            style=style,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        game = self.view.game

        if interaction.user not in (game.red_player, game.blue_player):
            await interaction.response.send_message(
                "You are not part of this game!",
                ephemeral=True,
            )
            return

        if interaction.user != game.turn:
            await interaction.response.send_message(
                "It is not your turn yet!",
                ephemeral=True,
            )
            return

        if game.board[0][self.number - 1] != BLANK:
            await interaction.response.send_message(
                "Selected column is full!",
                ephemeral=True,
            )
            return

        game.place_move(self.number - 1, interaction.user)

        status = game.is_game_over()

        embed = game.make_embed(status=status)

        if status:
            self.view.disable_all()
            self.view.stop()

        await interaction.response.edit_message(
            view=self.view,
            embed=embed,
            content=game.board_string(),
        )


class ConnectFourView(BaseView):
    game: ConnectFour

    def __init__(self, game: BetaConnectFour, timeout: float | None) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        for i in range(1, 8):
            self.add_item(ConnectFourButton(i, self.game.button_style))


class BetaConnectFour(ConnectFour):
    """Connect Four, button-based.

    Same as :class:`ConnectFour` but uses numbered buttons
    to select columns.
    """

    async def start(
        self,
        ctx: commands.Context[Parrot],
        *,
        timeout: float | None = None,
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        embed_color: DiscordColor = DEFAULT_COLOR,
    ) -> discord.Message:
        self.embed_color = embed_color
        self.button_style = button_style

        self.view = ConnectFourView(self, timeout=timeout)

        embed = self.make_embed(status=False)
        self.message = await ctx.reply(
            content=self.board_string(),
            view=self.view,
            embed=embed,
        )
        self.view.message = self.message

        await self.view.wait()
        return self.message
