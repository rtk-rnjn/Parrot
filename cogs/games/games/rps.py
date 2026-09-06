from __future__ import annotations

import random
from typing import ClassVar

import discord
from discord.ext import commands

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player, double_wait


class RockPaperScissors:
    """Rock-Paper-Scissors, reaction-based.

    Two players pick their choice via emoji reactions.
    """

    message: discord.Message

    OPTIONS: ClassVar[tuple[str, str, str]] = ("\N{ROCK}", "\N{BLACK SCISSORS}", "\N{NEWSPAPER}")
    BEATS: ClassVar[dict[str, str]] = {
        OPTIONS[0]: OPTIONS[1],
        OPTIONS[1]: OPTIONS[2],
        OPTIONS[2]: OPTIONS[0],
    }

    def check_win(self, bot_choice: str, user_choice: str) -> bool:
        return self.BEATS[user_choice] == bot_choice

    async def wait_for_choice(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        timeout: float | None,
    ) -> str:
        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return str(reaction.emoji) in self.OPTIONS and user == ctx.author and reaction.message.id == self.message.id

        done, _ = await double_wait(
            ctx.bot.wait_for("reaction_add", timeout=timeout, check=check),
            ctx.bot.wait_for("reaction_remove", timeout=timeout, check=check),
        )
        reaction, _ = done.pop().result()
        return str(reaction.emoji)

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        timeout: float | None = None,
        embed_color: DiscordColor = DEFAULT_COLOR,
    ) -> discord.Message:
        embed = discord.Embed(
            title="Rock Paper Scissors",
            description="React to play!",
            color=embed_color,
        )
        self.message = await ctx.reply(embed=embed)

        for option in self.OPTIONS:
            await self.message.add_reaction(option)

        bot_choice = random.choice(self.OPTIONS)

        try:
            user_choice = await self.wait_for_choice(ctx, timeout=timeout)
        except TimeoutError:
            return self.message

        if user_choice == bot_choice:
            embed.description = f"**Tie!**\nWe both picked {user_choice}"
        elif self.check_win(bot_choice, user_choice):
            embed.description = f"**You Won!**\nYou picked {user_choice} and I picked {bot_choice}."
        else:
            embed.description = f"**You Lost!**\nI picked {bot_choice} and you picked {user_choice}."

        await self.message.edit(embed=embed)
        return self.message


class RPSButton(discord.ui.Button["RPSView"]):
    def __init__(self, emoji: str, *, style: discord.ButtonStyle) -> None:
        super().__init__(
            emoji=emoji,
            style=style,
        )

    def get_choice(
        self,
        user: Player,
        other: bool = False,
    ) -> str | None:
        assert self.view is not None
        game = self.view.game
        if other:
            return game.player2_choice if user == game.player1 else game.player1_choice
        else:
            return game.player1_choice if user == game.player1 else game.player2_choice

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        game = self.view.game
        players = (game.player1, game.player2) if game.player2 else (game.player1,)

        if interaction.user not in players:
            await interaction.response.send_message(
                "This is not your game!",
                ephemeral=True,
            )
            return

        if not game.player2:
            bot_choice = random.choice(game.OPTIONS)
            assert self.emoji is not None and self.emoji.name is not None
            user_choice = self.emoji.name

            if user_choice == bot_choice:
                game.embed.description = f"**Tie!**\nWe both picked {user_choice}"
            elif game.check_win(bot_choice, user_choice):
                game.embed.description = f"**You Won!**\nYou picked {user_choice} and I picked {bot_choice}."
            else:
                game.embed.description = f"**You Lost!**\nI picked {bot_choice} and you picked {user_choice}."

            self.view.disable_all()
            self.view.stop()

        else:
            if self.get_choice(interaction.user):
                await interaction.response.send_message(
                    "You have chosen already!",
                    ephemeral=True,
                )
                return

            other_player_choice = self.get_choice(interaction.user, other=True)

            assert self.emoji is not None and self.emoji.name is not None
            if interaction.user == game.player1:
                game.player1_choice = self.emoji.name

                if not other_player_choice:
                    game.embed.description = (
                        game.embed.description or ""
                    ) + f"\n\n{game.player1.mention} has chosen...\n*Waiting for {game.player2.mention} to choose...*"
            else:
                game.player2_choice = self.emoji.name

                if not other_player_choice:
                    game.embed.description = (
                        game.embed.description or ""
                    ) + f"\n\n{game.player2.mention} has chosen...\n*Waiting for {game.player1.mention} to choose...*"

            if game.player1_choice and game.player2_choice:
                result = "You both tied!" if game.player1_choice == game.player2_choice else f"**{game.check_human_win()} Won!**"
                game.embed.description = (
                    f"{result}\n\n{game.player1.mention} chose {game.player1_choice}.\n{game.player2.mention} chose {game.player2_choice}."
                )

                self.view.disable_all()
                self.view.stop()

        await interaction.response.edit_message(embed=game.embed, view=self.view)


class RPSView(BaseView):
    game: BetaRockPaperScissors

    def __init__(
        self,
        game: BetaRockPaperScissors,
        *,
        button_style: discord.ButtonStyle,
        timeout: float | None,
    ) -> None:
        super().__init__(timeout=timeout)

        self.button_style = button_style
        self.game = game

        for option in self.game.OPTIONS:
            self.add_item(RPSButton(option, style=self.button_style))


class BetaRockPaperScissors(RockPaperScissors):
    """Rock-Paper-Scissors, button-based.

    Same as :class:`RockPaperScissors` but uses emoji buttons
    instead of reactions.
    """

    player1: Player
    embed: discord.Embed

    def __init__(
        self,
        other_player: Player | None = None,
    ) -> None:
        self.player2: Player | None = other_player

        if self.player2:
            self.player1_choice: str | None = None
            self.player2_choice: str | None = None

    def check_human_win(self) -> Player:
        assert self.player1_choice is not None
        assert self.player2 is not None
        return self.player1 if self.BEATS[self.player1_choice] == self.player2_choice else self.player2

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        embed_color: DiscordColor = DEFAULT_COLOR,
        timeout: float | None = None,
    ) -> discord.Message:
        self.player1 = ctx.author

        self.embed = discord.Embed(
            title="Rock Paper Scissors",
            description="Select a button to play!",
            color=embed_color,
        )

        self.view = RPSView(self, button_style=button_style, timeout=timeout)
        self.message = await ctx.reply(embed=self.embed, view=self.view)
        self.view.message = self.message

        await self.view.wait()
        return self.message
