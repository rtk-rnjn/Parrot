from __future__ import annotations

import asyncio
import random
import re

from functools import wraps
from collections import defaultdict
from collections.abc import Iterable
from typing import Literal, NamedTuple, Optional

import discord
from discord.ext import commands
from discord.ext import old_menus as menus

from core import Parrot, Cog, Context


def ordinal(number: int, /) -> str:
    return f'{number}{"tsnrhtdd"[(number // 10 % 10 != 1) * (number % 10 < 4) * number % 10 :: 4]}'


from .parser import View

SMALL = 3
ORIGINAL = 4
BIG = 5
SUPER_BIG = 6

NUMBER_EMOJI = {
    "0": "0\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "1": "1\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "2": "2\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "3": "3\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "4": "4\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "5": "5\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "6": "6\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "7": "7\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "8": "8\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "9": "9\ufe0f\N{COMBINING ENCLOSING KEYCAP}",
    "A": "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
    "B": "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
    "C": "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
    "D": "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
    "E": "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
    "F": "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
}

Bases = Literal[2, 10, 16]

# fmt: off

DIE = {
    2: {
        SMALL: [
            "110010", "000101", "100101",
            "000010", "101000", "010000",
            "011000", "101101", "100010",
        ],
        ORIGINAL: [
            "110110", "111000", "010111", "011000",
            "100101", "101011", "101011", "101101",
            "110110", "001011", "110100", "010000",
            "000001", "010100", "111111", "011010",
        ],
        BIG: [
            "101011", "001010", "110001", "011110", "001100",
            "111001", "100001", "001101", "011111", "011101",
            "110110", "011001", "000110", "000000", "101000",
            "001110", "110001", "100100", "000011", "001000",
            "100001", "000101", "101011", "011101", "101011",
        ],
        SUPER_BIG: [
            "001111", "001010", "001111", "011000", "000001", "110111",
            "010001", "010110", "101001", "101111", "110100", "001010",
            "010101", "111101", "011010", "111101", "010111", "101101",
            "100100", "101000", "101100", "110100", "011010", "101010",
            "001011", "001001", "100110", "010101", "011111", "011001",
            "011111", "111011", "010011", "000111", "011110", "111111",
        ],
    },
    10: {
        SMALL: [
            "129640", "417582", "116313",
            "304380", "615522", "469022",
            "110322", "982485", "081472",
        ],
        ORIGINAL: [
            "781923", "442727", "286382", "674674",
            "434257", "612362", "761386", "917136",
            "389292", "912198", "218613", "522074",
            "421587", "319059", "403934", "503529",
        ],
        BIG: [
            "467377", "368015", "881118", "152754", "403491",
            "496754", "322870", "476441", "930914", "124178",
            "985631", "692161", "213957", "930884", "183380",
            "140851", "217378", "853915", "932265", "727123",
            "562516", "215186", "776605", "849463", "410954",
        ],
        SUPER_BIG: [
            "150704", "153141", "695329", "829765", "147583", "433529",
            "154691", "586481", "256164", "470592", "126134", "975732",
            "402085", "235228", "247811", "531376", "440231", "948365",
            "243870", "958379", "432140", "354431", "246147", "518645",
            "413514", "722772", "791934", "553194", "175219", "971067",
            "603808", "294025", "456713", "611644", "173820", "455798",
        ],
    },
    16: {
        SMALL: [
            "5FC8FD", "791DC0", "FFBF88",
            "EECD26", "FB6C70", "401566",
            "4144A8", "6AA545", "868638",
        ],
        ORIGINAL: [
            "FDD696", "E768F4", "2E4200", "1A56FD",
            "710160", "D3525E", "CD6B3D", "E2CB33",
            "02F5A7", "8866C5", "2B6DB0", "51583D",
            "55ADA7", "31D288", "BC1DAA", "86CD4C",
        ],
        BIG: [
            "73931C", "CE3551", "D379D8", "5F9E10", "AD9751",
            "A9F9AC", "C66062", "4BB572", "3F4422", "E0200A",
            "87FB2F", "BE50BA", "3793F3", "C5F683", "CACBE0",
            "37BAFF", "8B535D", "DC3CFD", "3BD64D", "B140C3",
            "5BAE1C", "74E597", "1AD50C", "87FA8C", "E00C03",
        ],
        SUPER_BIG: [
            "576417", "33FC3B", "1985E3", "686B97", "3FD723", "BC09B0",
            "151B21", "86CBC4", "244242", "83335D", "05DBE9", "949976",
            "8E890C", "FAF0E9", "E723EA", "547636", "15C463", "6E2B51",
            "D8CBC1", "4D0724", "812FA3", "544A30", "CCD20E", "62A418",
            "5A2200", "8D087A", "67EB11", "F37864", "089578", "DC625E",
            "DAFCF8", "2D9839", "982921", "4FBC0E", "D9AF5B", "6F244D",
        ],
    }
}

