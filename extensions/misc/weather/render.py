from __future__ import annotations

import itertools
import math
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .api import Units

type RGB = tuple[int, int, int]
type RGBA = tuple[int, int, int, int]
type Box = tuple[int, int, int, int]

FONT_DIR = Path("assets")


BG_TOP: RGB = (17, 18, 20)
BG_BOTTOM: RGB = (24, 25, 29)
PANEL_RGB: RGB = (30, 31, 34)
TILE_RGB: RGB = (43, 45, 49)
ELEVATED_RGB: RGB = (49, 51, 56)
TRACK_RGB: RGB = (18, 19, 22)

PANEL_BG: RGBA = (*PANEL_RGB, 255)
TILE_BG: RGBA = (*TILE_RGB, 255)
ELEVATED_BG: RGBA = (*ELEVATED_RGB, 255)
TRACK_BG: RGBA = (*TRACK_RGB, 255)
BORDER: RGBA = (58, 60, 66, 255)
DIVIDER: RGBA = (46, 48, 53, 255)

WHITE: RGBA = (242, 243, 245, 255)
SUBTEXT: RGBA = (181, 186, 193, 255)
MUTED: RGBA = (148, 155, 164, 255)
FAINT: RGBA = (109, 113, 120, 255)

BLURPLE: RGB = (88, 101, 242)
DISCORD_BLUE: RGB = (59, 165, 236)
DISCORD_GREEN: RGB = (35, 165, 90)
DISCORD_YELLOW: RGB = (240, 178, 50)
DISCORD_ORANGE: RGB = (242, 126, 53)
DISCORD_RED: RGB = (242, 63, 67)
DISCORD_PURPLE: RGB = (138, 100, 246)

COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")

AQI_COLOURS: dict[int, RGB] = {
    1: DISCORD_GREEN,
    2: (130, 195, 75),
    3: DISCORD_YELLOW,
    4: DISCORD_ORANGE,
    5: DISCORD_RED,
}
AQI_NAMES = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
BREAKPOINTS = {
    "so2": (20, 80, 250, 350),
    "no2": (40, 70, 150, 200),
    "pm10": (20, 50, 100, 200),
    "o3": (60, 100, 140, 180),
    "pm2_5": (10, 25, 50, 75),
    "co": (4400, 9400, 12400, 15400),
}
POLLUTANTS = (
    ("pm2_5", "PM2.5"),
    ("pm10", "PM10"),
    ("o3", "O3"),
    ("no2", "NO2"),
    ("so2", "SO2"),
    ("co", "CO"),
    ("no", "NO"),
    ("nh3", "NH3"),
)
TEMP_STOPS: tuple[tuple[float, RGB], ...] = (
    (-20, (138, 100, 246)),
    (0, (88, 101, 242)),
    (10, (59, 165, 236)),
    (20, (35, 165, 90)),
    (28, (240, 178, 50)),
    (36, (242, 126, 53)),
    (45, (242, 63, 67)),
)


@dataclass(frozen=True, slots=True)
class Theme:
    top: RGB
    bottom: RGB
    accent: RGB


def _blend(base: RGB, tint: RGB, weight: float) -> RGBA:
    """Blend two RGB colours into an opaque RGBA tuple so PIL draws never punch alpha holes."""
    return (
        int(base[0] * (1 - weight) + tint[0] * weight),
        int(base[1] * (1 - weight) + tint[1] * weight),
        int(base[2] * (1 - weight) + tint[2] * weight),
        255,
    )


@cache
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("Inter-Bold.ttf", "ggsans-Bold.ttf", "DejaVuSans-Bold.ttf") if bold else ("Inter-Regular.ttf", "ggsans-Regular.ttf", "DejaVuSans.ttf")
    for name in names:
        for source in (FONT_DIR / name, Path(name)):
            try:
                return ImageFont.truetype(str(source), size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def theme_for(code: int, night: bool) -> Theme:
    """Return a Discord-dark surface pair and a vibrant weather-matched Discord accent colour."""
    group = code // 100
    if code == 800:
        accent = BLURPLE if night else DISCORD_YELLOW
    elif code > 800:
        accent = (130, 148, 192) if night else DISCORD_BLUE
    elif group == 2:
        accent = DISCORD_PURPLE
    elif group in {3, 5}:
        accent = BLURPLE if night else DISCORD_BLUE
    elif group == 6:
        accent = (165, 215, 255)
    else:
        accent = DISCORD_ORANGE

    top: tuple[int, int, int] = tuple(int(b * 0.90 + a * 0.10) for b, a in zip(BG_TOP, accent, strict=True))  # pyright: ignore[reportAssignmentType]
    return Theme(top=top, bottom=BG_BOTTOM, accent=accent)


def temp_colour(celsius: float) -> RGB:
    if celsius <= TEMP_STOPS[0][0]:
        return TEMP_STOPS[0][1]
    for (t0, c0), (t1, c1) in itertools.pairwise(TEMP_STOPS):
        if celsius <= t1:
            f = (celsius - t0) / (t1 - t0)
            return tuple(int(a + (b - a) * f) for a, b in zip(c0, c1, strict=True))  # pyright: ignore[reportReturnType]
    return TEMP_STOPS[-1][1]


def local(ts: float, offset: int) -> datetime:
    return datetime.fromtimestamp(ts + offset, UTC)


def clock(ts: float, offset: int) -> str:
    d = local(ts, offset)
    return f"{d.hour % 12 or 12}:{d.minute:02d} {'AM' if d.hour < 12 else 'PM'}"


def hour_label(ts: float, offset: int) -> str:
    d = local(ts, offset)
    return f"{d.hour % 12 or 12} {'AM' if d.hour < 12 else 'PM'}"


def wind_dir(deg: float | None) -> str:
    return "\N{EM DASH}" if deg is None else COMPASS[round(deg / 22.5) % 16]


def uv_category(uvi: float | None) -> tuple[str, RGB]:
    if uvi is None:
        return "Standard tier", (90, 95, 105)
    for limit, name, colour in (
        (3, "Low", DISCORD_GREEN),
        (6, "Moderate", DISCORD_YELLOW),
        (8, "High", DISCORD_ORANGE),
        (11, "Very high", DISCORD_RED),
    ):
        if uvi < limit:
            return name, colour
    return "Extreme", DISCORD_PURPLE


def moon_name(phase: float) -> str:
    for limit, name in (
        (0.03, "New Moon"),
        (0.22, "Waxing Crescent"),
        (0.28, "First Quarter"),
        (0.47, "Waxing Gibbous"),
        (0.53, "Full Moon"),
        (0.72, "Waning Gibbous"),
        (0.78, "Last Quarter"),
        (0.97, "Waning Crescent"),
    ):
        if phase < limit:
            return name
    return "New Moon"


def aqi_index(component: str, value: float) -> int:
    return 1 + sum(value >= limit for limit in BREAKPOINTS.get(component, ()))


class Layer:
    """Anti-aliased OpenCV drawing surface that composites cleanly (no dark fringes) into PIL."""

    def __init__(self, size: tuple[int, int]) -> None:
        self.size = size
        self.rgb = np.zeros((size[1], size[0], 3), np.uint8)
        self.cov = np.zeros((size[1], size[0]), np.uint8)

    @staticmethod
    def _fixed(points: Sequence[tuple[float, float]]) -> np.ndarray:
        return (np.array(points, np.float32) * 16).astype(np.int32)

    def polyline(self, points: Sequence[tuple[float, float]], colour: RGB, thickness: int) -> None:
        arr = self._fixed(points)
        cv2.polylines(self.rgb, [arr], False, colour, thickness, cv2.LINE_AA, 4)
        cv2.polylines(self.cov, [arr], False, 255, thickness, cv2.LINE_AA, 4)

    def circle(self, centre: tuple[float, float], radius: float, colour: RGB, thickness: int = -1) -> None:
        c, r = (int(centre[0] * 16), int(centre[1] * 16)), int(radius * 16)
        cv2.circle(self.rgb, c, r, colour, thickness, cv2.LINE_AA, 4)
        cv2.circle(self.cov, c, r, 255, thickness, cv2.LINE_AA, 4)

    def arc(self, centre: tuple[float, float], axes: tuple[float, float], start: float, end: float, colour: RGB, thickness: int) -> None:
        c, a = (int(centre[0] * 16), int(centre[1] * 16)), (int(axes[0] * 16), int(axes[1] * 16))
        cv2.ellipse(self.rgb, c, a, 0, start, end, colour, thickness, cv2.LINE_AA, 4)
        cv2.ellipse(self.cov, c, a, 0, start, end, 255, thickness, cv2.LINE_AA, 4)

    def image(self, opacity: float = 1.0, blur: float = 0) -> Image.Image:
        rgb, cov = self.rgb.astype(np.float32), self.cov.astype(np.float32) / 255
        if blur:
            rgb, cov = cv2.GaussianBlur(rgb, (0, 0), blur), cv2.GaussianBlur(cov, (0, 0), blur)
        colour = np.clip(rgb / np.maximum(cov[..., None], 1e-3), 0, 255)
        return Image.fromarray(np.dstack([colour, cov * 255 * opacity]).astype(np.uint8))


def smooth(points: Sequence[tuple[float, float]], samples: int = 14) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for (x0, y0), (x1, y1) in itertools.pairwise(points):
        for i in range(samples):
            t = i / samples
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * (1 - math.cos(math.pi * t)) / 2))
    out.append(points[-1])
    return out


