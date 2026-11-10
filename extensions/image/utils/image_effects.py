from __future__ import annotations

import io
import math
from collections.abc import Callable, Sequence

lazy import numpy as np
lazy from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .image_effects_basic import _luminance, _sample_bilinear, duotone, edge, glitch, grayscale, invert, mirror, pixelate, posterize, spin
from .image_effects_distortions import bulge as distortion_bulge
from .image_effects_distortions import chromatic as distortion_chromatic
from .image_effects_distortions import crt as distortion_crt
from .image_effects_distortions import fisheye as distortion_fisheye
from .image_effects_distortions import gaussian_blur as distortion_gaussian_blur
from .image_effects_distortions import melt as distortion_melt
from .image_effects_distortions import motion_blur as distortion_motion_blur
from .image_effects_distortions import radial_blur as distortion_radial_blur
from .image_effects_distortions import ripple as distortion_ripple
from .image_effects_distortions import swirl as distortion_swirl
from .image_effects_distortions import tilt_shift as distortion_tilt_shift
from .image_effects_distortions import vhs as distortion_vhs
from .image_effects_distortions import zoom_blur as distortion_zoom_blur
from .image_utils import (
    EncodedImage,
    Frame,
    apply_mask,
    crop_circle,
    encode_animation,
    encode_image,
    fit_within,
    from_array,
    join_rgb_alpha,
    load_font,
    load_frames,
    load_image,
    make_rng,
    map_frames,
    resize_rgba,
    rounded_rect_mask,
    to_array,
    to_rgba,
)
from .image_validators import (
    MAX_OUTPUT_DIMENSION,
    MAX_OUTPUT_FRAMES,
    MAX_WORKING_DIMENSION,
    Color,
    ImageValidationError,
    clamp_float,
    clamp_int,
    parse_hex_color,
    validate_choice,
)

EffectFunc = Callable[..., Image.Image]


def gaussian_blur(img: Image.Image, radius: float = 6.0) -> Image.Image:
    """Apply a Gaussian blur with premultiplied alpha protection."""
    r = clamp_float(radius, 0.5, 32.0, "radius")
    rgba = to_rgba(img)
    return rgba.convert("RGBa").filter(ImageFilter.GaussianBlur(r)).convert("RGBA")


def motion_blur(img: Image.Image, size: int = 15, angle: float = 0.0) -> Image.Image:
    """Directional motion blur along ``angle`` degrees."""
    k = clamp_int(size, 3, 45, "size")
    deg = clamp_float(angle, -180.0, 180.0, "angle")
    rad = math.radians(deg)
    arr = to_array(img).astype(np.float32)
    h, w = arr.shape[:2]
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    dx, dy = math.cos(rad), math.sin(rad)
    acc = np.zeros_like(arr)
    samples = min(k, 15)
    offsets = np.linspace(-k / 2.0, k / 2.0, samples)
    u8 = arr.astype(np.uint8)
    for t in offsets:
        acc += _sample_bilinear(u8, xs + t * dx, ys + t * dy)
    return from_array(acc / len(offsets))


def zoom_blur(img: Image.Image, strength: float = 0.15) -> Image.Image:
    """Radial zoom blur radiating from the centre of the image."""
    s = clamp_float(strength, 0.01, 0.5, "strength")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    acc = np.zeros((h, w, 4), dtype=np.float32)
    for factor in np.linspace(1.0 - s, 1.0 + s, 9):
        sx = cx + (xs - cx) * factor
        sy = cy + (ys - cy) * factor
        acc += _sample_bilinear(arr, sx, sy)
    return from_array(acc / 9.0)


def radial_blur(img: Image.Image, angle: float = 12.0) -> Image.Image:
    """Rotational spin/radial blur around the image centre."""
    a = clamp_float(angle, 1.0, 45.0, "angle")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32) - cx, np.arange(h, dtype=np.float32) - cy)
    acc = np.zeros((h, w, 4), dtype=np.float32)
    for theta in np.linspace(math.radians(-a / 2.0), math.radians(a / 2.0), 9):
        c, s = math.cos(theta), math.sin(theta)
        rx = cx + xs * c - ys * s
        ry = cy + xs * s + ys * c
        acc += _sample_bilinear(arr, rx, ry)
    return from_array(acc / 9.0)


def tilt_shift(img: Image.Image, focus_y: float = 0.5, dof: float = 0.25, radius: float = 10.0) -> Image.Image:
    """Miniature tilt-shift effect keeping a horizontal band in sharp focus."""
    fy = clamp_float(focus_y, 0.0, 1.0, "focus_y")
    band = clamp_float(dof, 0.05, 0.6, "dof")
    r = clamp_float(radius, 2.0, 24.0, "radius")
    sharp = to_array(img).astype(np.float32)
    blurred = to_array(gaussian_blur(img, r)).astype(np.float32)
    h = sharp.shape[0]
    y_norm = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    dist = np.abs(y_norm - fy)
    blend = np.clip((dist - band * 0.5) / max(band, 1e-4), 0.0, 1.0)
    out = sharp * (1.0 - blend) + blurred * blend
    return from_array(out)


def swirl(img: Image.Image, strength: float = 3.0, radius: float = 0.85) -> Image.Image:
    """Swirl/twirl distortion around the centre."""
    s = clamp_float(strength, -12.0, 12.0, "strength")
    rad_scale = clamp_float(radius, 0.1, 1.5, "radius")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    max_r = min(cx, cy) * rad_scale
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32) - cx, np.arange(h, dtype=np.float32) - cy)
    r = np.hypot(xs, ys)
    theta = np.arctan2(ys, xs) + s * np.clip(1.0 - r / max(max_r, 1.0), 0.0, 1.0) ** 2
    sx = cx + r * np.cos(theta)
    sy = cy + r * np.sin(theta)
    return from_array(_sample_bilinear(arr, sx, sy))


