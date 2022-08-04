# https://github.com/bijij/BotBot
# https://github.com/python-discord/sir-lancebot

from __future__ import annotations

import asyncio
import io
import itertools
import json
import random
import re
from collections import defaultdict
from collections.abc import Iterable
from functools import cached_property, partial, wraps
from pathlib import Path
from random import choice, sample
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Union,
    overload,
)

import discord
import emojis
import pymongo
from aiofile import async_open
from cogs.meta.robopage import SimplePages
from core import Cog, Context, Parrot
from discord.ext import boardgames, commands  # type: ignore
from discord.ext import old_menus as menus  # type: ignore
from discord.utils import MISSING
from interactions.buttons.__2048 import Twenty48, Twenty48_Button
from interactions.buttons.__aki import Akinator
from interactions.buttons.__battleship import BetaBattleShip
from interactions.buttons.__chess import Chess
from interactions.buttons.__constants import (
    _2048_GAME,
    BIG,
    DIE,
    LETTERS_EMOJI,
    ORIGINAL,
    POINTS,
    SMALL,
    SUPER_BIG,
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
from interactions.buttons.__light_out import LightsOut
from interactions.buttons.__memory_game import MemoryGame
from interactions.buttons.__number_slider import NumberSlider
from interactions.buttons.__sokoban import SokobanGame, SokobanGameView
from interactions.buttons.__wordle import BetaWordle
from interactions.buttons.secret_hitler.ui.join import JoinUI
from pymongo import ReturnDocument
from pymongo.collection import Collection
from utilities.constants import Colours
from utilities.converters import convert_bool
from utilities.uno.game import UNO

from .__command_flags import (
    ChessStatsFlag,
    CountryGuessStatsFlag,
    HangmanGuessStatsFlag,
    MemoryStatsFlag,
    ReactionStatsFlag,
    TwentyFortyEightStatsFlag,
    TypingStatsFlag,
)

emoji = emojis  # Idk

DIAGRAPHS = {"1": "AN", "2": "ER", "3": "HE", "4": "IN", "5": "QU", "6": "TH"}


with open("extra/boggle.txt") as f:
    DICTIONARY = set(f.read().splitlines())


class Position(NamedTuple):
    col: int
    row: int


def ordinal(number: int, /) -> str:
    return f'{number}{"tsnrhtdd"[(number // 10 % 10 != 1) * (number % 10 < 4) * number % 10 :: 4]}'


class MadlibsTemplate(TypedDict):
    """Structure of a template in the madlibs JSON file."""

    title: str
    blanks: List[str]
    value: List[str]


class BoardBoogle:
    def __init__(self, *, size=ORIGINAL, board=None):
        self.size = size

        if board is None:
            board = DIE[self.size].copy()
            random.shuffle(board)
            board = [[random.choice(board[row * self.size + column]) for column in range(self.size)] for row in range(self.size)]

        self.columns = board

    def board_contains(
        self, word: str, pos: Position = None, passed: List[Position] = None
    ) -> bool:  # sourcery skip: use-itertools-product
        if passed is None:
            passed = []
        # Empty words
        if not word:
            return True

        # When starting out
        if pos is None:

            # Check all positions
            for col in range(self.size):
                for row in range(self.size):
                    if self.board_contains(word, Position(col, row)):
                        return True

        # Checking new squares
        elif pos not in passed:
            # Check if letter matches current start of word
            letter = self.columns[pos.col][pos.row]
            if letter.isdigit():
                letter = DIAGRAPHS[letter]

            if word[: len(letter)] == letter:

                # Check adjacent for next letter
                for x in range(-1, 2):
                    for y in range(-1, 2):

                        # don't check yourself
                        if x == 0 and y == 0:
                            continue

                        new_pos = Position(pos.col + x, pos.row + y)

                        # don't check out of bounds
                        if new_pos.col < 0 or new_pos.col >= self.size or new_pos.row < 0 or new_pos.row >= self.size:
                            continue

                        if self.board_contains(word[len(letter) :], new_pos, [*passed, pos]):
                            return True

        # Otherwise cannot find word
        return False

    def is_legal(self, word: str) -> bool:
        if len(word) < 3:
            return False
        word = word.upper()
        return False if word not in DICTIONARY else self.board_contains(word)

    def points(self, word: str) -> int:
        return POINTS[len(word)] if self.is_legal(word) else 0

    def total_points(self, words: Iterable[str]) -> int:
        return sum(self.points(word) for word in words)


class GameBoogle(menus.Menu):
    name: Optional[str] = "Boggle"
    footer: Optional[str] = None

    def __init__(self, *, size=ORIGINAL, **kwargs):
        self.board = BoardBoogle(size=size)
        self.setup()
        super().__init__(**kwargs)

    @property
    def state(self):
        state = ""

        for row in range(self.board.size):
            emoji = [LETTERS_EMOJI[self.board.columns[column][row]] for column in range(self.board.size)]

            state = " ".join(emoji) + "\n" + state

        return discord.Embed(title=self.name, description=state).set_footer(text=self.footer)

    def setup(self):
        raise NotImplementedError

    async def send_initial_message(self, ctx, channel):
        return await channel.send(content="Boggle game started, you have 3 minutes!", embed=self.state)

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)
        # await self.bot.loop.run_in_executor(None, lambda: self.board.legal_words)

    async def finalize(self, timed_out):
        self.bot.dispatch("boggle_game_complete", self.message.channel)

    def get_points(self, words: Iterable[str]) -> int:
        return self.board.total_points(words)

    def check_word(self, word: str) -> bool:
        return self.board.is_legal(word)

    async def check_message(self, message: discord.Message):
        raise NotImplementedError

    @menus.button("\N{BLACK SQUARE FOR STOP}\ufe0f", position=menus.Last(0))
    async def cancel(self, payload):
        await self.message.edit(content="Game Cancelled.")
        self.stop()


