from __future__ import annotations

import asyncio
import itertools
import random
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from functools import cached_property, wraps
from typing import TYPE_CHECKING, Literal, NamedTuple, TypedDict, overload

from discord.utils import MISSING

import discord
import emojis
from core import Context, Parrot
from discord.ext import boardgames, commands, old_menus as menus

from .__constants import (
    BIG,
    CROSS_EMOJI,
    DIAGRAPHS,
    DIE,
    LETTERS_EMOJI,
    NUMBERS,
    ORIGINAL,
    POINTS,
    SMALL,
    STATES,
    SUPER_BIG,
    BoardState,
    Coordinate,
)

with open("extra/boggle.txt", encoding="utf-8", errors="ignore") as f:
    DICTIONARY = set(f.read().splitlines())


class Position(NamedTuple):
    col: int
    row: int


def ordinal(number: int, /) -> str:
    return f'{number}{"tsnrhtdd"[(number // 10 % 10 != 1) * (number % 10 < 4) * number % 10 :: 4]}'


class MadlibsTemplate(TypedDict):
    """Structure of a template in the madlibs JSON file."""

    title: str
    blanks: list[str]
    value: list[str]


class BoardBoogle:
    def __init__(self, *, size=ORIGINAL, board=None):
        self.size = size

        if board is None:
            board = DIE[self.size].copy()
            random.shuffle(board)
            board = [
                [random.choice(board[row * self.size + column]) for column in range(self.size)] for row in range(self.size)
            ]

        self.columns = board

    def board_contains(self, word: str, pos: Position = None, passed: list[Position] = None) -> bool:
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

        elif pos not in passed:
            # Check if letter matches current start of word
            letter = self.columns[pos.col][pos.row]
            if letter.isdigit():
                letter = DIAGRAPHS[letter]

            if word[: len(letter)] == letter:
                # Check adjacent for next letter
                for x, y in itertools.product(range(-1, 2), range(-1, 2)):
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
    name: str | None = "Boggle"
    footer: str | None = None

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
        self.words: dict[discord.Member | discord.User, set[str]] = defaultdict(set)

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
        self.word_lists: dict[discord.Member | discord.User, str] = {}
        self.words: dict[discord.Member | discord.User, set[str]] = defaultdict(set)
        self.unique_words: dict[discord.Member | discord.User, set[str]] = defaultdict(set)

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
    if TYPE_CHECKING:
        from .games import Games

    def wrapper(signature):
        @wraps(signature)
        async def command(self: Games, ctx: Context):
            # Ignore if rules invoke
            if ctx.invoked_subcommand is self.boggle_rules:
                return

            # Raise if game already running
            if ctx.channel in self.games_boogle:
                msg = "There is already a game running in this channel."
                raise commands.CheckFailure(msg)

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
        msg = "FEN doesn`t match follow this example: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 "
        raise commands.BadArgument(
            msg,
        )
    regexList = regexMatch.groups()
    fen = regexList[0].split("/")
    if len(fen) != 8:
        msg = f"Expected 8 rows in position part of FEN: `{repr(fen)}`"
        raise commands.BadArgument(msg)

    for fenPart in fen:
        field_sum = 0
        previous_was_digit, previous_was_piece = False, False

        for c in fenPart:
            if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                if previous_was_digit:
                    msg = f"Two subsequent digits in position part of FEN: `{repr(fen)}`"
                    raise commands.BadArgument(msg)
                field_sum += int(c)
                previous_was_digit = True
                previous_was_piece = False
            elif c == "~":
                if not previous_was_piece:
                    msg = f"~ not after piece in position part of FEN: `{repr(fen)}`"
                    raise commands.BadArgument(msg)
                previous_was_digit, previous_was_piece = False, False
            elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                field_sum += 1
                previous_was_digit = False
                previous_was_piece = True
            else:
                msg = f"Invalid character in position part of FEN: `{repr(fen)}`"
                raise commands.BadArgument(msg)

        if field_sum != 8:
            msg = f"Expected 8 columns per row in position part of FEN: `{repr(fen)}`"
            raise commands.BadArgument(msg)


