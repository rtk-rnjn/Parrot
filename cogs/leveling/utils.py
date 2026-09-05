from __future__ import annotations

import asyncio
from io import BytesIO

import aiohttp
import discord
from jishaku.functools import executor_function
from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = (934, 282)
AVATAR_SIZE = (170, 170)
AVATAR_POSITION = (50, 50)

PROGRESS_BAR_POSITION = (260, 180)
PROGRESS_BAR_WIDTH = 575
PROGRESS_BAR_HEIGHT = 40

PROGRESS_BAR_BACKGROUND = "#484B4E"
TEXT_COLOR = "#FFFFFF"

FONT_PATH = r"assets/Montserrat-Regular.ttf"


async def _fetch_avatar(
    session: aiohttp.ClientSession,
    member: discord.Member | discord.User,
) -> Image.Image:
    async with session.get(member.display_avatar.url) as response:
        response.raise_for_status()
        avatar_data = await response.read()

    return Image.open(BytesIO(avatar_data)).convert("RGBA")


@executor_function
def _create_circular_avatar(avatar: Image.Image) -> Image.Image:
    avatar = avatar.resize(AVATAR_SIZE)

    mask = Image.new("L", avatar.size, 0)
    mask_draw = ImageDraw.Draw(mask)

    mask_draw.ellipse(
        (0, 0, *avatar.size),
        fill=255,
    )

    avatar.putalpha(mask)

    return avatar


@executor_function
def _create_card_background(background_color: str) -> Image.Image:
    return Image.new(
        "RGB",
        CARD_SIZE,
        color=background_color,
    )


@executor_function
def _draw_progress_bar(
    draw: ImageDraw.ImageDraw,
    progress: float,
    progress_color: str,
) -> None:
    bar_x, bar_y = PROGRESS_BAR_POSITION
    bar_width = PROGRESS_BAR_WIDTH
    bar_height = PROGRESS_BAR_HEIGHT

    _draw_rounded_bar(
        draw=draw,
        x=bar_x,
        y=bar_y,
        width=bar_width,
        height=bar_height,
        color=PROGRESS_BAR_BACKGROUND,
    )

    progress_width = bar_width * progress

    if progress_width <= 0:
        return

    _draw_rounded_bar(
        draw=draw,
        x=bar_x,
        y=bar_y,
        width=progress_width,
        height=bar_height,
        color=progress_color,
    )


@executor_function
def _draw_rounded_bar(  # noqa: PLR0913
    draw: ImageDraw.ImageDraw,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
) -> None:
    radius = height / 2

    draw.ellipse(
        (x, y, x + height, y + height),
        fill=color,
    )
    draw.ellipse(
        (x + width - height, y, x + width, y + height),
        fill=color,
    )
    draw.rectangle(
        (
            x + radius,
            y,
            x + width - radius,
            y + height,
        ),
        fill=color,
    )


def _load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    return (
        ImageFont.truetype(FONT_PATH, size=40),
        ImageFont.truetype(FONT_PATH, size=25),
    )


@executor_function
def _draw_card_text(  # noqa: PLR0913
    draw: ImageDraw.ImageDraw,
    *,
    member_name: str,
    level: int,
    rank: int,
    current_level_xp: int,
    xp_required_for_next_level: int,
    progress_color: str,
) -> None:
    title_font, subtitle_font = _load_fonts()

    draw.text(
        (260, 100),
        member_name,
        fill=TEXT_COLOR,
        font=title_font,
    )

    draw.text(
        (740, 130),
        f"{current_level_xp}/{xp_required_for_next_level} XP",
        fill=TEXT_COLOR,
        font=subtitle_font,
    )

    draw.text(
        (650, 50),
        f"LEVEL {level}",
        fill=progress_color,
        font=title_font,
    )

    draw.text(
        (260, 50),
        f"RANK #{rank}",
        fill=TEXT_COLOR,
        font=subtitle_font,
    )


@executor_function
def _image_to_discord_file(image: Image.Image) -> discord.File:
    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    return discord.File(
        image_buffer,
        filename="image.png",
    )


async def rank_card(  # noqa: PLR0913
    level: int,
    rank: int,
    member: discord.Member | discord.User,
    *,
    session: aiohttp.ClientSession,
    current_level_xp: int,
    custom_background: str = "#2C2F33",
    xp_color: str = "#00FF00",
    xp_required_for_next_level: int,
) -> discord.File:
    card_image = await _create_card_background(custom_background)

    avatar = await _fetch_avatar(session, member)
    circular_avatar = await _create_circular_avatar(avatar)

    await asyncio.to_thread(
        card_image.paste,
        circular_avatar,
        AVATAR_POSITION,
        circular_avatar,
    )

    draw = ImageDraw.Draw(card_image)

    progress = current_level_xp / xp_required_for_next_level if xp_required_for_next_level > 0 else 0

    await _draw_progress_bar(
        draw,
        progress,
        xp_color,
    )

    await _draw_card_text(
        draw,
        member_name=member.name,
        level=level,
        rank=rank,
        current_level_xp=current_level_xp,
        xp_required_for_next_level=xp_required_for_next_level,
        progress_color=xp_color,
    )

    return await _image_to_discord_file(card_image)