class ShuffflingGame(GameBoogle):
    def __init__(self, *, size=ORIGINAL, **kwargs):
        super().__init__(size=size, **kwargs)
        self.boards = [self.board]

    def shuffle(self):
        raise NotImplementedError

    async def shuffle_task(self):
        for i in range(5):
            await asyncio.sleep(30)
            if not self._running:
                return

            # Shuffle board
            self.shuffle()
            self.boards.append(self.board)

            # Note Board Updated
            await self.message.channel.send("Board Updated!")

            # Update Board Message
            time = [
                "2 minutes, 30 seconds",
                "2 minutes",
                "1 minute, 30 seconds",
                "1 minute",
                "30 seconds",
            ][i]
            await self.message.edit(content=f"Board Updated! You have {time} left!", embed=self.state)

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)
        self.bot.loop.create_task(self.shuffle_task())

    def get_points(self, words: Iterable[str]) -> int:
        points = 0
        for word in words:
            for board in self.boards:
                if pts := board.points(word):
                    points += pts
                    break

        return points


class DiscordGame(GameBoogle):
    name = "Discord Boggle"
    footer = "First to find a word wins points!"

    @property
    def scores(self):
        embed = discord.Embed()

        i = 0
        old = None

        for user, words in sorted(self.words.items(), key=lambda v: self.get_points(v[1]), reverse=True):
            points = self.get_points(words)

            if points != old:
                old = points
                i += 1

            embed.add_field(
                name=f"{ordinal(i)}: {user}",
                value=f"**{len(words)}** words, **{points}** points.",
                inline=False,
            )

        return embed

    def setup(self):
        self.all_words: set[str] = set()
        self.words: Dict[Union[discord.Member, discord.User], set[str]] = defaultdict(set)

    async def check_message(self, message: discord.Message):
        word = message.content
        if word is None:
            return

        if not word.isalpha():
            return
        word = word.upper()

        if not self.check_word(word):
            return

        if word in self.all_words:
            return

        # Add to user words
        self.all_words.add(word)
        self.words[message.author].add(word)

        await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    async def finalize(self, timed_out: bool):
        await super().finalize(timed_out)
        if timed_out:
            await self.message.edit(content="Game Over!")
            await self.message.reply(embed=self.scores)


class ClassicGame(GameBoogle):
    name = "Classic Boggle"
    footer = "Keep a list of words til the end!"

    @property
    def scores(self):
        embed = discord.Embed()

        i = 0
        old = None

        for user, unique in sorted(
            self.unique_words.items(),
            key=lambda v: self.board.total_points(v[1]),
            reverse=True,
        ):
            words = self.words[user]
            points = self.board.total_points(unique)

            if points != old:
                old = points
                i += 1

            embed.add_field(
                name=f"{ordinal(i)}: {user}",
                value=f"**{len(words)}** words, **{len(unique)}** unique, **{points}** points.",
                inline=False,
            )

        return embed

    def filter_lists(self):
        for user, word_list in self.word_lists.items():

            for word in word_list.split():
                word = word.strip().upper()

                if not word.isalpha():
                    continue

                if not self.check_word(word):
                    continue

                self.words[user].add(word)

                # Remove from all sets if not unique
                if word in self.used_words:
                    for ls in self.unique_words.values():
                        if word in ls:
                            ls.remove(word)
                    continue

                self.used_words.add(word)
                self.unique_words[user].add(word)

    async def check_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if not self.over:
            return

        if message.content is None:
            return

        if message.author in self.word_lists:
            return

        self.word_lists[message.author] = message.content
        await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    def setup(self):
        self.over = False
        self.used_words: set[str] = set()
        self.word_lists: Dict[Union[discord.Member, discord.User], str] = {}
        self.words: Dict[Union[discord.Member, discord.User], set[str]] = defaultdict(set)
        self.unique_words: Dict[Union[discord.Member, discord.User], set[str]] = defaultdict(set)

    async def finalize(self, timed_out: bool):
        await super().finalize(timed_out)

        if timed_out:
            await self.message.edit(content="Game Over!")
            await self.message.reply("Game Over! you have 10 seconds to send in your words.")
            self.over = True
            await asyncio.sleep(10)
            self.filter_lists()
            await self.message.reply(embed=self.scores)


class FlipGame(ShuffflingGame, DiscordGame):
    name = "Flip Boggle"
    footer = "Find words as fast as you can, rows will flip positions every 30 seconds."

    def shuffle(self):
        rows = [[self.board.columns[x][y] for x in range(self.board.size)] for y in range(self.board.size)]
        random.shuffle(rows)
        self.board = BoardBoogle(
            size=self.board.size,
            board=[[rows[x][y] for x in range(self.board.size)] for y in range(self.board.size)],
        )


class BoggleGame(ShuffflingGame, DiscordGame):
    name = "Boggle Boggle"
    footer = "Find words as fast as you can, letters will shuffle positions every 30 seconds."

    def shuffle(self):
        letters = [self.board.columns[y][x] for x in range(self.board.size) for y in range(self.board.size)]
        random.shuffle(letters)
        self.board = BoardBoogle(
            size=self.board.size,
            board=[letters[x * self.board.size : x * self.board.size + self.board.size] for x in range(self.board.size)],
        )


def check_size(ctx: Context) -> int:
    assert ctx.prefix is not None
    prefix = ctx.prefix.upper()
    if prefix.endswith("SUPER BIG "):
        return SUPER_BIG
    if prefix.endswith("BIG "):
        return BIG
    if prefix.endswith("SMALL ") or prefix.endswith("SMOL "):
        return SMALL
    return ORIGINAL


def boggle_game(game_type: type[Game]):
    def wrapper(signature):
        @wraps(signature)
        async def command(self: Games, ctx: Context):
            # Ignore if rules invoke
            if ctx.invoked_subcommand is self.boggle_rules:
                return

            # Raise if game already running
            if ctx.channel in self.games_boogle:
                raise commands.CheckFailure("There is already a game running in this channel.")

            # Start the game
            self.games_boogle[ctx.channel] = game = game_type(size=check_size(ctx))
            await game.start(ctx, wait=False)

            # Wait for game to end
            def check(channel):
                return channel.id == ctx.channel.id

            await self.bot.wait_for("boggle_game_complete", check=check, timeout=200)
            if ctx.channel in self.games_boogle:
                del self.games_boogle[ctx.channel]

        return command

    return wrapper


