from __future__ import annotations

import io
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

import discord
from utilities.converters import ToAsync

IMAGE = "extra/imagine.png"
TITLE_FONT = "extra/GintoNord-Black.ttf"
BYLINE_FONT = "extra/roboto-bold.ttf"

IMAGE_WIDTH = 2048
IMAGE_HEIGHT = 1024

TITLE_OFFSET = (0, 0)
TITLE_BOUND = (
    IMAGE_WIDTH - (TITLE_OFFSET[0] * 2),
    IMAGE_HEIGHT - 224 - TITLE_OFFSET[1],
)

BYLINE_OFFSET = (TITLE_OFFSET[0] * 2, TITLE_OFFSET[1] + TITLE_BOUND[1])
BYLINE_BOUND = (IMAGE_WIDTH - (BYLINE_OFFSET[0] * 2), 192)

WHITE = (255, 255, 255)


def draw_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_name: str,
    colour: Tuple[int, int, int],
    bounds: Tuple[int, int],
    offsets: Tuple[int, int],
    max_font_size: int,
    line_height: float = 1,
) -> None:
    font_size = max_font_size
    lines = text.split("\n")
    while not lines[-1]:
        lines.pop(-1)
    while True:
        font = ImageFont.truetype(font_name, font_size)
        left, _, right, _ = draw.multiline_textbbox((0, 0), text)
        text_width = right - left
        _, top, _, bottom = draw.multiline_textbbox((0, 0), "\N{FULL BLOCK}", font=font)
        _line_height = bottom - top
        text_height = int(_line_height * line_height * len(lines))

        if text_width < bounds[0] and text_height < bounds[1]:
            break
        font_size -= 1

    y_pos = offsets[1] + (bounds[1] - text_height) // 2
    for line in lines:
        line_width = draw.textlength(line, font=font)
        x_pos = offsets[0] + (bounds[0] - line_width) // 2
        draw.text((x_pos, y_pos), line, colour, font=font)
        y_pos += int(_line_height * line_height) + 100


@ToAsync()
def imagine(text: str) -> discord.File:
    image = Image.open(IMAGE)
    draw = ImageDraw.Draw(image)
    title, _, byline = text.upper().partition("\n")
    title = f"IMAGINE\n{title.strip()}"
    byline = byline.strip()
    draw_text(draw, title, TITLE_FONT, WHITE, TITLE_BOUND, TITLE_OFFSET, 200, 0.95)
    if byline:
        draw_text(draw, byline, TITLE_FONT, WHITE, BYLINE_BOUND, BYLINE_OFFSET, 200)
    out_fp = io.BytesIO()
    image.save(out_fp, "PNG")
    out_fp.seek(0)
    return discord.File(out_fp, "imagine.png")
