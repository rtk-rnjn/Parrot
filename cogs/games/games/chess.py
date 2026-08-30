from __future__ import annotations

from typing import ClassVar, Literal

import chess
import discord
from discord.ext import commands

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player
from .wordle import WordInputButton


class Chess:
    """Chess game, message-based.

    Two-player chess rendered as a board image.
    Moves are submitted in standard algebraic notation.
    """

    BASE_URL: ClassVar[str] = "http://www.fen-to-image.com/image/64/double/coords/"

    def __init__(
        self,
        *,
        white: Player,
        black: Player,
    ) -> None:
        self.white = white
        self.black = black
        self.turn = self.white

        self.winner: Player | None = None
        self.message: discord.Message | None = None

        self.board: chess.Board = chess.Board()

        self.last_move: dict[str, str] = {}

    def get_color(self) -> Literal["white", "black"]:
        return "white" if self.turn == self.white else "black"

    async def make_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Chess Game", color=self.embed_color)
        embed.description = f"**Turn:** `{self.turn}`\n**Color:** `{self.get_color()}`\n**Check:** `{self.board.is_check()}`"
        embed.set_image(url=f"{self.BASE_URL}{self.board.board_fen()}")

        embed.add_field(
            name="Last Move",
            value=f"```yml\n{self.last_move.get('color', '-')}: {self.last_move.get('move', '-')}\n```",
        )
        return embed

    async def place_move(self, uci: str) -> chess.Board:
        self.last_move = {"color": self.get_color(), "move": f"{uci[:2]} -> {uci[2:]}"}

        self.board.push_uci(uci)
        self.turn = self.white if self.turn == self.black else self.black
        return self.board

    async def fetch_results(self) -> discord.Embed:
        results = self.board.result()
        embed = discord.Embed(title="Chess Game")

        if self.board.is_checkmate():
            embed.description = f"Game over\nCheckmate | Score: `{results}`"
        elif self.board.is_stalemate():
            embed.description = f"Game over\nStalemate | Score: `{results}`"
        elif self.board.is_insufficient_material():
            embed.description = f"Game over\nInsufficient material left to continue the game | Score: `{results}`"
        elif self.board.is_seventyfive_moves():
            embed.description = f"Game over\n75-moves rule | Score: `{results}`"
        elif self.board.is_fivefold_repetition():
            embed.description = f"Game over\nFive-fold repitition. | Score: `{results}`"
        else:
            embed.description = f"Game over\nVariant end condition. | Score: `{results}`"

        embed.set_image(url=f"{self.BASE_URL}{self.board.board_fen()}")
        return embed

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        timeout: float | None = None,
        embed_color: DiscordColor = DEFAULT_COLOR,
        add_reaction_after_move: bool = False,
        **kwargs,
    ) -> discord.Message | None:
        self.embed_color = embed_color

        embed = await self.make_embed()
        self.message = await ctx.reply(embed=embed, **kwargs)

        while not ctx.bot.is_closed():

            def check(m: discord.Message) -> bool:
                try:
                    if self.board.parse_uci(m.content.lower()):
                        return m.author == self.turn and m.channel == ctx.channel
                    else:
                        return False
                except ValueError:
                    return False

            try:
                message: discord.Message = await ctx.bot.wait_for(
                    "message",
                    timeout=timeout,
                    check=check,
                )
            except TimeoutError:
                return

            await self.place_move(message.content.lower())
            embed = await self.make_embed()

            if add_reaction_after_move:
                await message.add_reaction("✅")

            if self.board.is_game_over():
                break

            await self.message.edit(embed=embed)

        embed = await self.fetch_results()
        await self.message.edit(embed=embed)
        await ctx.reply("~ Game Over ~")

        return self.message


class ChessInput(discord.ui.Modal, title="Make your move"):
    def __init__(self, view: ChessView) -> None:
        super().__init__()
        self.view = view

        self.move_from = discord.ui.TextInput(
            label="from coordinate",
            style=discord.TextStyle.short,
            required=True,
            min_length=2,
            max_length=2,
        )

        self.move_to = discord.ui.TextInput(
            label="to coordinate",
            style=discord.TextStyle.short,
            required=True,
            min_length=2,
            max_length=2,
        )

        self.add_item(self.move_from)
        self.add_item(self.move_to)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        game = self.view.game
        from_coord = self.move_from.value.strip().lower()
        to_coord = self.move_to.value.strip().lower()

        uci = from_coord + to_coord

        try:
            is_valid_uci = game.board.parse_uci(uci)
        except ValueError:
            is_valid_uci = False

        if not is_valid_uci:
            await interaction.response.send_message(
                f"Invalid coordinates for move: `{from_coord} -> {to_coord}`",
                ephemeral=True,
            )
            return
        else:
            await game.place_move(uci)

            if game.board.is_game_over():
                self.view.disable_all()
                embed = await game.fetch_results()
                self.view.stop()
            else:
                embed = await game.make_embed()

            await interaction.response.edit_message(embed=embed, view=self.view)


class ChessButton(WordInputButton):
    view: ChessView

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        game = self.view.game
        if interaction.user not in (game.black, game.white):
            await interaction.response.send_message(
                "You are not part of this game!",
                ephemeral=True,
            )
            return
        elif self.label == "Cancel":
            self.view.disable_all()
            assert interaction.message is not None
            await interaction.message.edit(view=self.view)
            await interaction.response.send_message("**Game Over!** Cancelled")
            self.view.stop()
            return
        elif interaction.user != game.turn:
            await interaction.response.send_message(
                "It is not your turn yet!",
                ephemeral=True,
            )
            return
        else:
            await interaction.response.send_modal(ChessInput(self.view))


class ChessView(BaseView):
    def __init__(self, game: BetaChess, *, timeout: float | None) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        inpbutton = ChessButton()
        inpbutton.label = "Make your move!"

        self.add_item(inpbutton)
        self.add_item(ChessButton(cancel_button=True))


class BetaChess(Chess):
    """Chess game, button-based.

    Same as :class:`Chess` but uses a modal for move input.
    """

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: float | None = None,
    ) -> discord.Message:
        self.embed_color = embed_color

        embed = await self.make_embed()
        self.view = ChessView(self, timeout=timeout)

        self.message = await ctx.reply(embed=embed, view=self.view)
        self.view.message = self.message

        await self.view.wait()
        return self.message
