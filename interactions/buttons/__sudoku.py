from __future__ import annotations

import itertools
import random
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, TypeVar

import discord

if TYPE_CHECKING:
    from core import Context

T = TypeVar("T")


class Sudoku:
    def __init__(self, base: int = 3):
        self.base: int = base
        self.side = base**2

        self.rows = [g * base + r for g in self.suffle(list(range(base))) for r in self.suffle(list(range(base)))]
        self.cols = [g * base + c for g in self.suffle(list(range(base))) for c in self.suffle(list(range(base)))]

        self.nums = self.suffle(list(range(1, base**2 + 1)))

        self.board = [[self.nums[self.pattern(r, c)] for c in self.cols] for r in self.rows]
        self.original_board = self.board.copy()

        self._current_row = 0
        self._current_col = 0

        self._changeable_positions = []

    def pattern(self, r: int, c: int) -> int:
        return (self.base * (r % self.base) + r // self.base + c) % self.side

    def suffle(self, s: List[T]) -> List[T]:
        return random.sample(s, len(s))

    def expand_line(self, line: str) -> str:
        return line[0] + line[5:9].join([line[1:5] * (self.base - 1)] * self.base) + line[9:]

    def display_board(self, view="pretty") -> str:
        line0 = "  " + self.expand_line("╔═══╤═══╦═══╗")
        line1 = "# " + self.expand_line("║ . │ . ║ . ║ #")
        line2 = "  " + self.expand_line("╟───┼───╫───╢")
        line3 = "  " + self.expand_line("╠═══╪═══╬═══╣")
        line4 = "  " + self.expand_line("╚═══╧═══╩═══╝")

        symbol = " 123456789"
        nums = []
        for row_index, row in enumerate(self.board):
            temp = []
            for col_index, n in enumerate(row):
                if (self._current_row, self._current_col) == (row_index, col_index):
                    if n < 0:
                        temp.append(f"[{symbol[-n]}]")
                    else:
                        temp.append(f"[{symbol[n]}]")
                if n < 0:
                    temp.append("   ")
                else:
                    temp.append(f" {symbol[n]} ")
            nums.append([""] + temp)

        coord = "   " + "".join(f" {s}  " for s in symbol[1 : self.side + 1])
        lines = [coord, line0]
        board = ""

        for r in range(1, self.side + 1):
            line1n = line1.replace("#", str(symbol[r]))
            lines.append("".join(n + s for n, s in zip(nums[r - 1], line1n.split(" . "))))
            lines.append([line2, line3, line4][(r % self.side == 0) + (r % self.base == 0)])
        lines.append(coord)

        board = "\n".join(lines)

        if view == "discord":
            head = "- - - - - - - - S U D O K U - - - - - - - -"
            board = f"```\n{head}\n\n{board}\n``` Location: `{self._current_row + 1}, {self._current_col + 1}`"

        if view == "pretty":
            print(*lines, sep="\n")
            return ""

        return board

    def generate_board(self) -> None:
        squares = self.side * self.side
        empties = squares * 3 // 4
        for p in random.sample(range(squares), empties):
            self.board[p // self.side][p % self.side] = 0
            self._changeable_positions.append((p // self.side, p % self.side))

    def place_number_at(self, row: int, col: int, number: int) -> None:
        self.board[row][col] = number

    def place_number(self, number: int) -> None:
        if (self._current_row, self._current_col) not in self._changeable_positions:
            return
        self.board[self._current_row][self._current_col] = number

    def checker(self) -> bool:
        def line_ok(e):
            if len(set(e)) != 9:
                return False
            for i in range(len(e)):
                if e[i] not in range(1, 10):
                    return False
            return True

        bad_rows = [False for row in self.board if not line_ok(row)]
        grid = list(zip(*self.board))
        bad_cols = [False for col in grid if not line_ok(col)]
        squares = []
        for i in range(0, 9, 3):
            for j in range(0, 9, 3):
                square = list(itertools.chain.from_iterable(row[j : j + 3] for row in grid[i : i + 3]))
                squares.append(square)
        bad_squares = [False for sq in squares if not line_ok(sq)]
        return not any([bad_rows, bad_cols, bad_squares])

    def move_cursor_at(self, row: int, col: int) -> None:
        if row < 0 or row > self.side - 1:
            row = 0
        if col < 0 or col > self.side - 1:
            col = 0
        self._current_row = row
        self._current_col = col

    def move_cursor_up(self) -> None:
        if self._current_row == 0:
            self._current_row = self.side - 1
        else:
            self._current_row -= 1

    def move_cursor_down(self) -> None:
        if self._current_row == self.side - 1:
            self._current_row = 0
        else:
            self._current_row += 1

    def move_cursor_left(self) -> None:
        if self._current_col == 0:
            self._current_col = self.side - 1
        else:
            self._current_col -= 1

    def move_cursor_right(self) -> None:
        if self._current_col == self.side - 1:
            self._current_col = 0
        else:
            self._current_col += 1

    @property
    def get_current_row(self) -> int:
        return self._current_row

    @property
    def get_current_col(self) -> int:
        return self._current_col

    def current_number(self) -> int:
        return self.board[self._current_row][self._current_col]

    @property
    def is_current_number_empty(self) -> bool:
        return self.current_number() == 0 or self.current_number() < 0

    @property
    def cursor_position(self) -> Tuple[int, int]:
        return self._current_row, self._current_col

    @cursor_position.setter
    def cursor_position(self, position: Tuple[int, int]) -> None:
        self._current_row, self._current_col = position

    def erase_current_position(self) -> None:
        if (self._current_row, self._current_col) in self._changeable_positions:
            return
        self.board[self._current_row][self._current_col] = 0


class SudokuButton(discord.ui.Button["SudokuView"]):
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None

        if self.view.game.is_current_number_empty and self.label:
            self.view.game.place_number(int(self.label))
            await interaction.response.edit_message(content=self.view.game.display_board("discord"), view=self.view)
        else:
            await interaction.response.defer()


class SudokuView(discord.ui.View):
    message: discord.Message

    def __init__(self, timeout: Optional[float] = None) -> None:
        super().__init__(timeout=timeout)

        self.game = Sudoku()
        self.game.generate_board()

    def init(self):
        for i in range(1, 5 + 1):
            self.add_item(
                SudokuButton(
                    label=str(i),
                    custom_id=f"sudoku_{i}",
                    row=3,
                )
            )

        for j in range(6, 9 + 1):
            self.add_item(
                SudokuButton(
                    label=str(j),
                    custom_id=f"sudoku_{j}",
                    row=4,
                )
            )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.message.author.id:
            return True
        await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
        return False

    @discord.ui.button(
        label="\u200b",
        style=discord.ButtonStyle.secondary,
        disabled=True,
    )
    async def __null_1(self, interaction: discord.Interaction, _: discord.ui.Button):
        return

    @discord.ui.button(
        emoji="\N{UPWARDS BLACK ARROW}",
        style=discord.ButtonStyle.secondary,
    )
    async def up_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.move_cursor_up()
        await interaction.response.edit_message(content=self.game.display_board("discord"), view=self)

    @discord.ui.button(
        label="\u200b",
        style=discord.ButtonStyle.secondary,
        disabled=True,
    )
    async def __null_2(self, interaction: discord.Interaction, _: discord.ui.Button):
        return

    @discord.ui.button(
        emoji="\N{LEFTWARDS BLACK ARROW}",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def left_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.move_cursor_left()
        await interaction.response.edit_message(content=self.game.display_board("discord"), view=self)

    @discord.ui.button(
        emoji="\N{MEMO}",
        style=discord.ButtonStyle.secondary,
        disabled=True,
        row=1,
    )
    async def erase(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.erase_current_position()
        await interaction.response.edit_message(content=self.game.display_board("discord"), view=self)

    @discord.ui.button(
        emoji="\N{BLACK RIGHTWARDS ARROW}",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def right_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.move_cursor_right()
        await interaction.response.edit_message(content=self.game.display_board("discord"), view=self)

    @discord.ui.button(
        label="\u200b",
        style=discord.ButtonStyle.secondary,
        disabled=True,
        row=2,
    )
    async def __null_4(self, interaction: discord.Interaction, _: discord.ui.Button):
        return

    @discord.ui.button(
        emoji="\N{DOWNWARDS BLACK ARROW}",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def down_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.move_cursor_down()
        await interaction.response.edit_message(content=self.game.display_board("discord"), view=self)

    @discord.ui.button(
        label="\u200b",
        style=discord.ButtonStyle.secondary,
        disabled=True,
        row=2,
    )
    async def __null_5(self, interaction: discord.Interaction, _: discord.ui.Button):
        return

    async def start(
        self,
        ctx: Context,
    ) -> None:
        self.init()
        self.message = await ctx.send(self.game.display_board("discord"), view=self)  # type: ignore