def bulge(img: Image.Image, strength: float = 0.5) -> Image.Image:
    """Bulge (positive strength) or pinch (negative strength) distortion."""
    s = clamp_float(strength, -0.9, 1.5, "strength")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    max_r = min(cx, cy)
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32) - cx, np.arange(h, dtype=np.float32) - cy)
    r = np.hypot(xs, ys) / max(max_r, 1.0)
    mask = r < 1.0
    exponent = 1.0 / (1.0 + s) if s >= 0 else 1.0 - s * 1.5
    r_new = np.where(mask, np.power(np.clip(r, 1e-6, 1.0), exponent), r)
    scale = np.where(r > 1e-6, r_new / np.maximum(r, 1e-6), 1.0)
    sx = cx + xs * scale
    sy = cy + ys * scale
    return from_array(_sample_bilinear(arr, sx, sy))


def fisheye(img: Image.Image, strength: float = 1.0) -> Image.Image:
    """Barrel / fisheye lens distortion."""
    k = clamp_float(strength, 0.1, 2.5, "strength")
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    nx = (np.arange(w, dtype=np.float32)[None, :] - cx) / max(cx, 1.0)
    ny = (np.arange(h, dtype=np.float32)[:, None] - cy) / max(cy, 1.0)
    r2 = nx * nx + ny * ny
    factor = (1.0 + k * r2) / (1.0 + k)
    sx = cx + nx * factor * cx
    sy = cy + ny * factor * cy
    return from_array(_sample_bilinear(arr, sx, sy))


def ripple(
    img: Image.Image,
    amplitude: float = 10.0,
    wavelength: float = 48.0,
    mode: str = "both",
) -> Image.Image:
    """Sinusoidal ripple / wave distortion."""
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
    """Drip / melt columns downward using smooth multi-frequency sine offsets."""
    k = clamp_float(intensity, 0.05, 1.0, "intensity")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]
    x = np.arange(w, dtype=np.float32)
    offsets = np.zeros(w, dtype=np.float32)
    for freq in (1.5, 4.0, 9.0, 19.0):
        phase = float(rng.uniform(0, 2 * math.pi))
        offsets += np.sin(2 * math.pi * freq * x / w + phase) / freq
    offsets = (offsets - offsets.min()) / max(float(np.ptp(offsets)), 1e-5)
    shifts = offsets * (h * 0.35 * k)
    xs, ys = np.meshgrid(x, np.arange(h, dtype=np.float32))
    sy = ys - shifts[None, :] * (ys / max(h, 1))
    return from_array(_sample_bilinear(arr, xs, sy))


def crt(img: Image.Image, scanline: float = 0.45, curvature: float = 0.12) -> Image.Image:
    """CRT monitor look with scanlines, phosphor subpixel tint, vignette and barrel curve."""
    sc = clamp_float(scanline, 0.05, 0.9, "scanline")
    curv = clamp_float(curvature, 0.0, 0.4, "curvature")
    warped = fisheye(img, curv) if curv > 0.01 else to_rgba(img)
    arr = to_array(warped).astype(np.float32)
    h, w = arr.shape[:2]
    # Scanlines every 2 rows
    arr[1::2, :, :3] *= 1.0 - sc
    # Subtle RGB phosphor columns
    phosphor = np.ones((1, w, 3), dtype=np.float32)
    phosphor[0, 0::3, 0] = 1.08
    phosphor[0, 1::3, 1] = 1.08
    phosphor[0, 2::3, 2] = 1.08
    arr[..., :3] *= phosphor
    # Corner vignette
    nx = (np.arange(w, dtype=np.float32)[None, :] - w / 2) / (w / 2)
    ny = (np.arange(h, dtype=np.float32)[:, None] - h / 2) / (h / 2)
    vig = np.clip(1.0 - 0.35 * (nx * nx + ny * ny), 0.25, 1.0)[..., None]
    arr[..., :3] *= vig
    return from_array(arr)


def vhs(img: Image.Image, intensity: float = 0.5, seed: int | None = None) -> Image.Image:
    """Retro VHS tape distortion: chroma bleed, tracking jitter, noise bars, and desaturation."""
    k = clamp_float(intensity, 0.1, 1.0, "intensity")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]
    # Per-row horizontal jitter
    row_shifts = rng.normal(0.0, 2.5 * k, size=h).astype(np.int32)
    # Occasional tracking tear band
    band_y = int(rng.integers(0, max(1, int(h * 0.85))))
    band_h = max(4, int(h * 0.08 * k))
    row_shifts[band_y : band_y + band_h] += int(rng.integers(int(6 * k), int(22 * k) + 2))
    out = np.empty_like(arr)
    for y in range(h):
        out[y] = np.roll(arr[y], int(row_shifts[y]), axis=0)
    # Chromatic shift
    shift = max(1, round(w * 0.015 * k))
    out[..., 0] = np.roll(out[..., 0], shift, axis=1)
    out[..., 2] = np.roll(out[..., 2], -shift, axis=1)
    # Static snow in tracking band
    snow = rng.integers(140, 255, (min(band_h, h - band_y), w, 3), dtype=np.uint8)
    mask = rng.random((min(band_h, h - band_y), w, 1)) < (0.35 * k)
    out[band_y : band_y + band_h, :, :3] = np.where(mask, snow, out[band_y : band_y + band_h, :, :3])
    # Slight scanlines
    out[::2, :, :3] = (out[::2, :, :3] * 0.85).astype(np.uint8)
    return from_array(out)


