from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .games import (
    UNO,
    Akinator,
    BattleShip,
    Blackjack,
    Boggle,
    Chess,
    ChimpTest,
    ConnectFour,
    CountryGuesser,
    Hangman,
    LightsOut,
    MemoryGame,
    NumberMemory,
    NumberSlider,
    RockPaperScissors,
    SokobanGameView,
    Tictactoe,
    Twenty48,
    TypingTest,
    VerbalMemory,
    Wordle,
)

if TYPE_CHECKING:
    from core import Parrot

_log = logging.getLogger("bot.cogs.games")


class JoinGameView(discord.ui.View):
    message: discord.Message

    def __init__(self, ctx: commands.Context[Parrot]) -> None:
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.player: discord.Member | discord.User | None = None

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        if hasattr(self, "message"):
            await self.message.edit(content="No one joined the game in time.", view=self)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction[Parrot], button: discord.ui.Button) -> None:
        if interaction.user == self.ctx.author:
            await interaction.response.send_message("You cannot join your own game!", ephemeral=True)
            return

        self.player = interaction.user
        button.disabled = True
        button.label = "Joined"
        await interaction.response.edit_message(view=self)

        self.stop()


class Games(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        self.uno_games: dict[int, UNO] = {}
        _log.info("Cog loaded: %s", self.__class__.__name__)

    async def wait_for_player(self, ctx: commands.Context[Parrot]) -> discord.Member | discord.User:
        """Wait for a player to join the game."""
        view = JoinGameView(ctx)

        message = await ctx.reply("Waiting for a player to join... Click the button below to join the game.", view=view)
        view.message = message

        timed_out = await view.wait()

        if view.player is None or timed_out:
            raise commands.CommandError("No player joined the game.")

        return view.player

    @commands.command(name="akinator", aliases=["aki"])
    async def akinator(self, ctx: commands.Context[Parrot]) -> None:
        """Think of a person, character, or object and answer Akinator's questions until it guesses."""
        await Akinator().start(ctx)

    @commands.command(name="battleship", aliases=["bs"])
    async def battleship(self, ctx: commands.Context[Parrot]) -> None:
        """Play two-player Battleship: place your fleet and fire at coordinates to sink the opponent's ships."""
        opponent = await self.wait_for_player(ctx)
        await BattleShip(ctx.author, opponent).start(ctx)

    @commands.command(name="boggle")
    async def boggle(self, ctx: commands.Context[Parrot]) -> None:
        """Find as many connected words as possible in the letter grid before the timer ends."""
        await Boggle().start(ctx)

    @commands.command(name="chimp_test", aliases=["ct", "chimp", "chimptest", "chimp-test"])
    async def chimp_test(self, ctx: commands.Context[Parrot]) -> None:
        """Memorize the numbered tiles, then select them in ascending order after they are hidden."""
        await ChimpTest().start(ctx)

    @commands.command(name="chess")
    async def chess(self, ctx: commands.Context[Parrot]) -> None:
        """Play two-player Chess and checkmate the opposing king."""
        opponent = await self.wait_for_player(ctx)
        await Chess(white=ctx.author, black=opponent).start(ctx)

    @commands.command(name="connect_four", aliases=["cf", "connect4", "connect-four", "c4"])
    async def connect_four(self, ctx: commands.Context[Parrot]) -> None:
        """Play Connect Four: drop pieces and connect four horizontally, vertically, or diagonally."""
        opponent = await self.wait_for_player(ctx)
        await ConnectFour(red=ctx.author, blue=opponent).start(ctx)

    @commands.command(name="country_guesser", aliases=["cg", "countryguesser", "country-guesser"])
    async def country_guesser(self, ctx: commands.Context[Parrot]) -> None:
        """Identify the country from the clues and submit your answer before the round ends."""
        await CountryGuesser().start(ctx)

    @commands.command(name="hangman", aliases=["hm"])
    async def hangman(self, ctx: commands.Context[Parrot]) -> None:
        """Guess letters to reveal the hidden word before you run out of attempts."""
        await Hangman().start(ctx)

    @commands.command(name="lights_out", aliases=["lo", "lightout", "lightsout"])
    async def lights_out(self, ctx: commands.Context[Parrot]) -> None:
        """Turn off every light; pressing a tile changes it and its neighbours."""
        await LightsOut().start(ctx)

    @commands.command(name="memory_game", aliases=["mg", "memorygame", "memory-game"])
    async def memory_game(self, ctx: commands.Context[Parrot]) -> None:
        """Reveal two tiles at a time and find all matching pairs."""
        await MemoryGame().start(ctx)

    @commands.command(name="number_memory", aliases=["nm", "numbermemory", "number-memory"])
    async def number_memory(self, ctx: commands.Context[Parrot]) -> None:
        """Memorize the displayed number and enter it after it disappears; the challenge grows each round."""
        await NumberMemory().start(ctx)

    @commands.command(name="number_slider", aliases=["ns", "numberslider", "number-slider"])
    async def number_slider(self, ctx: commands.Context[Parrot]) -> None:
        """Arrange the numbered tiles into order by sliding them through the empty space."""
        await NumberSlider().start(ctx)

    @commands.command(name="rock_paper_scissors", aliases=["rps", "rockpaperscissors", "rock-paper-scissors"])
    async def rock_paper_scissors(self, ctx: commands.Context[Parrot]) -> None:
        """Choose rock, paper, or scissors against the bot: rock beats scissors, scissors beats paper, and paper beats rock."""
        await RockPaperScissors().start(ctx)

    @commands.command(name="tictactoe", aliases=["ttt", "tic-tac-toe", "tic_tac_toe"])
    async def tictactoe(self, ctx: commands.Context[Parrot]) -> None:
        """Play two-player Tic-Tac-Toe and get three marks in a row to win."""
        opponent = await self.wait_for_player(ctx)
        await Tictactoe(cross=ctx.author, circle=opponent).start(ctx)

    @commands.command(name="twenty_48", aliases=["2048", "twenty48", "twenty-48"])
    async def twenty_48(self, ctx: commands.Context[Parrot]) -> None:
        """Slide equal numbered tiles together to merge them and build toward 2048."""
        await Twenty48().start(ctx)

    @commands.command(name="verbal_memory", aliases=["vm", "verbalmemory", "verbal-memory"])
    async def verbal_memory(self, ctx: commands.Context[Parrot]) -> None:
        """Decide whether each displayed word is new or has appeared before; mistakes cost a life."""
        await VerbalMemory().start(ctx)

    @commands.command(name="wordle", aliases=["wdl", "wordlegame", "wordle-game"])
    async def wordle(self, ctx: commands.Context[Parrot]) -> None:
        """Guess the hidden word in limited attempts; tile colours show correct, misplaced, and absent letters."""
        await Wordle().start(ctx)

    @commands.command(name="typing_test", aliases=["tt", "typingtest", "typing-test"])
    async def typing_test(self, ctx: commands.Context[Parrot]) -> None:
        """Type the displayed passage quickly and accurately to receive a speed and accuracy result."""
        await TypingTest().start(ctx)

    @commands.command(name="blackjack", aliases=["bj", "black-jack", "black_jack"])
    async def blackjack(self, ctx: commands.Context[Parrot]) -> None:
        """Play Blackjack against the dealer.

        Goal: get as close to 21 as possible without going over. Number cards
        are worth their number, face cards are worth 10, and an Ace is worth
        1 or 11. Use Hit, Stand, Double, Split, Insurance, or Surrender.
        The dealer stands on 17. A natural Blackjack pays 3:2 in the game
        result display.
        """
        await Blackjack().start(ctx)

    @commands.command("uno", aliases=["unogame"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def play_uno(self, ctx: commands.Context):
        """Play multiplayer UNO by matching colour or value and using action and wild cards; empty your hand first."""
        if ctx.channel.id in self.uno_games:
            raise commands.MaxConcurrencyReached(1, commands.BucketType.channel)

        game = UNO(ctx)
        self.uno_games[ctx.channel.id] = game

        await game.start()
        await game.wait()

        try:
            del self.uno_games[ctx.channel.id]
        except KeyError:
            pass

    @commands.command(name="sokoban", aliases=["sk", "soko", "sokobangame", "sokoban-game"])
    async def sokoban(self, ctx: commands.Context[Parrot], level: int | None = 1) -> None:
        """Push boxes onto the target locations in the warehouse maze; you can only push, not pull."""
        await SokobanGameView().start(ctx, level=level)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Games(bot))
