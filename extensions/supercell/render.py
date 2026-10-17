from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

__all__ = ("BRAWL_STARS", "CLASH_OF_CLANS", "CLASH_ROYALE", "Bar", "DeckSlot", "Theme", "bars_card", "deck_card", "profile_card")

type Colour = tuple[int, int, int, int]
type Box = tuple[int, int, int, int]
type Size = tuple[int, int]

FONT_DIR = Path("assets")
FONT_FILES = ("LilitaOne-Regular.ttf", "DejaVuSansMNerdFontMono-Regular.ttf")

W = 920
PAD = 30
GAP = 14
TILE_H = 88
STRIP_H = 140

WHITE: Colour = (255, 255, 255, 255)
MUTED: Colour = (190, 200, 225, 255)
OUTLINE: Colour = (15, 20, 40, 255)
GREEN: Colour = (110, 230, 120, 255)
PANEL: Colour = (0, 0, 0, 110)


@dataclass(frozen=True, slots=True)
class Theme:
    top: tuple[int, int, int]
    bottom: tuple[int, int, int]
    accent: Colour


CLASH_ROYALE = Theme((38, 92, 190), (14, 28, 70), (255, 205, 70, 255))
CLASH_OF_CLANS = Theme((62, 122, 52), (16, 38, 24), (255, 190, 60, 255))
BRAWL_STARS = Theme((112, 48, 170), (30, 12, 58), (255, 205, 30, 255))


@dataclass(frozen=True, slots=True)
class DeckSlot:
    image: bytes | None
    label: str
    elixir: int | None = None


@dataclass(frozen=True, slots=True)
class Bar:
    label: str
    value: int
    maximum: int