def chromatic(img: Image.Image, shift_x: int = 8, shift_y: int = 3) -> Image.Image:
    """Chromatic aberration (RGB channel split)."""
    sx = clamp_int(shift_x, -48, 48, "shift_x")
    sy = clamp_int(shift_y, -48, 48, "shift_y")
    arr = to_array(img)
    arr[..., 0] = np.roll(np.roll(arr[..., 0], sx, axis=1), sy, axis=0)
    arr[..., 2] = np.roll(np.roll(arr[..., 2], -sx, axis=1), -sy, axis=0)
    return from_array(arr)


def halftone(img: Image.Image, dot_size: int = 8) -> Image.Image:
    """Comic-print halftone dots scaled by local luminance."""
    cell = clamp_int(dot_size, 4, 24, "dot_size")
    arr = to_array(img)
    h, w = arr.shape[:2]
    canvas = Image.new("RGBA", (w, h), (245, 242, 235, 255))
    draw = ImageDraw.Draw(canvas)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            block = arr[y : y + cell, x : x + cell]
            if block[..., 3].mean() < 32:
                continue
            avg_rgb = tuple(int(c) for c in block[..., :3].mean(axis=(0, 1)))
            luma = (0.299 * avg_rgb[0] + 0.587 * avg_rgb[1] + 0.114 * avg_rgb[2]) / 255.0
            radius = (1.0 - luma * 0.85) * (cell * 0.62)
            if radius >= 0.8:
                cx, cy = x + cell / 2.0, y + cell / 2.0
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(*avg_rgb, 255))
    canvas.putalpha(from_array(arr).getchannel("A"))
    return canvas


_BAYER_4X4 = (
    np.array(
        [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5],
        ],
        dtype=np.float32,
    )
    - 0.5
)


def dither(img: Image.Image, mode: str = "bayer", levels: int = 3) -> Image.Image:
    """Ordered Bayer or Floyd-Steinberg dithered quantization."""
    mode = validate_choice(mode, ("bayer", "floyd"), "mode")
    lv = clamp_int(levels, 2, 8, "levels")
    rgba = to_rgba(img)
    if mode == "floyd":
        pal_img = rgba.convert("RGB").quantize(colors=lv**3, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        out = pal_img.convert("RGBA")
        out.putalpha(rgba.getchannel("A"))
        return out
    arr = to_array(rgba)
    h, w = arr.shape[:2]
    tiled = np.tile(_BAYER_4X4, (math.ceil(h / 4), math.ceil(w / 4)))[:h, :w, None]
    steps = lv - 1
    spread = 255.0 / steps
    rgb = np.clip(arr[..., :3].astype(np.float32) + tiled * spread, 0.0, 255.0)
    quant = np.rint(np.rint(rgb / 255.0 * steps) * 255.0 / steps).astype(np.uint8)
    return join_rgb_alpha(quant, arr[..., 3])


_GAMEBOY_PALETTES: dict[str, list[Color]] = {
    "dmg": [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)],
    "pocket": [(24, 24, 24), (88, 88, 80), (168, 168, 152), (224, 224, 208)],
    "light": [(0, 48, 59), (0, 119, 119), (0, 189, 156), (155, 246, 218)],
}


def gameboy(img: Image.Image, palette_kind: str = "dmg", pixel_size: int = 3) -> Image.Image:
    """Retro 4-shade Game Boy screen effect with Bayer dithering and pixel grid."""
    kind = validate_choice(palette_kind, tuple(_GAMEBOY_PALETTES.keys()), "palette_kind")
    px = clamp_int(pixel_size, 1, 12, "pixel_size")
    work = pixelate(img, px) if px > 1 else to_rgba(img)
    arr = to_array(work)
    h, w = arr.shape[:2]
    luma = _luminance(arr[..., :3]) / 255.0
    tiled = np.tile(_BAYER_4X4, (math.ceil(h / 4), math.ceil(w / 4)))[:h, :w]
    idx = np.clip(np.floor((luma + tiled * 0.22) * 4.0).astype(np.int32), 0, 3)
    pal = np.asarray(_GAMEBOY_PALETTES[kind], dtype=np.uint8)
    return join_rgb_alpha(pal[idx], arr[..., 3])


def cartoon(img: Image.Image, levels: int = 6, edge_threshold: float = 0.35) -> Image.Image:
    """Toon / cel-shaded effect combining smoothed colour quantization and bold ink outlines."""
    lv = clamp_int(levels, 3, 12, "levels")
    thresh = clamp_float(edge_threshold, 0.1, 0.9, "edge_threshold")
    rgba = to_rgba(img)
    smoothed = rgba.convert("RGB").filter(ImageFilter.MedianFilter(size=3))
    quant = posterize(smoothed.convert("RGBA"), lv)
    edges_arr = to_array(edge(rgba, strength=1.5))[..., 0] / 255.0
    q_arr = to_array(quant)
    ink = edges_arr > thresh
    q_arr[ink, :3] = (q_arr[ink, :3] * 0.15).astype(np.uint8)
    q_arr[..., 3] = to_array(rgba)[..., 3]
    return from_array(q_arr)


def sketch(img: Image.Image, shade: float = 0.5) -> Image.Image:
    """Pencil sketch effect using colour-dodge blending between grayscale and blurred inverse."""
    s = clamp_float(shade, 0.1, 1.0, "shade")
    arr = to_array(img)
    gray = _luminance(arr[..., :3])
    inv_blur = np.asarray(
        Image.fromarray((255.0 - gray).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=12.0 * s)),
        dtype=np.float32,
    )
    denom = np.maximum(255.0 - inv_blur, 1.0)
    dodged = np.clip(gray * 256.0 / denom, 0.0, 255.0).astype(np.uint8)
    return join_rgb_alpha(np.repeat(dodged[..., None], 3, axis=2), arr[..., 3])