def fenPass(fen: str) -> bool:
    if not (
        regexMatch := re.match(
            r"\s*^(((?:[rnbqkpRNBQKP1-8]+\/){7})[rnbqkpRNBQKP1-8]+)\s([b|w])\s([K|Q|k|q]{1,4})\s(-|[a-h][1-8])\s(\d+\s\d+)$",
            fen,
        )
    ):
        raise commands.BadArgument(
            "FEN doesn`t match follow this example: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 "
        )
    regexList = regexMatch.groups()
    fen = regexList[0].split("/")
    if len(fen) != 8:
        raise commands.BadArgument("Expected 8 rows in position part of FEN: `{0}`".format(repr(fen)))

    for fenPart in fen:
        field_sum = 0
        previous_was_digit, previous_was_piece = False, False

        for c in fenPart:
            if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                if previous_was_digit:
                    raise commands.BadArgument("Two subsequent digits in position part of FEN: `{0}`".format(repr(fen)))
                field_sum += int(c)
                previous_was_digit = True
                previous_was_piece = False
            elif c == "~":
                if not previous_was_piece:
                    raise commands.BadArgument("~ not after piece in position part of FEN: `{0}`".format(repr(fen)))
                previous_was_digit, previous_was_piece = False, False
            elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                field_sum += 1
                previous_was_digit = False
                previous_was_piece = True
            else:
                raise commands.BadArgument("Invalid character in position part of FEN: `{0}`".format(repr(fen)))

        if field_sum != 8:
            raise commands.BadArgument("Expected 8 columns per row in position part of FEN: `{0}`".format(repr(fen)))


BoardState = List[List[Optional[bool]]]


STATES = (
    "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
)

NUMBERS = list(Emojis.number_emojis.values())
CROSS_EMOJI = Emojis.incident_unactioned

Coordinate = Optional[Tuple[int, int]]
EMOJI_CHECK = Union[discord.Emoji, discord.PartialEmoji, str]


class GameC4:
    """A Connect 4 Game."""

    def __init__(
        self,
        bot: Parrot,
        channel: discord.TextChannel,
        player1: discord.Member,
        player2: Optional[discord.Member],
        tokens: list,
        size: int = 7,
    ):
        self.bot = bot
        self.channel = channel
        self.player1 = player1
        self.player2 = player2 or AI_C4(self.bot, game=self)
        self.tokens = tokens

        self.grid = self.generate_board(size)
        self.grid_size = size

        self.unicode_numbers = [emojis.encode(i) for i in NUMBERS[: self.grid_size]]

        self.message: discord.Message = None

        self.player_active: Union[AI_C4, discord.Member, None] = None
        self.player_inactive: Union[AI_C4, discord.Member, None] = None

    @staticmethod
    def generate_board(size: int) -> List[List[int]]:
        """Generate the connect 4 board."""
        return [[0 for _ in range(size)] for _ in range(size)]

    async def print_grid(self) -> None:
        """Formats and outputs the Connect Four grid to the channel."""
        title = f"Connect 4: {self.player1}" f" VS {self.bot.user if isinstance(self.player2, AI_C4) else self.player2}"

        rows = [" ".join(str(self.tokens[s]) for s in row) for row in self.grid]
        first_row = " ".join(NUMBERS[: self.grid_size])
        formatted_grid = "\n".join([first_row] + rows)
        embed = discord.Embed(title=title, description=formatted_grid)

        if self.message:
            await self.message.edit(embed=embed)
        else:
            self.message = await self.channel.send(content="Loading...")
            for emoji in self.unicode_numbers:
                await self.message.add_reaction(emojis.encode(emoji))
            await self.message.add_reaction(CROSS_EMOJI)
            await self.message.edit(content=None, embed=embed)

    async def game_over(self, action: str, player1: discord.User, player2: discord.User) -> None:
        """Announces to public chat."""
        if action == "win":
            await self.channel.send(f"Game Over! {player1.mention} won against {player2.mention}")
        elif action == "draw":
            await self.channel.send(f"Game Over! {player1.mention} {player2.mention} It's A Draw :tada:")
        elif action == "quit":
            await self.channel.send(f"{self.player1.mention} surrendered. Game over!")
        await self.print_grid()

    async def start_game(self) -> None:
        """Begins the game."""
        self.player_active, self.player_inactive = self.player1, self.player2

        while True:
            await self.print_grid()

            if isinstance(self.player_active, AI_C4):
                coords = self.player_active.play()
                if not coords:
                    await self.game_over(
                        "draw",
                        self.bot.user if isinstance(self.player_active, AI_C4) else self.player_active,
                        self.bot.user if isinstance(self.player_inactive, AI_C4) else self.player_inactive,
                    )
            else:
                coords = await self.player_turn()

            if not coords:
                return

            if self.check_win(coords, 1 if self.player_active == self.player1 else 2):
                await self.game_over(
                    "win",
                    self.bot.user if isinstance(self.player_active, AI_C4) else self.player_active,
                    self.bot.user if isinstance(self.player_inactive, AI_C4) else self.player_inactive,
                )
                return

            self.player_active, self.player_inactive = (
                self.player_inactive,
                self.player_active,
            )

    def predicate(self, reaction: discord.Reaction, user: discord.Member) -> bool:
        """The predicate to check for the player's reaction."""
        return (
            reaction.message.id == self.message.id
            and user.id == self.player_active.id
            and str(reaction.emoji) in (*self.unicode_numbers, CROSS_EMOJI)
        )

    async def player_turn(self) -> Optional[Coordinate]:
        """Initiate the player's turn."""
        message = await self.channel.send(
            f"{self.player_active.mention}, it's your turn! React with the column you want to place your token in."
        )
        player_num = 1 if self.player_active == self.player1 else 2
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=self.predicate, timeout=30.0)
            except asyncio.TimeoutError:
                await self.channel.send(f"{self.player_active.mention}, you took too long. Game over!")
                return None
            else:
                await message.delete(delay=0)
                if str(reaction.emoji) == CROSS_EMOJI:
                    await self.game_over("quit", self.player_active, self.player_inactive)
                    return None

                try:
                    await self.message.remove_reaction(reaction, user)
                except discord.Forbidden:
                    pass

                column_num = self.unicode_numbers.index(str(reaction.emoji))
                column = [row[column_num] for row in self.grid]

                for row_num, square in reversed(list(enumerate(column))):
                    if not square:
                        self.grid[row_num][column_num] = player_num
                        return row_num, column_num
                message = await self.channel.send(f"Column {column_num + 1} is full. Try again")

    def check_win(self, coords: Coordinate, player_num: int) -> bool:
        """Check that placing a counter here would cause the player to win."""
        vertical = [(-1, 0), (1, 0)]
        horizontal = [(0, 1), (0, -1)]
        forward_diag = [(-1, 1), (1, -1)]
        backward_diag = [(-1, -1), (1, 1)]
        axes = [vertical, horizontal, forward_diag, backward_diag]

        for axis in axes:
            counters_in_a_row = 1  # The initial counter that is compared to
            for (row_incr, column_incr) in axis:
                row, column = coords
                row += row_incr
                column += column_incr

                while 0 <= row < self.grid_size and 0 <= column < self.grid_size and self.grid[row][column] == player_num:
                    counters_in_a_row += 1
                    row += row_incr
                    column += column_incr
            if counters_in_a_row >= 4:
                return True
        return False


