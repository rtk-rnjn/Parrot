from __future__ import annotations

import asyncio
import random
import re

from dataclasses import dataclass
from functools import partial, cached_property, wraps
from string import ascii_uppercase
from collections import defaultdict
from collections.abc import Iterable
from typing import Any, Iterator, Literal, Optional, Union, overload, Dict, NamedTuple

import discord
from discord import Member as User
from discord.ext import commands, boardgames
from discord.ext import old_menus as menus
from discord.utils import MISSING
from random import sample, choice

from core import Cog, Parrot, Context
import akinator
from akinator.async_aki import Akinator
import emojis
import chess
import tabulate

from aiofile import async_open
from interactions.buttons.secret_hitler.ui.join import JoinUI
from utilities.paginator import ParrotPaginator

emoji = emojis  # Idk
SMALL = 3
ORIGINAL = 4
BIG = 5
SUPER_BIG = 6

# Diagram Emoji
AN_EMOJI = "<:regional_indicator_an:929993092390596609>"
ER_EMOJI = "<:regional_indicator_er:929994016471261224>"
HE_EMOJI = "<:regional_indicator_he:929994202572554240>"
IN_EMOJI = "<:regional_indicator_in:929994734372536361>"
QU_EMOJI = "<:regional_indicator_qu:929994922923274260>"
TH_EMOJI = "<:regional_indicator_th:929995052153970789>"

REGIONAL_INDICATOR_EMOJI = (
    "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER H}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER J}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER K}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER L}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER N}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER P}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER S}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER T}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER U}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER V}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER W}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Y}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Z}",
)

DIAGRAPHS = {"1": "AN", "2": "ER", "3": "HE", "4": "IN", "5": "QU", "6": "TH"}

LETTERS_EMOJI = {
    "#": "\N{BLACK SQUARE FOR STOP}\ufe0f",
    "1": AN_EMOJI,
    "2": ER_EMOJI,
    "3": HE_EMOJI,
    "4": IN_EMOJI,
    "5": QU_EMOJI,
    "6": TH_EMOJI,
} | dict(zip(ascii_uppercase, REGIONAL_INDICATOR_EMOJI))

# fmt: off

DIE = {
    SMALL: [
        "ATSWKA", "ZHIWIR", "WYASAY",
        "NELTDL", "UJNIIQ", "ORQPII",
        "PCOAUB", "TKRTAU", "ZAQLPG",
    ],
    ORIGINAL: [
        "RIFOBX", "IFEHEY", "DENOWS", "UTOKND",
        "HMSRAO", "LUPETS", "ACITOA", "YLGKUE",
        "5BMJOA", "EHISPN", "VETIGN", "BALIYT",
        "EZAVND", "RALESC", "UWILRG", "PACEMD",
    ],
    BIG: [
        "5BZJXK", "TOUOTO", "OVWGR", "AAAFSR", "AUMEEG",
        "HHLRDO", "MJDTHO", "LHNROD", "AFAISR", "YIFASR",
        "TELPCI", "SSNSEU", "RIYPRH", "DORDLN", "CCWNST",
        "TTOTEM", "SCTIEP", "EANDNN", "MNNEAG", "UOTOWN",
        "AEAEEE", "YIFPSR", "EEEEMA", "ITITIE", "ETILIC",
    ],
    SUPER_BIG: [
        "AAAFRS", "AAEEEE", "AAEEOO", "AAFIRS", "ABDEIO", "ADENNN",
        "AEEEEM", "AEEGMU", "AEGMNN", "AEILMN", "AEINOU", "AFIRSY",
        "123456", "BBJKXZ", "CCENST", "CDDLNN", "CEIITT", "CEIPST",
        "CFGNUY", "DDHNOT", "DHHLOR", "DHHNOW", "DHLNOR", "EHILRS",
        "EIILST", "EILPST", "EIO###", "EMTTTO", "ENSSSU", "GORRVW",
        "HIRSTV", "HOPRST", "IPRSYY", "JK5WXZ", "NOOTUW", "OOOTTU",
    ],
}

# fmt: on

with open("extra/boggle.txt") as f:
    DICTIONARY = set(f.read().splitlines())

POINTS = {
    3: 1,
    4: 1,
    5: 2,
    6: 3,
    7: 5,
} | {x: 11 for x in range(8, SUPER_BIG ** 2)}


class Position(NamedTuple):
    col: int
    row: int


def ordinal(number: int, /) -> str:
    return f'{number}{"tsnrhtdd"[(number // 10 % 10 != 1) * (number % 10 < 4) * number % 10 :: 4]}'


class BoardBoogle:
    def __init__(self, *, size=ORIGINAL, board=None):
        self.size = size

        if board is None:
            board = DIE[self.size].copy()
            random.shuffle(board)
            board = [
                [
                    random.choice(board[row * self.size + column])
                    for column in range(self.size)
                ]
                for row in range(self.size)
            ]

        self.columns = board

    def board_contains(
        self, word: str, pos: Position = None, passed: list[Position] = None
    ) -> bool:
        if passed is None:
            passed = []
        # Empty words
        if len(word) == 0:
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
                        if (
                            new_pos.col < 0
                            or new_pos.col >= self.size
                            or new_pos.row < 0
                            or new_pos.row >= self.size
                        ):
                            continue

                        if self.board_contains(
                            word[len(letter) :], new_pos, [*passed, pos]
                        ):
                            return True

        # Otherwise cannot find word
        return False

    def is_legal(self, word: str) -> bool:
        if len(word) < 3:
            return False
        word = word.upper()
        if word not in DICTIONARY:
            return False
        return self.board_contains(word)

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
            emoji = []
            for column in range(self.board.size):
                emoji.append(LETTERS_EMOJI[self.board.columns[column][row]])

            state = " ".join(emoji) + "\n" + state

        return discord.Embed(title=self.name, description=state).set_footer(
            text=self.footer
        )

    def setup(self):
        raise NotImplementedError

    async def send_initial_message(self, ctx, channel):
        return await channel.send(
            content="Boggle game started, you have 3 minutes!", embed=self.state
        )

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
            await self.message.edit(
                content=f"Board Updated! You have {time} left!", embed=self.state
            )

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)
        self.bot.loop.create_task(self.shuffle_task())

    def get_points(self, words: Iterable[str]) -> int:
        points = 0
        for word in words:
            for board in self.boards:
                pts = board.points(word)
                if pts:
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

        for user, words in sorted(
            self.words.items(), key=lambda v: self.get_points(v[1]), reverse=True
        ):
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
        self.words: dict[User, set[str]] = defaultdict(set)

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
        self.word_lists: dict[User, str] = {}
        self.words: dict[User, set[str]] = defaultdict(set)
        self.unique_words: dict[User, set[str]] = defaultdict(set)

    async def finalize(self, timed_out: bool):
        await super().finalize(timed_out)

        if timed_out:
            await self.message.edit(content="Game Over!")
            await self.message.reply(
                "Game Over! you have 10 seconds to send in your words."
            )
            self.over = True
            await asyncio.sleep(10)
            self.filter_lists()
            await self.message.reply(embed=self.scores)


