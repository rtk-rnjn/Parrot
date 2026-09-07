from __future__ import annotations

from io import BytesIO
from pathlib import Path

import discord
from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = (1000, 420)
ASSETS_DIR = Path("assets")
BACKGROUND = (20, 25, 45)
ACCENT = (255, 188, 92)
TEXT = (255, 255, 255)
MUTED = (184, 194, 220)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(ASSETS_DIR / name, size)


def _fit_name(draw: ImageDraw.ImageDraw, name: str, font: ImageFont.FreeTypeFont, maximum_width: int) -> str:
    if draw.textbbox((0, 0), name, font=font)[2] <= maximum_width:
        return name

    shortened = name
    while shortened and draw.textbbox((0, 0), f"{shortened}...", font=font)[2] > maximum_width:
        shortened = shortened[:-1]
    return f"{shortened}..."


def render_birthday_card(name: str, birthday: str, avatar: Image.Image | None = None) -> BytesIO:
    image = Image.new("RGB", CARD_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(image)

    for y in range(CARD_SIZE[1]):
        blend = y / CARD_SIZE[1]
        color = tuple(int(BACKGROUND[index] * (1 - blend) + (42, 52, 86)[index] * blend) for index in range(3))
        draw.line((0, y, CARD_SIZE[0], y), fill=color)

    draw.ellipse((740, -130, 1110, 240), fill=(40, 61, 100))
    draw.ellipse((810, 245, 1080, 520), fill=(37, 48, 78))
    for x, y, radius, color in ((70, 54, 7, ACCENT), (140, 120, 4, (245, 111, 125)), (900, 70, 5, (118, 220, 180)), (930, 190, 3, ACCENT)):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    if avatar is not None:
        avatar = avatar.convert("RGB").resize((190, 190), Image.Resampling.LANCZOS)
        mask = Image.new("L", avatar.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, *avatar.size), fill=255)
        image.paste(avatar, (70, 115), mask)
        draw.ellipse((66, 111, 264, 309), outline=ACCENT, width=5)
    else:
        draw.ellipse((70, 115, 260, 305), fill=(55, 68, 104), outline=ACCENT, width=5)
        draw.text((127, 158), "?", font=_font("HelveticaNeuBold.ttf", 92), fill=ACCENT)

    title_font = _font("HelveticaNeuBold.ttf", 54)
    detail_font = _font("Montserrat-Regular.ttf", 27)
    name = _fit_name(draw, name, title_font, 630)
    draw.text((315, 115), "HAPPY BIRTHDAY", font=title_font, fill=TEXT)
    draw.text((315, 188), name, font=title_font, fill=ACCENT)
    draw.text((315, 270), f"Celebrating {birthday}", font=detail_font, fill=MUTED)
    draw.text((315, 322), "Wishing you a brilliant day!", font=detail_font, fill=TEXT)

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    output.seek(0)
    return output


def birthday_card_file(name: str, birthday: str, avatar: Image.Image | None = None) -> discord.File:
    return discord.File(render_birthday_card(name, birthday, avatar), filename="birthday.png")