class AI_C4:
    """The Computer Player for Single-Player games."""

    def __init__(self, bot: Parrot, game: GameC4):
        self.game = game
        self.mention = bot.user.mention

    def get_possible_places(self) -> List[Coordinate]:
        """Gets all the coordinates where the AI_C4 could possibly place a counter."""
        possible_coords: List[Coordinate] = []
        for column_num in range(self.game.grid_size):
            column = [row[column_num] for row in self.game.grid]
            for row_num, square in reversed(list(enumerate(column))):
                if not square:
                    possible_coords.append((row_num, column_num))
                    break
        return possible_coords

    def check_ai_win(self, coord_list: List[Coordinate]) -> Optional[Coordinate]:
        """
        Check AI_C4 win.
        Check if placing a counter in any possible coordinate would cause the AI_C4 to win
        with 10% chance of not winning and returning None
        """
        if random.randint(1, 10) == 1:
            return None
        return next(
            (coords for coords in coord_list if self.game.check_win(coords, 2)),
            None,
        )

    def check_player_win(self, coord_list: List[Coordinate]) -> Optional[Coordinate]:
        """
        Check Player win.
        Check if placing a counter in possible coordinates would stop the player
        from winning with 25% of not blocking them  and returning None.
        """
        if random.randint(1, 4) == 1:
            return None
        return next(
            (coords for coords in coord_list if self.game.check_win(coords, 1)),
            None,
        )

    @staticmethod
    def random_coords(coord_list: List[Coordinate]) -> Coordinate:
        """Picks a random coordinate from the possible ones."""
        return random.choice(coord_list)

    def play(self) -> Union[Coordinate, bool]:
        """
        Plays for the AI_C4.
        Gets all possible coords, and determins the move:
        1. coords where it can win.
        2. coords where the player can win.
        3. Random coord
        The first possible value is choosen.
        """
        possible_coords = self.get_possible_places()

        if not possible_coords:
            return False

        coords = (
            self.check_ai_win(possible_coords) or self.check_player_win(possible_coords) or self.random_coords(possible_coords)
        )

        row, column = coords
        self.game.grid[row][column] = 2
        return coords


class Board:
    def __init__(
        self,
        state: BoardState,
        current_player: bool = False,
    ) -> None:
        self.state = state
        self.current_player = current_player
        self.winner: Optional[bool] = MISSING

    @property
    def legal_moves(self) -> Iterator[Tuple[int, int]]:
        for c, r in itertools.product(range(3), range(3)):
            if self.state[r][c] is None:
                yield (r, c)

    @cached_property
    def over(self) -> bool:

        # vertical
        for c in range(3):
            token = self.state[0][c]
            if token is None:
                continue
            if self.state[1][c] == token and self.state[2][c] == token:
                self.winner = token
                return True

        # horizontal
        for r in range(3):
            token = self.state[r][0]
            if token is None:
                continue
            if self.state[r][1] == token and self.state[r][2] == token:
                self.winner = token
                return True

        # descending diag
        if self.state[0][0] is not None:
            token = self.state[0][0]
            if self.state[1][1] == token and self.state[2][2] == token:
                self.winner = token
                return True

        # ascending diag
        if self.state[0][2] is not None:
            token = self.state[0][2]
            if self.state[1][1] == token and self.state[2][0] == token:
                self.winner = token
                return True

        # Check if board is empty
        for _ in self.legal_moves:
            break
        else:
            self.winner = None
            return True

        return False

    def move(self, r: int, c: int) -> Board:
        if (r, c) not in self.legal_moves:
            raise ValueError("Illegal Move")

        new_state = [[self.state[r][c] for c in range(3)] for r in range(3)]
        new_state[r][c] = self.current_player

        return Board(new_state, not self.current_player)

    @classmethod
    def new_game(cls) -> Board:
        state: BoardState = [[None for _ in range(3)] for _ in range(3)]
        return cls(state)


class AI:
    def __init__(self, player: bool) -> None:
        self.player = player

    def move(self, game: Board) -> Board:
        column = random.choice(tuple(game.legal_moves))
        return game.move(*column)


