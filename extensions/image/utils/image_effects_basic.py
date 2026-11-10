from __future__ import annotations

from typing import Final

lazy import numpy as np
lazy from PIL import Image

from .image_utils import from_array, join_rgb_alpha, make_rng, resize_rgba, to_array, to_rgba
from .image_validators import Color, ImageValidationError, clamp_float, clamp_int, parse_hex_color, validate_choice

_LUMA: Final = np.array([0.299, 0.587, 0.114], dtype=np.float32)
MIRROR_MODES = ("left", "right", "top", "bottom", "quad")


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """Rec.601 luma of an ``(H, W, 3)`` array as float32 in 0..255."""
    return rgb.astype(np.float32) @ _LUMA


def _sample_bilinear(arr: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Fast vectorized bilinear coordinate remapping for ``(H, W, C)`` uint8 arrays."""
    h, w = arr.shape[:2]
    x = np.clip(xs, 0.0, w - 1.001)
    y = np.clip(ys, 0.0, h - 1.001)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    wx = (x - x0)[..., None].astype(np.float32)
    wy = (y - y0)[..., None].astype(np.float32)
    c00 = arr[y0, x0].astype(np.float32)
    c10 = arr[y0, x1].astype(np.float32)
    c01 = arr[y1, x0].astype(np.float32)
    c11 = arr[y1, x1].astype(np.float32)
    top = c00 * (1.0 - wx) + c10 * wx
    bot = c01 * (1.0 - wx) + c11 * wx
    return np.clip(np.rint(top * (1.0 - wy) + bot * wy), 0, 255).astype(np.uint8)


def pixelate(img: Image.Image, pixel_size: int = 8) -> Image.Image:
    size = clamp_int(pixel_size, 2, 128, "pixel_size")
    rgba = to_rgba(img)
    width, height = rgba.size
    small = (max(1, width // size), max(1, height // size))
    reduced = resize_rgba(rgba, small, Image.Resampling.BOX)
    return reduced.resize((width, height), Image.Resampling.NEAREST)


def glitch(img: Image.Image, intensity: float = 0.5, seed: int | None = None) -> Image.Image:
    k = clamp_float(intensity, 0.0, 1.0, "intensity")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]
    max_shift = int(w * 0.18 * k)
    for _ in range(int(2 + 18 * k)):
        band = min(int(rng.integers(max(1, h // 64), max(2, h // 8) + 1)), h)
        y = int(rng.integers(0, h - band + 1))
        shift = int(rng.integers(-max_shift, max_shift + 1)) if max_shift > 0 else 0
        arr[y : y + band] = np.roll(arr[y : y + band], shift, axis=1)
    split = round(w * 0.03 * k)
    if split:
        arr[..., 0] = np.roll(arr[..., 0], split, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -split, axis=1)
        arr[..., 1] = np.roll(arr[..., 1], round(h * 0.01 * k), axis=0)
    arr[::3, :, :3] = (arr[::3, :, :3] * (1.0 - 0.45 * k)).astype(np.uint8)
    for _ in range(round(10 * k)):
        bh = min(h, int(rng.integers(1, max(2, h // 10) + 1)))
        bw = min(w, int(rng.integers(1, max(2, w // 4) + 1)))
        y = int(rng.integers(0, h - bh + 1))
        x = int(rng.integers(0, w - bw + 1))
        if rng.random() < 0.5:
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
    arr = to_array(img)
    arr[..., :3] = 255 - arr[..., :3]
    return from_array(arr)


def grayscale(img: Image.Image) -> Image.Image:
    arr = to_array(img)
    luma = np.rint(_luminance(arr[..., :3])).astype(np.uint8)
    return join_rgb_alpha(np.repeat(luma[..., None], 3, axis=2), arr[..., 3])


def posterize(img: Image.Image, levels: int = 4) -> Image.Image:
    n = clamp_int(levels, 2, 32, "levels")
    arr = to_array(img)
    steps = n - 1
    rgb = np.rint(np.rint(arr[..., :3] / 255.0 * steps) * 255.0 / steps)
    return join_rgb_alpha(rgb.astype(np.uint8), arr[..., 3])


def duotone(img: Image.Image, shadow_color: Color = (20, 10, 60), highlight_color: Color = (255, 200, 80)) -> Image.Image:
    if isinstance(shadow_color, str):
        shadow_color = parse_hex_color(shadow_color, "shadow_color")
    if isinstance(highlight_color, str):
        highlight_color = parse_hex_color(highlight_color, "highlight_color")
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
    moved = np.moveaxis(arr, axis, 0)
    n = moved.shape[0]
    half = n // 2
    first, mid, last = moved[:half], moved[half : n - half], moved[n - half :]
    out = np.concatenate([first, mid, first[::-1]], axis=0) if keep_first else np.concatenate([last[::-1], mid, last], axis=0)
    return np.moveaxis(out, 0, axis)


def mirror(img: Image.Image, mode: str = "left") -> Image.Image:
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
    a = clamp_float(angle, -360.0, 360.0, "angle")
    premultiplied = to_rgba(img).convert("RGBa")
    rotated = premultiplied.rotate(a, resample=Image.Resampling.BICUBIC, expand=bool(expand), fillcolor=(0, 0, 0, 0))
    return rotated.convert("RGBA")


def edge(img: Image.Image, strength: float = 1.0) -> Image.Image:
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
