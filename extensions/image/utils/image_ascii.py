from __future__ import annotations

import numpy as np
from PIL import Image

from .image_utils import load_image, resize_rgba, to_array, to_rgba
from .image_validators import Color, ImageValidationError, clamp_int

ASCII_RAMP = " .:-=+*#%@"
_LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def _luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb @ _LUMA


def ascii_art(
    img: Image.Image,
    columns: int = 60,
    *,
    ramp: str = ASCII_RAMP,
    invert_ramp: bool = False,
    max_chars: int = 1900,
) -> str:
    """Render an image as ASCII text that is guaranteed to fit ``max_chars``."""
    cols = clamp_int(columns, 8, 120, "columns")
    cap = clamp_int(max_chars, 100, 4000, "max_chars")
    if not isinstance(ramp, str) or len(ramp) < 2 or "`" in ramp:
        msg = "The ASCII ramp needs at least two characters and no backticks."
        raise ImageValidationError(msg)
    chars = np.array(list(ramp[::-1] if invert_ramp else ramp))
    rgba = to_rgba(img)
    w, h = rgba.size

    def rows_for(c: int) -> int:
        return max(1, round(h / w * c * 0.5))

    while cols > 8 and rows_for(cols) * (cols + 1) - 1 > cap:
        cols -= 1
    rows = rows_for(cols)
    arr = to_array(resize_rgba(rgba, (cols, rows), Image.Resampling.BOX))
    index = np.rint(_luminance(arr[..., :3]) / 255.0 * (len(chars) - 1)).astype(np.intp)
    grid = chars[index]
    grid[arr[..., 3] < 40] = " "
    lines = ["".join(row) for row in grid]
    max_rows = max(1, (cap + 1) // (cols + 1))
    return "\n".join(lines[:max_rows])


_ANSI_PALETTE = np.array(
    [
        (30, (79, 84, 92)),
        (31, (220, 50, 47)),
        (32, (133, 153, 0)),
        (33, (181, 137, 0)),
        (34, (38, 139, 210)),
        (35, (211, 54, 130)),
        (36, (42, 161, 152)),
        (37, (255, 255, 255)),
    ],
    dtype=object,
)


def colored_ascii_from_bytes(data: bytes, columns: int = 38, max_chars: int = 1850) -> str:
    """Render an image as ANSI-coloured ASCII art for Discord ```ansi code blocks."""
    img = load_image(data, max_dim=256)
    cols = clamp_int(columns, 8, 56, "columns")
    w, h = img.size
    rows = max(1, round(h / w * cols * 0.5))
    arr = to_array(resize_rgba(img, (cols, rows), Image.Resampling.BOX))
    chars = list(ASCII_RAMP)
    ansi_codes = [int(item[0]) for item in _ANSI_PALETTE]
    ansi_rgbs = np.array([item[1] for item in _ANSI_PALETTE], dtype=np.float32)

    lines: list[str] = []
    total_len = 0
    for y in range(rows):
        row_parts: list[str] = []
        last_code: int | None = None
        for x in range(cols):
            r, g, b, a = arr[y, x]
            if a < 40:
                row_parts.append(" ")
                continue
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            ch = chars[round(luma / 255.0 * (len(chars) - 1))]
            dists = np.sum((ansi_rgbs - np.array([r, g, b], dtype=np.float32)) ** 2, axis=1)
            code = ansi_codes[int(np.argmin(dists))]
            if code != last_code:
                row_parts.append(f"\x1b[{code}m{ch}")
                last_code = code
            else:
                row_parts.append(ch)
        row_str = "".join(row_parts) + "\x1b[0m"
        if total_len + len(row_str) + 1 > max_chars and lines:
            break
        lines.append(row_str)
        total_len += len(row_str) + 1
    return "\n".join(lines)


_BRAILLE_DOTS = (
    (0, 0, 0x01),
    (1, 0, 0x02),
    (2, 0, 0x04),
    (0, 1, 0x08),
    (1, 1, 0x10),
    (2, 1, 0x20),
    (3, 0, 0x40),
    (3, 1, 0x80),
)


def braille_from_bytes(data: bytes, columns: int = 44, invert_dots: bool = False, max_chars: int = 1900) -> str:
    """Render an image as high-density Unicode Braille art (2x4 subpixels per character)."""
    img = load_image(data, max_dim=256)
    cols = clamp_int(columns, 8, 80, "columns")
    w, h = img.size
    rows = max(1, round(h / w * cols * 0.5))
    while cols > 8 and rows * (cols + 1) > max_chars:
        cols -= 1
        rows = max(1, round(h / w * cols * 0.5))
    arr = to_array(resize_rgba(img, (cols * 2, rows * 4), Image.Resampling.BOX))
    luma = _luminance(arr[..., :3])
    thresh = float(np.median(luma))
    active = (luma < thresh) if invert_dots else (luma >= thresh)
    active &= arr[..., 3] >= 40
    lines: list[str] = []
    for r in range(rows):
        chars: list[str] = []
        for c in range(cols):
            mask = 0
            for dy, dx, bit in _BRAILLE_DOTS:
                if active[r * 4 + dy, c * 2 + dx]:
                    mask |= bit
            chars.append(chr(0x2800 + mask))
        lines.append("".join(chars))
    return "\n".join(lines)


_EMOJI_SWATCHES: list[tuple[str, Color]] = [
    ("\N{LARGE RED SQUARE}", (221, 46, 68)),
    ("\N{LARGE ORANGE SQUARE}", (244, 144, 12)),
    ("\N{LARGE YELLOW SQUARE}", (253, 203, 88)),
    ("\N{LARGE GREEN SQUARE}", (120, 177, 89)),
    ("\N{LARGE BLUE SQUARE}", (85, 172, 238)),
    ("\N{LARGE PURPLE SQUARE}", (170, 142, 214)),
    ("\N{LARGE BROWN SQUARE}", (193, 105, 79)),
    ("\N{BLACK LARGE SQUARE}", (49, 55, 61)),
    ("\N{WHITE LARGE SQUARE}", (230, 231, 232)),
]


def emoji_mosaic_from_bytes(data: bytes, columns: int = 22) -> str:
    """Rebuild an image as a grid of Discord colour-square emojis."""
    img = load_image(data, max_dim=256)
    cols = clamp_int(columns, 6, 30, "columns")
    w, h = img.size
    rows = max(1, min(26, round(h / w * cols)))
    arr = to_array(resize_rgba(img, (cols, rows), Image.Resampling.BOX))
    emojis = [e for e, _ in _EMOJI_SWATCHES]
    rgbs = np.array([rgb for _, rgb in _EMOJI_SWATCHES], dtype=np.float32)
    lines: list[str] = []
    for y in range(rows):
        row_chars: list[str] = []
        for x in range(cols):
            r, g, b, a = arr[y, x]
            if a < 40:
                row_chars.append("⬛")
                continue
            dists = np.sum((rgbs - np.array([r, g, b], dtype=np.float32)) ** 2, axis=1)
            row_chars.append(emojis[int(np.argmin(dists))])
        lines.append("".join(row_chars))
    return "\n".join(lines)


def ascii_from_bytes(data: bytes, columns: int = 60, *, invert_ramp: bool = False, max_chars: int = 1900) -> str:
    """Decode the first frame of ``data`` and return ASCII art that fits ``max_chars``."""
    img = load_image(data, max_dim=256)
    return ascii_art(img, columns, invert_ramp=invert_ramp, max_chars=max_chars)