def oil_paint(img: Image.Image, radius: int = 3, levels: int = 10) -> Image.Image:
    """Painterly oil-paint filter using median filtering and warm colour quantization."""
    r = clamp_int(radius, 1, 7, "radius")
    lv = clamp_int(levels, 4, 24, "levels")
    rgba = to_rgba(img)
    rgb = rgba.convert("RGB").filter(ImageFilter.ModeFilter(size=r * 2 + 1))
    out = posterize(rgb.convert("RGBA"), lv)
    out.putalpha(rgba.getchannel("A"))
    return out


def emboss(img: Image.Image, strength: float = 1.5) -> Image.Image:
    """Directional relief emboss filter."""
    s = clamp_float(strength, 0.5, 4.0, "strength")
    arr = to_array(img)
    luma = np.pad(_luminance(arr[..., :3]), 1, mode="edge")
    diff = luma[:-2, :-2] * -2 - luma[:-2, 1:-1] - luma[1:-1, :-2] + luma[1:-1, 2:] + luma[2:, 1:-1] + luma[2:, 2:] * 2
    gray = np.clip(128.0 + diff * s * 0.5, 0.0, 255.0).astype(np.uint8)
    return join_rgb_alpha(np.repeat(gray[..., None], 3, axis=2), arr[..., 3])


def sepia(img: Image.Image, intensity: float = 1.0) -> Image.Image:
    """Warm vintage sepia tone."""
    k = clamp_float(intensity, 0.0, 1.0, "intensity")
    arr = to_array(img)
    rgb = arr[..., :3].astype(np.float32)
    matrix = np.array(
        [
            [0.393, 0.769, 0.189],
            [0.349, 0.686, 0.168],
            [0.272, 0.534, 0.131],
        ],
        dtype=np.float32,
    )
    sep = np.clip(rgb @ matrix.T, 0.0, 255.0)
    blended = rgb * (1.0 - k) + sep * k
    return join_rgb_alpha(np.rint(blended).astype(np.uint8), arr[..., 3])


def solarize(img: Image.Image, threshold: int = 128) -> Image.Image:
    """Invert tones above ``threshold`` (Sabattier solarization)."""
    t = clamp_int(threshold, 0, 255, "threshold")
    arr = to_array(img)
    rgb = arr[..., :3]
    arr[..., :3] = np.where(rgb >= t, 255 - rgb, rgb)
    return from_array(arr)


_THERMAL_STOPS = np.array(
    [
        [10, 7, 35],
        [65, 15, 115],
        [165, 30, 95],
        [235, 85, 30],
        [252, 185, 25],
        [255, 252, 190],
    ],
    dtype=np.float32,
)


def thermal(img: Image.Image) -> Image.Image:
    """Infrared thermal / heatmap false-colour mapping."""
    arr = to_array(img)
    t = _luminance(arr[..., :3]) / 255.0
    stops = np.linspace(0.0, 1.0, len(_THERMAL_STOPS))
    rgb = np.stack([np.interp(t, stops, _THERMAL_STOPS[:, c]) for c in range(3)], axis=-1)
    return join_rgb_alpha(np.rint(rgb).astype(np.uint8), arr[..., 3])