# fmt: on

NUMBER_PATTERN = re.compile("[^0-9A-Fa-f]")

POINTS = {
    3: 1,
    4: 1,
    5: 2,
    6: 3,
    7: 5,
} | {x: 11 for x in range(8, SUPER_BIG ** 2)}

FOGGLE_RULES = """The goal of Foggle is create equations, using simple arithmetic (e.g. +, -, *, /, ^ and parentheses) which equates to the given magic number.
Numbers must be adjacent (up-down, left-right or diagonal) to eachother on the Foggle board.
For example with the magic number `42` an equation such as `(3 * 6 + 3) * 2` would be valid.
The more numbers an equation contains, the more points awarded, at least 3 numbers are required for an equation to count.
Submitting equations which do not contain adjacent numbers, or do not equal the magic number will deduct points.
Points are awarded as follows:
```
nums | points
  3  |  1
  4  |  1
  5  |  2
  6  |  3
  7  |  5
  8+ |  11
```
The original rules can be found below:
"""


class Position(NamedTuple):
    col: int
    row: int


class Board:
    def __init__(
        self, *, size: int = ORIGINAL, base: int = 10, board=None, magic_number=None
    ):
        self.size = size
        self.base = base

        if board is None:
            board = DIE[self.base][self.size].copy()
            random.shuffle(board)
            board = [
                [
                    random.choice(board[row * self.size + column])
                    for column in range(self.size)
                ]
                for row in range(self.size)
            ]
        if magic_number is None:
            magic_number = random.randint(00, base ** 2 - 1)

        self.columns = board
        self.number = magic_number

    def board_contains(
        self, numbers: str, pos: Position = None, passed: list[Position] = None
    ) -> bool:
        if passed is None:
            passed = []
        # Empty numberss
        if len(numbers) == 0:
            return True

        # When starting out
        if pos is None:

            # Check all positions
            for col in range(self.size):
                for row in range(self.size):
                    if self.board_contains(numbers, Position(col, row)):
                        return True

        # Checking new squares
        elif pos not in passed:
            # Check if letter matches current start of numbers
            if numbers[0] == self.columns[pos.col][pos.row]:

                # Check adjacent for next letter
                for x in range(-1, 2):
                    for y in range(-1, 2):

                        # don't check yourself
                        if x == 0 and y == 0:
                            continue

                        new_pos = Position(pos.col + x, pos.row + y)

                        # don't check out of bounds
                        if (
                            new_pos.col < 0
                            or new_pos.col >= self.size
                            or new_pos.row < 0
                            or new_pos.row >= self.size
                        ):
                            continue

                        if self.board_contains(numbers[1:], new_pos, [*passed, pos]):
                            return True

        # Otherwise cannot find numbers
        return False

    def get_chain(self, equation: str) -> str:
        view = View(equation, self.base)
        return re.sub(NUMBER_PATTERN, "", view.string)

    def is_legal(self, equation: str) -> bool:
        view = View(equation, self.base)

        # Check equation
        result = view.parse_full()
        if result is None:  # If equation is invalid discard
            return False
        if result != self.number:
            return False

        # Check chain is valid
        chain = self.get_chain(equation)
        return len(chain) >= 3 and self.board_contains(chain)

    def points(self, equation: str) -> int:
        return POINTS[len(self.get_chain(equation))] if self.is_legal(equation) else -1

    def total_points(self, equations: Iterable[str]) -> int:
        return sum(self.points(equation) for equation in equations)


