"""Validation, clamping and parsing helpers shared by every image module.

Nothing in this module knows about Discord. Every message carried by
:class:`ImageValidationError` is written to be safe to show to end users.

Policy
------
* Numeric parameters that are *numbers but out of range* are clamped.
* Parameters that are *not numbers / not finite / not an allowed choice* raise
  :class:`ImageValidationError`.
* Image bytes are never trusted: the real format is detected from magic bytes,
  cross-checked against what Pillow decodes, and size / dimension / frame
  limits are enforced *before* any pixel data is decoded.
"""

from __future__ import annotations

import io
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from PIL import Image, ImageColor

Color = tuple[int, int, int]

MAX_DOWNLOAD_BYTES: Final = 8 * 1024 * 1024
MAX_INPUT_DIMENSION: Final = 4096
MAX_INPUT_PIXELS: Final = 16_000_000
MAX_INPUT_FRAMES: Final = 500
MAX_TOTAL_INPUT_PIXELS: Final = 160_000_000  # pixels * frames
MAX_WORKING_DIMENSION: Final = 1024
MIN_OUTPUT_DIMENSION: Final = 16
MAX_OUTPUT_DIMENSION: Final = 2048
MAX_HEAVY_DIMENSION: Final = 1024
MAX_OUTPUT_FRAMES: Final = 40
MAX_OUTPUT_BYTES: Final = 8 * 1024 * 1024
ALLOWED_FORMATS: Final = frozenset({"PNG", "JPEG", "GIF", "WEBP"})


class ImageError(Exception):
    """Base class for all errors raised by the image utilities."""


class ImageValidationError(ImageError, ValueError):
    """Invalid input. The message is safe to display to users."""


@dataclass(frozen=True)
class ImageInfo:
    """Header-level facts about an image, obtained without decoding pixels."""

    format: str
    width: int
    height: int
    frames: int