def neon_edges(img: Image.Image, glow: float = 2.0) -> Image.Image:
    """Cyberpunk glowing neon edges colored by local gradient angle."""
    g = clamp_float(glow, 0.5, 5.0, "glow")
    arr = to_array(img)
    p = np.pad(_luminance(arr[..., :3]) / 255.0, 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    mag = np.hypot(gx, gy)
    peak = max(float(np.percentile(mag, 99)), 1e-5)
    val = np.clip((mag / peak) * g, 0.0, 1.0)
    angle = (np.arctan2(gy, gx) / (2.0 * math.pi)) % 1.0
    r = np.abs(angle * 6.0 - 3.0) - 1.0
    gr = 2.0 - np.abs(angle * 6.0 - 2.0)
    b = 2.0 - np.abs(angle * 6.0 - 4.0)
    hue_rgb = np.clip(np.stack([r, gr, b], axis=-1), 0.0, 1.0)
    neon = (hue_rgb * val[..., None] * 255.0).astype(np.uint8)
    base = join_rgb_alpha(neon, arr[..., 3])
    bloom = gaussian_blur(base, radius=3.5)
    b_arr = np.clip(to_array(base)[..., :3].astype(np.int32) + to_array(bloom)[..., :3].astype(np.int32), 0, 255).astype(np.uint8)
    return join_rgb_alpha(b_arr, arr[..., 3])


def hue_shift(img: Image.Image, degrees: float = 90.0) -> Image.Image:
    """Rotate image hue in HSV space by ``degrees`` (-360..360)."""
    deg = clamp_float(degrees, -360.0, 360.0, "degrees")
    rgba = to_rgba(img)
    hsv = np.array(rgba.convert("HSV"), dtype=np.uint8)
    shift = round((deg % 360.0) / 360.0 * 255.0)
    hsv[..., 0] = (hsv[..., 0].astype(np.int32) + shift) % 256
    rgb = Image.fromarray(hsv, mode="HSV").convert("RGB")
    out = rgb.convert("RGBA")
    out.putalpha(rgba.getchannel("A"))
    return out


def bcs(
    img: Image.Image,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
) -> Image.Image:
    """Adjust Brightness, Contrast, and Saturation simultaneously."""
    b = clamp_float(brightness, 0.1, 3.0, "brightness")
    c = clamp_float(contrast, 0.1, 3.0, "contrast")
    s = clamp_float(saturation, 0.0, 3.0, "saturation")
    rgba = to_rgba(img)
    rgb = rgba.convert("RGB")
    if abs(b - 1.0) > 1e-3:
        rgb = ImageEnhance.Brightness(rgb).enhance(b)
    if abs(c - 1.0) > 1e-3:
        rgb = ImageEnhance.Contrast(rgb).enhance(c)
    if abs(s - 1.0) > 1e-3:
        rgb = ImageEnhance.Color(rgb).enhance(s)
    out = rgb.convert("RGBA")
    out.putalpha(rgba.getchannel("A"))
    return out


def channel_swap(img: Image.Image, order: str = "gbr") -> Image.Image:
    """Permute RGB channels (`gbr`, `brg`, `bgr`, `rbg`, `grb`)."""
    order = validate_choice(order, ("gbr", "brg", "bgr", "rbg", "grb", "rgb"), "order")
    idx = [{"r": 0, "g": 1, "b": 2}[ch] for ch in order]
    arr = to_array(img)
    arr[..., :3] = arr[..., idx]
    return from_array(arr)


def threshold(img: Image.Image, cutoff: int = 128) -> Image.Image:
    """High-contrast 1-bit black & white thresholding."""
    c = clamp_int(cutoff, 1, 254, "cutoff")
    arr = to_array(img)
    bw = np.where(_luminance(arr[..., :3]) >= c, 255, 0).astype(np.uint8)
    return join_rgb_alpha(np.repeat(bw[..., None], 3, axis=2), arr[..., 3])


def colorize(img: Image.Image, color: Color | str = (0, 200, 255), strength: float = 0.7) -> Image.Image:
    """Tint an image toward ``color`` while preserving luminance highlights."""
    if isinstance(color, str):
        color = parse_hex_color(color, "color")
    s = clamp_float(strength, 0.05, 1.0, "strength")
    arr = to_array(img)
    rgb = arr[..., :3].astype(np.float32)
    luma = (_luminance(rgb) / 255.0)[..., None]
    tint = np.asarray(color, dtype=np.float32) * luma
    out = rgb * (1.0 - s) + tint * s
    return join_rgb_alpha(np.clip(np.rint(out), 0, 255).astype(np.uint8), arr[..., 3])


def pixel_sort(
    img: Image.Image,
    direction: str = "horizontal",
    low: int = 55,
    high: int = 210,
) -> Image.Image:
    """Sort contiguous spans of pixels whose luminance falls within ``[low, high]``."""
    direction = validate_choice(direction, ("horizontal", "vertical"), "direction")
    lo = clamp_int(low, 0, 240, "low")
    hi = clamp_int(high, lo + 5, 255, "high")
    arr = to_array(img)
    if direction == "vertical":
        arr = np.swapaxes(arr, 0, 1).copy()
    luma = _luminance(arr[..., :3])
    mask = (luma >= lo) & (luma <= hi) & (arr[..., 3] > 32)
    h, _ = arr.shape[:2]
    for y in range(h):
        row_mask = mask[y]
        if not row_mask.any():
            continue
        padded = np.concatenate(([False], row_mask, [False]))
        starts = np.flatnonzero(padded[1:] & ~padded[:-1])
        ends = np.flatnonzero(~padded[1:] & padded[:-1])
        for s_idx, e_idx in zip(starts, ends, strict=False):
            if e_idx - s_idx > 2:
                order = np.argsort(luma[y, s_idx:e_idx])
                arr[y, s_idx:e_idx] = arr[y, s_idx + order]
    if direction == "vertical":
        arr = np.swapaxes(arr, 0, 1)
    return from_array(arr)


def datamosh(img: Image.Image, blocks: int = 24, shift: int = 28, seed: int | None = None) -> Image.Image:
    """Datamosh macroblock displacement and motion-vector smearing."""
    n = clamp_int(blocks, 4, 80, "blocks")
    max_s = clamp_int(shift, 4, 96, "shift")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]
    bs = 16
    for _ in range(n):
        bw = int(rng.integers(1, 5)) * bs
        bh = int(rng.integers(1, 4)) * bs
        if bw >= w or bh >= h:
            continue
        x = int(rng.integers(0, w - bw))
        y = int(rng.integers(0, h - bh))
        dx = int(rng.integers(-max_s, max_s + 1))
        dy = int(rng.integers(-max_s, max_s + 1))
        sx = int(np.clip(x + dx, 0, w - bw))
        sy = int(np.clip(y + dy, 0, h - bh))
        arr[y : y + bh, x : x + bw] = arr[sy : sy + bh, sx : sx + bw]
    return from_array(arr)


def jpeg_crush(img: Image.Image, quality: int = 6, passes: int = 3) -> Image.Image:
    """Repeated low-quality JPEG re-encoding with subtle resolution jitter."""
    q = clamp_int(quality, 1, 35, "quality")
    p = clamp_int(passes, 1, 6, "passes")
    rgba = to_rgba(img)
    rgb = rgba.convert("RGB")
    w, h = rgb.size
    for i in range(p):
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=max(1, q - i), subsampling=2)
        buf.seek(0)
        rgb = Image.open(buf).convert("RGB")
        if i < p - 1 and min(w, h) > 32:
            rgb = rgb.resize((max(16, w - i * 2), max(16, h - i * 2)), Image.Resampling.BILINEAR).resize((w, h), Image.Resampling.NEAREST)
    out = rgb.convert("RGBA")
    out.putalpha(rgba.getchannel("A"))
    return out


