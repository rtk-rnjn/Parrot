# https://github.com/bijij/BotBot
# https://github.com/python-discord/sir-lancebot
# https://github.com/Tom-the-Bomb/Discord-Games

from __future__ import annotations

import asyncio
import io
import json
import random
import re
from functools import partial, wraps
from pathlib import Path
from random import choice, sample
from typing import Any, Callable, Dict, List, Literal, Optional, Set, Tuple

import pymongo
from aiofile import async_open
from discord.utils import MISSING
from pymongo import ReturnDocument
from pymongo.collection import Collection

import discord
import emojis
from cogs.meta.robopage import SimplePages
from core import Cog, Context, Parrot
from discord.ext import boardgames, commands  # type: ignore
from discord.ext import old_menus as menus  # type: ignore
from interactions.buttons.__2048 import Twenty48, Twenty48_Button
from interactions.buttons.__aki import Akinator
from interactions.buttons.__battleship import BetaBattleShip
from interactions.buttons.__chess import Chess
from interactions.buttons.__constants import (
    _2048_GAME,
    CHOICES,
    CROSS_EMOJI,
    EMOJI_CHECK,
    HAND_RAISED_EMOJI,
    SHORT_CHOICES,
    WINNER_DICT,
    Emojis,
)
from interactions.buttons.__country_guess import BetaCountryGuesser
from interactions.buttons.__duckgame import (
    ANSWER_REGEX,
    CORRECT_GOOSE,
    CORRECT_SOLN,
    EMOJI_WRONG,
    GAME_DURATION,
    HELP_IMAGE_PATH,
    HELP_TEXT,
    INCORRECT_GOOSE,
    INCORRECT_SOLN,
    SOLN_DISTR,
    DuckGame,
    assemble_board_image,
)
from interactions.buttons.__games_utils import (
    BoggleGame,
    ClassicGame,
    DiscordGame,
    FlipGame,
    Game,
    GameC4,
    GameTicTacToe,
    MadlibsTemplate,
    MetaGameUI,
    boggle_game,
    fenPass,
    is_game,
    is_no_game,
)
from interactions.buttons.__light_out import LightsOut
from interactions.buttons.__memory_game import MemoryGame
from interactions.buttons.__number_slider import NumberSlider
from interactions.buttons.__sokoban import SokobanGame, SokobanGameView
from interactions.buttons.__wordle import BetaWordle
from interactions.buttons.secret_hitler.ui.join import JoinUI
from utilities.constants import Colours
from utilities.converters import convert_bool
from utilities.uno.game import UNO

from .__command_flags import GameCommandFlag

emoji = emojis  # Idk