def sniff_format(data: bytes) -> str | None:
    """Return the image format implied by the magic bytes, or ``None``."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data[:3] == b"\xff\xd8\xff":
        return "JPEG"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "GIF"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


def inspect_image(data: bytes) -> ImageInfo:
    """Validate untrusted image bytes without decoding pixel data.

    Raises:
        ImageValidationError: if the data is empty, too large, not a supported
            format, inconsistent, unreadable, or exceeds dimension / pixel /
            frame limits (decompression-bomb protection).
    """
    if not isinstance(data, (bytes, bytearray)) or not data:
        msg = "The image is empty."
        raise ImageValidationError(msg)
    if len(data) > MAX_DOWNLOAD_BYTES:
        limit = MAX_DOWNLOAD_BYTES // (1024 * 1024)
        msg = f"The image is too large (limit {limit} MB)."
        raise ImageValidationError(msg)
    data = bytes(data)
    sniffed = sniff_format(data)
    if sniffed is None:
        msg = "Unsupported or unrecognised image. Please use PNG, JPEG, GIF or WebP."
        raise ImageValidationError(msg)
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = "JPEG" if img.format == "MPO" else img.format
            width, height = img.size
            frames = int(getattr(img, "n_frames", 1))
    except Image.DecompressionBombError as exc:
        msg = "The image has too many pixels."
        raise ImageValidationError(msg) from exc
    except (OSError, SyntaxError, ValueError, EOFError, MemoryError) as exc:
        msg = "The image could not be read; it may be corrupt."
        raise ImageValidationError(msg) from exc

    if fmt not in ALLOWED_FORMATS or fmt != sniffed:
        msg = "The file contents do not match a supported image format."
        raise ImageValidationError(msg)
    if width < 1 or height < 1:
        msg = "The image has invalid dimensions."
        raise ImageValidationError(msg)
    if max(width, height) > MAX_INPUT_DIMENSION or width * height > MAX_INPUT_PIXELS:
        msg = f"The image is too large ({width}x{height}). Max {MAX_INPUT_DIMENSION}px per side and {MAX_INPUT_PIXELS // 1_000_000} megapixels."
        raise ImageValidationError(msg)
    if frames > MAX_INPUT_FRAMES or width * height * frames > MAX_TOTAL_INPUT_PIXELS:
        msg = "The animation has too many frames or is too large."
        raise ImageValidationError(msg)
    return ImageInfo(format=fmt, width=width, height=height, frames=max(1, frames))


def clamp_int(value: object, low: int, high: int, name: str = "value") -> int:
    """Convert ``value`` to ``int`` and clamp to ``[low, high]``."""
    if isinstance(value, bool):
        msg = f"`{name}` must be a whole number."
        raise ImageValidationError(msg)
    try:
        number = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError, OverflowError) as exc:
        msg = f"`{name}` must be a whole number."
        raise ImageValidationError(msg) from exc
    return max(low, min(high, number))


def clamp_float(value: object, low: float, high: float, name: str = "value") -> float:
    """Convert ``value`` to a finite ``float`` and clamp to ``[low, high]``."""
    if isinstance(value, bool):
        msg = f"`{name}` must be a number."
        raise ImageValidationError(msg)
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError) as exc:
        msg = f"`{name}` must be a number."
        raise ImageValidationError(msg) from exc
    if not math.isfinite(number):
        msg = f"`{name}` must be a finite number."
        raise ImageValidationError(msg)
    return max(low, min(high, number))


def validate_choice(value: object, allowed: Sequence[str], name: str = "option") -> str:
    """Return the lower-cased ``value`` if it is in ``allowed``."""
    choice = str(value).strip().lower()
    if choice not in allowed:
        msg = f"`{name}` must be one of: {', '.join(allowed)}."
        raise ImageValidationError(msg)
    return choice


def clamp_dimensions(width: object, height: object, *, max_dim: int = MAX_OUTPUT_DIMENSION) -> tuple[int, int]:
    """Clamp requested output dimensions to the allowed range."""
    return (
        clamp_int(width, MIN_OUTPUT_DIMENSION, max_dim, "width"),
        clamp_int(height, MIN_OUTPUT_DIMENSION, max_dim, "height"),
    )


def normalize_seed(seed: object) -> int | None:
    """Map any integer seed onto the ``[0, 2**32)`` range; ``None`` stays ``None``."""
    if seed is None:
        return None
    if isinstance(seed, bool):
        msg = "`seed` must be a whole number."
        raise ImageValidationError(msg)
    try:
        return int(seed) % (2**32)  # type: ignore[call-overload]
    except (TypeError, ValueError, OverflowError) as exc:
        msg = "`seed` must be a whole number."
        raise ImageValidationError(msg) from exc


_HEX_RE = re.compile(r"(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})|[A-Za-z]{3,20}")


def parse_hex_color(text: object, name: str = "color") -> Color:
    """Parse ``#rgb``, ``#rrggbb``, ``rrggbb`` or a CSS colour name into RGB."""
    if not isinstance(text, str) or not text.strip() or len(text) > 2**5:
        msg = f"`{name}` must be a hex colour such as #ff8800."
        raise ImageValidationError(msg)
    cleaned = text.strip()
    if _HEX_RE.fullmatch(cleaned):
        cleaned = "#" + cleaned
    if not _COLOR_RE.fullmatch(cleaned):
        msg = f"`{name}` must be a hex colour such as #ff8800."
        raise ImageValidationError(msg)
    try:
        rgb = ImageColor.getrgb(cleaned)
    except ValueError as exc:
        msg = f"`{name}` is not a recognised colour."
        raise ImageValidationError(msg) from exc
    return int(rgb[0]), int(rgb[1]), int(rgb[2])


def parse_color_list(text: str | None, *, min_count: int = 2, max_count: int = 12, name: str = "colors") -> list[Color]:
    """Parse a comma/space separated list of colours. Blank or ``None`` \N{RIGHTWARDS ARROW} ``[]``."""
    if text is None or not text.strip():
        return []
    tokens = [t for t in re.split(r"[,\s;]+", text.strip()) if t]
    if len(tokens) > max_count:
        msg = f"`{name}` accepts at most {max_count} colours."
        raise ImageValidationError(msg)
    if len(tokens) < min_count:
        msg = f"`{name}` needs at least {min_count} colours."
        raise ImageValidationError(msg)
    return [parse_hex_color(token, name) for token in tokens]