class NegamaxAI(AI):
    def __init__(self, player: bool) -> None:
        super().__init__(player)

    def heuristic(self, game: Board, sign: int) -> float:
        player = not self.player if sign == -1 else self.player
        if game.over:
            if game.winner is None:
                return 0
            return 1_000_000 if game.winner == player else -1_000_000
        return random.randint(-10, 10)

    @overload
    def negamax(
        self,
        game: Board,
        depth: Literal[0] = ...,
        alpha: float = ...,
        beta: float = ...,
        sign: int = ...,
    ) -> Tuple[int, int]:
        ...

    @overload
    def negamax(
        self,
        game: Board,
        depth: int = ...,
        alpha: float = ...,
        beta: float = ...,
        sign: int = ...,
    ) -> float:
        ...

    def negamax(
        self,
        game: Board,
        depth: int = 0,
        alpha: float = float("-inf"),
        beta: float = float("inf"),
        sign: int = 1,
    ) -> Union[float, Tuple[int, int]]:
        if game.over:
            return sign * self.heuristic(game, sign)

        move = MISSING

        score = float("-inf")
        for c in game.legal_moves:
            move_score = -self.negamax(game.move(*c), depth + 1, -beta, -alpha, -sign)

            if move_score > score:
                score = move_score
                move = c

            alpha = max(alpha, score)
            if alpha >= beta:
                break

        return move if depth == 0 else score

    def move(self, game: Board) -> Board:
        return game.move(*self.negamax(game))


class ButtonTicTacToe(discord.ui.Button["GameTicTacToe"]):
    def __init__(self, r: int, c: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=c)
        self.r = r
        self.c = c

    def update(self):
        cell = self.view.board.state[self.r][self.c]

        if cell is not None or self.view.board.over:
            self.disabled = True

        if cell is True:
            self.style = discord.ButtonStyle.success
            self.label = "O"
        if cell is False:
            self.style = discord.ButtonStyle.danger
            self.label = "X"

    async def callback(self, interaction: discord.Interaction):

        self.view.board = self.view.board.move(self.r, self.c)
        self.view.update()

        if self.view.board.over:
            await self.view.game_over(interaction)
            return

        if self.view.current_player.bot:
            self.view.make_ai_move()
            self.view.update()

        if self.view.board.over:
            await self.view.game_over(interaction)
            return

        await interaction.response.edit_message(
            content=f"{self.view.current_player.mention}'s' ({STATES[self.view.board.current_player]}) turn!",
            view=self.view,
        )


class GameTicTacToe(discord.ui.View):
    children: Sequence[ButtonTicTacToe]

    def __init__(self, players: Tuple[discord.Member, discord.Member]):
        self.players = list(players)
        random.shuffle(self.players)
        super().__init__(timeout=None)
        self.board = Board.new_game()
        if self.current_player.bot:
            self.make_ai_move()
        for r, c in itertools.product(range(3), range(3)):
            self.add_item(ButtonTicTacToe(r, c))
        self.update()

    def update(self):
        for child in self.children:
            child.update()

    async def game_over(self, interaction: discord.Interaction):
        if self.board.winner is not None:
            content = f"{self.players[self.board.winner].mention} ({STATES[self.board.winner]}) wins!"
        else:
            content = "Draw!"

        for child in self.children:
            child.disabled = True  # flake8: noqa

        self.stop()
        return await interaction.response.edit_message(content=content, view=self)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user not in self.players:
            await interaction.response.send_message("Sorry, you are not playing", ephemeral=True)
            return False
        if interaction.user != self.current_player:
            await interaction.response.send_message("Sorry, it is not your turn!", ephemeral=True)
            return False
        return True

    def make_ai_move(self):
        ai = NegamaxAI(self.board.current_player)
        self.board = ai.move(self.board)

    @property
    def current_player(self) -> discord.Member:
        return self.players[self.board.current_player]


EmojiSet = Dict[Tuple[bool, bool], str]


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
    },
}

# This is for the opposing player's board which only shows aimed locations.
HIDDEN_EMOJIS = {
    (True, True): ":red_circle:",
    (True, False): ":black_circle:",
    (False, True): ":white_circle:",
    (False, False): ":black_circle:",
}

# For the top row of the board
LETTERS = (
    ":stop_button::regional_indicator_a::regional_indicator_b::regional_indicator_c::regional_indicator_d:"
    ":regional_indicator_e::regional_indicator_f::regional_indicator_g::regional_indicator_h:"
    ":regional_indicator_i::regional_indicator_j:"
)

# For the first column of the board
NUMBERS = [
    ":one:",
    ":two:",
    ":three:",
    ":four:",
    ":five:",
    ":six:",
    ":seven:",
    ":eight:",
    ":nine:",
    ":keycap_ten:",
]

CROSS_EMOJI = "\u274e"
HAND_RAISED_EMOJI = "\U0001f64b"


class Cell:
    def __init__(self, board, y: int, x: int):
        self.board = board
        self.y = y
        self.x = x
        self.mine = False
        self.clicked = False
        self.flagged = False

    @property
    def number(self):
        return sum(
            bool(0 <= y < self.board.size_y and 0 <= x < self.board.size_x and self.board[x, y].mine)
            for y, x in itertools.product(range(self.y - 1, self.y + 2), range(self.x - 1, self.x + 2))
        )

    def __str__(self):
        if self.clicked:

            number = "\u200b" if self.number == 0 else boardgames.keycap_digit(self.number)
            return "\N{COLLISION SYMBOL}" if self.mine else number
        return "\N{TRIANGULAR FLAG ON POST}" if self.flagged else "\N{WHITE LARGE SQUARE}"


