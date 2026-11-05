from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
from PIL import Image, ImageDraw

from .image_effects import glitch, hue_shift, pixelate, spin, swirl
from .image_utils import EncodedImage, Frame, encode_animation, from_array, load_frames, make_rng, resize_rgba, to_array
from .image_validators import MAX_OUTPUT_FRAMES, clamp_int, validate_choice

ANIMATION_KINDS = ("spin", "pixelate", "rainbow", "shake", "bounce", "pulse", "petpet", "wiggle", "zoom", "sweep")
AnimationHandler = Callable[..., Image.Image]


def _spin(img: Image.Image, t: float, **_: object) -> Image.Image:
    return spin(img, angle=t * 360.0, expand=False)


def _pixelate(img: Image.Image, t: float, **_: object) -> Image.Image:
    wave = 0.5 - 0.5 * math.cos(2.0 * math.pi * t)
    return pixelate(img, max(2, round(2 + wave * 26)))


def _rainbow(img: Image.Image, t: float, **_: object) -> Image.Image:
    return hue_shift(img, degrees=t * 360.0)


def _shake(img: Image.Image, t: float, rng: np.random.Generator, **_: object) -> Image.Image:
    w, h = img.size
    dx = int(rng.integers(-max(2, w // 18), max(3, w // 18) + 1))
    dy = int(rng.integers(-max(2, h // 18), max(3, h // 18) + 1))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(img, (dx, dy))
    return canvas


def _bounce(img: Image.Image, t: float, **_: object) -> Image.Image:
    w, h = img.size
    arc = abs(math.sin(math.pi * t))
    squash = 1.0 - 0.18 * math.cos(2.0 * math.pi * t)
    nw = max(8, round(w * (2.0 - squash)))
    nh = max(8, round(h * squash))
    scaled = resize_rgba(img, (min(w, nw), min(h, nh)))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox = (w - scaled.width) // 2
    oy = max(0, h - scaled.height - round(arc * h * 0.25))
    canvas.alpha_composite(scaled, (ox, oy))
    return canvas


def _pulse(img: Image.Image, t: float, **_: object) -> Image.Image:
    w, h = img.size
    beat = math.sin(2.0 * math.pi * t) ** 4
    scale = 0.84 + 0.16 * beat
    nw, nh = max(8, round(w * scale)), max(8, round(h * scale))
    scaled = resize_rgba(img, (nw, nh))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(scaled, ((w - nw) // 2, (h - nh) // 2))
    return canvas


def _petpet(img: Image.Image, t: float, **_: object) -> Image.Image:
    w, h = img.size
    s = math.sin(2.0 * math.pi * t)
    sw = max(8, round(w * (0.82 + 0.10 * s)))
    sh = max(8, round(h * (0.76 - 0.12 * s)))
    avatar = resize_rgba(img, (min(w, sw), min(h, sh)))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ax = (w - avatar.width) // 2
    ay = h - avatar.height
    canvas.alpha_composite(avatar, (ax, ay))
    draw = ImageDraw.Draw(canvas)
    hx = w // 2 + round(math.cos(2.0 * math.pi * t) * w * 0.08)
    hy = max(6, ay - round(h * 0.04))
    hr_x, hr_y = max(12, w // 4), max(8, h // 9)
    draw.ellipse((hx - hr_x, hy - hr_y, hx + hr_x, hy + hr_y), fill=(255, 224, 178, 235), outline=(90, 60, 40, 255), width=2)
    return canvas


def _wiggle(img: Image.Image, t: float, **_: object) -> Image.Image:
    w, h = img.size
    arr = to_array(img)
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    sx = xs + (w * 0.04) * np.sin(2.0 * math.pi * (ys / max(h * 0.5, 1.0) + t))
    return from_array(_sample_bilinear(arr, sx, ys))


def _sample_bilinear(arr: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
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


def _zoom(img: Image.Image, t: float, **_: object) -> Image.Image:
    w, h = img.size
    scale = 1.0 + 1.2 * t
    cw, ch = max(8, round(w / scale)), max(8, round(h / scale))
    cropped = img.crop(((w - cw) // 2, (h - ch) // 2, (w + cw) // 2, (h + ch) // 2))
    return resize_rgba(cropped, (w, h))


def _sweep(img: Image.Image, t: float, sweep_effect: str, seed: int, frame_index: int, **_: object) -> Image.Image:
    wave = 0.5 - 0.5 * math.cos(2.0 * math.pi * t)
    handlers = {
        "swirl": lambda: swirl(img, strength=(wave * 2.0 - 1.0) * 6.0),
        "pixelate": lambda: pixelate(img, pixel_size=max(2, round(2 + wave * 28))),
        "hue": lambda: hue_shift(img, degrees=t * 360.0),
        "glitch": lambda: glitch(img, intensity=0.05 + 0.85 * wave, seed=seed + frame_index),
    }
    return handlers.get(sweep_effect, handlers["glitch"])()


_ANIMATION_HANDLERS: dict[str, AnimationHandler] = {
    "spin": _spin,
    "pixelate": _pixelate,
    "rainbow": _rainbow,
    "shake": _shake,
    "bounce": _bounce,
    "pulse": _pulse,
    "petpet": _petpet,
    "wiggle": _wiggle,
    "zoom": _zoom,
    "sweep": _sweep,
}


def render_animated_effect(
    data: bytes,
    kind: str = "spin",
    *,
    frames_count: int = 16,
    duration_ms: int = 60,
    sweep_effect: str = "glitch",
    seed: int | None = None,
) -> EncodedImage:
    """Generate a looping GIF animation from a static or animated image."""
    kind = validate_choice(kind, ANIMATION_KINDS, "kind")
    n = clamp_int(frames_count, 6, MAX_OUTPUT_FRAMES, "frames_count")
    dur = clamp_int(duration_ms, 25, 250, "duration_ms")
    src_frames = load_frames(data, max_frames=n, max_dim=320)
    rng = make_rng(seed)
    handler = _ANIMATION_HANDLERS[kind]
    actual_seed = seed if seed is not None else 42
    out_frames = [
        Frame(
            handler(
                src_frames[i % len(src_frames)].image,
                i / n,
                rng=rng,
                sweep_effect=sweep_effect,
                seed=actual_seed,
                frame_index=i,
            ),
            dur,
        )
        for i in range(n)
    ]
    return encode_animation(out_frames)
