from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageFilter

from .image_effects_basic import _sample_bilinear
from .image_utils import from_array, make_rng, to_array, to_rgba
from .image_validators import clamp_float, clamp_int, validate_choice


def gaussian_blur(img: Image.Image, radius: float = 6.0) -> Image.Image:
    r = clamp_float(radius, 0.5, 32.0, "radius")
    return to_rgba(img).convert("RGBa").filter(ImageFilter.GaussianBlur(r)).convert("RGBA")


def motion_blur(img: Image.Image, size: int = 15, angle: float = 0.0) -> Image.Image:
    k = clamp_int(size, 3, 45, "size")
    deg = clamp_float(angle, -180.0, 180.0, "angle")
    rad = math.radians(deg)
    arr = to_array(img).astype(np.float32)
    h, w = arr.shape[:2]
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    dx, dy = math.cos(rad), math.sin(rad)
    acc = np.zeros_like(arr)
    offsets = np.linspace(-k / 2.0, k / 2.0, min(k, 15))
    for offset in offsets:
        acc += _sample_bilinear(arr.astype(np.uint8), xs + offset * dx, ys + offset * dy)
    return from_array(acc / len(offsets))


def zoom_blur(img: Image.Image, strength: float = 0.15) -> Image.Image:
    s = clamp_float(strength, 0.01, 0.5, "strength")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    acc = np.zeros((h, w, 4), dtype=np.float32)
    for factor in np.linspace(1.0 - s, 1.0 + s, 9):
        acc += _sample_bilinear(arr, cx + (xs - cx) * factor, cy + (ys - cy) * factor)
    return from_array(acc / 9.0)


def radial_blur(img: Image.Image, angle: float = 12.0) -> Image.Image:
    a = clamp_float(angle, 1.0, 45.0, "angle")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32) - cx, np.arange(h, dtype=np.float32) - cy)
    acc = np.zeros((h, w, 4), dtype=np.float32)
    for theta in np.linspace(math.radians(-a / 2.0), math.radians(a / 2.0), 9):
        c, s = math.cos(theta), math.sin(theta)
        acc += _sample_bilinear(arr, cx + xs * c - ys * s, cy + xs * s + ys * c)
    return from_array(acc / 9.0)


def tilt_shift(img: Image.Image, focus_y: float = 0.5, dof: float = 0.25, radius: float = 10.0) -> Image.Image:
    fy = clamp_float(focus_y, 0.0, 1.0, "focus_y")
    band = clamp_float(dof, 0.05, 0.6, "dof")
    sharp = to_array(img).astype(np.float32)
    blurred = to_array(gaussian_blur(img, clamp_float(radius, 2.0, 24.0, "radius"))).astype(np.float32)
    y_norm = np.linspace(0.0, 1.0, sharp.shape[0], dtype=np.float32)[:, None, None]
    blend = np.clip((np.abs(y_norm - fy) - band * 0.5) / max(band, 1e-4), 0.0, 1.0)
    return from_array(sharp * (1.0 - blend) + blurred * blend)


def swirl(img: Image.Image, strength: float = 3.0, radius: float = 0.85) -> Image.Image:
    s = clamp_float(strength, -12.0, 12.0, "strength")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32) - cx, np.arange(h, dtype=np.float32) - cy)
    r = np.hypot(xs, ys)
    theta = np.arctan2(ys, xs) + s * np.clip(1.0 - r / max(min(cx, cy) * clamp_float(radius, 0.1, 1.5, "radius"), 1.0), 0.0, 1.0) ** 2
    return from_array(_sample_bilinear(arr, cx + r * np.cos(theta), cy + r * np.sin(theta)))


def bulge(img: Image.Image, strength: float = 0.5) -> Image.Image:
    s = clamp_float(strength, -0.9, 1.5, "strength")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32) - cx, np.arange(h, dtype=np.float32) - cy)
    r = np.hypot(xs, ys) / max(min(cx, cy), 1.0)
    mask = r < 1.0
    exponent = 1.0 / (1.0 + s) if s >= 0 else 1.0 - s * 1.5
    r_new = np.where(mask, np.power(np.clip(r, 1e-6, 1.0), exponent), r)
    scale = np.where(r > 1e-6, r_new / np.maximum(r, 1e-6), 1.0)
    return from_array(_sample_bilinear(arr, cx + xs * scale, cy + ys * scale))


def fisheye(img: Image.Image, strength: float = 1.0) -> Image.Image:
    k = clamp_float(strength, 0.1, 2.5, "strength")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    nx = (np.arange(w, dtype=np.float32)[None, :] - cx) / max(cx, 1.0)
    ny = (np.arange(h, dtype=np.float32)[:, None] - cy) / max(cy, 1.0)
    factor = (1.0 + k * (nx * nx + ny * ny)) / (1.0 + k)
    return from_array(_sample_bilinear(arr, cx + nx * factor * cx, cy + ny * factor * cy))