class Games(Cog):
    """Play the classic Games!"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.ON_TESTING = False
        self.games: List[Game] = []
        self.waiting: List[discord.Member] = []
        self._games: Dict[discord.TextChannel, Game] = {}
        self.games_c4: List[GameC4] = []
        self.waiting_c4: List[discord.Member] = []
        self.games_boogle: Dict[discord.TextChannel, Game] = {}
        self.tokens = [":white_circle:", ":blue_circle:", ":red_circle:"]
        self.games_hitler: Dict[int, discord.ui.View] = {}
        self.chess_games: List[int] = []

        self.max_board_size = 9
        self.min_board_size = 5
        self.templates = self._load_templates()
        self.edited_content: Dict[int, str] = {}
        self.checks: Set[Callable] = set()
        self.current_games: Dict[int, DuckGame] = {}
        self.uno_games: Dict[int, UNO] = {}

    @staticmethod
    def _load_templates() -> List[MadlibsTemplate]:
        madlibs_stories = Path("extra/madlibs_templates.json")

        with open(madlibs_stories, encoding="utf-8", errors="ignore") as file:
            return json.load(file)

    @staticmethod
    def madlibs_embed(part_of_speech: str, number_of_inputs: int) -> discord.Embed:
        """Method to generate an embed with the game information."""
        madlibs_embed = discord.Embed(title="Madlibs", color=Colours.python_blue)

        madlibs_embed.add_field(
            name="Enter a word that fits the given part of speech!",
            value=f"Part of speech: {part_of_speech}\n\nMake sure not to spam, or you may get auto-muted!",
        )

        madlibs_embed.set_footer(text=f"Inputs remaining: {number_of_inputs}")

        return madlibs_embed

    @Cog.listener()
    async def on_message_edit(self, _: discord.Message, after: discord.Message) -> None:
        """A listener that checks for message edits from the user."""
        for check in self.checks:
            if check(after):
                break
        else:
            return

        self.edited_content[after.id] = after.content

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{VIDEO GAME}")

    def predicate(
        self,
        ctx: Context,
        announcement: discord.Message,
        reaction: discord.Reaction,
        user: discord.Member,
    ) -> bool:
        """Predicate checking the criteria for the announcement message."""
        if self.already_playing(
            ctx.author
        ):  # If they've joined a game since requesting a player 2
            return True  # Is dealt with later on
        if (
            user.id not in (ctx.me.id, ctx.author.id)
            and str(reaction.emoji) == HAND_RAISED_EMOJI
            and reaction.message.id == announcement.id
        ):
            if self.already_playing(user):
                self.bot.loop.create_task(
                    ctx.send(f"{user.mention} You're already playing a game!")
                )
                self.bot.loop.create_task(announcement.remove_reaction(reaction, user))
                return False

            if user in self.waiting:
                self.bot.loop.create_task(
                    ctx.send(
                        f"{user.mention} Please cancel your game first before joining another one."
                    )
                )
                self.bot.loop.create_task(announcement.remove_reaction(reaction, user))
                return False

            return True

        return (
            user.id == ctx.author.id
            and str(reaction.emoji) == CROSS_EMOJI
            and reaction.message.id == announcement.id
        )

    def already_playing(self, player: discord.Member) -> bool:
        """Check if someone is already in a game."""
        return any(player in (game.p1.user, game.p2.user) for game in self.games)

    async def _get_opponent(self, ctx: Context) -> Optional[discord.Member]:
        message = await ctx.channel.send(
            embed=discord.Embed(
                description=f"{ctx.author.mention} wants to play Tic-Tac-Toe."
            ).set_footer(
                text="react with \N{WHITE HEAVY CHECK MARK} to accept the challenge."
            )
        )
        await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        def check(reaction, user):
            if reaction.emoji != "\N{WHITE HEAVY CHECK MARK}":
                return False
            return False if user.bot else user != ctx.author

        try:
            _, opponent = await self.bot.wait_for(
                "reaction_add", check=check, timeout=60
            )
            return opponent
        except asyncio.TimeoutError:
            pass
        finally:
            await message.delete()
        return None

    async def check_author(self, ctx: Context, board_size: int) -> bool:
        """Check if the requester is free and the board size is correct."""
        if self.already_playing_cf(ctx.author):
            await ctx.send("You're already playing a game!")
            return False

        if ctx.author in self.waiting_c4:
            await ctx.send("You've already sent out a request for a player 2")
            return False

        if not self.min_board_size <= board_size <= self.max_board_size:
            await ctx.send(
                f"{board_size} is not a valid board size. A valid board size is "
                f"between `{self.min_board_size}` and `{self.max_board_size}`."
            )
            return False

        return True

    def get_player(
        self,
        ctx: Context,
        announcement: discord.Message,
        reaction: discord.Reaction,
        user: discord.Member,
    ) -> bool:
        """Predicate checking the criteria for the announcement message."""
        if self.already_playing_cf(
            ctx.author
        ):  # If they've joined a game since requesting a player 2
            return True  # Is dealt with later on

        if (
            user.id not in (ctx.me.id, ctx.author.id)
            and str(reaction.emoji) == Emojis.hand_raised
            and reaction.message.id == announcement.id
        ):
            if self.already_playing_cf(user):
                self.bot.loop.create_task(
                    ctx.send(f"{user.mention} You're already playing a game!")
                )
                self.bot.loop.create_task(announcement.remove_reaction(reaction, user))
                return False

            if user in self.waiting_c4:
                self.bot.loop.create_task(
                    ctx.send(
                        f"{user.mention} Please cancel your game first before joining another one."
                    )
                )
                self.bot.loop.create_task(announcement.remove_reaction(reaction, user))
                return False

            return True

        return (
            user.id == ctx.author.id
            and str(reaction.emoji) == CROSS_EMOJI
            and reaction.message.id == announcement.id
        )

    def already_playing_cf(self, player: discord.Member) -> bool:
        """Check if someone is already in a game."""
        return any(player in (game.player1, game.player2) for game in self.games_c4)

    @staticmethod
    def check_emojis(e1: EMOJI_CHECK, e2: EMOJI_CHECK) -> Tuple[bool, Optional[str]]:
        """Validate the emojis, the user put."""
        if isinstance(e1, str) and emoji.count(e1) != 1:
            return False, e1
        if isinstance(e2, str) and emoji.count(e2) != 1:
            return False, e2
        return True, None

    async def _play_game(
        self,
        ctx: Context,
        user: Optional[discord.Member],
        board_size: int,
        emoji1: Any,
        emoji2: Any,
    ) -> None:
        """Helper for playing a game of connect four."""
        self.tokens = [":white_circle:", emoji1, emoji2]
        game = None  # if game fails to intialize in try...except

        try:
            game = GameC4(
                self.bot, ctx.channel, ctx.author, user, self.tokens, size=board_size
            )
            self.games_c4.append(game)
            await game.start_game()
            self.games_c4.remove(game)
        except Exception as e:
            # End the game in the event of an unforeseen error so the players aren't stuck in a game
            await ctx.send(
                f"{ctx.author.mention} {user.mention if user else ''} An error occurred. Game failed | Error: {e}"
            )
            if game in self.games_c4:
                self.games_c4.remove(game)
            raise

    @commands.group(
        invoke_without_command=True,
        aliases=("4inarow", "connect4", "connectfour", "c4"),
        case_insensitive=True,
    )
    @commands.bot_has_permissions(
        manage_messages=True, embed_links=True, add_reactions=True
    )
    async def connect_four(
        self,
        ctx: Context,
        board_size: Optional[int] = None,
        emoji1: Optional[EMOJI_CHECK] = None,
        emoji2: Optional[EMOJI_CHECK] = None,
    ) -> None:
        """
        Play the classic game of Connect Four with someone!
        Sets up a message waiting for someone else to react and play along.
        The game will start once someone has reacted.
        All inputs will be through reactions.
        """
        emoji1 = emoji1 or "\N{LARGE BLUE CIRCLE}"
        emoji2 = emoji2 or "\N{LARGE RED CIRCLE}"
        board_size = board_size or 7
        check, emoji = self.check_emojis(emoji1, emoji2)
        if not check:
            raise commands.EmojiNotFound(emoji)

        check_author_result = await self.check_author(ctx, board_size)
        if not check_author_result:
            return

        announcement = await ctx.send(
            "**Connect Four**: A new game is about to start!\n"
            f"Press {Emojis.hand_raised} to play against {ctx.author.mention}!\n"
            f"(Cancel the game with {CROSS_EMOJI}.)"
        )
        self.waiting_c4.append(ctx.author)
        await announcement.add_reaction(Emojis.hand_raised)
        await announcement.add_reaction(CROSS_EMOJI)

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=partial(self.get_player, ctx, announcement),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            self.waiting_c4.remove(ctx.author)
            await announcement.delete()
            await ctx.send(
                f"{ctx.author.mention} Seems like there's no one here to play. "
                f"Use `{ctx.prefix}{ctx.invoked_with} ai` to play against a computer."
            )
            return

        if str(reaction.emoji) == CROSS_EMOJI:
            self.waiting_c4.remove(ctx.author)
            await announcement.delete()
            await ctx.send(f"{ctx.author.mention} Game cancelled.")
            return

        await announcement.delete()
        self.waiting_c4.remove(ctx.author)
        if self.already_playing_cf(ctx.author):
            return

        await self._play_game(ctx, user, board_size, emoji1, emoji2)

    @connect_four.command(aliases=("bot", "computer", "cpu"))
    async def ai(
        self,
        ctx: Context,
        board_size: int = 7,
        emoji1: EMOJI_CHECK = "\N{LARGE BLUE CIRCLE}",
        emoji2: EMOJI_CHECK = "\N{LARGE RED CIRCLE}",
    ) -> None:
        """Play Connect Four against a computer player."""
        check, emoji = self.check_emojis(emoji1, emoji2)
        if not check:
            raise commands.EmojiNotFound(emoji)

        check_author_result = await self.check_author(ctx, board_size)
        if not check_author_result:
            return

        await self._play_game(ctx, None, board_size, emoji1, emoji2)

    @commands.command(aliases=["akinator"])
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def aki(self, ctx: Context):
        """Answer the questions and let the bot guess your character!"""
        await Akinator().start(ctx)

    @commands.command(aliases=["tic", "tic_tac_toe", "ttt"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def tictactoe(
        self, ctx: Context, *, opponent: Optional[discord.Member] = None
    ):
        """Start a Tic-Tac-Toe game!
        `opponent`: Another member of the server to play against. If not is set an open challenge is started.
        """
        if opponent is None:
            opponent = await self._get_opponent(ctx)
        else:
            if opponent == ctx.author:
                raise commands.BadArgument("You cannot play against yourself.")
            if not opponent.bot and not await ctx.confirm(
                ctx.channel,
                opponent,
                f"{opponent.mention}, {ctx.author} has challenged you to Tic-Tac-Toe! do you accept?",
            ):
                opponent = None

        # If challenge timed out
        if opponent is None:
            raise commands.BadArgument("Challenge cancelled.")

        game = GameTicTacToe((ctx.author, opponent))

        await ctx.send(
            f"{game.current_player.mention}'s (X) turn!", view=game
        )  # flake8: noqa

    @commands.group(name="minesweeper", aliases=["ms"], invoke_without_command=True)
    async def minesweeper(self, ctx: Context):
        """Minesweeper game commands"""
        await self.bot.invoke_help_command(ctx)

    @minesweeper.group(name="start")
    @commands.check(is_no_game)
    async def ms_start(self, ctx: Context):
        """Starts a Minesweeper game"""
        if ctx.invoked_subcommand is None:
            await MetaGameUI(ctx.author, ctx.channel).start()

    @ms_start.command(name="tiny")
    async def ms_start_tiny(self, ctx: Context):
        """Starts a easy difficulty Minesweeper game"""
        game = self._games[ctx.channel] = Game(5, 5)
        game.last_state = await ctx.send(
            f"Minesweeper Game Started!\n>>> {game}\n\nReveal cells with `{ctx.prefix}ms click`."
        )

    @ms_start.command(name="easy")
    async def ms_start_easy(self, ctx: Context):
        """Starts a easy difficulty Minesweeper game"""
        game = self._games[ctx.channel] = Game(10, 7)
        game.last_state = await ctx.send(
            f"Minesweeper Game Started!\n>>> {game}\n\nReveal cells with `{ctx.prefix}ms click`."
        )

    @ms_start.command(name="medium")
    async def ms_start_medium(self, ctx: Context):
        """Starts a medium difficulty Minesweeper game"""
        game = self._games[ctx.channel] = Game(17, 8)
        game.last_state = await ctx.send(
            f"Minesweeper Game Started!\n>>> {game}\n\nReveal cells with `{ctx.prefix}ms click`."
        )

    @minesweeper.command(name="click")
    @commands.check(is_game)
    async def ms_click(self, ctx: Context, cells: commands.Greedy[boardgames.Cell]):
        """Clicks a cell on the board.
        cells are referenced by column then row for example `A2`"""
        game = self._games[ctx.channel]

        for cell in cells:
            game.click(*cell)

        game.clean()

        message = ""
        if game.lost:
            message += "\nToo bad, you lose."
        elif game.solved:
            message += "\nCongratulations, you win! :tada:"

        if game.last_state is not None:
            try:
                await game.last_state.delete()
            except Exception:
                pass
        game.last_state = await ctx.send(f">>> {game}{message}")

        # If game over delete the game.
        if game.lost or game.solved:
            del self._games[ctx.channel]

    @minesweeper.command(name="flag", aliases=["guess"])
    @commands.check(is_game)
    async def ms_flag(self, ctx: Context, cells: commands.Greedy[boardgames.Cell]):
        """Flags a cell on the board.
        cells are referenced by column then row for example `A2`"""
        game = self._games[ctx.channel]

        for cell in cells:
            game.flag(*cell)

        if game.last_state is not None:
            try:
                await game.last_state.delete()
            except Exception:
                pass
        game.last_state = await ctx.send(f">>> {game}")

    @commands.command()
    async def rps(self, ctx: Context, move: str) -> None:
        """Play the classic game of Rock Paper Scissors with your own Parrot!"""
        move = move.lower()
        player_mention = ctx.author.mention

        if move not in CHOICES and move not in SHORT_CHOICES:
            raise commands.BadArgument(
                f"Invalid move. Please make move from options: {', '.join(CHOICES).upper()}."
            )

        bot_move = choice(CHOICES)
        # value of player_result will be from (-1, 0, 1) as (lost, tied, won).
        player_result = WINNER_DICT[move[0]][bot_move[0]]

        if player_result == 0:
            message_string = f"{player_mention} You and **{self.bot.user.name}** played {bot_move}, it's a tie."
            await ctx.reply(message_string)
        elif player_result == 1:
            await ctx.reply(
                f"{player_mention} **{self.bot.user.name}** {bot_move}! {ctx.author.name} won!"
            )
        else:
            await ctx.reply(
                f"{player_mention} **{self.bot.user.name}** {bot_move}! {ctx.author.name} lost!"
            )

    @commands.group(invoke_without_command=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def sokoban(
        self,
        ctx: Context,
        level: Optional[int] = None,
    ):
        """A classic sokoban game"""
        if ctx.invoked_subcommand:
            return
        level = level or 1
        if not 10 >= level >= 1:
            return await ctx.send(
                f"{ctx.author.mention} for now existing levels are from range 1-10"
            )
        async with async_open(f"extra/sokoban/level{level or 1}.txt", "r") as fp:
            lvl_str = await fp.read()
        ls = [list(list(i)) for i in lvl_str.split("\n")]
        game = SokobanGame(ls)
        game._get_cords()
        main_game = SokobanGameView(game, ctx.author, level=level, ctx=ctx)
        await main_game.start(ctx)

    @sokoban.command(name="custom")
    async def custom_sokoban(self, ctx: Context, *, text: str):
        """To make a custom sokoban Game. Here are some rules to make:
        - Your level must be enclosed with `#`
        - Your level must have atleast one target block (`.`) one box (`$`)
        - Your level must have only and only 1 character (`@`)
        - There should be equal number of `.` (target) and `$` (box)
        """
        level = text.strip("```")
        ls = [list(list(i)) for i in level.split("\n")]
        game = SokobanGame(ls)
        game._get_cords()
        main_game = SokobanGameView(game, ctx.author, level=None, ctx=ctx)
        await main_game.start(ctx)

    @commands.command(name="2048")
    @commands.bot_has_permissions(embed_links=True)
    async def _2048(self, ctx: Context, *, boardsize: int = None):
        """Classis 2048 Game"""
        boardsize = boardsize or 4
        if boardsize < 4:
            return await ctx.send(
                f"{ctx.author.mention} board size must not less than 4"
            )
        if boardsize > 10:
            return await ctx.send(f"{ctx.author.mention} board size must less than 10")

        game = Twenty48(_2048_GAME, size=boardsize)
        game.start()
        BoardString = game.number_to_emoji()
        embed = discord.Embed(
            title="2048 Game",
            description=f"{BoardString}",
        ).set_footer(text=f"User: {ctx.author}")
        await ctx.send(
            ctx.author.mention,
            embed=embed,
            view=Twenty48_Button(game, ctx.author, bot=self.bot),
        )

    @commands.group(name="chess", invoke_without_command=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def chess(self, ctx: Context):
        """Chess game. In testing"""
        if ctx.invoked_subcommand:
            return
        announcement: discord.Message = await ctx.send(
            "**Chess**: A new game is about to start!\n"
            f"Press {HAND_RAISED_EMOJI} to play against {ctx.author.mention}!\n"
            f"(Cancel the game with {CROSS_EMOJI}.)"
        )
        self.waiting.append(ctx.author)
        await announcement.add_reaction(HAND_RAISED_EMOJI)
        await announcement.add_reaction(CROSS_EMOJI)

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=partial(self.predicate, ctx, announcement),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            self.waiting.remove(ctx.author)
            await announcement.delete()
            await ctx.send(
                f"{ctx.author.mention} Seems like there's no one here to play..."
            )
            return

        if str(reaction.emoji) == CROSS_EMOJI:
            self.waiting.remove(ctx.author)
            await announcement.delete()
            await ctx.send(f"{ctx.author.mention} Game cancelled.")
            return

        await announcement.delete()
        game = Chess(
            white=ctx.author,
            black=user,
            bot=self.bot,
            ctx=ctx,
        )
        await game.start()

    @chess.command()
    async def custom_chess(self, ctx: Context, board: fenPass):  # type: ignore
        """To play chess, from a custom FEN notation"""
        announcement: discord.Message = await ctx.send(
            "**Chess**: A new game is about to start!\n"
            f"Press {HAND_RAISED_EMOJI} to play against {ctx.author.mention}!\n"
            f"(Cancel the game with {CROSS_EMOJI}.)"
        )
        self.waiting.append(ctx.author)
        await announcement.add_reaction(HAND_RAISED_EMOJI)
        await announcement.add_reaction(CROSS_EMOJI)

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=partial(self.predicate, ctx, announcement),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            self.waiting.remove(ctx.author)
            await announcement.delete()
            await ctx.send(
                f"{ctx.author.mention} Seems like there's no one here to play..."
            )
            return

        if str(reaction.emoji) == CROSS_EMOJI:
            self.waiting.remove(ctx.author)
            await announcement.delete()
            await ctx.send(f"{ctx.author.mention} Game cancelled.")
            return

        await announcement.delete()

        game = Chess(white=ctx.author, black=user, bot=self.bot, ctx=ctx, custom=board)
        await game.start()

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def slidingpuzzle(self, ctx: Context, boardsize: Literal[1, 2, 3, 4, 5] = 4):
        """A Classic Sliding game"""
        await NumberSlider(boardsize).start(ctx)

    @commands.group(invoke_without_command=True)
    @boggle_game(DiscordGame)
    async def boggle(self, ctx: Context):
        """Start's a game of Boggle.
        The board size can be set by command prefix.
        `$big boggle` will result in a 5x5 board.
        `$super big boggle` will result in a 6x6 board.
        Players have 3 minutes to find as many words as they can, the first person to find
        a word gets the points.
        """
        ...

    @boggle.command(name="classic")
    @boggle_game(ClassicGame)
    async def boggle_classic(self, ctx: Context):
        """Starts a cassic game of boggle.
        Players will write down as many words as they can and send after 3 minutes has passed.
        Points are awarded to players with unique words.
        """
        ...

    @boggle.command(name="flip")
    @boggle_game(FlipGame)
    async def boggle_flip(self, ctx: Context):
        """Starts a flip game of boggle.
        Rows will randomly shuffle every 30s.
        The first person to finda word gets the points.
        """
        ...

    @boggle.command(name="boggle")
    @boggle_game(BoggleGame)
    async def boggle_boggle(self, ctx: Context):
        """Starts a boggling game of boggle.
        All letters will randomly shuffle flip every 30s.
        The first person to finda word gets the points.
        """
        ...

    @boggle.error
    @boggle_classic.error
    @boggle_flip.error
    @boggle_boggle.error
    async def on_boggle_error(self, ctx, error):
        if not isinstance(error, commands.CheckFailure) and ctx.channel in self.games:
            del self.games[ctx.channel]

    @boggle.command(name="rules", aliases=["help"])
    async def boggle_rules(self, ctx: Context, type: str = "discord"):
        """Displays information about a given boggle game type."""
        embed = discord.Embed(
            title="About Boggle:",
            description="The goal of Boggle is to using at least 3 adjacent letters, create words, longer words score more points.",
        )
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/735564593048584343/811590353748230184/boggle-rules-jpeg-900x1271_orig.png"
        )
        await ctx.send(embed=embed)

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        # Check if channel has a game going
        if message.channel not in self.games_boogle:
            return

        if isinstance(message.channel, discord.TextChannel):
            game: Game = self.games_boogle[message.channel]
            await game.check_message(message)

    @commands.command(aliases=["umbrogus", "secret_hitler", "secret-hitler"])
    @commands.bot_has_permissions(embed_links=True)
    async def secrethitler(self, ctx: Context) -> None:
        if ctx.channel.id in self.games_hitler:
            raise commands.BadArgument(
                "There is already a game running in this channel."
            )

        self.games_hitler[ctx.channel.id] = MISSING
        await JoinUI.start(ctx, self.games_hitler)

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def madlibs(self, ctx: Context) -> None:
        """
        Play Madlibs with the bot!
        Madlibs is a game where the player is asked to enter a word that
        fits a random part of speech (e.g. noun, adjective, verb, plural noun, etc.)
        a random amount of times, depending on the story chosen by the bot at the beginning.
        """
        random_template = choice(self.templates)

        def author_check(message: discord.Message) -> bool:
            return (
                message.channel.id == ctx.channel.id
                and message.author.id == ctx.author.id
            )

        self.checks.add(author_check)

        loading_embed = discord.Embed(
            title="Madlibs",
            description="Loading your Madlibs game...",
            color=Colours.python_blue,
        )
        original_message = await ctx.send(embed=loading_embed)

        submitted_words = {}

        for i, part_of_speech in enumerate(random_template["blanks"]):
            inputs_left = len(random_template["blanks"]) - i

            madlibs_embed = self.madlibs_embed(part_of_speech, inputs_left)
            await original_message.edit(embed=madlibs_embed)

            try:
                message = await self.bot.wait_for(
                    "message", check=author_check, timeout=60
                )
            except TimeoutError:
                timeout_embed = discord.Embed(
                    description="Uh oh! You took too long to respond!",
                    color=Colours.soft_red,
                )

                await ctx.send(ctx.author.mention, embed=timeout_embed)

                for msg_id in submitted_words:
                    self.edited_content.pop(msg_id, submitted_words[msg_id])

                self.checks.remove(author_check)

                return

            submitted_words[message.id] = message.content

        blanks = [
            self.edited_content.pop(msg_id, submitted_words[msg_id])
            for msg_id in submitted_words
        ]

        self.checks.remove(author_check)

        story = []
        for value, blank in zip(random_template["value"], blanks):
            story.append(f"{value}__{blank}__")

        # In each story template, there is always one more "value"
        # (fragment from the story) than there are blanks (words that the player enters)
        # so we need to compensate by appending the last line of the story again.
        story.append(random_template["value"][-1])

        story_embed = discord.Embed(
            title=random_template["title"],
            description="".join(story),
            color=Colours.bright_green,
        )

        story_embed.set_footer(
            text=f"Generated for {ctx.author}", icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=story_embed)

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def wordle(self, ctx: Context):
        """To start wordle game"""
        await BetaWordle().start(ctx)

    @commands.command(aliases=["lightsout"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def lightout(self, ctx: Context, count: int = 4):
        """Light Out Game"""
        lg = LightsOut(count)
        await lg.start(ctx, timeout=120)

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def countryguess(self, ctx: Context, is_flag: convert_bool = False):
        """Country guessing game"""
        cg = BetaCountryGuesser(is_flags=is_flag)
        await cg.start(ctx, timeout=120)

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def battleship(self, ctx: Context):
        """Solo Battleship Game"""
        announcement: discord.Message = await ctx.send(
            "**Battleship**: A new game is about to start!\n"
            f"Press {HAND_RAISED_EMOJI} to play against {ctx.author.mention}!\n"
            f"(Cancel the game with {CROSS_EMOJI}.)"
        )
        self.waiting.append(ctx.author)
        await announcement.add_reaction(HAND_RAISED_EMOJI)
        await announcement.add_reaction(CROSS_EMOJI)

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=partial(self.predicate, ctx, announcement),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            self.waiting.remove(ctx.author)
            await announcement.delete()
            await ctx.send(
                f"{ctx.author.mention} Seems like there's no one here to play..."
            )
            return

        if str(reaction.emoji) == CROSS_EMOJI:
            self.waiting.remove(ctx.author)
            await announcement.delete()
            await ctx.send(f"{ctx.author.mention} Game cancelled.")
            return

        await announcement.delete()
        bs = BetaBattleShip(player1=ctx.author, player2=user)
        await bs.start(ctx, timeout=120)

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def memory(self, ctx: Context):
        """Memory Game"""
        await MemoryGame().start(ctx, timeout=120)

    @commands.group(invoke_without_command=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def top(self, ctx: Context):
        """To display your statistics of games, WIP"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @top.command(name="2048")
    async def twenty_four_eight_stats(
        self,
        ctx: Context,
        user: Optional[discord.User] = None,
        *,
        flag: GameCommandFlag,
    ):
        """2048 Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `moves` or `played`
        `--order_by`: Sort the list either `asc` (ascending) or `desc` (descending)
        `--limit`: To limit the search, default is 100
        """
        user = user or ctx.author
        col: Collection = self.bot.game_collections
        sort_by = (
            f"game_twenty48_{flag.sort_by.lower()}"
            if flag.sort_by
            else "game_twenty48_played"
        )
        order_by = pymongo.ASCENDING if flag.order_by == "asc" else pymongo.DESCENDING

        FILTER = {sort_by: {"$exists": True}}

        if flag.me:
            FILTER["_id"] = user.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}
        LIMIT = flag.limit or float("inf")
        entries = []
        i = 0
        async for data in col.find(FILTER).sort(sort_by, order_by):
            user: Optional[discord.Member] = await self.bot.get_or_fetch_member(
                ctx.guild, data["_id"], in_guild=False
            )
            entries.append(
                f"""User: `{user or 'NA'}`
`Games Played`: {data['game_twenty48_played']} games played
`Total Moves `: {data['game_twenty48_moves']} moves
"""
            )
            if i > LIMIT:
                break
            i += 1
        if not entries:
            await ctx.send(f"{ctx.author.mention} No results found")
            return

        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command(name="countryguess")
    async def country_guess_stats(
        self,
        ctx: Context,
        user: Optional[discord.User] = None,
        *,
        flag: GameCommandFlag,
    ):
        """Country Guess Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `moves` or `played`
        `--order_by`: Sort the list either `asc` (ascending) or `desc` (descending)
        `--limit`: To limit the search, default is 100
        """
        return await self.__guess_stats(
            game_type="country_guess", ctx=ctx, user=user, flag=flag
        )

    @top.command(name="hangman")
    async def hangman_stats(
        self,
        ctx: Context,
        user: Optional[discord.User] = None,
        *,
        flag: GameCommandFlag,
    ):
        """Country Guess Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `win` or `games`
        `--order_by`: Sort the list either `1` (ascending) or `-1` (descending)
        """
        return await self.__guess_stats(
            game_type="hangman", ctx=ctx, user=user, flag=flag
        )

    async def __guess_stats(
        self,
        *,
        game_type: str,
        ctx: Context,
        user: Optional[discord.User] = None,
        flag: GameCommandFlag,
    ):
        user = user or ctx.author
        col: Collection = self.bot.game_collections

        sort_by = f"game_{game_type}_{flag.sort_by or 'played'}"
        order_by = pymongo.ASCENDING if flag.order_by == "asc" else pymongo.DESCENDING

        FILTER = {sort_by: {"$exists": True}}

        if flag.me and flag._global:
            return await ctx.send(
                f"{ctx.author.mention} you can't use both `--me` and `--global` at the same time!"
            )

        if flag.me:
            FILTER["_id"] = user.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}

        LIMIT = flag.limit or float("inf")
        entries = []
        i = 0
        async for data in col.find(FILTER).sort(sort_by, order_by):
            user = await self.bot.get_or_fetch_member(
                ctx.guild, data["_id"], in_guild=False
            )
            entries.append(
                f"""User: `{user or 'NA'}`
`Games Played`: {data[f'game_{game_type}_played']} games played
`Total Wins  `: {data[f'game_{game_type}_won']} Wins
`Total Loss  `: {data[f'game_{game_type}_loss']} Loss
"""
            )
            if i > LIMIT:
                break
            i += 1
        if not entries:
            await ctx.send(f"{ctx.author.mention} No records found")
            return

        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command(name="chess")
    async def chess_stats(
        self,
        ctx: Context,
        user: Optional[discord.User] = None,
        *,
        flag: GameCommandFlag,
    ):
        """Chess Game stats

        Flag Options:
        `--sort_by`: Sort the list either by `won` or `draw`
        `--order_by`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        user = user or ctx.author
        col: Collection = self.bot.game_collections

        sort_by = flag.sort_by

        data = await col.find_one(
            {"_id": user.id, "game_chess_played": {"$exists": True}},
        )
        if not data:
            await ctx.send(
                f"{f'{ctx.author.mention} you' if user is ctx.author else user} haven't played chess yet!"
            )

            return
        entries = []
        chess_data = data["game_chess_stat"]
        for i in chess_data:
            user1 = await self.bot.getch(
                self.bot.get_user, self.bot.fetch_user, i["game_chess_player_1"]
            )
            user2 = await self.bot.getch(
                self.bot.get_user, self.bot.fetch_user, i["game_chess_player_2"]
            )
            if not user1 and not user2:
                continue

            if ctx.author.id in {user1.id, user2.id}:
                entries.append(
                    f"""**{user1 or 'NA'} vs {user2 or 'NA'}**