def deep_fry(img: Image.Image, intensity: float = 0.7, seed: int | None = None) -> Image.Image:
    """Meme deep-fry effect: extreme saturation, sharpening, contrast boost, noise, and JPEG crush."""
    k = clamp_float(intensity, 0.1, 1.0, "intensity")
    rng = make_rng(seed)
    work = bcs(img, brightness=1.0 + 0.15 * k, contrast=1.0 + 1.8 * k, saturation=1.0 + 2.2 * k)
    rgba = to_rgba(work)
    sharp = rgba.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=int(250 * k), threshold=1))
    arr = np.array(sharp, dtype=np.float32)
    arr += rng.normal(0.0, 14.0 * k, size=arr.shape)
    return jpeg_crush(join_rgb_alpha(np.clip(arr, 0, 255).astype(np.uint8), to_array(rgba)[..., 3]), quality=max(2, int(14 * (1.1 - k))), passes=2)


def kaleidoscope(img: Image.Image, folds: int = 6, angle: float = 0.0) -> Image.Image:
    """Reflect an angular wedge around the centre across ``folds`` axes of symmetry."""
    n = clamp_int(folds, 2, 16, "folds")
    offset = math.radians(clamp_float(angle, -360.0, 360.0, "angle"))
    arr = to_array(img)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32) - cx, np.arange(h, dtype=np.float32) - cy)
    r = np.hypot(xs, ys)
    sector = 2.0 * math.pi / n
    theta = (np.arctan2(ys, xs) - offset) % sector
    theta = np.minimum(theta, sector - theta) + offset
    sx = cx + r * np.cos(theta)
    sy = cy + r * np.sin(theta)
    return from_array(_sample_bilinear(arr, sx, sy))


def tile_repeat(img: Image.Image, tiles: int = 3) -> Image.Image:
    """Repeat the image in a ``tiles x tiles`` grid of the same canvas size."""
    n = clamp_int(tiles, 2, 8, "tiles")
    rgba = to_rgba(img)
    w, h = rgba.size
    tw, th = max(1, w // n), max(1, h // n)
    small = resize_rgba(rgba, (tw, th))
    arr = np.tile(to_array(small), (n + 1, n + 1, 1))[:h, :w]
    return from_array(arr)


def low_poly(img: Image.Image, points: int = 120, seed: int | None = None) -> Image.Image:
    """Low-poly triangulation mosaic sampling average image colours per triangle."""
    n = clamp_int(points, 20, 400, "points")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]
    grid_n = max(3, int(math.sqrt(n)))
    gx = np.linspace(0, w - 1, grid_n)
    gy = np.linspace(0, h - 1, grid_n)
    cell_w = w / max(grid_n - 1, 1)
    cell_h = h / max(grid_n - 1, 1)
    verts = np.zeros((grid_n, grid_n, 2), dtype=np.float32)
    for r in range(grid_n):
        for c in range(grid_n):
            jx = float(rng.uniform(-0.35, 0.35) * cell_w) if 0 < c < grid_n - 1 else 0.0
            jy = float(rng.uniform(-0.35, 0.35) * cell_h) if 0 < r < grid_n - 1 else 0.0
            verts[r, c] = (np.clip(gx[c] + jx, 0, w - 1), np.clip(gy[r] + jy, 0, h - 1))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for r in range(grid_n - 1):
        for c in range(grid_n - 1):
            p00, p10 = tuple(verts[r, c]), tuple(verts[r, c + 1])
            p01, p11 = tuple(verts[r + 1, c]), tuple(verts[r + 1, c + 1])
            tris = [(p00, p10, p11), (p00, p11, p01)] if (r + c) % 2 == 0 else [(p00, p10, p01), (p10, p11, p01)]
            for tri in tris:
                cx = int(np.clip(sum(p[0] for p in tri) / 3.0, 0, w - 1))
                cy = int(np.clip(sum(p[1] for p in tri) / 3.0, 0, h - 1))
                color = tuple(int(v) for v in arr[cy, cx])
                draw.polygon(tri, fill=color)
    return canvas


