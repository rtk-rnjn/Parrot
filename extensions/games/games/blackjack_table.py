from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from io import BytesIO
from math import ceil
from typing import TYPE_CHECKING, Final, Literal

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from extensions.supercell.api import IMAGE_DIRECTORY, ImageStore
from extensions.supercell.render import font

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from core import Bot

__all__ = ("BACK", "HandView", "Kind", "card_store", "card_url", "render_table")

type Kind = Literal["dark", "good", "bad", "gold", "neutral", "info", "chip"]
type RGBA = tuple[int, int, int, int]

BACK: Final = "back"
CARD_URL: Final = "https://deckofcardsapi.com/static/img/{}.png"
CARD_RATIO: Final = 226 / 314

TABLE_WIDTH: Final = 840
LABEL_H: Final = 48

FELT_CENTRE: Final = (30, 112, 70)
FELT_EDGE: Final = (7, 38, 25)
GOLD: Final[RGBA] = (240, 196, 72, 255)

KINDS: Final[dict[str, RGBA]] = {
    "dark": (0, 0, 0, 140),
    "good": (62, 170, 86, 255),
    "bad": (214, 70, 62, 255),
    "gold": GOLD,
    "neutral": (96, 108, 124, 255),
    "info": (140, 90, 210, 255),
    "chip": (190, 40, 50, 255),
}
SUITS: Final = {
    "S": "\N{BLACK SPADE SUIT}",
    "H": "\N{BLACK HEART SUIT}",
    "D": "\N{BLACK DIAMOND SUIT}",
    "C": "\N{BLACK CLUB SUIT}",
}


@dataclass(frozen=True, slots=True)
class HandView:
    cards: tuple[str, ...]
    label: str
    total: str
    total_kind: Kind = "dark"
    bet: int | None = None
    badge: str | None = None
    badge_kind: Kind = "neutral"
    active: bool = False
    dim: bool = False
    hidden_index: int | None = None


@dataclass(slots=True)
class _Placed:
    code: str
    x: int
    y: int
    w: int
    h: int
    dim: bool


def card_url(code: str) -> str:
    return CARD_URL.format(code)


def card_store(bot: Bot) -> ImageStore:
    """One shared card image cache per bot."""
    store = getattr(bot, "_card_image_store", None)
    if store is None:
        store = ImageStore(bot, capacity=64, directory=IMAGE_DIRECTORY.parent / "cards")
        bot._card_image_store = store  # pyright: ignore[reportAttributeAccessIssue]
    return store


@cache
def _symbol_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("assets/DejaVuSansMNerdFontMono-Regular.ttf", size)
    except OSError:
        return font(size)


def _felt(size: tuple[int, int]) -> Image.Image:
    mask = Image.radial_gradient("L").resize(size)
    centre = Image.new("RGBA", size, (*FELT_CENTRE, 255))
    edge = Image.new("RGBA", size, (*FELT_EDGE, 255))
    return Image.composite(edge, centre, mask)