`Winner`: {i["game_chess_winner"]}
"""
                )
            else:
                entries.append(
                    f"""{user1 or 'NA'} vs {user2 or 'NA'}
`Winner`: {i["game_chess_winner"]}
"""
                )
        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command(name="reaction")
    async def top_reaction(self, ctx: Context, *, flag: GameCommandFlag):
        """Reaction Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--order_by`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        await self.__test_stats("reaction_test", ctx, flag)

    @top.command(name="memory")
    async def top_memory(self, ctx: Context, *, flag: GameCommandFlag):
        """Memory Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--order_by`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        await self.__test_stats("memory_test", ctx, flag)

    async def __test_stats(self, game_type: str, ctx: Context, flag: GameCommandFlag):
        entries = []
        i = 1
        sort_by = f"game_{game_type}_{flag.sort_by or 'played'}".replace(
            " ", "_"
        ).lower()
        FILTER = {sort_by: {"$exists": True}}
        if flag.me:
            FILTER["_id"] = ctx.author.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}

        LIMIT = flag.limit or float("inf")
        col: Collection = self.bot.game_collections
        async for data in col.find(FILTER).sort(
            sort_by, pymongo.ASCENDING if flag.order_by == "asc" else pymongo.DESCENDING
        ):
            user: Optional[discord.Member] = await self.bot.get_or_fetch_member(
                ctx.guild, data["_id"], in_guild=False
            )
            if user is None:
                continue

            if user.id == ctx.author.id:
                entries.append(
                    f"""**{user or 'NA'}**
`{sort_by.replace('_', ' ').title()}`: {data[sort_by]}
"""
                )
            else:
                entries.append(
                    f"""{user or 'NA'}
`{sort_by.replace('_', ' ').title()}`: {data[sort_by]}
"""
                )
            if i >= LIMIT:
                break
            i += 1

        if not entries:
            await ctx.send(f"{ctx.author.mention} No records found")
            return

        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command("typing")
    async def top_typing(self, ctx: Context, *, flag: GameCommandFlag):
        """Typing Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list by any of the following: `speed`, `accuracy`, `wpm`
        `--order_by`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        await self.__test_stats("typing_test", ctx, flag)

    @commands.group(
        name="duckduckduckgoose",
        aliases=["dddg", "ddg", "duckduckgoose", "duckgoose"],
        invoke_without_command=True,
    )
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.channel)
    async def duck_start_game(self, ctx: Context) -> None:
        """Start a new Duck Duck Duck Goose game."""
        if ctx.channel.id in self.current_games:
            await ctx.send("There's already a game running!")
            return

        (minimum_solutions,) = random.choices(
            range(len(SOLN_DISTR)), weights=SOLN_DISTR
        )
        game = DuckGame(minimum_solutions=minimum_solutions)
        game.running = True
        self.current_games[ctx.channel.id] = game

        game.board_msg = await self.send_board_embed(ctx, game)
        game.found_msg = await self.send_found_embed(ctx)
        await asyncio.sleep(GAME_DURATION)

        # Checking for the channel ID in the currently running games is not sufficient.
        # The game could have been ended by a player, and a new game already started in the same channel.
        if game.running:
            try:
                del self.current_games[ctx.channel.id]
                await self.end_game(ctx.channel, game, end_message="Time's up!")
            except KeyError:
                pass

    @Cog.listener("on_message")
    async def duck_game_on_message(self, msg: discord.Message) -> None:
        """Listen for messages and process them as answers if appropriate."""
        if msg.author.bot:
            return

        channel = msg.channel
        if channel.id not in self.current_games:
            return

        game = self.current_games[channel.id]
        if msg.content.strip().lower() == "goose":
            # If all of the solutions have been claimed, i.e. the "goose" call is correct.
            if len(game.solutions) == len(game.claimed_answers):
                try:
                    del self.current_games[channel.id]
                    game.scores[msg.author] += CORRECT_GOOSE
                    await self.end_game(
                        channel, game, end_message=f"{msg.author.display_name} GOOSED!"
                    )
                except KeyError:
                    pass
            else:
                await msg.add_reaction(EMOJI_WRONG)
                game.scores[msg.author] += INCORRECT_GOOSE
            return

        # Valid answers contain 3 numbers.
        if not (match := re.match(ANSWER_REGEX, msg.content)):
            return
        answer = tuple(sorted(int(m) for m in match.groups()))

        # Be forgiving for answers that use indices not on the board.
        if any((0 <= n < len(game.board) for n in answer)):
            return

        # Also be forgiving for answers that have already been claimed (and avoid penalizing for racing conditions).
        if answer in game.claimed_answers:
            return

        if answer in game.solutions:
            game.claimed_answers[answer] = msg.author
            game.scores[msg.author] += CORRECT_SOLN
            await self.append_to_found_embed(
                game, f"{str(answer):12s}  -  {msg.author.display_name}"
            )
        else:
            await msg.add_reaction(EMOJI_WRONG)
            game.scores[msg.author] += INCORRECT_SOLN

    async def send_board_embed(self, ctx: Context, game: DuckGame) -> discord.Message:
        """Create and send an embed to display the board."""
        image = assemble_board_image(game.board, game.rows, game.columns)
        with io.BytesIO() as image_stream:
            image.save(image_stream, format="png")
            image_stream.seek(0)
            file = discord.File(fp=image_stream, filename="board.png")
        embed = discord.Embed(
            title="Duck Duck Duck Goose!",
            color=discord.Color.dark_purple(),
        ).set_image(url="attachment://board.png")
        return await ctx.send(embed=embed, file=file)

    async def send_found_embed(self, ctx: Context) -> discord.Message:
        """Create and send an embed to display claimed answers. This will be edited as the game goes on."""
        # Can't be part of the board embed because of discord.py limitations with editing an embed with an image.
        embed = discord.Embed(
            title="Flights Found",
            color=discord.Color.dark_purple(),
        )
        return await ctx.send(embed=embed)

    async def append_to_found_embed(self, game: DuckGame, text: str) -> None:
        """Append text to the claimed answers embed."""
        async with game.editing_embed:
            (found_embed,) = game.found_msg.embeds
            old_desc = found_embed.description or ""
            found_embed.description = f"{old_desc.rstrip()}\n{text}"
            await game.found_msg.edit(embed=found_embed)

    async def end_game(
        self, channel: discord.TextChannel, game: DuckGame, end_message: str
    ) -> None:
        """Edit the game embed to reflect the end of the game and mark the game as not running."""
        game.running = False

        scoreboard_embed = discord.Embed(
            title=end_message,
            color=discord.Color.dark_purple(),
        )
        scores: List[discord.Member, int] = sorted(
            game.scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        scoreboard = "Final scores:\n\n" + "\n".join(
            f"{member.display_name}: {score}" for member, score in scores
        )

        scoreboard_embed.description = scoreboard
        await channel.send(embed=scoreboard_embed)

        if missed := [ans for ans in game.solutions if ans not in game.claimed_answers]:
            missed_text = "Flights everyone missed:\n" + "\n".join(
                f"{ans}" for ans in missed
            )
        else:
            missed_text = "All the flights were found!"
        await self.append_to_found_embed(game, f"\n{missed_text}")

    @duck_start_game.command(name="help")
    async def show_rules(self, ctx: Context) -> None:
        """Explain the rules of the game."""
        await self.send_help_embed(ctx)

    @duck_start_game.command(name="stop")
    @commands.has_permissions(manage_messages=True)
    async def stop_game(self, ctx: Context) -> None:
        """Stop a currently running game. Only available to mods."""
        try:
            game = self.current_games.pop(ctx.channel.id)
        except KeyError:
            await ctx.send("No game currently running in this channel")
            return
        await self.end_game(ctx.channel, game, end_message="Game canceled.")

    @staticmethod
    async def send_help_embed(ctx: Context) -> discord.Message:
        """Send rules embed."""
        embed = discord.Embed(
            title="Compete against other players to find valid flights!",
            color=discord.Color.dark_purple(),
        )
        embed.description = HELP_TEXT
        file = discord.File(HELP_IMAGE_PATH, filename="help.png")
        embed.set_image(url="attachment://help.png")
        embed.set_footer(
            text="Tip: using Discord's compact message display mode can help keep the board on the screen"
        )
        return await ctx.send(file=file, embed=embed)

    @commands.command("uno", aliases=["unogame"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def play_uno(self, ctx: Context, /) -> None:
        """Play a game of Uno."""
        if ctx.channel.id in self.uno_games:
            return await ctx.error(
                "An instance of UNO is already running in this channel."
            )

        game = UNO(ctx)
        self.uno_games[ctx.channel.id] = game

        await game.start()
        await game.wait()

        try:
            del self.uno_games[ctx.channel.id]
        except KeyError:
            pass