def stained_glass(img: Image.Image, cells: int = 80, border: int = 1, seed: int | None = None) -> Image.Image:
    """Voronoi stained-glass mosaic that samples each cell's colour from the source image."""
    n = clamp_int(cells, 16, 250, "cells")
    b_width = clamp_int(border, 0, 4, "border")
    rng = make_rng(seed)
    arr = to_array(img)
    h, w = arr.shape[:2]
    px = rng.uniform(0, w - 1, n).astype(np.float32)
    py = rng.uniform(0, h - 1, n).astype(np.float32)
    xs = np.arange(w, dtype=np.float32)[None, :]
    ys = np.arange(h, dtype=np.float32)[:, None]
    best = np.full((h, w), np.inf, dtype=np.float32)
    label = np.zeros((h, w), dtype=np.int32)
    for i in range(n):
        d = (xs - px[i]) ** 2 + (ys - py[i]) ** 2
        mask = d < best
        best = np.where(mask, d, best)
        label = np.where(mask, i, label)
    sample_x = np.clip(px.astype(np.int32), 0, w - 1)
    sample_y = np.clip(py.astype(np.int32), 0, h - 1)
    colors = arr[sample_y, sample_x, :3]
    out_rgb = colors[label]
    if b_width > 0:
        edge_mask = np.zeros((h, w), dtype=bool)
        edge_mask[:, 1:] |= label[:, 1:] != label[:, :-1]
        edge_mask[1:, :] |= label[1:, :] != label[:-1, :]
        if b_width > 1:
            edge_img = Image.fromarray((edge_mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(size=b_width * 2 + 1))
            edge_mask = np.asarray(edge_img) > 127
        out_rgb[edge_mask] = (20, 20, 26)
    return join_rgb_alpha(out_rgb, arr[..., 3])


def circle_cutout(img: Image.Image) -> Image.Image:
    """Crop the image into an anti-aliased circle."""
    rgba = to_rgba(img)
    return crop_circle(rgba, min(rgba.size))


def rounded_cutout(img: Image.Image, radius_ratio: float = 0.22) -> Image.Image:
    """Clip the image to a rounded rectangle."""
    r = clamp_float(radius_ratio, 0.02, 0.5, "radius_ratio")
    rgba = to_rgba(img)
    w, h = rgba.size
    mask = rounded_rect_mask(w, h, min(w, h) * r)
    return apply_mask(rgba, mask)


def sticker(
    img: Image.Image,
    outline: int = 8,
    color: Color | str = (255, 255, 255),
    shadow: bool = True,
) -> Image.Image:
    """Create a die-cut sticker with a thick outline and optional drop shadow."""
    if isinstance(color, str):
        color = parse_hex_color(color, "color")
    thick = clamp_int(outline, 2, 24, "outline")
    rgba = to_rgba(img)
    # If completely opaque, round the corners slightly so the sticker outline is visible
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] == 255:
        rgba = rounded_cutout(rgba, 0.12)
    pad = thick + (14 if shadow else 4)
    w, h = rgba.size
    cw, ch = w + pad * 2, h + pad * 2
    padded = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    padded.paste(rgba, (pad, pad))
    a_mask = padded.getchannel("A")
    dilated = a_mask.filter(ImageFilter.MaxFilter(size=thick * 2 + 1)).filter(ImageFilter.GaussianBlur(1.2))
    dilated = dilated.point(lambda p: 255 if p > 80 else p * 3)
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    if shadow:
        sh_mask = dilated.filter(ImageFilter.GaussianBlur(6.0))
        sh_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 150))
        sh_layer.putalpha(Image.fromarray((np.asarray(sh_mask, dtype=np.float32) * 0.55).astype(np.uint8)))
        canvas.alpha_composite(sh_layer, dest=(4, 6))
    border_layer = Image.new("RGBA", (cw, ch), (*color, 255))
    border_layer.putalpha(dilated)
    canvas.alpha_composite(border_layer)
    canvas.alpha_composite(padded)
    return canvas


def bg_remove(img: Image.Image, tolerance: int = 42) -> Image.Image:
    """Chroma/corner-flood background removal based on corner background sampling."""
    tol = clamp_int(tolerance, 8, 140, "tolerance")
    arr = to_array(img)
    h, w = arr.shape[:2]
    corners = np.array([arr[0, 0, :3], arr[0, w - 1, :3], arr[h - 1, 0, :3], arr[h - 1, w - 1, :3]], dtype=np.float32)
    bg_color = np.median(corners, axis=0)
    dist = np.linalg.norm(arr[..., :3].astype(np.float32) - bg_color[None, None, :], axis=-1)
    alpha_scale = np.clip((dist - tol * 0.7) / max(tol * 0.5, 1.0), 0.0, 1.0)
    arr[..., 3] = (arr[..., 3].astype(np.float32) * alpha_scale).astype(np.uint8)
    return from_array(arr)


EFFECT_REGISTRY: dict[str, EffectFunc] = {
    # Original
    "pixelate": pixelate,
    "glitch": glitch,
    "invert": invert,
    "grayscale": grayscale,
    "posterize": posterize,
    "duotone": duotone,
    "mirror": mirror,
    "spin": spin,
    "edge": edge,
    # Blur family
    "gaussian": distortion_gaussian_blur,
    "motionblur": distortion_motion_blur,
    "zoomblur": distortion_zoom_blur,
    "radialblur": distortion_radial_blur,
    "tiltshift": distortion_tilt_shift,
    # Distortions
    "swirl": distortion_swirl,
    "bulge": distortion_bulge,
    "fisheye": distortion_fisheye,
    "ripple": distortion_ripple,
    "melt": distortion_melt,
    # Retro
    "crt": distortion_crt,
    "vhs": distortion_vhs,
    "chromatic": distortion_chromatic,
    "halftone": halftone,
    "dither": dither,
    "gameboy": gameboy,
    # Stylize
    "cartoon": cartoon,
    "sketch": sketch,
    "oilpaint": oil_paint,
    "emboss": emboss,
    "sepia": sepia,
    "solarize": solarize,
    "thermal": thermal,
    "neon": neon_edges,
    # Color
    "hueshift": hue_shift,
    "bcs": bcs,
    "channelswap": channel_swap,
    "threshold": threshold,
    "colorize": colorize,
    # Glitch variants
    "pixelsort": pixel_sort,
    "datamosh": datamosh,
    "jpegcrush": jpeg_crush,
    "deepfry": deep_fry,
    # Geometric / Cutouts
    "kaleidoscope": kaleidoscope,
    "tile": tile_repeat,
    "lowpoly": low_poly,
    "stainedglass": stained_glass,
    "circlecrop": circle_cutout,
    "rounded": rounded_cutout,
    "sticker": sticker,
    "bgremove": bg_remove,
}


def process_image_bytes(
    data: bytes,
    effect: str,
    params: dict[str, object] | None = None,
) -> EncodedImage:
    """Validate, decode, apply a registered effect to every frame and encode."""
    try:
        func = EFFECT_REGISTRY[effect]
    except KeyError:
        msg = f"Unknown effect {effect!r}. Available: {', '.join(sorted(EFFECT_REGISTRY))}."
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


