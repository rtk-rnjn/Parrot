from __future__ import annotations

from typing import Generic, Iterator, TypeVar, Union

T = TypeVar("T")


__all__ = (
    "regional_indicator",
    "keycap_digit",
    "Board",
)


def regional_indicator(c: str) -> str:
    """Returns a regional indicator emoji given a character."""
    return chr(0x1F1E6 - ord("A") + ord(c.upper()))


def keycap_digit(c: Union[int, str]) -> str:
    """Returns a keycap digit emoji given a character."""
    c = int(c)
    if 0 < c < 10:
        return str(c) + "\U0000FE0F\U000020E3"
    if c == 10:
        return "\U000FE83B"
    raise ValueError("Invalid keycap digit")


class Board(Generic[T]):
    """Simple emoji grid with row and column markers.
    size_x: int
        The width of the board, must be between 1 and 26.
    size_y: int
        The height of the board, must be between 1 and 10.
    fill_with: str
        An emoji to fill the board with by default.
    """

    pivot = "\N{black circle for record}"
    spacer = "\N{black large square}"

    def __init__(
        self,
        size_x: int,
        size_y: int,
        fill_with: T = "\N{white large square}",
        *,
        draw_row_guide: bool = True,
        draw_column_guide: bool = True,
    ):
        if not 1 <= size_x <= 26:
            raise ValueError("Boards can have a maximum width of 26.")
        if not 1 <= size_y <= 10:
            raise ValueError("Boards can have a maximum height of 10.")

        self.size_x = size_x
        self.size_y = size_y
        self._state: list[list[T]] = [
            [fill_with for _ in range(size_x)] for _ in range(size_y)
        ]
        self._draw_row_guide = draw_row_guide
        self._draw_column_guide = draw_column_guide

    def __getitem__(self, ij: tuple[int, int]) -> T:
        i, j = ij
        return self._state[j][i]

    def __setitem__(self, ij: tuple[int, int], value: T):
        i, j = ij
        self._state[j][i] = value

    def __iter__(self) -> Iterator[list[T]]:
        return self._state.__iter__()

    def __len__(self) -> int:
        return self.size_x * self.size_y

    def __str__(self):
        out = ""

        if self._draw_column_guide:
            if self._draw_row_guide:
                out += self.pivot + self.spacer

            for i, _ in enumerate(self._state[0]):
                out += "​" + regional_indicator(chr(i + ord("A")))
            out += "\n" + self.spacer * (
                len(self._state[0]) + (2 if self._draw_row_guide else 0)
            )

        for y, row in enumerate(self._state):
            out += "\n"

            if self._draw_row_guide:
                out += keycap_digit(y + 1) + self.spacer

            for cell in row:
                out += str(cell)

        return out