class Game(boardgames.Board[Cell]):
    def __init__(self, size_x=10, size_y=7):
        super().__init__(size_x, size_y)
        self.record = None
        self.last_state = None

        self._state = [[Cell(self, y, x) for x in range(self.size_x)] for y in range(self.size_y)]

    def setup(self, click_y: int, click_x: int):
        """Places mines on the board"""
        cells = [(i // self.size_x, i % self.size_x) for i in range(self.size_x * self.size_y)]
        cells.remove((click_y, click_x))

        for y, x in sample(
            cells,
            int((self.size_x * self.size_y + 1) // ((self.size_x * self.size_y) ** 0.5)),
        ):
            self[x, y].mine = True

    @property
    def num_mines(self) -> int:
        """Returns the number of mines"""
        count = 0
        for row in self:
            for cell in row:
                if cell.mine:
                    count += 1
        return count

    @property
    def num_flags(self) -> int:
        """Returns the currently placed number of flags"""
        count = 0
        for row in self:
            for cell in row:
                if cell.flagged:
                    count += 1
        return count

    @property
    def lost(self) -> bool:
        """Returns wether the game was lost or not."""
        for row in self:
            for cell in row:
                if cell.mine and cell.clicked:
                    return True
        return False

    @property
    def solved(self) -> bool:
        """Returns wether the board has been solved"""
        count = 0
        for row in self:
            for cell in row:
                if cell.clicked:
                    count += 1
        return count >= self.size_y * self.size_x - self.num_mines

    def click(self, y: int, x: int):
        """Clicks on a cell"""
        if self.size_x < x or self.size_y < y:
            raise commands.BadArgument("Cell out side the board.")

        cell = self[x, y]

        if not self.num_mines:
            self.setup(y, x)

        if cell.flagged:
            raise commands.BadArgument("You cannot click on a flagged cell.")

        cell.clicked = True

    def flag(self, y: int, x: int):
        """Flags a cell"""
        if self.size_x < x or self.size_y < y:
            raise commands.BadArgument("Cell out side the board.")

        cell = self[x, y]

        if cell.clicked:
            raise commands.BadArgument("You cannot flag a revealed cell.")

        cell.flagged = not cell.flagged

    def clean(self):
        """Cleans up the board state"""
        for y, row in enumerate(self):
            for x, cell in enumerate(row):
                if cell.clicked and not cell.number:
                    for i, j in itertools.product(range(y - 1, y + 2), range(x - 1, x + 2)):
                        if 0 <= i < self.size_y and 0 <= j < self.size_x and not self[j, i].clicked:
                            self[j, i].flagged = False
                            self[j, i].clicked = True
                            self.clean()


class Button(discord.ui.Button["GameUI"]):
    def __init__(self, x: int, y: int, offset: int):
        self.x = x
        self.y = y
        self.offset = offset
        super().__init__(style=discord.ButtonStyle.blurple, label="\u200b", row=y)

    @property
    def cell(self):
        return self.view.meta.board[self.x, self.y + self.offset]

    def reveal(self):
        self.disabled = True
        self.style = discord.ButtonStyle.secondary
        self.label = str(self.cell)

        if self.cell.mine:
            self.style = discord.ButtonStyle.danger
        elif self.cell.flagged:
            self.style = discord.ButtonStyle.success
        elif self.cell.clicked:
            self.label = str(self.cell.number or "\u200b")

    def click(self):
        self.view.meta.board.click(self.y + self.offset, self.x)
        self.view.meta.board.clean()

        for view in self.view.meta.views:
            for child in view.children:
                if child.cell.clicked:
                    child.reveal()

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.click()
        await self.view.meta.update()


class GameUI(discord.ui.View):
    children: List[Button]

    def __init__(self, meta: MetaGameUI, offset: int):
        self.meta = meta
        self.offset = offset
        self.message = discord.utils.MISSING
        super().__init__(timeout=None)
        for r, c in itertools.product(range(5), range(5)):
            self.add_item(Button(r, c, offset))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.meta.player:
            await interaction.response.send_message("Sorry, you are not playing", ephemeral=True)
            return False
        return True

    async def update(self):
        if self.offset != 0:
            content = "\u200b"
        elif self.meta.board.lost:
            content = "💥"
        elif self.meta.board.solved:
            content = ":tada:"
        else:
            content = "Minesweeper!"
        await self.message.edit(content=content, view=self)


class MetaGameUI:
    def __init__(self, player: discord.Member, channel: discord.TextChannel, size: int = 2):
        self.player = player
        self.channel = channel

        self.board = Game(5, size * 5)
        self.views = [GameUI(self, i * 5) for i in range(size)]

    async def update(self):
        if self.board.lost or self.board.solved:
            for view in self.views:
                for child in view.children:
                    child.disabled = True
                view.stop()

        for view in self.views:
            await view.update()

    async def start(self):
        for view in self.views:
            view.message = await self.channel.send(content="Minesweeper" if view.offset == 0 else "\u200b", view=view)


def is_no_game(ctx: Context):
    if ctx.channel in ctx.cog._games:
        raise commands.CheckFailure("There is already a Minesweeper game running.")
    return True


def is_game(ctx: Context):
    try:
        is_no_game(ctx)
    except commands.CheckFailure:
        return True
    raise commands.CheckFailure("No Connect Four game is running.")


class Games(Cog):
    """Play the classic Games!"""

    def __init__(self, bot: Parrot):
        self.bot = bot
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

        with open(madlibs_stories) as file:
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
        if self.already_playing(ctx.author):  # If they've joined a game since requesting a player 2
            return True  # Is dealt with later on
        if (
            user.id not in (ctx.me.id, ctx.author.id)
            and str(reaction.emoji) == HAND_RAISED_EMOJI
            and reaction.message.id == announcement.id
        ):
            if self.already_playing(user):
                self.bot.loop.create_task(ctx.send(f"{user.mention} You're already playing a game!"))
                self.bot.loop.create_task(announcement.remove_reaction(reaction, user))
                return False

            if user in self.waiting:
                self.bot.loop.create_task(ctx.send(f"{user.mention} Please cancel your game first before joining another one."))
                self.bot.loop.create_task(announcement.remove_reaction(reaction, user))
                return False

            return True

        return user.id == ctx.author.id and str(reaction.emoji) == CROSS_EMOJI and reaction.message.id == announcement.id

    def already_playing(self, player: discord.Member) -> bool:
        """Check if someone is already in a game."""
        return any(player in (game.p1.user, game.p2.user) for game in self.games)

    async def _get_opponent(self, ctx: Context) -> Optional[discord.Member]:
        message = await ctx.channel.send(
            embed=discord.Embed(description=f"{ctx.author.mention} wants to play Tic-Tac-Toe.").set_footer(
                text="react with \N{WHITE HEAVY CHECK MARK} to accept the challenge."
            )
        )
        await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        def check(reaction, user):
            if reaction.emoji != "\N{WHITE HEAVY CHECK MARK}":
                return False
            return False if user.bot else user != ctx.author

        try:
            _, opponent = await self.bot.wait_for("reaction_add", check=check, timeout=60)
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
        if self.already_playing_cf(ctx.author):  # If they've joined a game since requesting a player 2
            return True  # Is dealt with later on

        if (
            user.id not in (ctx.me.id, ctx.author.id)
            and str(reaction.emoji) == Emojis.hand_raised
            and reaction.message.id == announcement.id
        ):
            if self.already_playing_cf(user):
                self.bot.loop.create_task(ctx.send(f"{user.mention} You're already playing a game!"))
                self.bot.loop.create_task(announcement.remove_reaction(reaction, user))
                return False

            if user in self.waiting_c4:
                self.bot.loop.create_task(ctx.send(f"{user.mention} Please cancel your game first before joining another one."))
                self.bot.loop.create_task(announcement.remove_reaction(reaction, user))
                return False

            return True

        return user.id == ctx.author.id and str(reaction.emoji) == CROSS_EMOJI and reaction.message.id == announcement.id

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
            game = GameC4(self.bot, ctx.channel, ctx.author, user, self.tokens, size=board_size)
            self.games_c4.append(game)
            await game.start_game()
            self.games_c4.remove(game)
        except Exception as e:
            # End the game in the event of an unforeseen error so the players aren't stuck in a game
            await ctx.send(f"{ctx.author.mention} {user.mention if user else ''} An error occurred. Game failed | Error: {e}")
            if game in self.games_c4:
                self.games_c4.remove(game)
            raise

    @commands.group(
        invoke_without_command=True,
        aliases=("4inarow", "connect4", "connectfour", "c4"),
        case_insensitive=True,
    )
    @commands.bot_has_permissions(manage_messages=True, embed_links=True, add_reactions=True)
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
    async def tictactoe(self, ctx: Context, *, opponent: Optional[discord.Member] = None):
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

        await ctx.send(f"{game.current_player.mention}'s (X) turn!", view=game)  # flake8: noqa

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
        game.last_state = await ctx.send(f"Minesweeper Game Started!\n>>> {game}\n\nReveal cells with `{ctx.prefix}ms click`.")

    @ms_start.command(name="easy")
    async def ms_start_easy(self, ctx: Context):
        """Starts a easy difficulty Minesweeper game"""
        game = self._games[ctx.channel] = Game(10, 7)
        game.last_state = await ctx.send(f"Minesweeper Game Started!\n>>> {game}\n\nReveal cells with `{ctx.prefix}ms click`.")

    @ms_start.command(name="medium")
    async def ms_start_medium(self, ctx: Context):
        """Starts a medium difficulty Minesweeper game"""
        game = self._games[ctx.channel] = Game(17, 8)
        game.last_state = await ctx.send(f"Minesweeper Game Started!\n>>> {game}\n\nReveal cells with `{ctx.prefix}ms click`.")

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
            return await ctx.send(f"{ctx.author.mention} for now existing levels are from range 1-10")
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
            return await ctx.send(f"{ctx.author.mention} board size must not less than 4")
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
            await ctx.send(f"{ctx.author.mention} Seems like there's no one here to play...")
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
            await ctx.send(f"{ctx.author.mention} Seems like there's no one here to play...")
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
            raise commands.BadArgument("There is already a game running in this channel.")

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
            return message.channel.id == ctx.channel.id and message.author.id == ctx.author.id

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
                message = await self.bot.wait_for("message", check=author_check, timeout=60)
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

        blanks = [self.edited_content.pop(msg_id, submitted_words[msg_id]) for msg_id in submitted_words]

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

        story_embed.set_footer(text=f"Generated for {ctx.author}", icon_url=ctx.author.display_avatar.url)

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
            await ctx.send(f"{ctx.author.mention} Seems like there's no one here to play...")
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
        flag: TwentyFortyEightStatsFlag,
    ):
        """2048 Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `moves` or `games`
        `--sort`: Sort the list either `1` (ascending) or `-1` (descending)
        """
        user = user or ctx.author
        col: Collection = self.bot.mongo.extra.games_leaderboard

        sort_by = "games_played" if flag.sort_by.lower() == "games" else flag.sort_by.lower()
        sort_by = "moves" if sort_by == "total_moves" else sort_by

        FILTER = {"twenty48": {"$exists": True}}

        if flag.me:
            FILTER["_id"] = user.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}
        entries = []
        async for data in col.find(FILTER).sort(sort_by, flag.sort):
            user = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, data["_id"])
            entries.append(
                f"""User: `{user or 'NA'}`
`Games Played`: {data['twenty48']['games_played']} games played
`Total Moves `: {data['twenty48']['total_moves']} moves
"""
            )
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
        flag: CountryGuessStatsFlag,
    ):
        """Country Guess Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `win` or `games`
        `--sort`: Sort the list either `1` (ascending) or `-1` (descending)
        """
        return await self.__guess_stats(game_type="country_guess", ctx=ctx, user=user, flag=flag)

    @top.command(name="hangman")
    async def hangman_stats(
        self,
        ctx: Context,
        user: Optional[discord.User] = None,
        *,
        flag: HangmanGuessStatsFlag,
    ):
        """Country Guess Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `win` or `games`
        `--sort`: Sort the list either `1` (ascending) or `-1` (descending)
        """
        return await self.__guess_stats(game_type="hangman", ctx=ctx, user=user, flag=flag)

    async def __guess_stats(
        self,
        *,
        game_type: str,
        ctx: Context,
        user: Optional[discord.User] = None,
        flag: Union[CountryGuessStatsFlag, HangmanGuessStatsFlag],
    ):
        user = user or ctx.author
        col: Collection = self.bot.mongo.extra.games_leaderboard

        sort_by = "games_played" if flag.sort_by.lower() == "games" else flag.sort_by.lower()
        sort_by = "games_won" if sort_by == "win" else sort_by

        FILTER = {game_type: {"$exists": True}}

        if flag.me and flag._global:
            return await ctx.send(f"{ctx.author.mention} you can't use both `--me` and `--global` at the same time!")

        if flag.me:
            FILTER["_id"] = user.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}

        entries = []
        async for data in col.find(FILTER).sort(sort_by, flag.sort):
            user = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, data["_id"])
            entries.append(
                f"""User: `{user or 'NA'}`
`Games Played`: {data[game_type].get('games_played', 0)} games played
`Total Wins  `: {data[game_type].get('games_won', 0)} Wins
"""
            )
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
        flag: ChessStatsFlag,
    ):
        """Chess Game stats

        Flag Options:
        `--sort_by`: Sort the list either by `winner` or `draw`
        `--sort`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        user = user or ctx.author
        col: Collection = self.bot.mongo.extra.games_leaderboard

        sort_by = flag.sort_by

        data = await col.find_one_and_update(
            {"_id": user.id, "chess": {"$exists": True}},
            {
                "$push": {
                    "chess": {
                        "$each": [],
                        "$sort": {sort_by: int(flag.sort)},
                        "$slice": int(flag.limit),
                    }
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not data:
            await ctx.send(f"{f'{ctx.author.mention} you' if user is ctx.author else user} haven't played chess yet!")

            return
        entries = []
        chess_data = data["chess"]
        for i in chess_data:
            user1 = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, i["white"])
            user2 = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, i["black"])
            if ctx.author.id in {user1.id, user2.id}:
                entries.append(
                    f"""**{user1 or 'NA'} vs {user2 or 'NA'}**
