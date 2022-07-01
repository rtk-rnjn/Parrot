from __future__ import annotations

import asyncio
from typing import Any, List, Optional
import chess

import discord
from core import Parrot, Context
from utilities.paginator import ParrotPaginator


class ChessView(discord.ui.View):
    def __init__(
        self, *, game: Chess, ctx: Context = None, timeout: float = 300.0, **kwargs: Any
    ):
        super().__init__(timeout=timeout, **kwargs)
        self.game = game
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user in (self.game.white, self.game.black):
            return True
        await interaction.response.send_message(
            content="This isn't your game!", ephemeral=True
        )
        return False

    @discord.ui.button(
        emoji="\N{BLACK CHESS PAWN}",
        label="Show Legal Moves",
        style=discord.ButtonStyle.gray,
        disabled=False,
    )
    async def show_moves(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        menu = ParrotPaginator(
            self.game.ctx,
            title="Legal Moves",
            embed_url="https://images.chesscomfiles.com/uploads/v1/images_users/tiny_mce/SamCopeland/phpmeXx6V.png",
            check_other_ids=[self.game.white.id, self.game.black.id],
        )
        for i in self.game.legal_moves():
            menu.add_line(i)
        await menu.start(start=False)
        await interaction.response.send_message(
            embed=menu.embed, view=menu.view, ephemeral=True
        )

    @discord.ui.button(
        emoji="\N{BLACK CHESS PAWN}",
        label="Show board FEN",
        style=discord.ButtonStyle.danger,
        disabled=False,
    )
    async def show_fen(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            f"**{interaction.user}** board FEN: `{self.game.board.board_fen()}`",
            ephemeral=True,
        )


class Chess:
    def __init__(
        self,
        white: discord.Member,
        black: discord.Member,
        *,
        bot: Parrot,
        ctx: Context,
        timeout: float = 300,
        react_on_success: bool = True,
        custom: str = None,
    ) -> None:
        self.white = white
        self.black = black

        self.bot = bot
        self.ctx = ctx
        self.timeout = timeout
        self.react_on_success = react_on_success

        if custom:
            self.board = chess.Board(custom)
        else:
            self.board = chess.Board()

        self.turn = white
        self.alternate_turn = black

        self.game_stop = False

    def legal_moves(self) -> List[str]:
        return [self.board.san(move) for move in self.board.legal_moves]

    async def wait_for_move(self) -> Optional[discord.Message]:
        LEGAL_MOVES = self.legal_moves()

        def check(m) -> bool:
            if m.content.lower() in ("exit", "quit", "resign", "abort", "draw"):
                return True
            return (
                (self.ctx.channel.id == m.channel.id)
                and (m.author == self.turn)
                and (m.content in LEGAL_MOVES)
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=self.timeout)
            return msg
        except asyncio.TimeoutError:
            if not self.game_stop:
                await self.ctx.send(
                    f"**{self.turn}** did not responded on time! Game Over!"
                )
                return None

    def switch(self) -> None:
        if self.turn == self.white:
            self.turn = self.black
            self.alternate_turn = self.white
            return
        if self.turn == self.black:
            self.turn = self.white
            self.alternate_turn = self.black
            return

    async def place_move(self, move: str) -> None:
        st = "white" if self.alternate_turn == self.white else "black"
        move = self.board.push_san(move)
        content = f"{self.white.mention} VS {self.black.mention}"
        embed = discord.Embed(
            timestamp=discord.utils.utcnow(),
        )
        embed.set_image(
            url=f"https://backscattering.de/web-boardimage/board.png?fen={self.board.board_fen()}&lastMove={move.uci()}&coordinates=true&orientation={st}"
        )
        embed.description = f"""```
On Check?      : {self.board.is_check()}
Can Claim Draw?: {self.board.can_claim_threefold_repetition()}
```
"""
        embed.set_footer(text=f"Turn: {self.alternate_turn} | Having 5m to make move")
        await self.ctx.send(
            content=content, embed=embed, view=ChessView(game=self, ctx=self.ctx)
        )
        await self.game_over()

    async def game_over(
        self,
    ) -> bool:
        if not self.game_stop:
            if self.board.is_checkmate():
                await self.ctx.send(f"Game over! **{self.turn}** wins by check-mate")
                self.game_stop = True
            elif self.board.is_stalemate():
                await self.ctx.send("Game over! Ended with draw!")
                self.game_stop = True
            elif self.board.is_insufficient_material():
                await self.ctx.send(
                    "Game over! Insfficient material left to continue the game! Draw!"
                )
                self.game_stop = True
            elif self.board.is_seventyfive_moves():
                await self.ctx.send("Game over! 75-moves rule | Game Draw!")
                self.game_stop = True
            elif self.board.is_fivefold_repetition():
                await self.ctx.send("Game over! Five-fold repitition. | Game Draw!")
                self.game_stop = True
            else:
                self.game_stop = False
        return self.game_stop

    async def start(self):
        content = f"{self.white.mention} VS {self.black.mention}"
        embed = discord.Embed(
            timestamp=discord.utils.utcnow(),
        )
        embed.set_image(
            url=f"https://backscattering.de/web-boardimage/board.png?fen={self.board.board_fen()}&coordinates=true"
        )
        embed.description = f"""```
On Check?      : {self.board.is_check()}
Can Claim Draw?: {self.board.can_claim_threefold_repetition()}
```
"""
        embed.set_footer(text=f"Turn: {self.turn} | Having 5m to make move")
        await self.ctx.send(
            content=content, embed=embed, view=ChessView(game=self, ctx=self.ctx)
        )
        while not self.game_stop:
            msg = await self.wait_for_move()
            if msg is None:
                return
            if msg.content.lower() in (
                "exit",
                "quit",
                "resign",
                "abort",
            ):
                return await self.ctx.send(
                    f"**{msg.author}** resigned/aborted the game. Game Over!"
                )
            if msg.content.lower() == "draw":
                value = await self.ctx.prompt(
                    f"**{msg.author}** offered draw! **{self.turn if self.turn.id != msg.author.id else self.alternate_turn}** to accept the draw click `Confirm`",
                    author_id=self.turn.id
                    if self.turn.id != msg.author.id
                    else self.alternate_turn.id,
                )
                if value:
                    msg_ = await self.ctx.send(
                        f"{self.black} VS {self.white} \N{HANDSHAKE} **Game over! Ended in draw by agreement!**"
                    )
                    await msg_.add_reaction("\N{HANDSHAKE}")
                    self.game_stop = True  # this is imp. as the game wasn't stopping
            else:
                if self.react_on_success:
                    try:
                        await msg.add_reaction("\N{BLACK CHESS PAWN}")
                    except discord.Forbidden:
                        pass
                await self.place_move(msg.content)
                self.switch()