class Game(menus.Menu):
    name: Optional[str] = "Foggle"
    footer: Optional[str] = None

    def __init__(self, *, size: int = ORIGINAL, base: int = 10, **kwargs):
        self.board = Board(size=size, base=base)
        self.setup()
        super().__init__(**kwargs)

    @property
    def state(self):
        state = ""

        for row in range(self.board.size):
            emoji = []
            for column in range(self.board.size):
                emoji.append(NUMBER_EMOJI[self.board.columns[column][row]])

            state = " ".join(emoji) + "\n" + state

        number = self.board.number
        if self.board.base == 2:
            number = bin(number)
        elif self.board.base == 16:
            number = hex(number)

        state += f"\n\n The magic number is **{number}**!"

        return discord.Embed(title=self.name, description=state).set_footer(
            text=self.footer
        )

    def setup(self):
        raise NotImplementedError

    async def send_initial_message(self, ctx, channel):
        return await channel.send(
            content="Foggle game started, you have 3 minutes!", embed=self.state
        )

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)
        # await self.bot.loop.run_in_executor(None, lambda: self.board.legal_equations)

    async def finalize(self, timed_out):
        self.bot.dispatch("foggle_game_complete", self.message.channel)

    def get_points(self, equations: Iterable[str]) -> int:
        return self.board.total_points(equations)

    def get_correct(self, equations: Iterable[str]):
        return sum(self.board.is_legal(equation) for equation in equations)

    def check_equation(self, equation: str) -> bool:
        return self.board.is_legal(equation)

    async def check_message(self, message: discord.Message):
        raise NotImplementedError

    @menus.button("\N{BLACK SQUARE FOR STOP}\ufe0f", position=menus.Last(0))
    async def cancel(self, payload):
        await self.message.edit(content="Game Cancelled.")
        self.stop()


class ShuffflingGame(Game):
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
            await self.message.edit(
                content=f"Board Updated! You have {time} left!", embed=self.state
            )

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)
        self.bot.loop.create_task(self.shuffle_task())

    def get_points(self, equations: Iterable[str]) -> int:
        return sum(
            max(board.points(equation) for board in self.boards)
            for equation in equations
        )

    def get_correct(self, equations: Iterable[str]):
        return sum(
            max(board.is_legal(equation) for board in self.boards)
            for equation in equations
        )


class DiscordGame(Game):
    name = "Discord Foggle"
    footer = "First to find an equation wins points!"

    @property
    def scores(self):
        embed = discord.Embed()

        i = 0
        old = None

        for user, equations in sorted(
            self.equations.items(), key=lambda v: self.get_points(v[1]), reverse=True
        ):
            points = self.get_points(equations)
            correct = self.get_correct(equations)

            if points != old:
                old = points
                i += 1

            embed.add_field(
                name=f"{ordinal(i)}: {user}",
                value=f"**{len(equations)}** attempts, **{correct}** correct, **{points}** points.",
                inline=False,
            )

        return embed

    def setup(self):
        self.all_chains = set()
        self.equations = defaultdict(set)

    async def check_message(self, message: discord.Message):
        equation = message.content
        if equation is None:
            return

        # strip equals half if needed
        if "=" in equation:
            equation, _ = equation.split("=")

        equation = equation.strip().upper()
        chain = self.board.get_chain(equation)

        if chain not in self.all_chains:
            self.all_chains.add(chain)

            is_valid = self.check_equation(equation)
            if is_valid is None:
                return
            if is_valid:
                await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

            # Add to user equations
            self.equations[message.author].add(equation)

    async def finalize(self, timed_out: bool):
        await super().finalize(timed_out)
        if timed_out:
            await self.message.edit(content="Game Over!")
            await self.message.reply(embed=self.scores)