`Winner`: {i["winner"]}
`Draw  `: {i["draw"]}
"""
                )
            else:
                entries.append(
                    f"""{user1 or 'NA'} vs {user2 or 'NA'}
`Winner`: {i["winner"]}
`Draw  `: {i["draw"]}
"""
                )
        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command(name="reaction")
    async def top_reaction(self, ctx: Context, *, flag: ReactionStatsFlag):
        """Reaction Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        await self.__test_stats("reaction_test", ctx, flag)

    @top.command(name="memory")
    async def top_memory(self, ctx: Context, *, flag: MemoryStatsFlag):
        """Memory Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        await self.__test_stats("memory_test", ctx, flag)

    async def __test_stats(self, name: str, ctx: Context, flag: ReactionStatsFlag):
        entries = []
        i = 1
        FILTER = {name: {"$exists": True}}
        if flag.me:
            FILTER["_id"] = ctx.author.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}

        col: Collection = self.bot.mongo.extra.games_leaderboard
        async for data in col.find(FILTER).sort(name, flag.sort):
            user = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, data["_id"])
            if user.id == ctx.author.id:
                entries.append(
                    f"""**{user or 'NA'}**
`Minimum Time`: {data[name]}
"""
                )
            else:
                entries.append(
                    f"""{user or 'NA'}
