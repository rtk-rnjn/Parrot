from __future__ import annotations

import asyncio
import random
import re
from collections import defaultdict
from itertools import product
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import discord

DECK = list(product(*[(0, 1, 2)] * 4))

GAME_DURATION = 180

# Scoring
CORRECT_SOLN = 1
INCORRECT_SOLN = -1
CORRECT_GOOSE = 2
INCORRECT_GOOSE = -1

# Distribution of minimum acceptable solutions at board generation.
# This is for gameplay reasons, to shift the number of solutions per board up,
# while still making the end of the game unpredictable.
# Note: this is *not* the same as the distribution of number of solutions.

SOLN_DISTR = 0, 0.05, 0.05, 0.1, 0.15, 0.25, 0.2, 0.15, 0.05

IMAGE_PATH = Path("extra", "duckgame", "all_cards.png")
FONT_PATH = Path("extra", "duckgame", "LuckiestGuy-Regular.ttf")
HELP_IMAGE_PATH = Path("extra", "duckgame", "ducks_help_ex.png")

ALL_CARDS = Image.open(IMAGE_PATH)
LABEL_FONT = ImageFont.truetype(str(FONT_PATH), size=16)
CARD_WIDTH = 155
CARD_HEIGHT = 97

EMOJI_WRONG = "\u274C"

ANSWER_REGEX = re.compile(r"^\D*(\d+)\D+(\d+)\D+(\d+)\D*$")

HELP_TEXT = """
**Each card has 4 features**
Color, Number, Hat, and Accessory
**A valid flight**
3 cards where each feature is either all the same or all different
**Call "GOOSE"**
if you think there are no more flights
**+1** for each valid flight
**+2** for a correct "GOOSE" call
**-1** for any wrong answer
The first flight below is invalid: the first card has swords while the other two have no accessory.\
 It would be valid if the first card was empty-handed, or one of the other two had paintbrushes.
The second flight is valid because there are no 2:1 splits; each feature is either all the same or all different.
"""


def assemble_board_image(board: list[tuple[int]], rows: int, columns: int) -> Image.Image:
    """Cut and paste images representing the given cards into an image representing the board."""
    new_im = Image.new("RGBA", (CARD_WIDTH * columns, CARD_HEIGHT * rows))
    draw = ImageDraw.Draw(new_im)
    for idx, card in enumerate(board):
        card_image = get_card_image(card)
        row, col = divmod(idx, columns)
        top, left = row * CARD_HEIGHT, col * CARD_WIDTH
        new_im.paste(card_image, (left, top))
        draw.text(
            xy=(left + 5, top + 5),  # magic numbers are buffers for the card labels
            text=str(idx),
            fill=(0, 0, 0),
            font=LABEL_FONT,
        )
    return new_im


def get_card_image(card: tuple[int]) -> Image.Image:
    """Slice the image containing all the cards to get just this card."""
    # The master card image file should have 9x9 cards,
    # arranged such that their features can be interpreted as ordered trinary.
    row, col = divmod(as_trinary(card), 9)
    x1 = col * CARD_WIDTH
    x2 = x1 + CARD_WIDTH
    y1 = row * CARD_HEIGHT
    y2 = y1 + CARD_HEIGHT
    return ALL_CARDS.crop((x1, y1, x2, y2))


def as_trinary(card: tuple[int]) -> int:
    """Find the card's unique index by interpreting its features as trinary."""
    return int("".join(str(x) for x in card), base=3)


class DuckGame:
    """A class for a single game."""

    running: bool

    def __init__(
        self,
        rows: int = 4,
        columns: int = 3,
        minimum_solutions: int = 1,
    ) -> None:
        """Take samples from the deck to generate a board.

        Args:
        ----
            rows (int, optional): Rows in the game board. Defaults to 4.
            columns (int, optional): Columns in the game board. Defaults to 3.
            minimum_solutions (int, optional): Minimum acceptable number of solutions in the board. Defaults to 1.
        """
        self.rows = rows
        self.columns = columns
        size = rows * columns

        self._solutions = None
        self.claimed_answers = {}
        self.scores = defaultdict(int)
        self.editing_embed = asyncio.Lock()

        self.board = random.sample(DECK, size)
        while len(self.solutions) < minimum_solutions:
            self.board = random.sample(DECK, size)

        self.board_msg: discord.Message | None = None
        self.found_msg: discord.Message | None = None

    @property
    def board(self) -> list[tuple[int]]:
        """Accesses board property."""
        return self._board

    @board.setter
    def board(self, val: list[tuple[int]]) -> None:
        """Erases calculated solutions if the board changes."""
        self._solutions = None
        self._board = val

    @property
    def solutions(self):
        """Calculate valid solutions and cache to avoid redoing work."""
        if self._solutions is None:
            self._solutions = set()
            for idx_a, card_a in enumerate(self.board):
                for idx_b, card_b in enumerate(self.board[idx_a + 1 :], start=idx_a + 1):
                    # Two points determine a line, and there are exactly 3 points per line in {0,1,2}^4.
                    # The completion of a line will only be a duplicate point if the other two points are the same,
                    # which is prevented by the triangle iteration.
                    completion = tuple(
                        feat_a if feat_a == feat_b else 3 - feat_a - feat_b
                        for feat_a, feat_b in zip(card_a, card_b, strict=False)
                    )
                    try:
                        idx_c = self.board.index(completion)
                    except ValueError:
                        continue

                    # Indices within the solution are sorted to detect duplicate solutions modulo order.
                    solution = tuple(sorted((idx_a, idx_b, idx_c)))
                    self._solutions.add(solution)

        return self._solutions