class FlipGame(ShuffflingGame, DiscordGame):
    name = "Flip Boggle"
    footer = "Find words as fast as you can, rows will flip positions every 30 seconds."

    def shuffle(self):
        rows = [
            [self.board.columns[x][y] for x in range(self.board.size)]
            for y in range(self.board.size)
        ]
        random.shuffle(rows)
        self.board = BoardBoogle(
            size=self.board.size,
            board=[
                [rows[x][y] for x in range(self.board.size)]
                for y in range(self.board.size)
            ],
        )


class BoggleGame(ShuffflingGame, DiscordGame):
    name = "Boggle Boggle"
    footer = "Find words as fast as you can, letters will shuffle positions every 30 seconds."

    def shuffle(self):
        letters = [
            self.board.columns[y][x]
            for x in range(self.board.size)
            for y in range(self.board.size)
        ]
        random.shuffle(letters)
        self.board = BoardBoogle(
            size=self.board.size,
            board=[
                letters[x * self.board.size : x * self.board.size + self.board.size]
                for x in range(self.board.size)
            ],
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


def boggle_game(game_type: type[Game]):
    def wrapper(signature):
        @wraps(signature)
        async def command(self: Games, ctx: Context):
            # Ignore if rules invoke
            if ctx.invoked_subcommand is self.boggle_rules:
                return

            # Raise if game already running
            if ctx.channel in self.games_boogle:
                raise commands.CheckFailure(
                    "There is already a game running in this channel."
                )

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
    regexMatch = re.match(
        r"\s*^(((?:[rnbqkpRNBQKP1-8]+\/){7})[rnbqkpRNBQKP1-8]+)\s([b|w])\s([K|Q|k|q]{1,4})\s(-|[a-h][1-8])\s(\d+\s\d+)$",
        fen,
    )
    if regexMatch:
        regexList = regexMatch.groups()
        fen = regexList[0].split("/")
        if len(fen) != 8:
            raise commands.BadArgument(
                "Expected 8 rows in position part of FEN: `{0}`".format(repr(fen))
            )

        for fenPart in fen:
            field_sum = 0
            previous_was_digit, previous_was_piece = False, False

            for c in fenPart:
                if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                    if previous_was_digit:
                        raise commands.BadArgument(
                            "Two subsequent digits in position part of FEN: `{0}`".format(
                                repr(fen)
                            )
                        )
                    field_sum += int(c)
                    previous_was_digit = True
                    previous_was_piece = False
                elif c == "~":
                    if not previous_was_piece:
                        raise commands.BadArgument(
                            "~ not after piece in position part of FEN: `{0}`".format(
                                repr(fen)
                            )
                        )
                    previous_was_digit, previous_was_piece = False, False
                elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                    field_sum += 1
                    previous_was_digit = False
                    previous_was_piece = True
                else:
                    raise commands.BadArgument(
                        "Invalid character in position part of FEN: `{0}`".format(
                            repr(fen)
                        )
                    )

            if field_sum != 8:
                raise commands.BadArgument(
                    "Expected 8 columns per row in position part of FEN: `{0}`".format(
                        repr(fen)
                    )
                )

    else:
        raise commands.BadArgument(
            "FEN doesn`t match follow this example: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 "
        )


_2048_GAME = a = {
    "0": "<:YELLO:922889092755259405>",
    "2": "<:2_:922741083983724544>",
    "8": "<:8_:922741084004687913>",
    "2048": "<:2048:922741084612861992>",
    "256": "<:256:922741084671602740>",
    "32": "<:32:922741084700966963>",
    "4": "<:4_:922741084738699314>",
    "1024": "<:1024:922741085007130624>",
    "16": "<:16:922741085464297472>",
    "64": "<:64:922741085539827772>",
    "128": "<:128:922741085866958868>",
    "4096": "<:4096:922741086009565204>",
    "512": "<:512:922741086017978368>",
}

BoardState = list[list[Optional[bool]]]


class SlidingPuzzle:
    def __init__(self, size, *, invert: bool = False) -> None:
        self.size = size

        self.grid = []
        self.temp = []

        self.x = []

        self._make_grid()
        self._get_blank()

        self.invert = invert

    def __repr__(self) -> str:
        _ = ""
        for i in self.grid:
            _ += str(i) + "\n"
        return _

    def board_str(self) -> str:
        return str(tabulate.tabulate(self.grid, tablefmt="grid", numalign="center"))

    def _make_grid(self) -> None:
        nums = list(range(self.size * self.size))
        nums[-1] = "\u200b"
        random.shuffle(nums)
        for i in range(0, len(nums), self.size):
            self.grid.append(nums[i : i + self.size])
        self.temp = self.grid

    def _get_blank(self) -> None:
        for i in self.grid:
            for j in i:
                if j == "\u200b":
                    self.x = [self.grid.index(i), i.index(j)]
                    return

    def _is_game_over(self) -> bool:
        return self.grid == self.temp

    def _move_up(self) -> None:
        if self.x[0] == self.size - 1:
            return
        self.grid[self.x[0]][self.x[1]] = self.grid[self.x[0] + 1][self.x[1]]
        self.x = [self.x[0] + 1, self.x[1]]
        self.grid[self.x[0]][self.x[1]] = "\u200b"

    def _move_down(self) -> None:
        if self.x[0] == 0:
            return
        self.grid[self.x[0]][self.x[1]] = self.grid[self.x[0] - 1][self.x[1]]
        self.x = [self.x[0] - 1, self.x[1]]
        self.grid[self.x[0]][self.x[1]] = "\u200b"

    def _move_left(self) -> None:
        if self.x[1] == self.size - 1:
            return
        self.grid[self.x[0]][self.x[1]] = self.grid[self.x[0]][self.x[1] + 1]
        self.x = [self.x[0], self.x[1] + 1]
        self.grid[self.x[0]][self.x[1]] = "\u200b"

    def _move_right(self) -> None:
        if self.x[1] == 0:
            return
        self.grid[self.x[0]][self.x[1]] = self.grid[self.x[0]][self.x[1] - 1]
        self.x = [self.x[0], self.x[1] - 1]
        self.grid[self.x[0]][self.x[1]] = "\u200b"

    def move_up(self) -> None:
        if self.invert:
            self._move_down()
            return
        self._move_up()

    def move_down(self) -> None:
        if self.invert:
            self._move_up()
            return
        self._move_down()

    def move_right(self) -> None:
        if self.invert:
            self._move_left()
            return
        self._move_right()

    def move_left(self) -> None:
        if self.invert:
            self._move_right()
            return
        self._move_left()


class SlidingPuzzleView(discord.ui.View):
    def __init__(
        self, game: SlidingPuzzle, user: discord.Member, timeout: float = 60.0, **kwargs
    ):
        super().__init__(timeout=timeout, **kwargs)
        self.game = game
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction):

        if interaction.user == self.user:
            return True
        await interaction.response.send_message(
            content="This isn't your game!", ephemeral=True
        )
        return False

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER R}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=True,
    )
    async def null_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        return

    @discord.ui.button(
        emoji="\N{UPWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
    )
    async def upward(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.move_up()

        embed = (
            discord.Embed(
                title="Sliding Puzzle",
                description=f"```diff\n{self.game.board_str()}\n```",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {interaction.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/923106185584984104/d1b246ff6d7c01f4bc372319877ef0f6.gif"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button2(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(
        emoji="\N{LEFTWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def left(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.move_left()

        embed = (
            discord.Embed(
                title="Sliding Puzzle",
                description=f"```diff\n{self.game.board_str()}\n```",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {interaction.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/923106185584984104/d1b246ff6d7c01f4bc372319877ef0f6.gif"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{DOWNWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def down(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.move_down()

        embed = (
            discord.Embed(
                title="Sliding Puzzle",
                description=f"```diff\n{self.game.board_str()}\n```",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {interaction.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/923106185584984104/d1b246ff6d7c01f4bc372319877ef0f6.gif"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{BLACK RIGHTWARDS ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def right(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.move_right()

        embed = (
            discord.Embed(
                title="Sliding Puzzle",
                description=f"```diff\n{self.game.board_str()}\n```",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {interaction.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/923106185584984104/d1b246ff6d7c01f4bc372319877ef0f6.gif"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self)


class ChessView(discord.ui.View):
    def __init__(
        self, *, game: Chess, ctx: Context = None, timeout: float = 300.0, **kwargs
    ):
        super().__init__(timeout=timeout, **kwargs)
        self.game = game
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
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
        self, button: discord.ui.Button, interaction: discord.Interaction
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
        self, button: discord.ui.Button, interaction: discord.Interaction
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

    def legal_moves(self) -> Optional[list]:
        return [self.board.san(move) for move in self.board.legal_moves]

    async def wait_for_move(self) -> Optional[discord.Message]:
        LEGAL_MOVES = self.legal_moves()

        def check(m):
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
        except Exception:
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
        move = self.board.push_san(move)
        content = f"{self.white.mention} VS {self.black.mention}"
        embed = discord.Embed(
            timestamp=discord.utils.utcnow(),
        )
        embed.set_image(
            url=f"https://backscattering.de/web-boardimage/board.png?fen={self.board.board_fen()}&lastMove={move.uci()}&coordinates=true"
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
    ) -> Optional[bool]:
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
                    except Exception:
                        pass
                await self.place_move(msg.content)
                self.switch()


class Twenty48:
    def __init__(self, number_to_display_dict, *, size: int = 4):

        self.board = [[0 for _ in range(size)] for _ in range(size)]
        self.size = size
        self.message = None
        self._controls = ["w", "a", "s", "d"]
        self._conversion = number_to_display_dict

    def reverse(self, board):
        new_board = []
        for i in range(self.size):
            new_board.append([])
            for j in range(self.size):
                new_board[i].append(board[i][(self.size - 1) - j])
        return new_board

    def transp(self, board):
        new_board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        for i in range(self.size):
            for j in range(self.size):
                new_board[i][j] = board[j][i]
        return new_board

    def merge(self, board):
        for i in range(self.size):
            for j in range(self.size - 1):
                if board[i][j] == board[i][j + 1] and board[i][j] != 0:
                    board[i][j] += board[i][j]
                    board[i][j + 1] = 0
        return board

    def compress(self, board):
        new_board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        for i in range(self.size):
            pos = 0
            for j in range(self.size):
                if board[i][j] != 0:
                    new_board[i][pos] = board[i][j]
                    pos += 1
        return new_board

    def MoveLeft(self):
        stage = self.compress(self.board)
        stage = self.merge(stage)
        stage = self.compress(stage)
        self.board = stage

    def MoveRight(self):
        stage = self.reverse(self.board)
        stage = self.compress(stage)
        stage = self.merge(stage)
        stage = self.compress(stage)
        stage = self.reverse(stage)
        self.board = stage

    def MoveUp(self):
        stage = self.transp(self.board)
        stage = self.compress(stage)
        stage = self.merge(stage)
        stage = self.compress(stage)
        stage = self.transp(stage)
        self.board = stage

    def MoveDown(self):
        stage = self.transp(self.board)
        stage = self.reverse(stage)
        stage = self.compress(stage)
        stage = self.merge(stage)
        stage = self.compress(stage)
        stage = self.reverse(stage)
        stage = self.transp(stage)
        self.board = stage

    def spawn_new(self):
        board = self.board
        zeroes = [
            (j, i) for j, sub in enumerate(board) for i, el in enumerate(sub) if el == 0
        ]
        if not zeroes:
            return
        i, j = random.choice(zeroes)
        board[i][j] = 2

    def number_to_emoji(self):
        board = self.board
        GameString = ""
        emoji_array = [[self._conversion[str(l)] for l in row] for row in board]
        for row in emoji_array:
            GameString += "".join(row) + "\n"
        return GameString

    def start(self):

        self.board[random.randrange(4)][random.randrange(4)] = 2
        self.board[random.randrange(4)][random.randrange(4)] = 2

        BoardString = self.number_to_emoji()


class Twenty48_Button(discord.ui.View):
    def __init__(
        self, game: Any, user: discord.Member, timeout: float = 60.0, **kwargs
    ):
        super().__init__(timeout=timeout, **kwargs)
        self.game = game
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction):

        if interaction.user == self.user:
            return True
        await interaction.response.send_message(
            content="This isn't your game!", ephemeral=True
        )
        return False

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER R}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=True,
    )
    async def null_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        return

    @discord.ui.button(
        emoji="\N{UPWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
    )
    async def upward(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.MoveUp()

        self.game.spawn_new()
        BoardString = self.game.number_to_emoji()
        embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{BoardString}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {interaction.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922771882904793120/41NgOgTVblL.png"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button2(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(
        emoji="\N{LEFTWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def left(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.MoveLeft()

        self.game.spawn_new()
        BoardString = self.game.number_to_emoji()
        embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{BoardString}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {interaction.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922771882904793120/41NgOgTVblL.png"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{DOWNWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def down(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.MoveDown()

        self.game.spawn_new()
        BoardString = self.game.number_to_emoji()
        embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{BoardString}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {interaction.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922771882904793120/41NgOgTVblL.png"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{BLACK RIGHTWARDS ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def right(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.MoveRight()

        self.game.spawn_new()
        BoardString = self.game.number_to_emoji()
        embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{BoardString}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {interaction.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922771882904793120/41NgOgTVblL.png"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self)


class SokobanGame:
    """The real sokoban game"""

    legend = {
        " ": "<:blank:922048341964103710>",
        "#": ":white_large_square:",
        "@": ":flushed:",
        "$": ":soccer:",
        ".": ":o:",
        "x": ":x:",  # TODO: change the "x"
    }
    # Do not DM me or mail me how this works
    # Thing is, I myself forget
    def __init__(self, level):
        self.level = level
        self.player = []
        self.blocks = []
        self.target = []

    def __repr__(self):
        return self.show()

    def display_board(self) -> str:
        main = ""
        for i in self.level:
            for j in i:
                main += self.legend[j]
            main += "\n"
        return main

    def _get_cords(self):
        self.player, self.blocks = [], []
        for index, i in enumerate(self.level):
            for _index, j in enumerate(i):
                if j == "@":
                    self.player = [index, _index]
                if j in ("$", "x"):
                    self.blocks.append([index, _index])
                if j in (".", "x"):
                    self.target.append([index, _index])

    def show(self) -> str:
        main = ""
        for i in self.level:
            for j in i:
                main += str(j)
            main += "\n"
        return main

    def move_up(self) -> None:
        if self.level[self.player[0] - 1][self.player[1]] in (" ", "."):
            self.level[self.player[0] - 1][self.player[1]] = "@"
            self.level[self.player[0]][self.player[1]] = (
                " " if self.player not in self.target else "."
            )
            self.player = [self.player[0] - 1, self.player[1]]
            return

        if (self.level[self.player[0] - 1][self.player[1]] in ("$", "x")) and (
            self.level[self.player[0] - 2][self.player[1]] in (" ", ".")
        ):
            self.level[self.player[0] - 1][self.player[1]] = "@"
            self.level[self.player[0] - 2][self.player[1]] = (
                "$" if self.level[self.player[0] - 2][self.player[1]] == " " else "x"
            )
            self.level[self.player[0]][self.player[1]] = (
                " " if self.player not in self.target else "."
            )
            self.player = [self.player[0] - 1, self.player[1]]
            return

    def move_down(self) -> None:
        if self.level[self.player[0] + 1][self.player[1]] in (" ", "."):
            self.level[self.player[0] + 1][self.player[1]] = "@"
            self.level[self.player[0]][self.player[1]] = (
                " " if self.player not in self.target else "."
            )
            self.player = [self.player[0] + 1, self.player[1]]
            return

        if (self.level[self.player[0] + 1][self.player[1]] in ("$", "x")) and (
            self.level[self.player[0] + 2][self.player[1]] in (" ", ".")
        ):
            self.level[self.player[0] + 1][self.player[1]] = "@"
            self.level[self.player[0] + 2][self.player[1]] = (
                "$" if self.level[self.player[0] + 2][self.player[1]] == " " else "x"
            )
            self.level[self.player[0]][self.player[1]] = (
                " " if self.player not in self.target else "."
            )
            self.player = [self.player[0] + 1, self.player[1]]
            return

    def move_left(self) -> None:
        if self.level[self.player[0]][self.player[1] - 1] in (" ", "."):
            self.level[self.player[0]][self.player[1] - 1] = "@"
            self.level[self.player[0]][self.player[1]] = (
                " " if self.player not in self.target else "."
            )
            self.player = [self.player[0], self.player[1] - 1]
            return

        if (self.level[self.player[0]][self.player[1] - 1] in ("$", "x")) and (
            self.level[self.player[0]][self.player[1] - 2] in (" ", ".")
        ):
            self.level[self.player[0]][self.player[1] - 1] = "@"
            self.level[self.player[0]][self.player[1] - 2] = (
                "$" if self.level[self.player[0]][self.player[1] - 2] == " " else "x"
            )
            self.level[self.player[0]][self.player[1]] = (
                " " if self.player not in self.target else "."
            )
            self.player = [self.player[0], self.player[1] - 1]
            return

    def move_right(self) -> None:
        if self.level[self.player[0]][self.player[1] + 1] in (" ", "."):
            self.level[self.player[0]][self.player[1] + 1] = "@"
            self.level[self.player[0]][self.player[1]] = (
                " " if self.player not in self.target else "."
            )
            self.player = [self.player[0], self.player[1] + 1]
            return

        if (self.level[self.player[0]][self.player[1] + 1] in ("$", "x")) and (
            self.level[self.player[0]][self.player[1] + 2] in (" ", ".")
        ):
            self.level[self.player[0]][self.player[1] + 1] = "@"
            self.level[self.player[0]][self.player[1] + 2] = (
                "$" if self.level[self.player[0]][self.player[1] + 2] == " " else "x"
            )
            self.level[self.player[0]][self.player[1]] = (
                " " if self.player not in self.target else "."
            )
            self.player = [self.player[0], self.player[1] + 1]
            return

    def is_game_over(self) -> bool:
        self.player = []
        self.blocks = []
        for index, i in enumerate(self.level):
            for _index, j in enumerate(i):
                if j == "@":
                    self.player = [index, _index]
                if j in ("$", "x"):
                    self.blocks.append([index, _index])
        return self.target == self.blocks


class SokobanGameView(discord.ui.View):
    def __init__(
        self,
        game: SokobanGame,
        user: discord.Member,
        level: int,
        ctx: Context,
        *,
        timeout: float = 60.0,
    ):
        super().__init__(timeout=timeout)
        self.user = user
        self.game = game
        self.level = level
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user == interaction.user:
            return True
        await interaction.response.send_message(
            f"Only **{self.user}** can interact. Run the command if you want to.",
            ephemeral=True,
        )
        return False

    def make_win_embed(self) -> discord.Embed:
        embed = (
            discord.Embed(title="You win! :tada:", timestamp=discord.utils.utcnow())
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png"
            )
        )
        embed.description = f"Thanks for playing!\nFor next level type `{self.ctx.prefix}sokoban {self.level+1}`"
        return embed

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER R}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        return

    @discord.ui.button(
        emoji="\N{UPWARDS BLACK ARROW}", style=discord.ButtonStyle.red, disabled=False
    )
    async def upward(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.move_up()
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png"
            )
        )

        if self.game.is_game_over():
            await interaction.response.edit_message(
                embed=self.make_win_embed(), view=None
            )
            return

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button2(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.message.delete()

    @discord.ui.button(
        emoji="\N{LEFTWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def left(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.move_left()
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png"
            )
        )

        if self.game.is_game_over():
            await interaction.response.edit_message(
                embed=self.make_win_embed(), view=None
            )
            return

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{DOWNWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def downward(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.game.move_down()
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png"
            )
        )

        if self.game.is_game_over():
            await interaction.response.edit_message(
                embed=self.make_win_embed(), view=None
            )
            return

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{BLACK RIGHTWARDS ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def right(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.game.move_right()
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png"
            )
        )

        if self.game.is_game_over():
            await interaction.response.edit_message(
                embed=self.make_win_embed(), view=None
            )
            return

        await interaction.response.edit_message(embed=embed, view=self)

    async def start(self, ctx: Context):
        await ctx.send(
            embed=discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png"
            ),
            view=self,
        )


STATES = (
    "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
)


class Emojis:
    cross_mark = "\u274C"
    star = "\u2B50"
    christmas_tree = "\U0001F384"
    check = "\u2611"
    envelope = "\U0001F4E8"

    ok_hand = ":ok_hand:"
    hand_raised = "\U0001F64B"

    number_emojis = {
        1: "\u0031\ufe0f\u20e3",
        2: "\u0032\ufe0f\u20e3",
        3: "\u0033\ufe0f\u20e3",
        4: "\u0034\ufe0f\u20e3",
        5: "\u0035\ufe0f\u20e3",
        6: "\u0036\ufe0f\u20e3",
        7: "\u0037\ufe0f\u20e3",
        8: "\u0038\ufe0f\u20e3",
        9: "\u0039\ufe0f\u20e3",
    }

    confirmation = "\u2705"
    decline = "\u274c"
    incident_unactioned = "\N{NEGATIVE SQUARED CROSS MARK}"

    x = "\U0001f1fd"
    o = "\U0001f1f4"


NUMBERS = list(Emojis.number_emojis.values())
CROSS_EMOJI = Emojis.incident_unactioned

Coordinate = Optional[tuple[int, int]]
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

        self.message = None

        self.player_active = None
        self.player_inactive = None

    @staticmethod
    def generate_board(size: int) -> list[list[int]]:
        """Generate the connect 4 board."""
        return [[0 for _ in range(size)] for _ in range(size)]

    async def print_grid(self) -> None:
        """Formats and outputs the Connect Four grid to the channel."""
        title = (
            f"Connect 4: {self.player1}"
            f" VS {self.bot.user if isinstance(self.player2, AI_C4) else self.player2}"
        )

        rows = [" ".join(str(self.tokens[s]) for s in row) for row in self.grid]
        first_row = " ".join(x for x in NUMBERS[: self.grid_size])
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
        self, action: str, player1: discord.user, player2: discord.user
    ) -> None:
        """Announces to public chat."""
        if action == "win":
            await self.channel.send(
                f"Game Over! {player1.mention} won against {player2.mention}"
            )
        elif action == "draw":
            await self.channel.send(
                f"Game Over! {player1.mention} {player2.mention} It's A Draw :tada:"
            )
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
                        self.bot.user
                        if isinstance(self.player_active, AI_C4)
                        else self.player_active,
                        self.bot.user
                        if isinstance(self.player_inactive, AI_C4)
                        else self.player_inactive,
                    )
            else:
                coords = await self.player_turn()

            if not coords:
                return

            if self.check_win(coords, 1 if self.player_active == self.player1 else 2):
                await self.game_over(
                    "win",
                    self.bot.user
                    if isinstance(self.player_active, AI_C4)
                    else self.player_active,
                    self.bot.user
                    if isinstance(self.player_inactive, AI_C4)
                    else self.player_inactive,
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

    async def player_turn(self) -> Coordinate:
        """Initiate the player's turn."""
        message = await self.channel.send(
            f"{self.player_active.mention}, it's your turn! React with the column you want to place your token in."
        )
        player_num = 1 if self.player_active == self.player1 else 2
        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=self.predicate, timeout=30.0
                )
            except asyncio.TimeoutError:
                await self.channel.send(
                    f"{self.player_active.mention}, you took too long. Game over!"
                )
                return
            else:
                await message.delete()
                if str(reaction.emoji) == CROSS_EMOJI:
                    await self.game_over(
                        "quit", self.player_active, self.player_inactive
                    )
                    return

                await self.message.remove_reaction(reaction, user)

                column_num = self.unicode_numbers.index(str(reaction.emoji))
                column = [row[column_num] for row in self.grid]

                for row_num, square in reversed(list(enumerate(column))):
                    if not square:
                        self.grid[row_num][column_num] = player_num
                        return row_num, column_num
                message = await self.channel.send(
                    f"Column {column_num + 1} is full. Try again"
                )

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

                while 0 <= row < self.grid_size and 0 <= column < self.grid_size:
                    if self.grid[row][column] == player_num:
                        counters_in_a_row += 1
                        row += row_incr
                        column += column_incr
                    else:
                        break
            if counters_in_a_row >= 4:
                return True
        return False


class AI_C4:
    """The Computer Player for Single-Player games."""

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

    def check_ai_win(self, coord_list: list[Coordinate]) -> Optional[Coordinate]:
        """
        Check AI_C4 win.
        Check if placing a counter in any possible coordinate would cause the AI_C4 to win
        with 10% chance of not winning and returning None
        """
        if random.randint(1, 10) == 1:
            return
        for coords in coord_list:
            if self.game.check_win(coords, 2):
                return coords

    def check_player_win(self, coord_list: list[Coordinate]) -> Optional[Coordinate]:
        """
        Check Player win.
        Check if placing a counter in possible coordinates would stop the player
        from winning with 25% of not blocking them  and returning None.
        """
        if random.randint(1, 4) == 1:
            return
        for coords in coord_list:
            if self.game.check_win(coords, 1):
                return coords

    @staticmethod
    def random_coords(coord_list: list[Coordinate]) -> Coordinate:
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
        self.winner: Optional[bool] = MISSING

    @property
    def legal_moves(self) -> Iterator[tuple[int, int]]:
        for c in range(3):
            for r in range(3):
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
        if sign == -1:
            player = not self.player
        else:
            player = self.player

        if game.over:
            if game.winner is None:
                return 0
            if game.winner == player:
                return 1_000_000
            return -1_000_000

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
    ) -> Union[float, tuple[int, int]]:
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

        if depth == 0:
            return move
        return score

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
    children: list[ButtonTicTacToe]

    def __init__(self, players: tuple[User, User]):
        self.players = list(players)
        random.shuffle(self.players)

        super().__init__(timeout=None)
        self.board = Board.new_game()

        if self.current_player.bot:
            self.make_ai_move()

        for r in range(3):
            for c in range(3):
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
            child.disabled = True  # type: ignore

        self.stop()
        return await interaction.response.edit_message(content=content, view=self)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user not in self.players:
            await interaction.response.send_message(
                "Sorry, you are not playing", ephemeral=True
            )
            return False
        if interaction.user != self.current_player:
            await interaction.response.send_message(
                "Sorry, it is not your turn!", ephemeral=True
            )
            return False
        return True

    def make_ai_move(self):
        ai = NegamaxAI(self.board.current_player)
        self.board = ai.move(self.board)

    @property
    def current_player(self) -> User:
        return self.players[self.board.current_player]


@dataclass
class Square:
    """Each square on the battleship grid - if they contain a boat and if they've been aimed at."""

    boat: Optional[str]
    aimed: bool


Grid = list[list[Square]]
EmojiSet = dict[tuple[bool, bool], str]


@dataclass
class Player:
    """Each player in the game - their messages for the boards and their current grid."""

    user: Optional[discord.Member]
    board: Optional[discord.Message]
    opponent_board: discord.Message
    grid: Grid


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

# The name of the ship and its size
SHIPS = {
    "Carrier": 5,
    "Battleship": 4,
    "Cruiser": 3,
    "Submarine": 3,
    "Destroyer": 2,
}


# For these two variables, the first boolean is whether the square is a ship (True) or not (False).
# The second boolean is whether the player has aimed for that square (True) or not (False)

# This is for the player's own board which shows the location of their own ships.
SHIP_EMOJIS = {
    (True, True): ":fire:",
    (True, False): ":ship:",
    (False, True): ":anger:",
    (False, False): ":ocean:",
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


class Colours:
    blue = 0x0279FD
    bright_green = 0x01D277
    dark_green = 0x1F8B4C
    orange = 0xE67E22
    pink = 0xCF84E0
    purple = 0xB734EB
    soft_green = 0x68C290
    soft_orange = 0xF9CB54
    soft_red = 0xCD6D6D
    yellow = 0xF9F586
    python_blue = 0x4B8BBE
    python_yellow = 0xFFD43B
    grass_green = 0x66FF00
    gold = 0xE6C200

    easter_like_colours = [
        (255, 247, 0),
        (255, 255, 224),
        (0, 255, 127),
        (189, 252, 201),
        (255, 192, 203),
        (255, 160, 122),
        (181, 115, 220),
        (221, 160, 221),
        (200, 162, 200),
        (238, 130, 238),
        (135, 206, 235),
        (0, 204, 204),
        (64, 224, 208),
    ]


class GameBattleShip:
    """A Battleship Game."""

    def __init__(
        self,
        bot: Parrot,
        channel: discord.TextChannel,
        player1: discord.Member,
        player2: discord.Member,
    ):

        self.bot = bot
        self.public_channel = channel

        self.p1 = Player(player1, None, None, self.generate_grid())
        self.p2 = Player(player2, None, None, self.generate_grid())

        self.gameover: bool = False

        self.turn: Optional[discord.Member] = None
        self.next: Optional[discord.Member] = None

        self.match: Optional[re.Match] = None
        self.surrender: bool = False

        self.setup_grids()

    @staticmethod
    def generate_grid() -> Grid:
        """Generates a grid by instantiating the Squares."""
        return [[Square(None, False) for _ in range(10)] for _ in range(10)]

    @staticmethod
    def format_grid(player: Player, emojiset: EmojiSet) -> str:
        """
        Gets and formats the grid as a list into a string to be output to the DM.
        Also adds the Letter and Number indexes.
        """
        grid = [
            [emojiset[bool(square.boat), square.aimed] for square in row]
            for row in player.grid
        ]

        rows = ["".join([number] + row) for number, row in zip(NUMBERS, grid)]
        return "\n".join([LETTERS] + rows)

    @staticmethod
    def get_square(grid: Grid, square: str) -> Square:
        """Grabs a square from a grid with an inputted key."""
        index = ord(square[0].upper()) - ord("A")
        number = int(square[1:])

        return grid[number - 1][index]  # -1 since lists are indexed from 0

    async def game_over(self, *, winner: discord.Member, loser: discord.Member) -> None:
        """Removes games from list of current games and announces to public chat."""
        await self.public_channel.send(
            f"Game Over! {winner.mention} won against {loser.mention}"
        )

        for player in (self.p1, self.p2):
            grid = self.format_grid(player, SHIP_EMOJIS)
            await self.public_channel.send(f"{player.user}'s Board:\n{grid}")

    @staticmethod
    def check_sink(grid: Grid, boat: str) -> bool:
        """Checks if all squares containing a given boat have sunk."""
        return all(
            square.aimed for row in grid for square in row if square.boat == boat
        )

    @staticmethod
    def check_gameover(grid: Grid) -> bool:
        """Checks if all boats have been sunk."""
        return all(square.aimed for row in grid for square in row if square.boat)

    def setup_grids(self) -> None:
        """Places the boats on the grids to initialise the game."""
        for player in (self.p1, self.p2):
            for name, size in SHIPS.items():
                while True:  # Repeats if about to overwrite another boat
                    ship_collision = False
                    coords = []

                    coord1 = random.randint(0, 9)
                    coord2 = random.randint(0, 10 - size)

                    if random.choice((True, False)):  # Vertical or Horizontal
                        x, y = coord1, coord2
                        xincr, yincr = 0, 1
                    else:
                        x, y = coord2, coord1
                        xincr, yincr = 1, 0

                    for i in range(size):
                        new_x = x + (xincr * i)
                        new_y = y + (yincr * i)
                        if player.grid[new_x][
                            new_y
                        ].boat:  # Check if there's already a boat
                            ship_collision = True
                            break
                        coords.append((new_x, new_y))
                    if (
                        not ship_collision
                    ):  # If not overwriting any other boat spaces, break loop
                        break

                for x, y in coords:
                    player.grid[x][y].boat = name

    async def print_grids(self) -> None:
        """Prints grids to the DM channels."""
        # Convert squares into Emoji

        boards = [
            self.format_grid(player, emojiset)
            for emojiset in (HIDDEN_EMOJIS, SHIP_EMOJIS)
            for player in (self.p1, self.p2)
        ]

        locations = (
            (self.p2, "opponent_board"),
            (self.p1, "opponent_board"),
            (self.p1, "board"),
            (self.p2, "board"),
        )

        for board, location in zip(boards, locations):
            player, attr = location
            if getattr(player, attr):
                await getattr(player, attr).edit(content=board)
            else:
                setattr(player, attr, await player.user.send(board))

    def predicate(self, message: discord.Message) -> bool:
        """Predicate checking the message typed for each turn."""
        if (
            message.author == self.turn.user
            and message.channel == self.turn.user.dm_channel
        ):
            if message.content.lower() == "surrender":
                self.surrender = True
                return True
            self.match = re.fullmatch(
                "([A-J]|[a-j]) ?((10)|[1-9])", message.content.strip()
            )
            if not self.match:
                self.bot.loop.create_task(message.add_reaction(CROSS_EMOJI))
            return bool(self.match)

    async def take_turn(self) -> Optional[Square]:
        """Lets the player who's turn it is choose a square."""
        square = None
        turn_message = await self.turn.user.send(
            "It's your turn! Type the square you want to fire at. Format it like this: A1\n"
            "Type `surrender` to give up."
        )
        await self.next.user.send("Their turn", delete_after=3.0)
        while True:
            try:
                await self.bot.wait_for("message", check=self.predicate, timeout=60.0)
            except asyncio.TimeoutError:
                await self.turn.user.send("You took too long. Game over!")
                await self.next.user.send(f"{self.turn.user} took too long. Game over!")
                await self.public_channel.send(
                    f"Game over! {self.turn.user.mention} timed out so {self.next.user.mention} wins!"
                )
                self.gameover = True
                break
            else:
                if self.surrender:
                    await self.next.user.send(
                        f"{self.turn.user} surrendered. Game over!"
                    )
                    await self.public_channel.send(
                        f"Game over! {self.turn.user.mention} surrendered to {self.next.user.mention}!"
                    )
                    self.gameover = True
                    break
                square = self.get_square(self.next.grid, self.match.string)
                if square.aimed:
                    await self.turn.user.send(
                        "You've already aimed at this square!", delete_after=3.0
                    )
                else:
                    break
        await turn_message.delete()
        return square

    async def hit(self, square: Square, alert_messages: list[discord.Message]) -> None:
        """Occurs when a player successfully aims for a ship."""
        await self.turn.user.send("Hit!", delete_after=3.0)
        alert_messages.append(await self.next.user.send("Hit!"))
        if self.check_sink(self.next.grid, square.boat):
            await self.turn.user.send(
                f"You've sunk their {square.boat} ship!", delete_after=3.0
            )
            alert_messages.append(
                await self.next.user.send(f"Oh no! Your {square.boat} ship sunk!")
            )
            if self.check_gameover(self.next.grid):
                await self.turn.user.send("You win!")
                await self.next.user.send("You lose!")
                self.gameover = True
                await self.game_over(winner=self.turn.user, loser=self.next.user)

    async def start_game(self) -> None:
        """Begins the game."""
        await self.p1.user.send(f"You're playing battleship with {self.p2.user}.")
        await self.p2.user.send(f"You're playing battleship with {self.p1.user}.")

        alert_messages = []

        self.turn = self.p1
        self.next = self.p2

        while True:
            await self.print_grids()

            if self.gameover:
                return

            square = await self.take_turn()
            if not square:
                return
            square.aimed = True

            for message in alert_messages:
                await message.delete()

            alert_messages = [
                await self.next.user.send(
                    f"{self.turn.user} aimed at {self.match.string}!"
                )
            ]

            if square.boat:
                await self.hit(square, alert_messages)
                if self.gameover:
                    return
            else:
                await self.turn.user.send("Miss!", delete_after=3.0)
                alert_messages.append(await self.next.user.send("Miss!"))

            self.turn, self.next = self.next, self.turn


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
        count = 0
        for y in range(self.y - 1, self.y + 2):
            for x in range(self.x - 1, self.x + 2):
                if (
                    0 <= y < self.board.size_y
                    and 0 <= x < self.board.size_x
                    and self.board[x, y].mine
                ):
                    count += 1
        return count

    def __str__(self):
        if self.clicked:

            if self.number == 0:
                number = "\u200b"
            else:
                number = boardgames.keycap_digit(self.number)

            return "💥" if self.mine else number
        return "🚩" if self.flagged else "⬜"


class Game(boardgames.Board[Cell]):
    def __init__(self, size_x=10, size_y=7):
        super().__init__(size_x, size_y)
        self.record = None
        self.last_state = None

        self._state = [
            [Cell(self, y, x) for x in range(self.size_x)] for y in range(self.size_y)
        ]

    def setup(self, click_y: int, click_x: int):
        """Places mines on the board"""
        cells = [
            (i // self.size_x, i % self.size_x)
            for i in range(self.size_x * self.size_y)
        ]
        cells.remove((click_y, click_x))

        for y, x in sample(
            cells,
            int(
                (self.size_x * self.size_y + 1) // ((self.size_x * self.size_y) ** 0.5)
            ),
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
                    for i in range(y - 1, y + 2):
                        for j in range(x - 1, x + 2):
                            if (
                                0 <= i < self.size_y
                                and 0 <= j < self.size_x
                                and not self[j, i].clicked
                            ):
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

        for r in range(5):
            for c in range(5):
                self.add_item(Button(r, c, offset))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.meta.player:
            await interaction.response.send_message(
                "Sorry, you are not playing", ephemeral=True
            )
            return False
        return True

    async def update(self):
        if self.offset != 0:
            content = "\u200b"
        else:
            if self.meta.board.lost:
                content = "💥"
            elif self.meta.board.solved:
                content = ":tada:"
            else:
                content = "Minesweeper!"
        await self.message.edit(content=content, view=self)


class MetaGameUI:
    def __init__(
        self, player: discord.Member, channel: discord.TextChannel, size: int = 2
    ):
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
            view.message = await self.channel.send(
                content="Minesweeper" if view.offset == 0 else "\u200b", view=view
            )


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
        self.games: list[Game] = []
        self.waiting: list[discord.Member] = []
        self._games: dict[discord.TextChannel, Game] = {}
        self.games_c4: list[GameC4] = []
        self.waiting_c4: list[discord.Member] = []
        self.games_boogle: dict[discord.TextChannel, Game] = {}
        self.tokens = [":white_circle:", ":blue_circle:", ":red_circle:"]
        self.games_hitler: dict[int, discord.ui.View] = {}
        self.chess_games = []

        self.max_board_size = 9
        self.min_board_size = 5

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{VIDEO GAME}")

    def predicate(
        self,
        ctx: commands.Context,
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

        if (
            user.id == ctx.author.id
            and str(reaction.emoji) == CROSS_EMOJI
            and reaction.message.id == announcement.id
        ):
            return True
        return False

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
            if user.bot:
                return False
            if user == ctx.author:
                return False
            return True

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

    async def check_author(self, ctx: commands.Context, board_size: int) -> bool:
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
        ctx: commands.Context,
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

        if (
            user.id == ctx.author.id
            and str(reaction.emoji) == CROSS_EMOJI
            and reaction.message.id == announcement.id
        ):
            return True
        return False

    def already_playing_cf(self, player: discord.Member) -> bool:
        """Check if someone is already in a game."""
        return any(player in (game.player1, game.player2) for game in self.games_c4)

    @staticmethod
    def check_emojis(e1: EMOJI_CHECK, e2: EMOJI_CHECK) -> tuple[bool, Optional[str]]:
        """Validate the emojis, the user put."""
        if isinstance(e1, str) and emoji.count(e1) != 1:
            return False, e1
        if isinstance(e2, str) and emoji.count(e2) != 1:
            return False, e2
        return True, None

    async def _play_game(
        self,
        ctx: commands.Context,
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
        except Exception:
            # End the game in the event of an unforeseen error so the players aren't stuck in a game
            await ctx.send(
                f"{ctx.author.mention} {user.mention if user else ''} An error occurred. Game failed."
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
        ctx: commands.Context,
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
        ctx: commands.Context,
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
    @commands.bot_has_permissions(embed_links=True)
    async def aki(self, ctx: Context):
        """Answer the questions and let the bot guess your character!"""
        aki = Akinator()
        q = await aki.start_game()
        question_num = 1
        while aki.progression <= 80:
            question = q + "\n\t"
            embed = discord.Embed(color=0xFF0000)
            embed.add_field(
                name=f"Q-{question_num}\n{question}",
                value="Reply with `yes/y` | `no/n` | `i/idk/i don't know` | `p/probably` | `proably not/pn`",
            )
            await ctx.send(embed=embed)

            def check_response(m):
                replies = (
                    "yes",
                    "y",
                    "no",
                    "n",
                    "i",
                    "idk",
                    "i don't know",
                    "probably",
                    "p",
                    "probably not",
                    "pn",
                )
                return (
                    m.content.lower() in replies
                    and m.channel == ctx.channel
                    and m.author == ctx.author
                )

            try:
                msg = await self.bot.wait_for(
                    "message", check=check_response, timeout=30
                )
            except Exception:
                return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
            if msg.content.lower() in ("b", "back"):
                try:
                    q = await aki.back()
                except akinator.CantGoBackAnyFurther:
                    pass
            else:
                q = await aki.answer(msg.content)
            question_num += 1
        await aki.win()

        embed = discord.Embed(
            title=f"It's {aki.first_guess['name']} ({aki.first_guess['description']})! Was I correct?\n\t",
            color=0xFF0000,
        )
        embed.set_image(url=f"{aki.first_guess['absolute_picture_path']}")
        embed.add_field(name="Reply with `yes/y` `no/n`", value="\u200b")
        await ctx.send(embed=embed)

        def check_yes_no(m):
            return (
                m.content.lower() in ("yes", "y", "no", "n")
                and m.channel == ctx.channel
                and m.author == ctx.author
            )

        try:
            correct = await self.bot.wait_for("message", check=check_yes_no, timeout=30)
        except Exception:
            return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
        if correct.content.lower() in ("yes", "y"):
            embed = discord.Embed(title="Yay! I guessed it right", color=0xFF0000)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Oof! Kinda hard one", color=0xFF0000)
            await ctx.send(embed=embed)

    @commands.command(aliases=["tic", "tic_tac_toe", "ttt"])
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
            if not opponent.bot:
                if not await ctx.confirm(
                    self.bot,
                    ctx.channel,
                    opponent,
                    f"{opponent.mention}, {ctx.author} has challenged you to Tic-Tac-Toe! do you accept?",
                ):
                    opponent = None

        # If challenge timed out
        if opponent is None:
            raise commands.BadArgument("Challenge cancelled.")

        game = GameTicTacToe((ctx.author, opponent))

        await ctx.send(f"{game.current_player.mention}'s (X) turn!", view=game)  # type: ignore

    @commands.group(name="minesweeper", aliases=["ms"], invoke_without_command=True)
    async def minesweeper(self, ctx):
        """Minesweeper game commands"""

    @minesweeper.group(name="start")
    @commands.check(is_no_game)
    async def ms_start(self, ctx):
        """Starts a Minesweeper game"""
        if ctx.invoked_subcommand is None:
            await MetaGameUI(ctx.author, ctx.channel).start()

    @ms_start.command(name="tiny")
    async def ms_start_tiny(self, ctx):
        """Starts a easy difficulty Minesweeper game"""
        game = self._games[ctx.channel] = Game(5, 5)
        game.last_state = await ctx.send(
            f"Minesweeper Game Started!\n>>> {game}\n\nReveal cells with `{ctx.prefix}ms click`."
        )

    @ms_start.command(name="easy")
    async def ms_start_easy(self, ctx):
        """Starts a easy difficulty Minesweeper game"""
        game = self._games[ctx.channel] = Game(10, 7)
        game.last_state = await ctx.send(
            f"Minesweeper Game Started!\n>>> {game}\n\nReveal cells with `{ctx.prefix}ms click`."
        )

    @ms_start.command(name="medium")
    async def ms_start_medium(self, ctx):
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
        game.last_state = await ctx.send(f">>> {game}" + message)

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

    @commands.group(invoke_without_command=True)
    async def battleship(self, ctx: commands.Context) -> None:
        """
        Play a game of Battleship with someone else!
        This will set up a message waiting for someone else to react and play along.
        The game takes place entirely in DMs.
        Make sure you have your DMs open so that the bot can message you.
        """
        if self.already_playing(ctx.author):
            await ctx.send("You're already playing a game!")
            return

        if ctx.author in self.waiting:
            await ctx.send("You've already sent out a request for a player 2.")
            return

        announcement = await ctx.send(
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
        self.waiting.remove(ctx.author)
        if self.already_playing(ctx.author):
            return
        game = GameBattleShip(self.bot, ctx.channel, ctx.author, user)
        self.games.append(game)
        try:
            await game.start_game()
            self.games.remove(game)
        except discord.Forbidden:
            await ctx.send(
                f"{ctx.author.mention} {user.mention} "
                "Game failed. This is likely due to you not having your DMs open. Check and try again."
            )
            self.games.remove(game)
        except Exception:
            # End the game in the event of an unforseen error so the players aren't stuck in a game
            await ctx.send(
                f"{ctx.author.mention} {user.mention} An error occurred. Game failed."
            )
            self.games.remove(game)
            raise

    @battleship.command(name="ships", aliases=("boats",))
    async def battleship_ships(self, ctx: commands.Context) -> None:
        """Lists the ships that are found on the battleship grid."""
        embed = discord.Embed(colour=Colours.blue)
        embed.add_field(name="Name", value="\n".join(SHIPS))
        embed.add_field(
            name="Size", value="\n".join(str(size) for size in SHIPS.values())
        )
        await ctx.send(embed=embed)

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
        if not ctx.invoked_subcommand:
            level = level or 1
            if not 10 >= level >= 1:
                return await ctx.send(
                    f"{ctx.author.mention} for now existing levels are from range 1-10"
                )
            ls = []
            async with async_open(
                fr"extra/sokoban/level{level if level else 1}.txt", "r"
            ) as fp:
                lvl_str = await fp.read()
            for i in lvl_str.split("\n"):
                ls.append(list(list(i)))
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
        ls = []
        level = text.strip("```")
        for i in level.split("\n"):
            ls.append(list(list(i)))
        game = SokobanGame(ls)
        game._get_cords()
        main_game = SokobanGameView(game, ctx.author)
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
        embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{BoardString}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {ctx.author}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/922771882904793120/41NgOgTVblL.png"
            )
        )
        await ctx.send(embed=embed, view=Twenty48_Button(game, ctx.author))

    @commands.group(name="chess", invoke_without_command=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def chess(self, ctx: Context):
        """Chess game. In testing"""
        if not ctx.invoked_subcommand:
            announcement = await ctx.send(
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
    async def custom_chess(self, ctx: Context, board: fenPass):
        """To play chess, from a custom FEN notation"""
        announcement = await ctx.send(
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
    async def slidingpuzzle(self, ctx: Context, boardsize: Optional[int] = None):
        """A Classic Sliding game"""
        boardsize = boardsize or 4
        if boardsize < 4:
            return await ctx.send(
                f"{ctx.author.mention} board size must not less than 4"
            )
        if boardsize > 10:
            return await ctx.send(f"{ctx.author.mention} board size must less than 10")

        game = SlidingPuzzle(boardsize if boardsize else 4)
        embed = (
            discord.Embed(
                title="2048 Game",
                description=f"```diff\n{game.board_str()}\n```",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {ctx.author}")
            .set_thumbnail(
                url="https://cdn.discordapp.com/attachments/894938379697913916/923106185584984104/d1b246ff6d7c01f4bc372319877ef0f6.gif"
            )
        )
        await ctx.send(embed=embed, view=SlidingPuzzleView(game, ctx.author))

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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Check if channel has a game going
        if message.channel not in self.games_boogle:
            return

        await self.games_boogle[message.channel].check_message(message)

    @commands.command(aliases=["umbrogus", "secret_hitler", "secret-hitler"])
    @commands.bot_has_permissions(embed_links=True)
    async def secrethitler(self, ctx: Context) -> None:
        if ctx.channel.id in self.games_hitler:
            raise commands.BadArgument(
                "There is already a game running in this channel."
            )

        self.games_hitler[ctx.channel.id] = MISSING
        await JoinUI.start(ctx, self.games_hitler)