`Minimum Time`: {data[name]}
"""
                )
            if i >= flag.limit:
                break
            i += 1

        if not entries:
            await ctx.send(f"{ctx.author.mention} No records found")
            return

        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command("typing")
    async def top_typing(self, ctx: Context, *, flag: TypingStatsFlag):
        """Typing Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list by any of the following: `speed`, `accuracy`, `wpm`
        `--sort`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        entries = []
        i = 1
        FILTER = {"typing_test": {"$exists": True}}
        if flag.me:
            FILTER["_id"] = ctx.author.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}

        col: Collection = self.bot.mongo.extra.games_leaderboard

        async for data in col.find(
            FILTER,
        ).sort(f"typing_test.{flag.sort_by}", flag.sort):

            user = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, data["_id"])

            if user.id == ctx.author.id:
                entries.append(
                    f"""**{user or 'NA'}**
`Minimum Time`: {round(data["typing_test"]['speed'], 2)} seconds
`Accuracy    `: {int(data["typing_test"]['accuracy'])} %
`Word Per Min`: {data["typing_test"]['wpm']}
"""
                )
            else:
                entries.append(
                    f"""{user or 'NA'}
`Minimum Time`: {round(data["typing_test"]['speed'], 2)} seconds
`Accuracy    `: {int(data["typing_test"]['accuracy'])} %
`Word Per Min`: {data["typing_test"]['wpm']}
"""
                )
            if i >= flag.limit:
                break
            i += 1

        if not entries:
            await ctx.send(f"{ctx.author.mention} No records found")
            return

        p = SimplePages(entries, ctx=ctx)
        await p.start()

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

        (minimum_solutions,) = random.choices(range(len(SOLN_DISTR)), weights=SOLN_DISTR)
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
                    await self.end_game(channel, game, end_message=f"{msg.author.display_name} GOOSED!")
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
            await self.append_to_found_embed(game, f"{str(answer):12s}  -  {msg.author.display_name}")
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
        )
        embed.set_image(url="attachment://board.png")
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

    async def end_game(self, channel: discord.TextChannel, game: DuckGame, end_message: str) -> None:
        """Edit the game embed to reflect the end of the game and mark the game as not running."""
        game.running = False

        scoreboard_embed = discord.Embed(
            title=end_message,
            color=discord.Color.dark_purple(),
        )
        scores = sorted(
            game.scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        scoreboard = "Final scores:\n\n" + "\n".join(f"{member.display_name}: {score}" for member, score in scores)

        scoreboard_embed.description = scoreboard
        await channel.send(embed=scoreboard_embed)

        if missed := [ans for ans in game.solutions if ans not in game.claimed_answers]:
            missed_text = "Flights everyone missed:\n" + "\n".join(f"{ans}" for ans in missed)
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
        embed.set_footer(text="Tip: using Discord's compact message display mode can help keep the board on the screen")
        return await ctx.send(file=file, embed=embed)

    @commands.command("uno", aliases=["unogame"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def play_uno(self, ctx: Context, /) -> None:
        if ctx.channel.id in self.uno_games:
            return await ctx.error("An instance of UNO is already running in this channel.")

        game = UNO(ctx)
        self.uno_games[ctx.channel.id] = game

        await game.start()
        await game.wait()

        try:
            del self.uno_games[ctx.channel.id]
        except KeyError:
            pass