def _parse_step_token(step_text: str) -> tuple[EffectFunc, tuple[object, ...], str]:
    tokens = step_text.strip().split()
    if not tokens:
        msg = "Empty effect step in chain."
        raise ImageValidationError(msg)
    name = tokens[0].lower()
    if name not in EFFECT_REGISTRY:
        msg = f"Unknown effect `{name}` in chain. Choose from: {', '.join(sorted(EFFECT_REGISTRY))}."
        raise ImageValidationError(msg)
    args: list[object] = []
    for raw in tokens[1:]:
        if raw.lower() in ("true", "false"):
            args.append(raw.lower() == "true")
            continue
        try:
            args.append(int(raw))
            continue
        except ValueError:
            pass
        try:
            args.append(float(raw))
            continue
        except ValueError:
            pass
        args.append(raw)
    return EFFECT_REGISTRY[name], tuple(args), name


def process_effect_chain(data: bytes, chain_spec: str) -> tuple[EncodedImage, list[str]]:
    """Parse and run a pipe-separated effect chain like ``pixelate 8 | duotone | spin 45``."""
    raw_steps = [s.strip() for s in chain_spec.split("|") if s.strip()]
    if not raw_steps:
        msg = "Provide at least one effect, e.g. `pixelate 8 | duotone | spin 45`."
        raise ImageValidationError(msg)
    if len(raw_steps) > 8:
        msg = "An effect chain can have at most 8 steps."
        raise ImageValidationError(msg)
    parsed = [_parse_step_token(s) for s in raw_steps]
    frames = load_frames(data, max_frames=MAX_OUTPUT_FRAMES, max_dim=MAX_WORKING_DIMENSION)

    def _run_chain(frame: Image.Image, _index: int) -> Image.Image:
        cur = frame
        for func, pos_args, name in parsed:
            try:
                cur = func(cur, *pos_args)
            except TypeError as exc:
                msg = f"Invalid arguments for `{name}` in chain: {exc}"
                raise ImageValidationError(msg) from exc
        return cur

    result = map_frames(frames, _run_chain)
    names = [name for _, _, name in parsed]
    enc = encode_image(result[0].image) if len(result) == 1 else encode_animation(result)
    return enc, names


def render_contact_sheet(
    data: bytes,
    effects: Sequence[str] | None = None,
    thumb_size: int = 136,
) -> EncodedImage:
    """Render a labeled contact sheet showing an avatar run through multiple effects."""
    base = load_image(data, max_dim=256)
    thumb_px = clamp_int(thumb_size, 80, 200, "thumb_size")
    small = resize_rgba(base, (thumb_px, thumb_px))
    chosen = (
        list(effects)
        if effects
        else [
            "pixelate",
            "glitch",
            "invert",
            "grayscale",
            "posterize",
            "duotone",
            "swirl",
            "bulge",
            "fisheye",
            "ripple",
            "crt",
            "vhs",
            "chromatic",
            "halftone",
            "gameboy",
            "cartoon",
            "sketch",
            "sepia",
            "solarize",
            "thermal",
            "neon",
            "deepfry",
            "kaleidoscope",
            "stainedglass",
        ]
    )
    n = len(chosen)
    cols = min(6, max(1, math.ceil(math.sqrt(n))))
    rows = math.ceil(n / cols)
    pad = 10
    label_h = 22
    cw = cols * (thumb_px + pad) + pad
    ch = rows * (thumb_px + label_h + pad) + pad
    canvas = Image.new("RGBA", (cw, ch), (18, 20, 26, 255))
    draw = ImageDraw.Draw(canvas)
    font = load_font(13, bold=True)
    for idx, eff in enumerate(chosen):
        r, c = divmod(idx, cols)
        x = pad + c * (thumb_px + pad)
        y = pad + r * (thumb_px + label_h + pad)
        func = EFFECT_REGISTRY.get(eff, invert)
        processed = resize_rgba(func(small), (thumb_px, thumb_px))
        canvas.alpha_composite(processed, (x, y))
        draw.text((x + 4, y + thumb_px + 3), eff, fill=(225, 230, 240, 255), font=font)
    return encode_image(fit_within(canvas, MAX_OUTPUT_DIMENSION))


def render_before_after(
    data: bytes,
    effect: str,
    params: dict[str, object] | None = None,
    mode: str = "side",
) -> EncodedImage:
    """Render a Before/After comparison as a side-by-side PNG or wiping slider GIF."""
    mode = validate_choice(mode, ("side", "slider"), "mode")
    if effect not in EFFECT_REGISTRY:
        msg = f"Unknown effect {effect!r}."
        raise ImageValidationError(msg)
    before = load_image(data, max_dim=480)
    after = resize_rgba(EFFECT_REGISTRY[effect](before, **(params or {})), before.size)
    w, h = before.size
    font = load_font(max(14, w // 22), bold=True)
    if mode == "side":
        gap = 12
        header = 32
        canvas = Image.new("RGBA", (w * 2 + gap * 3, h + header + gap), (20, 22, 28, 255))
        draw = ImageDraw.Draw(canvas)
        draw.text((gap + 6, 6), "Before", fill=(210, 215, 225, 255), font=font)
        draw.text((w + gap * 2 + 6, 6), f"After ({effect})", fill=(115, 215, 255, 255), font=font)
        canvas.alpha_composite(before, (gap, header))
        canvas.alpha_composite(after, (w + gap * 2, header))
        return encode_image(canvas)
    frames: list[Frame] = []
    n_steps = 16
    for i in range(n_steps):
        wave = 0.5 - 0.5 * math.cos(2.0 * math.pi * i / n_steps)
        split_x = clamp_int(round(w * wave), 2, w - 2)
        comp = after.copy()
        comp.paste(before.crop((0, 0, split_x, h)), (0, 0))
        draw = ImageDraw.Draw(comp)
        draw.line([(split_x, 0), (split_x, h)], fill=(255, 255, 255, 240), width=3)
        frames.append(Frame(comp, 65))
    return encode_animation(frames)