def ripple(img: Image.Image, amplitude: float = 10.0, wavelength: float = 48.0, mode: str = "both") -> Image.Image:
    amp = clamp_float(amplitude, 1.0, 40.0, "amplitude")
    wl = clamp_float(wavelength, 8.0, 160.0, "wavelength")
    mode = validate_choice(mode, ("both", "horizontal", "vertical"), "mode")
    arr = to_array(img)
    h, w = arr.shape[:2]
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    sx = xs + (amp * np.sin(2.0 * math.pi * ys / wl) if mode in ("both", "horizontal") else 0.0)
    sy = ys + (amp * np.sin(2.0 * math.pi * xs / wl) if mode in ("both", "vertical") else 0.0)
    return from_array(_sample_bilinear(arr, sx, sy))


def melt(img: Image.Image, intensity: float = 0.4, seed: int | None = None) -> Image.Image:
    k = clamp_float(intensity, 0.05, 1.0, "intensity")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]
    x = np.arange(w, dtype=np.float32)
    offsets = np.zeros(w, dtype=np.float32)
    for freq in (1.5, 4.0, 9.0, 19.0):
        offsets += np.sin(2 * math.pi * freq * x / w + float(rng.uniform(0, 2 * math.pi))) / freq
    offsets = (offsets - offsets.min()) / max(float(np.ptp(offsets)), 1e-5)
    xs, ys = np.meshgrid(x, np.arange(h, dtype=np.float32))
    return from_array(_sample_bilinear(arr, xs, ys - offsets[None, :] * (h * 0.35 * k) * (ys / max(h, 1))))


def crt(img: Image.Image, scanline: float = 0.45, curvature: float = 0.12) -> Image.Image:
    sc = clamp_float(scanline, 0.05, 0.9, "scanline")
    warped = fisheye(img, clamp_float(curvature, 0.0, 0.4, "curvature")) if curvature > 0.01 else to_rgba(img)
    arr = to_array(warped).astype(np.float32)
    h, w = arr.shape[:2]
    arr[1::2, :, :3] *= 1.0 - sc
    phosphor = np.ones((1, w, 3), dtype=np.float32)
    phosphor[0, 0::3, 0], phosphor[0, 1::3, 1], phosphor[0, 2::3, 2] = 1.08, 1.08, 1.08
    arr[..., :3] *= phosphor
    nx = (np.arange(w, dtype=np.float32)[None, :] - w / 2) / (w / 2)
    ny = (np.arange(h, dtype=np.float32)[:, None] - h / 2) / (h / 2)
    arr[..., :3] *= np.clip(1.0 - 0.35 * (nx * nx + ny * ny), 0.25, 1.0)[..., None]
    return from_array(arr)


def vhs(img: Image.Image, intensity: float = 0.5, seed: int | None = None) -> Image.Image:
    k = clamp_float(intensity, 0.1, 1.0, "intensity")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]
    shifts = rng.normal(0.0, 2.5 * k, size=h).astype(np.int32)
    band_y = int(rng.integers(0, max(1, int(h * 0.85))))
    band_h = max(4, int(h * 0.08 * k))
    shifts[band_y : band_y + band_h] += int(rng.integers(int(6 * k), int(22 * k) + 2))
    out = np.empty_like(arr)
    for y in range(h):
        out[y] = np.roll(arr[y], int(shifts[y]), axis=0)
    shift = max(1, round(w * 0.015 * k))
    out[..., 0], out[..., 2] = np.roll(out[..., 0], shift, axis=1), np.roll(out[..., 2], -shift, axis=1)
    height = min(band_h, h - band_y)
    snow = rng.integers(140, 255, (height, w, 3), dtype=np.uint8)
    mask = rng.random((height, w, 1)) < 0.35 * k
    out[band_y : band_y + band_h, :, :3] = np.where(mask, snow, out[band_y : band_y + band_h, :, :3])
    out[::2, :, :3] = (out[::2, :, :3] * 0.85).astype(np.uint8)
    return from_array(out)


def chromatic(img: Image.Image, shift_x: int = 8, shift_y: int = 3) -> Image.Image:
    sx, sy = clamp_int(shift_x, -48, 48, "shift_x"), clamp_int(shift_y, -48, 48, "shift_y")
    arr = to_array(img)
    arr[..., 0] = np.roll(np.roll(arr[..., 0], sx, axis=1), sy, axis=0)
    arr[..., 2] = np.roll(np.roll(arr[..., 2], -sx, axis=1), -sy, axis=0)
    return from_array(arr)
