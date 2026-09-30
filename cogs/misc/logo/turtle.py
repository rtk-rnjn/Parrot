from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageDraw


@dataclass
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float
    color: tuple[int, int, int]
    width: int


class Turtle:
    def __init__(self, width: int = 1000, height: int = 800) -> None:
        self.width = width
        self.height = height

        self.x = width / 2
        self.y = height / 2

        # Logo convention:
        # 0 degrees = north
        # 90 degrees = east
        self.heading = 0.0

        self.pen_down = True
        self.pen_color = (0, 0, 0)
        self.pen_width = 2

        self.segments: list[Segment] = []

    # Movement

    def forward(self, distance: float) -> None:
        radians = math.radians(self.heading)

        new_x = self.x + math.sin(radians) * distance
        new_y = self.y - math.cos(radians) * distance

        if self.pen_down:
            self.segments.append(
                Segment(
                    self.x,
                    self.y,
                    new_x,
                    new_y,
                    self.pen_color,
                    self.pen_width,
                )
            )

        self.x = new_x
        self.y = new_y

    def backward(self, distance: float) -> None:
        self.forward(-distance)

    def right(self, degrees: float) -> None:
        self.heading = (self.heading + degrees) % 360

    def left(self, degrees: float) -> None:
        self.heading = (self.heading - degrees) % 360

    # Pen

    def pen_up(self) -> None:
        self.pen_down = False

    def pen_down_mode(self) -> None:
        self.pen_down = True

    def set_color(self, color: tuple[int, int, int]) -> None:
        self.pen_color = color

    def set_width(self, width: int) -> None:
        if width < 1 or width > 50:
            msg = "Pen width must be between 1 and 50."
            raise ValueError(msg)

        self.pen_width = width

    # Position

    def home(self) -> None:
        self.x = self.width / 2
        self.y = self.height / 2
        self.heading = 0

    def set_heading(self, heading: float) -> None:
        self.heading = heading % 360

    def set_xy(self, x: float, y: float) -> None:
        # Convert Logo coordinates to Pillow coordinates.
        new_x = self.width / 2 + x
        new_y = self.height / 2 - y

        if self.pen_down:
            self.segments.append(
                Segment(
                    self.x,
                    self.y,
                    new_x,
                    new_y,
                    self.pen_color,
                    self.pen_width,
                )
            )

        self.x = new_x
        self.y = new_y

    def clear(self) -> None:
        self.segments.clear()

    # Rendering

    def render(self) -> BytesIO:
        image = Image.new(
            "RGB",
            (self.width, self.height),
            "white",
        )

        draw = ImageDraw.Draw(image)

        for segment in self.segments:
            draw.line(
                (
                    segment.x1,
                    segment.y1,
                    segment.x2,
                    segment.y2,
                ),
                fill=segment.color,
                width=segment.width,
            )

        output = BytesIO()

        image.save(output, format="PNG", optimize=True)

        output.seek(0)

        return output


COLORS: dict[str, tuple[int, int, int]] = {
    "BLACK": (0, 0, 0),
    "WHITE": (255, 255, 255),
    "RED": (255, 0, 0),
    "GREEN": (0, 128, 0),
    "BLUE": (0, 0, 255),
    "YELLOW": (255, 255, 0),
    "CYAN": (0, 255, 255),
    "MAGENTA": (255, 0, 255),
    "ORANGE": (255, 165, 0),
    "PURPLE": (128, 0, 128),
    "PINK": (255, 192, 203),
    "BROWN": (165, 42, 42),
}


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.lstrip('"').upper()

    try:
        return COLORS[value]
    except KeyError as exc:
        msg = f"Unknown color {value!r}. Available colors: {', '.join(COLORS)}"
        raise ValueError(msg) from exc