@cache
def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in FONT_FILES:
        for source in (FONT_DIR / name, Path(name)):
            try:
                return ImageFont.truetype(str(source), size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _gradient(size: Size, theme: Theme) -> Image.Image:
    mask = Image.linear_gradient("L").resize(size)
    top = Image.new("RGBA", size, (*theme.top, 255))
    bottom = Image.new("RGBA", size, (*theme.bottom, 255))
    return Image.composite(bottom, top, mask)


def _load(data: bytes | None, size: Size) -> Image.Image | None:
    if not data:
        return None
    try:
        sprite = Image.open(BytesIO(data)).convert("RGBA")
    except OSError:
        return None
    return ImageOps.contain(sprite, size)


def _panel(img: Image.Image, box: Box, fill: Colour = PANEL, radius: int = 20) -> None:
    x0, y0, x1, y1 = box
    tile = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius, fill=fill)
    img.alpha_composite(tile, (x0, y0))


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    size: int,
    *,
    fill: Colour = WHITE,
    anchor: str = "la",
) -> None:
    draw.text(xy, value, font=font(size), fill=fill, anchor=anchor, stroke_width=max(1, size // 14), stroke_fill=OUTLINE)


def _clip(draw: ImageDraw.ImageDraw, value: str, size: int, width: int) -> str:
    face = font(size)
    if draw.textlength(value, font=face) <= width:
        return value
    while value and draw.textlength(f"{value}\N{HORIZONTAL ELLIPSIS}", font=face) > width:
        value = value[:-1]
    return f"{value}\N{HORIZONTAL ELLIPSIS}"


def _png(img: Image.Image) -> bytes:
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


def profile_card(
    theme: Theme,
    *,
    name: str,
    tag: str,
    level: str,
    line: str,
    portrait: bytes | None,
    stats: Sequence[tuple[str, str]],
    strip: Sequence[bytes | None] = (),
    strip_size: Size = (84, 102),
    footer: str,
) -> bytes:
    """Header with portrait, a four-column stat grid and an optional row of icons."""
    columns = 4
    rows = -(-len(stats) // columns)
    tile_w = (W - 2 * PAD - (columns - 1) * GAP) // columns
    grid_top = 215
    grid_bottom = grid_top + rows * TILE_H + (rows - 1) * GAP
    strip_top = grid_bottom + 20
    bottom = strip_top + STRIP_H if strip else grid_bottom
    height = bottom + 60

    img = _gradient((W, height), theme)
    draw = ImageDraw.Draw(img, "RGBA")

    _panel(img, (PAD, PAD, W - PAD, 185))
    text_x = PAD + 24
    if art := _load(portrait, (130, 130)):
        img.alpha_composite(art, (PAD + 16 + (130 - art.width) // 2, PAD + 12 + (130 - art.height) // 2))
        text_x = PAD + 170

    pill_font = font(26)
    pill_w = int(draw.textlength(level, font=pill_font)) + 36
    pill = (W - PAD - 20 - pill_w, PAD + 14, W - PAD - 20, PAD + 58)
    draw.rounded_rectangle(pill, 22, fill=theme.accent)
    draw.text(((pill[0] + pill[2]) // 2, (pill[1] + pill[3]) // 2), level, font=pill_font, fill=(45, 28, 0, 255), anchor="mm")

    _text(draw, (text_x, PAD + 8), _clip(draw, name, 44, pill[0] - text_x - 16), 44)
    draw.text((text_x, PAD + 68), tag, font=font(24), fill=MUTED)
    draw.text((text_x, PAD + 104), _clip(draw, line, 24, W - PAD - 24 - text_x), font=font(24), fill=WHITE)

    for index, (label, value) in enumerate(stats):
        row, column = divmod(index, columns)
        x = PAD + column * (tile_w + GAP)
        y = grid_top + row * (TILE_H + GAP)
        _panel(img, (x, y, x + tile_w, y + TILE_H))
        draw.text((x + tile_w // 2, y + 14), label.upper(), font=font(16), fill=MUTED, anchor="ma")
        _text(draw, (x + tile_w // 2, y + 40), _clip(draw, value, 32, tile_w - 20), 32, anchor="ma")

    if strip:
        _panel(img, (PAD, strip_top, W - PAD, strip_top + STRIP_H))
        spacing = 14
        total = len(strip) * strip_size[0] + (len(strip) - 1) * spacing
        x = (W - total) // 2
        for data in strip:
            if sprite := _load(data, strip_size):
                img.alpha_composite(
                    sprite,
                    (x + (strip_size[0] - sprite.width) // 2, strip_top + (STRIP_H - sprite.height) // 2),
                )
            x += strip_size[0] + spacing

    draw.text((W - PAD, height - 30), footer, font=font(15), fill=MUTED, anchor="rm")
    return _png(img)


def deck_card(theme: Theme, *, title: str, subtitle: str, slots: Sequence[DeckSlot], footer: str) -> bytes:
    columns, cell_w, cell_h, top = 4, 190, 255, 120
    rows = -(-len(slots) // columns)
    width = 2 * PAD + columns * cell_w + (columns - 1) * GAP
    height = top + rows * cell_h + (rows - 1) * GAP + 60

    img = _gradient((width, height), theme)
    draw = ImageDraw.Draw(img, "RGBA")
    _text(draw, (PAD, 24), _clip(draw, title, 44, width - 2 * PAD), 44)
    draw.text((PAD, 80), subtitle, font=font(22), fill=MUTED)

    for index, slot in enumerate(slots):
        row, column = divmod(index, columns)
        x = PAD + column * (cell_w + GAP)
        y = top + row * (cell_h + GAP)
        _panel(img, (x, y, x + cell_w, y + cell_h))
        if sprite := _load(slot.image, (cell_w - 30, 185)):
            img.alpha_composite(sprite, (x + (cell_w - sprite.width) // 2, y + 16 + (185 - sprite.height) // 2))
        if slot.elixir is not None:
            draw.ellipse((x + 8, y + 8, x + 52, y + 52), fill=(196, 64, 224, 255), outline=WHITE, width=3)
            _text(draw, (x + 30, y + 30), str(slot.elixir), 26, anchor="mm")
        _text(draw, (x + cell_w // 2, y + cell_h - 28), slot.label, 26, anchor="mm")

    draw.text((width - PAD, height - 30), footer, font=font(15), fill=MUTED, anchor="rm")
    return _png(img)


def bars_card(theme: Theme, *, title: str, subtitle: str, bars: Sequence[Bar], footer: str) -> bytes:
    """Two columns of labelled progress bars; maxed entries turn green."""
    row_h, top = 62, 120
    col_w = (W - 2 * PAD - GAP) // 2
    per_column = max(1, -(-len(bars) // 2))
    height = top + per_column * row_h + 60

    img = _gradient((W, height), theme)
    draw = ImageDraw.Draw(img, "RGBA")
    _text(draw, (PAD, 24), _clip(draw, title, 44, W - 2 * PAD), 44)
    draw.text((PAD, 80), subtitle, font=font(22), fill=MUTED)

    for index, bar in enumerate(bars):
        column, row = divmod(index, per_column)
        x = PAD + column * (col_w + GAP)
        y = top + row * row_h
        ratio = min(1.0, bar.value / bar.maximum) if bar.maximum else 0.0
        colour = GREEN if bar.maximum and bar.value >= bar.maximum else theme.accent

        draw.text((x, y), _clip(draw, bar.label, 22, col_w - 110), font=font(22), fill=WHITE)
        draw.text((x + col_w, y), f"{bar.value}/{bar.maximum}", font=font(22), fill=MUTED, anchor="ra")
        draw.rounded_rectangle((x, y + 32, x + col_w, y + 46), 7, fill=(0, 0, 0, 140))
        if ratio > 0:
            draw.rounded_rectangle((x, y + 32, x + max(14, int(col_w * ratio)), y + 46), 7, fill=colour)

    draw.text((W - PAD, height - 30), footer, font=font(15), fill=MUTED, anchor="rm")
    return _png(img)