def area_fill(size: tuple[int, int], points: Sequence[tuple[float, float]], bottom: int, colour: RGB, strength: float = 0.28) -> Image.Image:
    w, h = size
    mask = np.zeros((h, w), np.uint8)
    polygon = np.vstack([np.array(points), [[points[-1][0], bottom], [points[0][0], bottom]]]).astype(np.int32)
    cv2.fillPoly(mask, [polygon], 255, cv2.LINE_AA)
    top = min(p[1] for p in points)
    gradient = np.clip((bottom - np.arange(h)) / max(1, bottom - top), 0, 1)[:, None]
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = colour
    rgba[..., 3] = (mask / 255 * gradient * strength * 255).astype(np.uint8)
    return Image.fromarray(rgba)


def background(size: tuple[int, int], theme: Theme, seed: int = 0) -> Image.Image:
    """Create a sleek Discord dark surface with a subtle top-left radial accent glow."""
    del seed
    w, h = size
    t = np.linspace(0, 1, h, retstep=False, dtype=np.float32)[:, None, None]
    canvas = (np.array(theme.top, np.float32) * (1 - t) + np.array(theme.bottom, np.float32) * t) * np.ones((1, w, 1), np.float32)

    yy, xx = np.ogrid[:h, :w]
    radial = np.exp(-(((xx - w * 0.18) / (w * 0.55)) ** 2 + ((yy - h * 0.12) / (h * 0.55)) ** 2))
    canvas += np.array(theme.accent, np.float32) * radial[..., None] * 0.09

    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).convert("RGBA")


def glass(
    img: Image.Image,
    box: Box,
    radius: int = 16,
    tint: RGBA = PANEL_BG,
    *,
    border: RGBA = BORDER,
) -> None:
    """Draw a crisp Discord dark UI card container with a 1px border."""
    if tint[3] < 255:
        x0, y0, x1, y1 = box
        overlay = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay, "RGBA")
        odraw.rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius, fill=tint, outline=border, width=1)
        img.alpha_composite(overlay, (x0, y0))
    else:
        draw = ImageDraw.Draw(img, "RGBA")
        draw.rounded_rectangle(box, radius, fill=tint, outline=border, width=1)


def put(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    value: str,
    size: int,
    *,
    bold: bool = False,
    fill: RGBA = WHITE,
    anchor: str = "la",
    shadow: bool = False,
) -> None:
    face = font(size, bold)
    if shadow:
        draw.text((xy[0], xy[1] + 1), value, font=face, fill=(0, 0, 0, 120), anchor=anchor)
    draw.text(xy, value, font=face, fill=fill, anchor=anchor)


def fit_put(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    value: str,
    size: int,
    max_width: int,
    *,
    min_size: int = 12,
    bold: bool = False,
    fill: RGBA = WHITE,
    anchor: str = "lm",
) -> None:
    """Render text that automatically scales down to fit ``max_width`` before ever truncating."""
    cur = size
    while cur > min_size and draw.textlength(value, font=font(cur, bold)) > max_width:
        cur -= 1
    text = clip_text(draw, value, cur, max_width, bold)
    draw.text(xy, text, font=font(cur, bold), fill=fill, anchor=anchor)


def clip_text(draw: ImageDraw.ImageDraw, value: str, size: int, width: int, bold: bool = False) -> str:
    face = font(size, bold)
    if draw.textlength(value, font=face) <= width:
        return value
    while value and draw.textlength(f"{value}\N{HORIZONTAL ELLIPSIS}", font=face) > width:
        value = value[:-1]
    return f"{value}\N{HORIZONTAL ELLIPSIS}"


def wrap(draw: ImageDraw.ImageDraw, value: str, size: int, width: int) -> list[str]:
    face, lines, line = font(size), [], ""
    for word in value.split():
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=face) <= width:
            line = candidate
        else:
            lines.append(line)
            line = word
    return [*lines, line] if line else lines