def _fallback(code: str, w: int, h: int) -> Image.Image:
    sprite = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)
    radius = max(6, w // 10)

    if code == BACK:
        draw.rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=(40, 70, 160, 255), outline=(255, 255, 255, 255), width=3)
        draw.rounded_rectangle((10, 10, w - 11, h - 11), radius // 2, outline=(255, 255, 255, 120), width=2)
        return sprite

    rank, suit = code[0], code[1]
    colour = (200, 30, 40, 255) if suit in "HD" else (25, 25, 30, 255)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=(250, 250, 250, 255), outline=(190, 190, 190, 255), width=2)
    draw.text((10, 6), "10" if rank == "0" else rank, font=_symbol_font(h // 5), fill=colour)
    draw.text((w // 2, h // 2 + 8), SUITS.get(suit, "?"), font=_symbol_font(h // 2), fill=colour, anchor="mm")
    return sprite


def _sprite(code: str, data: bytes | None, w: int, h: int) -> Image.Image:
    if data:
        try:
            return Image.open(BytesIO(data)).convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
        except OSError:
            pass
    return _fallback(code, w, h)


def _step(count: int, card_w: int, room: int) -> int:
    """Horizontal offset between overlapping cards, shrunk so the hand fits in ``room``."""
    if count <= 1:
        return 0
    return max(16, min(round(card_w * 0.55), (room - card_w) // (count - 1)))


def _pills(draw: ImageDraw.ImageDraw, view: HandView, size: int) -> list[tuple[str, Kind, int]]:
    face = font(size)
    entries: list[tuple[str, Kind]] = [(view.label, "dark"), (view.total, view.total_kind)]
    if view.bet is not None:
        entries.append((f"${view.bet}", "chip"))
    if view.badge:
        entries.append((view.badge, view.badge_kind))
    return [(text, kind, int(draw.textlength(text, font=face)) + 26) for text, kind in entries]


def _png(img: Image.Image) -> bytes:
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


def render_table(dealer: HandView, hands: Sequence[HandView], images: Mapping[str, bytes | None]) -> bytes:  # noqa: PLR0915
    columns = 1 if len(hands) == 1 else 2
    card_h = 160 if columns == 1 else 118
    dealer_h = 150 if columns == 1 else 128
    card_w, dealer_w = round(card_h * CARD_RATIO), round(dealer_h * CARD_RATIO)
    pill_size = 20 if columns == 1 else 17

    rows = ceil(len(hands) / columns)
    dealer_top = 26
    divider_y = dealer_top + LABEL_H + dealer_h + 24
    players_top = divider_y + 30
    row_h = LABEL_H + card_h + 30
    size = (TABLE_WIDTH, players_top + rows * row_h + 4)

    img = _felt(size)
    draw = ImageDraw.Draw(img, "RGBA")

    draw.rounded_rectangle((12, 12, size[0] - 13, size[1] - 13), 26, outline=(214, 170, 70, 130), width=3)
    draw.rounded_rectangle((22, 22, size[0] - 23, size[1] - 23), 20, outline=(255, 255, 255, 28), width=1)

    caption = "BLACKJACK PAYS 3 TO 2  \N{MIDDLE DOT}  DEALER STANDS ON 17"
    caption_font = font(15)
    half = draw.textlength(caption, font=caption_font) / 2
    centre = size[0] / 2
    draw.text((centre, divider_y), caption, font=caption_font, fill=(240, 230, 190, 120), anchor="mm")
    draw.line((60, divider_y, centre - half - 16, divider_y), fill=(240, 230, 190, 50), width=1)
    draw.line((centre + half + 16, divider_y, size[0] - 60, divider_y), fill=(240, 230, 190, 50), width=1)

    plans: list[tuple[HandView, int, int, int, int, int, int]] = [(dealer, 0, size[0], dealer_top, dealer_w, dealer_h, 20)]
    for index, view in enumerate(hands):
        row, column = divmod(index, columns)
        cell_w = (size[0] - 56) // columns
        plans.append((view, 28 + column * cell_w, cell_w, players_top + row * row_h - LABEL_H // 2 + 8, card_w, card_h, pill_size))

    placed: list[_Placed] = []
    pill_rows: list[tuple[list[tuple[str, Kind, int]], int, int, int]] = []

    for view, cell_x, cell_w, top, width, height, psize in plans:
        count = len(view.cards)
        step = _step(count, width, cell_w - 40)
        span = width + step * (count - 1)
        card_x = cell_x + (cell_w - span) // 2
        card_y = top + LABEL_H

        pills = _pills(draw, view, psize)
        pills_w = sum(w for _, _, w in pills) + 8 * (len(pills) - 1)
        pills_x = cell_x + (cell_w - pills_w) // 2
        pill_rows.append((pills, pills_x, top + 4, psize))

        if view.active:
            box = (min(card_x, pills_x) - 16, top - 4, max(card_x + span, pills_x + pills_w) + 16, card_y + height + 12)
            draw.rounded_rectangle(box, 20, fill=(255, 255, 255, 18), outline=GOLD, width=3)

        placed.extend(
            _Placed(BACK if i == view.hidden_index else code, card_x + i * step, card_y, width, height, view.dim) for i, code in enumerate(view.cards)
        )

    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    for card in placed:
        shadow_draw.rounded_rectangle((card.x + 3, card.y + 6, card.x + card.w + 3, card.y + card.h + 6), card.w // 10, fill=(0, 0, 0, 150))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))

    for card in placed:
        img.alpha_composite(_sprite(card.code, images.get(card.code), card.w, card.h), (card.x, card.y))
        if card.dim:
            draw.rounded_rectangle((card.x, card.y, card.x + card.w - 1, card.y + card.h - 1), card.w // 10, fill=(0, 0, 0, 120))

    for pills, pill_x, pill_y, psize in pill_rows:
        face = font(psize)
        height = psize + 16
        x, y = pill_x, pill_y
        for text, kind, width in pills:
            draw.rounded_rectangle((x, y, x + width, y + height), height // 2, fill=KINDS[kind])
            ink = (45, 28, 0, 255) if kind == "gold" else (255, 255, 255, 255)
            draw.text((x + width // 2, y + height // 2), text, font=face, fill=ink, anchor="mm")
            x += width + 8

    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), 32, fill=255)
    img.putalpha(mask)
    return _png(img)
