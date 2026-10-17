"""Reusable image transformations built on Pillow and NumPy.

Every effect has the shape ``effect(img, **params) -> PIL.Image.Image`` and:

* accepts any Pillow mode (converted to RGBA internally),
* never mutates its input,
* returns a new **RGBA** image,
* clamps numeric parameters to documented ranges,
* preserves the alpha channel unless the effect is *about* alpha (``spin``).

``EFFECT_REGISTRY`` maps command names to effect callables and
:func:`process_image_bytes` is the one-call pipeline used by the Discord cog
(validate \N{RIGHTWARDS ARROW} decode \N{RIGHTWARDS ARROW} effect per frame \N{RIGHTWARDS ARROW} encode).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from PIL import Image

from .image_utils import (
    EncodedImage,
    encode_animation,
    encode_image,
    from_array,
    join_rgb_alpha,
    load_frames,
    load_image,
    make_rng,
    map_frames,
    resize_rgba,
    to_array,
    to_rgba,
)
from .image_validators import MAX_OUTPUT_FRAMES, MAX_WORKING_DIMENSION, Color, ImageValidationError, clamp_float, clamp_int, validate_choice

EffectFunc = Callable[..., Image.Image]
_LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)
ASCII_RAMP = " .:-=+*#%@"
MIRROR_MODES = ("left", "right", "top", "bottom", "quad")


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """Rec.601 luma of an ``(H, W, 3)`` array as float32 in 0\N{TWO DOT LEADER}255."""
    return rgb.astype(np.float32) @ _LUMA


def pixelate(img: Image.Image, pixel_size: int = 8) -> Image.Image:
    """Pixelate by box-averaging then nearest-neighbour upscaling.

    Args:
        pixel_size: Block edge in pixels, clamped to 2\N{TWO DOT LEADER}128. The output keeps the
            input's exact dimensions and aspect ratio.
    """
    size = clamp_int(pixel_size, 2, 128, "pixel_size")
    rgba = to_rgba(img)
    width, height = rgba.size
    small = (max(1, width // size), max(1, height // size))
    reduced = resize_rgba(rgba, small, Image.Resampling.BOX)
    return reduced.resize((width, height), Image.Resampling.NEAREST)


def glitch(img: Image.Image, intensity: float = 0.5, seed: int | None = None) -> Image.Image:
    """Digital-corruption effect.

    Combines horizontal block displacement, RGB channel separation, scanlines
    and a few duplicated / noise-filled corruption blocks. The same ``seed`` and
    ``intensity`` always give the same result.

    Args:
        intensity: 0.0 (almost nothing) to 1.0 (heavy), clamped.
        seed: Optional RNG seed for reproducibility.
    """
    k = clamp_float(intensity, 0.0, 1.0, "intensity")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]

    # 1. Horizontal block displacement (shifts RGBA together).
    max_shift = int(w * 0.18 * k)
    for _ in range(int(2 + 18 * k)):
        band = int(rng.integers(max(1, h // 64), max(2, h // 8) + 1))
        band = min(band, h)
        y = int(rng.integers(0, h - band + 1))
        shift = int(rng.integers(-max_shift, max_shift + 1))
        arr[y : y + band] = np.roll(arr[y : y + band], shift, axis=1)

    # 2. RGB channel separation (alpha untouched).
    split = round(w * 0.03 * k)
    if split:
        arr[..., 0] = np.roll(arr[..., 0], split, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -split, axis=1)
        arr[..., 1] = np.roll(arr[..., 1], round(h * 0.01 * k), axis=0)

    # 3. Scanlines.
    arr[::3, :, :3] = (arr[::3, :, :3] * (1.0 - 0.45 * k)).astype(np.uint8)

    # 4. Controlled corruption blocks.
    for _ in range(round(10 * k)):
        bh = min(h, int(rng.integers(1, max(2, h // 10) + 1)))
        bw = min(w, int(rng.integers(1, max(2, w // 4) + 1)))
        y = int(rng.integers(0, h - bh + 1))
        x = int(rng.integers(0, w - bw + 1))
        if rng.random() < 1 / 2:
            sy = int(rng.integers(0, h - bh + 1))
            sx = int(rng.integers(0, w - bw + 1))
            arr[y : y + bh, x : x + bw] = arr[sy : sy + bh, sx : sx + bw].copy()
        else:
            noise = rng.integers(0, 256, (bh, bw, 3), dtype=np.uint8)
            region = arr[y : y + bh, x : x + bw]
            visible = region[..., 3:4] > 0
            region[..., :3] = np.where(visible, noise, region[..., :3])
    return from_array(arr)


def invert(img: Image.Image) -> Image.Image:
    """Invert RGB while leaving alpha untouched."""
    arr = to_array(img)
    arr[..., :3] = 255 - arr[..., :3]
    return from_array(arr)


def grayscale(img: Image.Image) -> Image.Image:
    """Convert to grayscale (Rec.601 luma), preserving alpha."""
    arr = to_array(img)
    luma = np.rint(_luminance(arr[..., :3])).astype(np.uint8)
    return join_rgb_alpha(np.repeat(luma[..., None], 3, axis=2), arr[..., 3])


def posterize(img: Image.Image, levels: int = 4) -> Image.Image:
    """Quantise each colour channel to ``levels`` evenly spaced values (2\N{TWO DOT LEADER}32)."""
    n = clamp_int(levels, 2, 32, "levels")
    arr = to_array(img)
    steps = n - 1
    rgb = np.rint(np.rint(arr[..., :3] / 255.0 * steps) * 255.0 / steps)
    return join_rgb_alpha(rgb.astype(np.uint8), arr[..., 3])


def duotone(
    img: Image.Image,
    shadow_color: Color = (20, 10, 60),
    highlight_color: Color = (255, 200, 80),
) -> Image.Image:
    """Map luminance onto a gradient from ``shadow_color`` to ``highlight_color``."""
    shadow = np.asarray([clamp_int(c, 0, 255, "shadow_color") for c in shadow_color], np.float32)
    light = np.asarray([clamp_int(c, 0, 255, "highlight_color") for c in highlight_color], np.float32)
    if shadow.shape != (3,) or light.shape != (3,):
        msg = "Colours must have exactly three RGB components."
        raise ImageValidationError(msg)
    arr = to_array(img)
    t = (_luminance(arr[..., :3]) / 255.0)[..., None]
    rgb = shadow + t * (light - shadow)
    return join_rgb_alpha(np.clip(np.rint(rgb), 0, 255).astype(np.uint8), arr[..., 3])


def _mirror_axis(arr: np.ndarray, axis: int, keep_first: bool) -> np.ndarray:
    """Mirror one half of ``arr`` over the other along ``axis`` (size preserved)."""
    moved = np.moveaxis(arr, axis, 0)
    n = moved.shape[0]
    half = n // 2
    first, mid, last = moved[:half], moved[half : n - half], moved[n - half :]
    out = np.concatenate([first, mid, first[::-1]], axis=0) if keep_first else np.concatenate([last[::-1], mid, last], axis=0)
    return np.moveaxis(out, 0, axis)


def mirror(img: Image.Image, mode: str = "left") -> Image.Image:
    """Create a symmetrical composition.

    Args:
        mode: ``left``/``right`` keep that half and mirror it across the vertical
            axis, ``top``/``bottom`` do the same horizontally, ``quad`` mirrors the
            top-left quadrant into all four corners.
    """
    mode = validate_choice(mode, MIRROR_MODES, "mode")
    arr = to_array(img)
    if mode in ("left", "right"):
        out = _mirror_axis(arr, 1, mode == "left")
    elif mode in ("top", "bottom"):
        out = _mirror_axis(arr, 0, mode == "top")
    else:
        out = _mirror_axis(_mirror_axis(arr, 1, True), 0, True)
    return from_array(out)


def spin(img: Image.Image, angle: float = 90.0, expand: bool = True) -> Image.Image:
    """Rotate counter-clockwise by ``angle`` degrees with transparent padding.

    Args:
        angle: -360\N{TWO DOT LEADER}360 degrees.
        expand: ``True`` grows the canvas so nothing is cropped; ``False`` keeps
            the original size and crops the corners.
    """
    a = clamp_float(angle, -360.0, 360.0, "angle")
    premultiplied = to_rgba(img).convert("RGBa")
    rotated = premultiplied.rotate(a, resample=Image.Resampling.BICUBIC, expand=bool(expand), fillcolor=(0, 0, 0, 0))
    return rotated.convert("RGBA")


def edge(img: Image.Image, strength: float = 1.0) -> Image.Image:
    """Sobel edge detection: light edges on black, alpha preserved.

    Args:
        strength: 0.1\N{TWO DOT LEADER}5.0 multiplier applied after normalisation.
    """
    gain = clamp_float(strength, 0.1, 5.0, "strength")
    arr = to_array(img)
    p = np.pad(_luminance(arr[..., :3]) / 255.0, 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    magnitude = np.hypot(gx, gy)
    peak = float(np.percentile(magnitude, 99))
    scaled = magnitude / peak if peak > 1e-6 else np.zeros_like(magnitude)
    gray = np.rint(np.clip(scaled * gain, 0.0, 1.0) * 255).astype(np.uint8)
    return join_rgb_alpha(np.repeat(gray[..., None], 3, axis=2), arr[..., 3])


def ascii_art(
    img: Image.Image,
    columns: int = 60,
    *,
    ramp: str = ASCII_RAMP,
    invert_ramp: bool = False,
    max_chars: int = 1900,
) -> str:
    """Render an image as ASCII text that is guaranteed to fit ``max_chars``.

    Characters are roughly twice as tall as wide, so rows are halved. Pixels with
    low alpha become spaces. Columns shrink automatically until the output fits;
    for extreme aspect ratios whole rows are dropped as a last resort.

    Args:
        columns: Requested width in characters (8\N{TWO DOT LEADER}120).
        ramp: Characters from lightest to densest (at least two).
        invert_ramp: Swap light/dense (useful on light backgrounds).
        max_chars: Hard cap on the returned string length (100\N{TWO DOT LEADER}4000).
    """
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


EFFECT_REGISTRY: dict[str, EffectFunc] = {
    "pixelate": pixelate,
    "glitch": glitch,
    "invert": invert,
    "grayscale": grayscale,
    "posterize": posterize,
    "duotone": duotone,
    "mirror": mirror,
    "spin": spin,
    "edge": edge,
}


def process_image_bytes(
    data: bytes,
    effect: str,
    params: dict[str, object] | None = None,
) -> EncodedImage:
    """Validate, decode, apply a registered effect to every frame and encode.

    Single images produce PNG, animations produce a looping GIF. When ``params``
    contains an integer ``seed`` each frame uses ``seed + frame_index`` so
    animated glitches flicker but stay reproducible.
    """
    try:
        func = EFFECT_REGISTRY[effect]
    except KeyError:
        msg = f"Unknown effect {effect!r}."
        raise ImageValidationError(msg) from None
    kwargs = dict(params or {})
    frames = load_frames(data, max_frames=MAX_OUTPUT_FRAMES, max_dim=MAX_WORKING_DIMENSION)

    def run(frame: Image.Image, index: int) -> Image.Image:
        call = dict(kwargs)
        if call.get("seed") is not None:
            call["seed"] = int(call["seed"]) + index  # type: ignore[call-overload]
        return func(frame, **call)

    result = map_frames(frames, run)
    if len(result) == 1:
        return encode_image(result[0].image)
    return encode_animation(result)


def ascii_from_bytes(
    data: bytes,
    columns: int = 60,
    *,
    invert_ramp: bool = False,
    max_chars: int = 1900,
) -> str:
    """Decode the first frame of ``data`` and return ASCII art that fits ``max_chars``."""
    img = load_image(data, max_dim=256)
    return ascii_art(img, columns, invert_ramp=invert_ramp, max_chars=max_chars)