def paste_icon(img: Image.Image, data: bytes | None, centre: tuple[int, int], size: int, accent: RGB | None = None) -> None:
    if not data:
        return
    try:
        icon = Image.open(BytesIO(data)).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    except OSError:
        return

    if accent is not None:
        glow = Layer(img.size)
        glow.circle(centre, size * 0.34, accent)
        img.alpha_composite(glow.image(0.18, blur=18))

    shadow = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    shadow.putalpha(icon.getchannel("A").point(lambda a: int(a * 0.45)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, size // 16)))
    x, y = centre[0] - size // 2, centre[1] - size // 2
    img.alpha_composite(shadow, (x, y + 4))
    img.alpha_composite(icon, (x, y))


def compass(img: Image.Image, centre: tuple[int, int], radius: int, deg: float | None, accent: RGB = BLURPLE) -> None:
    layer = Layer(img.size)
    layer.circle(centre, radius, TRACK_RGB, -1)
    layer.circle(centre, radius, (72, 76, 84), 2)
    img.alpha_composite(layer.image())

    draw = ImageDraw.Draw(img, "RGBA")
    for label, angle in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
        a = math.radians(angle)
        col = (*accent, 255) if label == "N" else MUTED
        draw.text(
            (centre[0] + (radius - 7) * math.sin(a), centre[1] - (radius - 7) * math.cos(a)),
            label,
            font=font(8, True),
            fill=col,
            anchor="mm",
        )
    if deg is None:
        layer_dot = Layer(img.size)
        layer_dot.circle(centre, 3, (148, 155, 164))
        img.alpha_composite(layer_dot.image())
        return

    a = math.radians((deg + 180) % 360)
    ux, uy = math.sin(a), -math.cos(a)
    tip = (centre[0] + ux * (radius - 11), centre[1] + uy * (radius - 11))
    base = (tip[0] - ux * 8, tip[1] - uy * 8)
    arrow = Layer(img.size)
    arrow.polyline([(centre[0] - ux * (radius * 0.35), centre[1] - uy * (radius * 0.35)), base], accent, 2)
    arrow.polyline([tip, (base[0] - uy * 4, base[1] + ux * 4), (base[0] + uy * 4, base[1] - ux * 4), tip], accent, 2)
    arrow.circle(centre, 2.5, (242, 243, 245))
    img.alpha_composite(arrow.image())


def sun_arc(img: Image.Image, box: Box, sunrise: int | None, sunset: int | None, now: int, accent: RGB) -> None:
    if not sunrise or not sunset:
        return
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    pad = 14
    surf_size = (w + pad * 2, h + pad * 2)
    track, progress, glow = Layer(surf_size), Layer(surf_size), Layer(surf_size)
    centre = (w / 2 + pad, h + pad - 4)
    axes = (w / 2 - 14, h - 10)

    track.arc(centre, axes, 180, 360, (68, 72, 80), 2)
    track.polyline([(pad + 4, centre[1]), (w + pad - 4, centre[1])], (56, 58, 64), 1)

    frac = (now - sunrise) / max(1, sunset - sunrise)
    up = 0 <= frac <= 1
    clamped = min(1.0, max(0.0, frac))

    if up:
        progress.arc(centre, axes, 180, 180 + 180 * clamped, accent, 3)

    angle = math.pi + math.pi * clamped
    pos = (centre[0] + axes[0] * math.cos(angle), centre[1] + axes[1] * math.sin(angle))
    dot_col = accent if up else (114, 118, 125)
    glow.circle(pos, 8, dot_col)

    img.alpha_composite(track.image(), (x0 - pad, y0 - pad))
    img.alpha_composite(progress.image(), (x0 - pad, y0 - pad))
    if up:
        img.alpha_composite(glow.image(0.75, blur=7), (x0 - pad, y0 - pad))
    dot_layer = Layer(surf_size)
    dot_layer.circle(pos, 5, (242, 243, 245) if up else dot_col)
    img.alpha_composite(dot_layer.image(), (x0 - pad, y0 - pad))


def moon(img: Image.Image, centre: tuple[int, int], radius: int, phase: float) -> None:
    scale = 4
    size = radius * 2 * scale
    yy, xx = np.mgrid[:size, :size].astype(np.float32)
    x, y = (xx - size / 2) / scale, (yy - size / 2) / scale
    half_width = np.sqrt(np.maximum(radius**2 - y**2, 0))
    t = math.cos(2 * math.pi * phase)
    lit = (x >= t * half_width) & (x <= half_width) if phase < 0.5 else (x >= -half_width) & (x <= -t * half_width)
    disc = (x**2 + y**2) <= radius**2

    rgba = np.zeros((size, size, 4), np.uint8)
    rgba[disc] = (54, 57, 65, 255)
    rgba[disc & lit] = (240, 232, 200, 255)
    sprite = Image.fromarray(rgba).resize((radius * 2, radius * 2), Image.Resampling.LANCZOS)
    img.alpha_composite(sprite, (centre[0] - radius, centre[1] - radius))


def gradient_bar(img: Image.Image, box: Box, low: float, high: float, week_low: float, week_high: float, units: Units) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    ImageDraw.Draw(img, "RGBA").rounded_rectangle(box, h // 2, fill=TRACK_BG)
    span = max(week_high - week_low, 1e-6)
    left = max(0, int((low - week_low) / span * w))
    right = max(left + h, min(w - 1, int((high - week_low) / span * w)))
    xs = np.linspace(week_low, week_high, w)
    colours = np.array([temp_colour(units.to_celsius(float(v))) for v in xs], np.uint8)
    bar = np.repeat(colours[None, :, :], h, axis=0)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((left, 0, right, h - 1), h // 2, fill=255)
    img.paste(Image.fromarray(bar), (x0, y0), mask)


def _pill_bar(
    draw: ImageDraw.ImageDraw,
    box: Box,
    fraction: float,
    colour: RGB,
) -> None:
    x0, y0, x1, y1 = box
    h = y1 - y0
    w = x1 - x0
    draw.rounded_rectangle(box, h // 2, fill=TRACK_BG)
    fill_w = max(h, int(w * min(1.0, max(0.05, fraction))))
    draw.rounded_rectangle((x0, y0, min(x1, x0 + fill_w), y1), h // 2, fill=(*colour, 255))


def _png(img: Image.Image) -> bytes:
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


def _seed(text: str) -> int:
    return zlib.crc32(text.encode()) % 10_000


def _base(
    size: tuple[int, int],
    place: str,
    weather: dict,
    title: str,
    subtitle: str,
    *,
    badge: str | None = None,
) -> tuple[Image.Image, ImageDraw.ImageDraw, Theme]:
    theme = theme_for(weather["id"], weather["icon"].endswith("n"))
    img = background(size, theme, _seed(place))
    draw = ImageDraw.Draw(img, "RGBA")

    draw.rounded_rectangle((32, 28, 38, 84), 3, fill=(*theme.accent, 255))
    max_title_w = size[0] - (260 if badge else 96)
    fit_put(draw, (52, 42), title, 30, max_title_w, min_size=20, bold=True, fill=WHITE, anchor="lm")
    fit_put(draw, (52, 72), subtitle, 16, max_title_w, min_size=12, fill=MUTED, anchor="lm")

    if badge:
        bw = int(draw.textlength(badge, font=font(14, True))) + 28
        bx1 = size[0] - 32
        bx0 = bx1 - bw
        draw.rounded_rectangle((bx0, 34, bx1, 66), 16, fill=_blend(TILE_RGB, theme.accent, 0.16), outline=(*theme.accent, 255), width=1)
        put(draw, ((bx0 + bx1) / 2, 50), badge, 14, bold=True, fill=(*theme.accent, 255), anchor="mm")

    return img, draw, theme


def current_card(  # noqa: PLR0915
    *,
    place: str,
    current: dict,
    units: Units,
    offset: int,
    icon: bytes | None,
    hi_lo: tuple[float, float] | None,
    pop: float | None,
    aqi: int | None,
    moon_phase: float | None,
    banner: str | None = None,
) -> bytes:
    weather = current["weather"][0]
    when = local(current["dt"], offset)
    subtitle = f"{when:%A, %d %B %Y}  \N{MIDDLE DOT}  {clock(current['dt'], offset)} local"
    img, draw, theme = _base((1000, 620), place, weather, place, subtitle, badge=banner or weather["main"].upper())

    glass(img, (32, 102, 468, 418), 18, PANEL_BG)
    draw.rounded_rectangle((32, 102, 468, 106), 2, fill=(*theme.accent, 255))
    paste_icon(img, icon, (108, 198), 124, accent=theme.accent)

    temp_num = f"{current['temp']:.0f}"
    num_size = 76 if len(temp_num) <= 2 else 64
    num_face = font(num_size, True)
    tx, ty = 184, 144
    draw.text((tx, ty), temp_num, font=num_face, fill=WHITE, anchor="la")
    bbox = draw.textbbox((tx, ty), temp_num, font=num_face, anchor="la")
    unit_label = "K" if units.key == "standard" else units.symbol
    draw.text((bbox[2] + 6, bbox[1] + 6), unit_label, font=font(28, True), fill=(*theme.accent, 255), anchor="la")

    fit_put(draw, (184, 242), weather["description"].title(), 22, 268, min_size=16, bold=True, fill=WHITE, anchor="lm")
    put(draw, (184, 272), f"Feels like {units.temp(current['feels_like'])}", 16, fill=SUBTEXT, anchor="lm")

    glass(img, (48, 314, 452, 400), 14, TILE_BG)
    draw.line((250, 328, 250, 386), fill=DIVIDER, width=1)

    put(draw, (68, 336), "TODAY'S RANGE", 11, bold=True, fill=MUTED, anchor="lm")
    if hi_lo:
        fit_put(
            draw,
            (68, 368),
            f"\N{UPWARDS ARROW} {units.temp(hi_lo[0])}   \N{DOWNWARDS ARROW} {units.temp(hi_lo[1])}",
            19,
            170,
            bold=True,
            fill=WHITE,
            anchor="lm",
        )
    else:
        fit_put(draw, (68, 368), units.temp(current["temp"]), 19, 170, bold=True, fill=WHITE, anchor="lm")

    put(draw, (270, 336), "DEW POINT", 11, bold=True, fill=MUTED, anchor="lm")
    dew_val = units.temp(current["dew_point"]) if current.get("dew_point") is not None else "N/A"
    fit_put(draw, (270, 368), f"{dew_val} ({current['humidity']}% RH)", 18, 170, bold=True, fill=WHITE, anchor="lm")

    glass(img, (32, 432, 468, 584), 18, PANEL_BG)
    sunrise, sunset = current.get("sunrise"), current.get("sunset")
    put(draw, (52, 454), "SUN & DAYLIGHT", 12, bold=True, fill=MUTED, anchor="lm")
    if sunrise and sunset:
        daylight = max(0, sunset - sunrise)
        put(
            draw,
            (448, 454),
            f"{daylight // 3600}h {daylight % 3600 // 60}m daylight",
            13,
            bold=True,
            fill=SUBTEXT,
            anchor="rm",
        )
        sun_arc(img, (68, 474, 432, 540), sunrise, sunset, current["dt"], theme.accent)
        put(draw, (52, 562), f"\N{BLACK UP-POINTING TRIANGLE} {clock(sunrise, offset)}", 14, bold=True, fill=SUBTEXT, anchor="lm")
        put(draw, (448, 562), f"{clock(sunset, offset)} \N{BLACK DOWN-POINTING TRIANGLE}", 14, bold=True, fill=SUBTEXT, anchor="rm")
    else:
        put(draw, (250, 514), "Solar data unavailable", 16, fill=MUTED, anchor="mm")

    rain = (current.get("rain") or {}).get("1h", 0) + (current.get("snow") or {}).get("1h", 0)
    uv_name, uv_colour = uv_category(current.get("uvi"))
    humidity = current["humidity"]
    visibility = current.get("visibility")
    clouds = current.get("clouds", 0)
    wind = current.get("wind_speed", 0)
    pressure = current["pressure"]

    def metric_tile(
        col: int,
        row: int,
        label: str,
        value: str,
        sub: str,
        *,
        dot_colour: RGB | None = None,
        bar_frac: float | None = None,
        bar_colour: RGB | None = None,
        value_right_pad: int = 0,
    ) -> tuple[int, int]:
        x = 484 + col * 164
        y = 102 + row * 164
        w, h = 152, 152
        glass(img, (x, y, x + w, y + h), 16, PANEL_BG)

        put(draw, (x + 16, y + 24), label.upper(), 11, bold=True, fill=MUTED, anchor="lm")
        if dot_colour is not None:
            draw.ellipse((x + w - 22, y + 19, x + w - 12, y + 29), fill=(*dot_colour, 255))

        max_val_w = w - 30 - value_right_pad
        fit_put(draw, (x + 16, y + 64), value, 25, max_val_w, min_size=16, bold=True, fill=WHITE, anchor="lm")

        if bar_frac is not None and bar_colour is not None:
            _pill_bar(draw, (x + 16, y + 96, x + w - 16, y + 103), bar_frac, bar_colour)
            fit_put(draw, (x + 16, y + 125), sub, 13, w - 30, min_size=11, fill=SUBTEXT, anchor="lm")
        else:
            fit_put(draw, (x + 16, y + 120), sub, 13, w - 30, min_size=11, fill=SUBTEXT, anchor="lm")
        return x, y

    wind_sub = f"{wind_dir(current.get('wind_deg'))}" + (
        f" \N{MIDDLE DOT} gust {units.speed(current['wind_gust'])}" if current.get("wind_gust") else " wind"
    )
    wx, wy = metric_tile(0, 0, "Wind", units.speed(wind), wind_sub, value_right_pad=46)
    compass(img, (wx + 122, wy + 58), 21, current.get("wind_deg"), accent=theme.accent)

    metric_tile(
        1,
        0,
        "Humidity",
        f"{humidity}%",
        "Comfortable" if 30 <= humidity <= 65 else ("Dry air" if humidity < 30 else "Humid"),
        bar_frac=humidity / 100,
        bar_colour=DISCORD_BLUE,
    )

    p_label = "Low" if pressure < 1000 else ("Normal" if pressure <= 1022 else "High")
    metric_tile(
        2,
        0,
        "Pressure",
        units.pressure(pressure),
        f"{p_label} pressure",
        dot_colour=DISCORD_GREEN if p_label == "Normal" else DISCORD_YELLOW,
    )

    metres = visibility if visibility is not None else 10_000
    vis_label = "Clear view" if metres >= 10_000 else ("Good" if metres >= 5000 else ("Moderate" if metres >= 2000 else "Low visibility"))
    metric_tile(
        0,
        1,
        "Visibility",
        units.distance(metres),
        vis_label,
        dot_colour=DISCORD_GREEN if metres >= 5000 else DISCORD_YELLOW,
    )

    uvi_val = current.get("uvi")
    metric_tile(
        1,
        1,
        "UV Index",
        f"{uvi_val:.1f}" if uvi_val is not None else "N/A",
        uv_name,
        bar_frac=(uvi_val / 11) if uvi_val is not None else 0.08,
        bar_colour=uv_colour,
    )

    cloud_desc = "Clear sky" if clouds < 20 else ("Scattered" if clouds < 50 else ("Broken" if clouds < 85 else "Overcast"))
    metric_tile(
        2,
        1,
        "Clouds",
        f"{clouds}%",
        cloud_desc,
        bar_frac=max(0.05, clouds / 100),
        bar_colour=(148, 155, 164),
    )

    pop_sub = f"{pop * 100:.0f}% next hour" if pop is not None else "Last 1 hour"
    metric_tile(
        0,
        2,
        "Precip",
        units.precip(rain) if rain else ("0.0 mm" if units.key != "imperial" else "0.00 in"),
        pop_sub,
        bar_frac=pop if pop is not None else (0.4 if rain else 0.05),
        bar_colour=DISCORD_BLUE,
    )

    aqi_col = AQI_COLOURS.get(aqi or 0, (114, 118, 125))
    metric_tile(
        1,
        2,
        "Air Quality",
        f"AQI {aqi}" if aqi else "N/A",
        AQI_NAMES.get(aqi or 0, "Unavailable"),
        dot_colour=aqi_col if aqi else None,
        bar_frac=(aqi / 5) if aqi else 0.08,
        bar_colour=aqi_col,
    )

    if moon_phase is not None:
        illum = round((1 - math.cos(2 * math.pi * moon_phase)) * 50)
        mx, my = metric_tile(2, 2, "Moon", f"{illum}%", moon_name(moon_phase), value_right_pad=46)
        moon(img, (mx + 120, my + 60), 20, moon_phase)
    else:
        metric_tile(2, 2, "Moon", "N/A", "Unavailable")

    put(draw, (500, 603), "OpenWeather \N{MIDDLE DOT} Discord Weather Suite", 12, fill=FAINT, anchor="mm")
    return _png(img)


def hourly_card(*, place: str, points: list[dict], icons: dict[str, bytes | None], units: Units, offset: int, step: int) -> bytes:  # noqa: PLR0915
    size = (1100, 660)
    weather = points[0]["weather"][0]
    hours = max(1, len(points) * step // 3600)
    img, draw, theme = _base(
        size,
        place,
        weather,
        place,
        f"Hourly forecast ({hours}h)  \N{MIDDLE DOT}  {units.label}",
        badge="HOURLY",
    )

    glass(img, (32, 102, 1068, 496), 18, PANEL_BG)
    put(draw, (56, 126), "TEMPERATURE & WIND", 12, bold=True, fill=MUTED, anchor="lm")

    count = len(points)
    x0, x1, top, bottom = 92, 1008, 190, 334
    xs = [x0 + i * (x1 - x0) / max(1, count - 1) for i in range(count)]
    temps = [p["temp"] for p in points]
    low, high = min(temps), max(temps)
    span = max(high - low, 1e-6)
    ys = [bottom - (t - low) / span * (bottom - top) for t in temps]

    for frac in (0.0, 0.5, 1.0):
        gy = int(bottom - frac * (bottom - top))
        draw.line((x0 - 20, gy, x1 + 20, gy), fill=DIVIDER, width=1)

    smoothed = smooth(list(zip(xs, ys, strict=True)))
    img.alpha_composite(area_fill(size, smoothed, bottom + 18, theme.accent, 0.24))

    line = Layer(size)
    for index, (p0, p1) in enumerate(itertools.pairwise(smoothed)):
        position = min(count - 1, index * (count - 1) // max(1, len(smoothed) - 1))
        line.polyline([p0, p1], temp_colour(units.to_celsius(temps[position])), 4)
    img.alpha_composite(line.image(0.55, blur=6))
    img.alpha_composite(line.image())

    num_slots = min(8, count)
    slots: list[tuple[int, float, int]] = []
    for k in range(num_slots):
        frac = k / max(1, num_slots - 1)
        sx = round(x0 + frac * (x1 - x0))
        s_idx = min(len(smoothed) - 1, round(frac * (len(smoothed) - 1)))
        sy = smoothed[s_idx][1]
        p_idx = min(count - 1, round(frac * (count - 1)))
        slots.append((sx, sy, p_idx))

    dots = Layer(size)
    for sx, sy, _ in slots:
        dots.circle((sx, sy), 6, BG_TOP)
        dots.circle((sx, sy), 4, (242, 243, 245))
    img.alpha_composite(dots.image())

    slot_point_indices = {p_idx for _, _, p_idx in slots}
    for sx, sy, p_idx in slots:
        lbl = units.deg(temps[p_idx])
        lw = int(draw.textlength(lbl, font=font(15, True))) + 14
        ly = int(sy) - 22
        draw.rounded_rectangle((sx - lw // 2, ly - 11, sx + lw // 2, ly + 11), 8, fill=TILE_BG, outline=BORDER, width=1)
        put(draw, (sx, ly), lbl, 15, bold=True, fill=WHITE, anchor="mm")

        glass(img, (sx - 48, 366, sx + 48, 480), 12, TILE_BG)
        paste_icon(img, icons.get(points[p_idx]["weather"][0]["icon"]), (sx, 398), 46)
        put(draw, (sx, 438), hour_label(points[p_idx]["dt"], offset), 14, bold=True, fill=WHITE, anchor="mm")
        put(draw, (sx, 462), units.speed(points[p_idx].get("wind_speed", 0)), 12, fill=MUTED, anchor="mm")

    glass(img, (32, 510, 1068, 628), 18, PANEL_BG)
    put(draw, (56, 532), "PRECIPITATION CHANCE", 11, bold=True, fill=MUTED, anchor="lm")

    base_y = 610
    max_bar_h = 54
    bar_w = max(8, int((x1 - x0) / count * 0.58))
    for i, point in enumerate(points):
        pop = float(point.get("pop") or 0.0)
        h = max(4, int(pop * max_bar_h))
        col = (*DISCORD_BLUE, 255) if pop >= 0.15 else (68, 72, 80, 255)
        draw.rounded_rectangle((xs[i] - bar_w / 2, base_y - h, xs[i] + bar_w / 2, base_y), 4, fill=col)
        if pop >= 0.15 and i in slot_point_indices:
            put(draw, (xs[i], base_y - h - 11), f"{pop * 100:.0f}%", 12, bold=True, fill=(*DISCORD_BLUE, 255), anchor="mm")

    put(draw, (550, 645), "OpenWeather \N{MIDDLE DOT} Discord Weather Suite", 12, fill=FAINT, anchor="mm")
    return _png(img)


def daily_card(*, place: str, days: list[dict], icons: dict[str, bytes | None], units: Units, offset: int, today: int) -> bytes:
    row_h = 74
    size = (1000, 128 + row_h * len(days) + 36)
    img, draw, _ = _base(
        size,
        place,
        days[0]["weather"][0],
        place,
        f"{len(days)}-day outlook  \N{MIDDLE DOT}  {units.label}",
        badge=f"{len(days)} DAYS",
    )

    week_low = min(d["temp"]["min"] for d in days)
    week_high = max(d["temp"]["max"] for d in days)
    today_date = local(today, offset).date()

    for i, day in enumerate(days):
        y0 = 104 + i * row_h
        y1 = y0 + row_h - 8
        cy = (y0 + y1) // 2
        row_bg = PANEL_BG if i % 2 == 0 else TILE_BG
        glass(img, (32, y0, 968, y1), 14, row_bg)

        date = local(day["dt"], offset)
        is_today = date.date() == today_date
        name = "Today" if is_today else f"{date:%a, %d %b}"
        if is_today:
            draw.rounded_rectangle((32, y0 + 10, 36, y1 - 10), 2, fill=(*BLURPLE, 255))

        weather = day["weather"][0]
        put(draw, (54, cy), name, 20, bold=True, fill=WHITE, anchor="lm")
        paste_icon(img, icons.get(weather["icon"]), (218, cy), 52)
        fit_put(draw, (258, cy - 10), weather["description"].title(), 17, 230, min_size=13, bold=True, fill=WHITE, anchor="lm")

        precip = (day.get("rain") or 0) + (day.get("snow") or 0)
        sub_meta = (
            f"Precip {units.precip(precip)}"
            if precip
            else (f"UV {day['uvi']:.0f}" if day.get("uvi") is not None else f"Wind {units.speed(day.get('wind_speed', 0))}")
        )
        put(draw, (258, cy + 12), sub_meta, 13, fill=MUTED, anchor="lm")

        pop_pct = round((day.get("pop") or 0) * 100)
        if pop_pct > 0:
            draw.rounded_rectangle(
                (498, cy - 13, 562, cy + 13), 13, fill=_blend(TRACK_RGB, DISCORD_BLUE, 0.16), outline=(*DISCORD_BLUE, 255), width=1
            )
            put(draw, (530, cy), f"{pop_pct}%", 14, bold=True, fill=(*DISCORD_BLUE, 255), anchor="mm")
        else:
            put(draw, (530, cy), "0%", 14, fill=MUTED, anchor="mm")

        put(draw, (628, cy), units.deg(day["temp"]["min"]), 20, bold=True, fill=MUTED, anchor="rm")
        gradient_bar(img, (644, cy - 7, 868, cy + 7), day["temp"]["min"], day["temp"]["max"], week_low, week_high, units)
        put(draw, (884, cy), units.deg(day["temp"]["max"]), 20, bold=True, fill=WHITE, anchor="lm")

    put(draw, (500, size[1] - 16), "OpenWeather \N{MIDDLE DOT} Discord Weather Suite", 12, fill=FAINT, anchor="mm")
    return _png(img)


def day_card(*, place: str, day: dict, icon: bytes | None, units: Units, offset: int) -> bytes:  # noqa: PLR0915
    size = (1000, 780)
    weather = day["weather"][0]
    date = local(day["dt"], offset)
    img, draw, theme = _base(
        size,
        place,
        weather,
        place,
        f"{date:%A, %d %B %Y}  \N{MIDDLE DOT}  Daily Breakdown",
        badge=f"{date:%a %d %b}".upper(),
    )

    glass(img, (32, 102, 968, 228), 18, PANEL_BG)
    paste_icon(img, icon, (104, 165), 104, accent=theme.accent)
    fit_put(draw, (176, 144), weather["description"].title(), 28, 760, min_size=20, bold=True, fill=WHITE, anchor="lm")
    put(
        draw,
        (176, 184),
        f"High {units.temp(day['temp']['max'])}   \N{MIDDLE DOT}   Low {units.temp(day['temp']['min'])}   \N{MIDDLE DOT}   Humidity {day['humidity']:.0f}%",
        18,
        fill=SUBTEXT,
        anchor="lm",
    )

    periods = (("Morning", "morn"), ("Afternoon", "day"), ("Evening", "eve"), ("Night", "night"))
    for i, (label, key) in enumerate(periods):
        x = 32 + i * 238
        w = 224
        glass(img, (x, 244, x + w, 374), 16, PANEL_BG)
        temp = day["temp"][key]
        t_col = temp_colour(units.to_celsius(temp))
        draw.rounded_rectangle((x + 18, 244, x + w - 18, 247), 2, fill=(*t_col, 255))
        put(draw, (x + w / 2, 270), label.upper(), 12, bold=True, fill=MUTED, anchor="mm")
        put(draw, (x + w / 2, 314), units.temp(temp), 36, bold=True, fill=WHITE, anchor="mm")
        put(draw, (x + w / 2, 352), f"Feels {units.temp(day['feels_like'][key])}", 14, fill=SUBTEXT, anchor="mm")

    def detail_tile(col: int, row: int, label: str, value: str, sub: str, *, value_right_pad: int = 0) -> tuple[int, int]:
        x = 32 + col * 238
        y = 390 + row * 140
        w, h = 224, 126
        glass(img, (x, y, x + w, y + h), 16, PANEL_BG)
        put(draw, (x + 18, y + 24), label.upper(), 11, bold=True, fill=MUTED, anchor="lm")
        fit_put(draw, (x + 18, y + 62), value, 24, w - 34 - value_right_pad, min_size=16, bold=True, fill=WHITE, anchor="lm")
        fit_put(draw, (x + 18, y + 100), sub, 13, w - 34, min_size=11, fill=SUBTEXT, anchor="lm")
        return x, y

    precip = (day.get("rain") or 0) + (day.get("snow") or 0)
    detail_tile(0, 0, "Precipitation", f"{(day.get('pop') or 0) * 100:.0f}% chance", units.precip(precip) if precip else "No accumulation")
    wind_sub = f"{wind_dir(day.get('wind_deg'))}" + (f" \N{MIDDLE DOT} gust {units.speed(day['wind_gust'])}" if day.get("wind_gust") else " wind")
    detail_tile(1, 0, "Wind", units.speed(day.get("wind_speed", 0)), wind_sub)
    detail_tile(2, 0, "Humidity", f"{day['humidity']:.0f}%", f"Dew point {units.temp(day['dew_point'])}" if day.get("dew_point") is not None else "")
    detail_tile(3, 0, "Pressure", units.pressure(day["pressure"]), f"Cloud cover {day.get('clouds', 0):.0f}%")

    uv_name, _ = uv_category(day.get("uvi"))
    detail_tile(0, 1, "UV Index", "N/A" if day.get("uvi") is None else f"{day['uvi']:.1f}", uv_name)
    detail_tile(1, 1, "Sunrise", clock(day["sunrise"], offset) if day.get("sunrise") else "N/A", "Local time")
    detail_tile(2, 1, "Sunset", clock(day["sunset"], offset) if day.get("sunset") else "N/A", "Local time")

    if day.get("moon_phase") is not None:
        mp = float(day["moon_phase"])
        illum = round((1 - math.cos(2 * math.pi * mp)) * 50)
        mx, my = detail_tile(3, 1, "Moon Phase", f"{illum}% lit", moon_name(mp), value_right_pad=56)
        moon(img, (mx + 184, my + 56), 22, mp)
    else:
        detail_tile(3, 1, "Moon Phase", "N/A", "Unavailable")

    summary_text = (
        day.get("summary")
        or f"{weather['description'].capitalize()} with temperatures between {units.temp(day['temp']['min'])} and {units.temp(day['temp']['max'])}."
    )
    glass(img, (32, 676, 968, 748), 14, TILE_BG)
    draw.rounded_rectangle((32, 676, 36, 748), 2, fill=(*theme.accent, 255))
    lines = wrap(draw, summary_text, 15, 896)[:2]
    if len(lines) == 1:
        put(draw, (52, 712), lines[0], 15, fill=SUBTEXT, anchor="lm")
    else:
        put(draw, (52, 700), lines[0], 15, fill=SUBTEXT, anchor="lm")
        put(draw, (52, 724), lines[1], 15, fill=SUBTEXT, anchor="lm")

    put(draw, (500, 764), "OpenWeather \N{MIDDLE DOT} Discord Weather Suite", 12, fill=FAINT, anchor="mm")
    return _png(img)


def minutely_card(*, place: str, minutely: list[dict], now: int, weather: dict, units: Units, headline: str) -> bytes:
    size = (1000, 440)
    img, draw, theme = _base(
        size,
        place,
        weather,
        place,
        "Next 60 minutes precipitation radar",
        badge="60-MIN RADAR",
    )
    glass(img, (32, 102, 968, 404), 18, PANEL_BG)

    points = [m for m in minutely if m["dt"] >= now - 60][:60]
    max_val = max((float(m.get("precipitation") or 0) for m in points), default=0.0)
    peak = max(max_val, 1.5)

    fit_put(draw, (58, 134), headline, 20, 680, min_size=14, bold=True, fill=WHITE, anchor="lm")
    peak_str = f"Peak {units.precip(max_val)}/h"
    put(draw, (942, 134), peak_str, 15, bold=True, fill=(*DISCORD_BLUE, 255), anchor="rm")

    left, right, base, height = 64, 936, 356, 184
    width = (right - left) / max(1, len(points))

    for frac in (0.25, 0.5, 0.75, 1.0):
        gy = int(base - frac * height)
        draw.line((left, gy, right, gy), fill=DIVIDER, width=1)

    for guide, label in ((0, "Now"), (15, "+15m"), (30, "+30m"), (45, "+45m"), (59, "+60m")):
        x = left + guide * width
        draw.line((x, base, x, base + 6), fill=BORDER, width=1)
        put(draw, (x, base + 22), label, 13, bold=True, fill=MUTED, anchor="mm")

    for i, point in enumerate(points):
        value = float(point.get("precipitation") or 0.0)
        h = max(4, int(value / peak * height)) if value > 0.01 else 4
        intensity = min(1.0, value / peak)
        col = (
            (
                int(DISCORD_BLUE[0] * (1 - intensity) + BLURPLE[0] * intensity),
                int(DISCORD_BLUE[1] * (1 - intensity) + BLURPLE[1] * intensity),
                int(DISCORD_BLUE[2] * (1 - intensity) + BLURPLE[2] * intensity),
                255,
            )
            if value > 0.01
            else (64, 68, 75, 255)
        )
        draw.rounded_rectangle((left + i * width + 1.5, base - h, left + (i + 1) * width - 1.5, base), 3, fill=col)

    del theme
    put(draw, (500, 423), "OpenWeather \N{MIDDLE DOT} Discord Weather Suite", 12, fill=FAINT, anchor="mm")
    return _png(img)


def air_card(*, place: str, air: dict, weather: dict, offset: int) -> bytes:  # noqa: PLR0915
    size = (1000, 720)
    current = air["current"]
    aqi = current["main"]["aqi"]
    img, draw, _ = _base(
        size,
        place,
        weather,
        place,
        f"Air Quality Index & Pollutant Breakdown  \N{MIDDLE DOT}  AQI {aqi}/5",
        badge=f"AQI: {AQI_NAMES.get(aqi, 'UNKNOWN').upper()}",
    )

    glass(img, (32, 102, 384, 492), 18, PANEL_BG)
    put(draw, (56, 128), "AIR QUALITY INDEX", 12, bold=True, fill=MUTED, anchor="lm")

    centre, radius = (208, 304), 126
    gauge, needle = Layer(size), Layer(size)
    for i in range(5):
        gauge.arc(centre, (radius, radius), 180 + i * 36 + 2, 180 + (i + 1) * 36 - 2, AQI_COLOURS[i + 1], 24)
    angle = math.radians(180 + 36 * (aqi - 0.5))
    tip = (centre[0] + (radius - 34) * math.cos(angle), centre[1] + (radius - 34) * math.sin(angle))
    needle.polyline([centre, tip], (242, 243, 245), 5)
    needle.circle(centre, 10, AQI_COLOURS[aqi])
    needle.circle(centre, 5, (242, 243, 245))
    img.alpha_composite(gauge.image())
    img.alpha_composite(needle.image(0.55, blur=5))
    img.alpha_composite(needle.image())

    put(draw, (centre[0], 366), AQI_NAMES[aqi], 34, bold=True, fill=(*AQI_COLOURS[aqi], 255), anchor="mm")
    put(draw, (centre[0], 404), f"Index {aqi} of 5", 16, fill=SUBTEXT, anchor="mm")

    for idx in range(1, 6):
        sx = 54 + (idx - 1) * 62
        active = idx == aqi
        pill_fill = (*AQI_COLOURS[idx], 255) if active else _blend(TILE_RGB, AQI_COLOURS[idx], 0.22)
        pill_outline = (*WHITE[:3], 255) if active else (*AQI_COLOURS[idx], 255)
        text_fill = (17, 18, 20, 255) if active else SUBTEXT
        draw.rounded_rectangle((sx, 444, sx + 54, 468), 8, fill=pill_fill, outline=pill_outline, width=1)
        put(draw, (sx + 27, 456), str(idx), 13, bold=True, fill=text_fill, anchor="mm")

    glass(img, (400, 102, 968, 492), 18, PANEL_BG)
    put(draw, (424, 128), "POLLUTANT CONCENTRATIONS (\N{MICRO SIGN}g/m\N{SUPERSCRIPT THREE})", 12, bold=True, fill=MUTED, anchor="lm")

    components = current["components"]
    for i, (key, label) in enumerate(POLLUTANTS):
        col = i % 2
        row = i // 2
        tx = 420 + col * 268
        ty = 152 + row * 80
        tw, th = 256, 68
        glass(img, (tx, ty, tx + tw, ty + th), 12, TILE_BG)

        value = float(components.get(key, 0.0))
        index = aqi_index(key, value) if key in BREAKPOINTS else 1
        bar_col = AQI_COLOURS.get(index, DISCORD_BLUE)

        put(draw, (tx + 14, ty + 22), label, 16, bold=True, fill=WHITE, anchor="lm")
        put(draw, (tx + tw - 14, ty + 22), f"{value:,.1f}", 16, bold=True, fill=SUBTEXT, anchor="rm")

        limit = (BREAKPOINTS[key][3] * 1.25) if key in BREAKPOINTS else max(value * 1.5, 10.0)
        _pill_bar(draw, (tx + 14, ty + 46, tx + tw - 14, ty + 54), value / limit, bar_col)

    glass(img, (32, 508, 968, 686), 18, PANEL_BG)
    put(draw, (56, 530), "24H HISTORY & 4-DAY AQI FORECAST", 12, bold=True, fill=MUTED, anchor="lm")

    entries = {item["dt"]: item for item in [*air["history"], *air["forecast"]]}
    series = [entries[k] for k in sorted(entries)]
    if series:
        left, right, top, base = 56, 944, 554, 658
        width = (right - left) / len(series)
        now_x = None
        for i, item in enumerate(series):
            lvl = item["main"]["aqi"]
            colour = (*AQI_COLOURS[lvl], 255)
            height = 12 + lvl * 12
            draw.rounded_rectangle(
                (left + i * width, base - height, max(left + i * width + 1, left + (i + 1) * width - 1.5), base),
                2,
                fill=colour,
            )
            if now_x is None and item["dt"] >= current["dt"]:
                now_x = left + i * width
            if local(item["dt"], offset).hour == 0:
                draw.line((left + i * width, top + 2, left + i * width, base + 2), fill=BORDER, width=1)
                put(draw, (left + i * width + 6, top + 8), f"{local(item['dt'], offset):%a}", 12, bold=True, fill=SUBTEXT, anchor="lm")
        if now_x is not None:
            draw.line((now_x, top, now_x, base + 4), fill=WHITE, width=2)
            put(draw, (now_x, base + 15), "NOW", 11, bold=True, fill=WHITE, anchor="mm")

    put(draw, (500, 703), "OpenWeather \N{MIDDLE DOT} Discord Weather Suite", 12, fill=FAINT, anchor="mm")
    return _png(img)


def tile_position(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    n = 2**zoom
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


MAP_SIZE = (1000, 560)


def needed_tiles(lat: float, lon: float, zoom: int) -> list[tuple[int, int]]:
    fx, fy = tile_position(lat, lon, zoom)
    w, h = MAP_SIZE
    n = 2**zoom
    xs = range(math.floor(fx - w / 512), math.floor(fx + w / 512) + 1)
    ys = range(math.floor(fy - h / 512), math.floor(fy + h / 512) + 1)
    return sorted({(x % n, y) for y in ys for x in xs if 0 <= y < n})


def map_card(
    *,
    base: dict[tuple[int, int], bytes | None],
    overlay: dict[tuple[int, int], bytes | None],
    lat: float,
    lon: float,
    zoom: int,
    place: str,
    layer: str,
    legend: tuple[str, str, Sequence[RGB]],
    accent: RGB,
) -> bytes:
    w, h = MAP_SIZE
    fx, fy = tile_position(lat, lon, zoom)
    n = 2**zoom
    ground = Image.new("RGBA", MAP_SIZE, (*BG_TOP, 255))
    weather = Image.new("RGBA", MAP_SIZE, (0, 0, 0, 0))

    for ty in range(math.floor(fy - h / 512), math.floor(fy + h / 512) + 1):
        for tx in range(math.floor(fx - w / 512), math.floor(fx + w / 512) + 1):
            key = (tx % n, ty)
            position = (round((tx - fx) * 256 + w / 2), round((ty - fy) * 256 + h / 2))
            for target, source in ((ground, base), (weather, overlay)):
                if (data := source.get(key)) is None:
                    continue
                try:
                    tile_img = Image.open(BytesIO(data)).convert("RGBA")
                    if position[0] >= 0 and position[1] >= 0:
                        target.alpha_composite(tile_img, (position[0], position[1]))
                    else:
                        target.paste(tile_img, position, tile_img)
                except OSError, ValueError:
                    continue

    soft = cv2.GaussianBlur(np.array(weather), (0, 0), 1.2)
    soft[..., 3] = (soft[..., 3] * 0.85).astype(np.uint8)
    ground.alpha_composite(Image.fromarray(soft))
    img = ground

    pin = Layer(MAP_SIZE)
    pin.circle((w / 2, h / 2), 24, accent)
    img.alpha_composite(pin.image(0.35, blur=5))
    ring = Layer(MAP_SIZE)
    ring.circle((w / 2, h / 2), 10, (242, 243, 245))
    ring.circle((w / 2, h / 2), 6, accent)
    img.alpha_composite(ring.image())

    glass(img, (24, 24, 444, 106), 16, (17, 18, 20, 232))
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle((24, 38, 28, 92), 2, fill=(*accent, 255))
    fit_put(draw, (44, 50), place, 24, 380, min_size=16, bold=True, fill=WHITE, anchor="lm")
    put(draw, (44, 80), f"{legend[0]}  \N{MIDDLE DOT}  Zoom {zoom}x", 15, fill=SUBTEXT, anchor="lm")

    glass(img, (24, h - 86, 336, h - 24), 14, (17, 18, 20, 232))
    draw = ImageDraw.Draw(img, "RGBA")
    stops = np.array(legend[2], np.float32)
    ramp = np.stack([np.interp(np.linspace(0, len(stops) - 1, 260), np.arange(len(stops)), stops[:, c]) for c in range(3)], axis=-1)
    bar_img = Image.fromarray(np.repeat(ramp[None], 10, axis=0).astype(np.uint8)).convert("RGBA")
    mask = Image.new("L", (260, 10), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 259, 9), 5, fill=255)
    img.paste(bar_img, (50, h - 46), mask)
    put(draw, (50, h - 64), legend[1].split("|")[0], 13, bold=True, fill=SUBTEXT, anchor="lm")
    put(draw, (310, h - 64), legend[1].split("|")[-1], 13, bold=True, fill=SUBTEXT, anchor="rm")

    put(draw, (w - 20, h - 16), "\N{COPYRIGHT SIGN} OpenStreetMap \N{MIDDLE DOT} CARTO \N{MIDDLE DOT} OpenWeather", 12, fill=SUBTEXT, anchor="rm")
    del layer
    return _png(img)


def animate(card: bytes, weather_id: int, night: bool, *, frames: int = 36, width: int = 760) -> bytes:
    """Loop a particle overlay (rain, snow, lightning, drifting cloud, twinkling stars) over a finished card."""
    base = Image.open(BytesIO(card)).convert("RGB")
    base = base.resize((width, round(base.height * width / base.width)), Image.Resampling.LANCZOS)
    frame_array = np.array(base)
    h, w = frame_array.shape[:2]
    rng = np.random.default_rng(11)

    group = weather_id // 100
    rain = group in {2, 3, 5}
    snow = group == 6
    count = 170 if rain else 110 if snow else 0
    x0, y0 = rng.uniform(0, w, count), rng.uniform(0, h, count)
    cycles = rng.integers(2, 4, count) if rain else rng.integers(1, 2, count)
    phase = rng.uniform(0, 1, count)
    scale = rng.uniform(0.6, 1.35, count)
    stars = rng.uniform(0, 1, (42, 3)) * np.array([w, h * 0.5, 1])

    out: list[Image.Image] = []
    for f in range(frames):
        t = f / frames
        layer = Layer((w, h))
        frame = frame_array.copy()

        for i in range(count):
            y = (y0[i] + cycles[i] * h * t) % h
            if rain:
                x = (x0[i] - 0.22 * (y - y0[i])) % w
                layer.polyline([(x, y), (x - 4 * scale[i], y + 15 * scale[i])], (135, 190, 255), 1)
            else:
                x = x0[i] + 12 * math.sin(2 * math.pi * (t + phase[i]))
                layer.circle((x % w, y), 1.3 * scale[i] + 0.5, (242, 243, 245))

        image = Image.fromarray(frame).convert("RGBA")
        if count:
            image.alpha_composite(layer.image(0.55))

        if (weather_id == 800 and night) or (weather_id // 100 == 8 and weather_id > 800 and night):
            sparkle = Layer((w, h))
            for sx, sy, sp in stars:
                brightness = 0.5 + 0.5 * math.sin(2 * math.pi * (t + sp))
                sparkle.circle((sx, sy), 1.1 + brightness, (210, 220, 255))
            image.alpha_composite(sparkle.image(0.7, blur=0.5))
        elif weather_id >= 700 or weather_id == 800:
            mist = Layer((w, h))
            for k in range(3):
                cx = (k * w / 3 + t * w) % w
                for shift in (-w, 0, w):
                    cv2.ellipse(
                        mist.cov,
                        (int(cx + shift), int(h * (0.25 + 0.25 * k))),
                        (int(w * 0.26), int(h * 0.06)),
                        0,
                        0,
                        360,
                        255,
                        -1,
                        cv2.LINE_AA,
                    )
            mist.rgb[:] = (180, 190, 215)
            image.alpha_composite(mist.image(0.06 if weather_id == 800 else 0.12, blur=34))

        if group == 2 and f in {5, 6, 18}:
            flash = Image.new("RGBA", image.size, (190, 180, 255, 45 if f != 6 else 80))
            image.alpha_composite(flash)
        out.append(image.convert("RGB").quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG))

    buffer = BytesIO()
    out[0].save(buffer, "GIF", save_all=True, append_images=out[1:], duration=80, loop=0, disposal=2)
    return buffer.getvalue()