class FlipGame(ShuffflingGame, DiscordGame):
    name = "Flip Foggle"
    footer = (
        "Find equations as fast as you can, rows will flip positions every 30 seconds."
    )

    def shuffle(self):
        rows = [
            [self.board.columns[x][y] for x in range(self.board.size)]
            for y in range(self.board.size)
        ]
        random.shuffle(rows)
        new_board = [
            [rows[x][y] for x in range(self.board.size)] for y in range(self.board.size)
        ]
        self.board = Board(
            size=self.board.size,
            base=self.board.base,
            board=new_board,
            magic_number=self.board.number,
        )


class FoggleGame(ShuffflingGame, DiscordGame):
    name = "Foggle Foggle"
    footer = "Find equations as fast as you can, letters will shuffle positions every 30 seconds."

    def shuffle(self):
        letters = [
            self.board.columns[y][x]
            for x in range(self.board.size)
            for y in range(self.board.size)
        ]
        random.shuffle(letters)
        new_board = [
            letters[x * self.board.size : x * self.board.size + self.board.size]
            for x in range(self.board.size)
        ]
        self.board = Board(
            size=self.board.size,
            base=self.board.base,
            board=new_board,
            magic_number=self.board.number,
        )


def check_size(ctx: Context) -> int:
    prefix = ctx.prefix.upper()
    if prefix.endswith("SUPER BIG "):
        return SUPER_BIG
    if prefix.endswith("BIG "):
        return BIG
    if prefix.endswith("SMALL ") or prefix.endswith("SMOL "):
        return SMALL
    return ORIGINAL


def foggle_game(game_type: type[Game]):
    def wrapper(signature):
        @wraps(signature)
        async def command(self: Foggle, ctx: Context, base: Bases = 10):
            # Ignore if rules invoke
            if ctx.invoked_subcommand is self.foggle_rules:
                return

            # Raise if game already running
            if ctx.channel in self.games:
                raise commands.CheckFailure(
                    "There is already a game running in this channel."
                )

            # Start the game
            self.games[ctx.channel] = game = game_type(size=check_size(ctx), base=base)
            await game.start(ctx, wait=False)

            # Wait for game to end
            def check(channel):
                return channel.id == ctx.channel.id

            await self.bot.wait_for("foggle_game_complete", check=check, timeout=200)
            if ctx.channel in self.games:
                del self.games[ctx.channel]

        return command

    return wrapper


class Foggle(Cog):
    """A mathematical game..."""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.games: dict[str, Game] = {}

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{HEAVY PLUS SIGN}")

    @commands.group(invoke_without_command=True)
    @foggle_game(DiscordGame)
    # @commands.max_concurrency(1, per=commands.BucketType.channel)  # rip
    async def foggle(self, ctx: Context, base: Bases = 10):
        """Start's a game of Foggle.
        The board size can be set by command prefix.
        `base` can be used to a custom base, supported bases are 2, 10 and 16
        Players have 3 minutes to find as many equation as they can, the first person to find
        an equation gets the points.
        """

    @foggle.command(name="flip")
    @foggle_game(FlipGame)
    async def foggle_flip(self, ctx: Context, base: Bases = 10):
        """Starts a flip game of foggle.
        Rows will randomly shuffle every 30s.
        The first person to find an equation gets the points.
        """
        ...

    @foggle.command(name="foggle")
    @foggle_game(FoggleGame)
    async def foggle_foggle(self, ctx: Context, base: Bases = 10):
        """Starts a boggling game of foggle.
        All letters will randomly shuffle flip every 30s.
        The first person to find an equation gets the points.
        """
        ...

    @foggle.error
    @foggle_flip.error
    @foggle_foggle.error
    async def on_foggle_error(self, ctx, error):
        if not isinstance(error, commands.CheckFailure) and ctx.channel in self.games:
            del self.games[ctx.channel]

    @foggle.command(name="rules", aliases=["help"])
    async def foggle_rules(self, ctx: Context, type: str = "discord"):
        """Displays information about a given foggle game type."""
        embed = discord.Embed(title="About Foggle:", description=FOGGLE_RULES)
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/336642776609456130/809275615676334100/pic127783.png"
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Check if channel has a game going
        if message.channel not in self.games:
            return

        await self.games[message.channel].check_message(message)


def setup(bot: Parrot):
    bot.add_cog(Foggle(bot))