class GameC4:
    """A Connect 4 Game."""

    if TYPE_CHECKING:
        from .__constants import Coordinate

    def __init__(
        self,
        bot: Parrot,
        channel: discord.TextChannel,
        player1: discord.Member | discord.User,
        player2: discord.Member | discord.User | None,
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

        self.message: discord.Message | None = None

        self.player_active: AI_C4 | discord.Member | discord.User | None = None
        self.player_inactive: AI_C4 | discord.Member | discord.User | None = None

    @staticmethod
    def generate_board(size: int) -> list[list[int]]:
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

    async def game_over(
        self,
        action: str,
        player1: discord.User | discord.Member | discord.ClientUser,
        player2: discord.User | discord.Member | discord.ClientUser,
    ) -> None:
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

    async def player_turn(self) -> Coordinate | None:
        """Initiate the player's turn."""
        message = await self.channel.send(
            f"{self.player_active.mention}, it's your turn! React with the column you want to place your token in.",
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
            for row_incr, column_incr in axis:
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

    if TYPE_CHECKING:
        from .__constants import Coordinate

    def __init__(self, bot: Parrot, game: GameC4):
        self.game = game
        self.mention = bot.user.mention

    def get_possible_places(self) -> list[Coordinate]:
        """Gets all the coordinates where the AI_C4 could possibly place a counter."""
        possible_coords = []
        for column_num in range(self.game.grid_size):
            column = [row[column_num] for row in self.game.grid]
            for row_num, square in reversed(list(enumerate(column))):
                if not square:
                    possible_coords.append((row_num, column_num))
                    break
        return possible_coords

    def check_ai_win(self, coord_list: list[Coordinate]) -> Coordinate | None:
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

    def check_player_win(self, coord_list: list[Coordinate]) -> Coordinate | None:
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
    def random_coords(coord_list: list[Coordinate]) -> Coordinate:
        """Picks a random coordinate from the possible ones."""
        return random.choice(coord_list)

    def play(self) -> Coordinate | bool:
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
            self.check_ai_win(possible_coords)
            or self.check_player_win(possible_coords)
            or self.random_coords(possible_coords)
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
        self.winner: bool | None = MISSING

    @property
    def legal_moves(self) -> Iterator[tuple[int, int]]:
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
            msg = "Illegal Move"
            raise ValueError(msg)

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
    ) -> tuple[int, int]:
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
    ) -> float | tuple[int, int]:
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
        assert self.view is not None

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

    def __init__(self, players: tuple[discord.Member, discord.Member]):
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
        self.last_state: discord.Message | None = None

        self._state = [[Cell(self, y, x) for x in range(self.size_x)] for y in range(self.size_y)]

    def setup(self, click_y: int, click_x: int):
        """Places mines on the board"""
        cells = [(i // self.size_x, i % self.size_x) for i in range(self.size_x * self.size_y)]
        cells.remove((click_y, click_x))

        for y, x in random.sample(
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
            msg = "Cell out side the board."
            raise commands.BadArgument(msg)

        cell = self[x, y]

        if not self.num_mines:
            self.setup(y, x)

        if cell.flagged:
            msg = "You cannot click on a flagged cell."
            raise commands.BadArgument(msg)

        cell.clicked = True

    def flag(self, y: int, x: int):
        """Flags a cell"""
        if self.size_x < x or self.size_y < y:
            msg = "Cell out side the board."
            raise commands.BadArgument(msg)

        cell = self[x, y]

        if cell.clicked:
            msg = "You cannot flag a revealed cell."
            raise commands.BadArgument(msg)

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
    children: list[Button]

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
        msg = "There is already a Minesweeper game running."
        raise commands.CheckFailure(msg)
    return True


def is_game(ctx: Context):
    try:
        is_no_game(ctx)
    except commands.CheckFailure:
        return True
    msg = "No Connect Four game is running."
    raise commands.CheckFailure(msg)
