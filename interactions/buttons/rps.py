from __future__ import annotations

from random import choice
from discord.ext import commands

from core import Parrot, Cog, Context

CHOICES = ["rock", "paper", "scissors"]
SHORT_CHOICES = ["r", "p", "s"]

# Using a dictionary instead of conditions to check for the winner.
WINNER_DICT = {
    "r": {
        "r": 0,
        "p": -1,
        "s": 1,
    },
    "p": {
        "r": 1,
        "p": 0,
        "s": -1,
    },
    "s": {
        "r": -1,
        "p": 1,
        "s": 0,
    }
}


class RPS(Cog):
    """Rock Paper Scissors. The Classic Game!"""
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.command()
    async def rps(self, ctx: Context, move: str) -> None:
        """Play the classic game of Rock Paper Scissors with your own sir-lancebot!"""
        move = move.lower()
        player_mention = ctx.author.mention

        if move not in CHOICES and move not in SHORT_CHOICES:
            raise commands.BadArgument(f"Invalid move. Please make move from options: {', '.join(CHOICES).upper()}.")

        bot_move = choice(CHOICES)
        # value of player_result will be from (-1, 0, 1) as (lost, tied, won).
        player_result = WINNER_DICT[move[0]][bot_move[0]]

        if player_result == 0:
            message_string = f"{player_mention} You and **{self.bot.user.name}** played {bot_move}, it's a tie."
            await ctx.reply(message_string)
        elif player_result == 1:
            await ctx.reply(f"{player_mention} **{self.bot.user.name}** {bot_move}! {ctx.author.name} won!")
        else:
            await ctx.reply(f"{player_mention} **{self.bot.user.name}** {bot_move}! {ctx.author.name} lost!")

