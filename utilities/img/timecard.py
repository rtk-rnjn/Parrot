from __future__ import annotations

import io
import random
from typing import NamedTuple, Optional

from PIL import Image, ImageDraw, ImageFont

import discord
from utilities.converters import ToAsync


class Timecard(NamedTuple):
    filename: str
    colour: discord.Colour
    shadow_colour: Optional[discord.Colour]


IMAGES = "extra/timecard/images"
FONT = "extra/timecard/kp.ttf"

TIMECARD_X_OFFSET = 32
TIMECARD_Y_OFFSET = 24

TIMECARD_X_BOUND = 576
TIMECARD_Y_BOUND = 432

TIMECARDS = [
    Timecard(
        "0",
        discord.Colour.from_rgb(226, 255, 159),
        None,
    ),
    Timecard(
        "1",
        discord.Colour.from_rgb(235, 4, 210),
        discord.Colour.from_rgb(60, 255, 23),
    ),
    Timecard(
        "2",
        discord.Colour.from_rgb(99, 250, 208),
        discord.Colour.from_rgb(1, 4, 0),
    ),
    Timecard(
        "3",
        discord.Colour.from_rgb(248, 103, 1),
        discord.Colour.from_rgb(32, 127, 34),
    ),
    Timecard(
        "4",
        discord.Colour.from_rgb(8, 2, 3),
        None,
    ),
    Timecard(
        "5",
        discord.Colour.from_rgb(30, 234, 239),
        None,
    ),
    Timecard(
        "6",
        discord.Colour.from_rgb(1, 180, 235),
        None,
    ),
    Timecard(
        "7",
        discord.Colour.from_rgb(91, 94, 2),
        None,
    ),
    Timecard(
        "8",
        discord.Colour.from_rgb(250, 240, 212),
        discord.Colour.from_rgb(37, 53, 60),
    ),
    Timecard(
        "9",
        discord.Colour.from_rgb(9, 160, 212),
        discord.Colour.from_rgb(0, 11, 23),
    ),
    Timecard(
        "10",
        discord.Colour.from_rgb(250, 236, 255),
        discord.Colour.from_rgb(28, 188, 234),
    ),
    Timecard(
        "11",
        discord.Colour.from_rgb(254, 254, 254),
        None,
    ),
    Timecard(
        "12",
        discord.Colour.from_rgb(252, 231, 40),
        None,
    ),
    Timecard(
        "13",
        discord.Colour.from_rgb(254, 254, 254),
        None,
    ),
    Timecard(
        "14",
        discord.Colour.from_rgb(70, 109, 40),
        None,
    ),
    Timecard(
        "15",
        discord.Colour.from_rgb(216, 34, 148),
        discord.Colour.from_rgb(122, 70, 13),
    ),
]


@ToAsync()
def timecard(text: str) -> discord.File:
    timecard: Timecard = random.choice(TIMECARDS)

    image = Image.open(f"{IMAGES}/timecard_{timecard.filename}.png")
    draw = ImageDraw.Draw(image)

    # Setup font
    font_size = 100
    font = ImageFont.truetype(FONT, font_size)

    # Calculate font-size
    while (text_size := draw.textsize(text, font=font)) > (
        TIMECARD_X_BOUND,
        TIMECARD_Y_BOUND,
    ):
        font_size -= 1
        font = ImageFont.truetype(FONT, font_size)

    # Calculate Starting Y position
    y_pos = TIMECARD_Y_OFFSET + (TIMECARD_Y_BOUND - text_size[1]) // 2

    # Draw text
    lines = text.split("\n")
    for line in lines:
        line_width, _ = draw.textsize(line, font=font)
        x_pos = TIMECARD_X_OFFSET + (TIMECARD_X_BOUND - line_width) // 2

        if timecard.shadow_colour is not None:
            shadow_offset = int(font_size**0.5 / 2) + 1
            draw.text(
                (x_pos - shadow_offset, y_pos - shadow_offset),
                line,
                timecard.shadow_colour.to_rgb(),
                font=font,
            )

        draw.text((x_pos, y_pos), line, timecard.colour.to_rgb(), font=font)

        y_pos += text_size[1] // len(lines)

    out_fp = io.BytesIO()
    image.save(out_fp, "PNG")
    out_fp.seek(0)

    return discord.File(out_fp, "timecard.png")
