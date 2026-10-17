"""Procedural image generators and avatar compositions.

Generators return ``PIL.Image.Image`` objects (RGB for pure generators, RGBA for
avatar compositions). They all accept ``seed`` (same seed + parameters \N{RIGHTWARDS ARROW} the
same pixels) and ``deadline`` (cooperative timeout; ignored by cheap ones).
Randomness comes exclusively from :func:`make_rng`.
"""

from __future__ import annotations

import colorsys
import math
from collections.abc import Callable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .image_utils import EncodedImage, apply_mask, center_crop_square, crop_circle, encode_image, load_image, make_rng, resize_rgba, rounded_mask
from .image_validators import (
    MAX_HEAVY_DIMENSION,
    MAX_OUTPUT_DIMENSION,
    Color,
    ImageValidationError,
    clamp_dimensions,
    clamp_float,
    clamp_int,
    validate_choice,
)

GRADIENT_KINDS = ("linear", "radial", "multicolor")
NOISE_KINDS = ("gray", "color", "value", "fractal")
FRACTAL_KINDS = ("mandelbrot", "julia")
SYMMETRIES = ("radial", "mirror", "none")
PATTERN_KINDS = ("checkerboard", "waves", "concentric", "tiles")
FRAME_STYLES = ("neon", "plasma", "geometric", "rainbow", "gold")
COLLAGE_LAYOUTS = ("grid", "row", "column", "circle")
MAX_COLLAGE_IMAGES = 36

_JULIA_CONSTANTS = [
    (-0.8, 0.156),
    (0.285, 0.01),
    (-0.4, 0.6),
    (-0.70176, -0.3842),
    (0.355, 0.355),
    (-0.835, -0.2321),
]


def random_palette(rng: np.random.Generator, count: int) -> list[Color]:
    """Return ``count`` harmonious colours using golden-ratio hue steps."""
    count = clamp_int(count, 1, 16, "count")
    hue = float(rng.random())
    palette: list[Color] = []
    for _ in range(count):
        hue = (hue + 0.618033988749895) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, float(rng.uniform(0.55, 0.95)), float(rng.uniform(0.65, 1.0)))
        palette.append((round(r * 255), round(g * 255), round(b * 255)))
    return palette


def _resolve_palette(colors: Sequence[Color] | None, rng: np.random.Generator, default_count: int) -> list[Color]:
    if not colors:
        return random_palette(rng, default_count)
    if len(colors) > 16:
        msg = "Use at most 16 colours."
        raise ImageValidationError(msg)
    palette: list[Color] = []
    for color in colors:
        if len(color) != 3:
            msg = "Colours must have exactly three RGB components."
            raise ImageValidationError(msg)
        palette.append(tuple(clamp_int(c, 0, 255, "colour") for c in color))  # type: ignore[arg-type]
    return palette


def _lerp_palette(t: np.ndarray, colors: Sequence[Color]) -> np.ndarray:
    """Map ``t`` in 0\N{TWO DOT LEADER}1 onto evenly spaced colour stops \N{RIGHTWARDS ARROW} float32 ``(..., 3)``."""
    cols = np.asarray(colors, dtype=np.float32)
    if len(cols) == 1:
        cols = np.repeat(cols, 2, axis=0)
    stops = np.linspace(0.0, 1.0, len(cols))
    t = np.clip(t, 0.0, 1.0)
    return np.stack([np.interp(t, stops, cols[:, i]) for i in range(3)], axis=-1).astype(np.float32)


def _cosine_palette(t: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Smooth cyclic palette ``a + b\N{MIDDLE DOT}cos(2\N{GREEK SMALL LETTER PI}(c\N{MIDDLE DOT}t + d))`` with seeded coefficients."""
    a, b = rng.uniform(0.35, 0.65, 3), rng.uniform(0.3, 0.5, 3)
    c, d = rng.uniform(0.8, 1.6, 3), rng.uniform(0.0, 1.0, 3)
    rgb = a + b * np.cos(2 * math.pi * (c * t[..., None] + d))
    return (np.clip(rgb, 0.0, 1.0) * 255).astype(np.float32)


def _to_rgb_image(rgb: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(np.rint(rgb), 0, 255).astype(np.uint8))


def _grid(w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Return broadcastable pixel-centre coordinate arrays ``xs (1,w)`` and ``ys (h,1)``."""
    return (
        (np.arange(w, dtype=np.float32) + 0.5)[None, :],
        (np.arange(h, dtype=np.float32) + 0.5)[:, None],
    )


def gradient(
    width: int = 768,
    height: int = 768,
    kind: str = "linear",
    colors: Sequence[Color] | None = None,
    angle: float = 0.0,
    seed: int | None = None,
) -> Image.Image:
    """Linear, radial or multicolour gradient with light dithering (no banding).

    Args:
        kind: ``linear`` (2 colours by default), ``radial`` (2) or ``multicolor`` (5).
        colors: Optional explicit stops; random harmonious colours otherwise.
        angle: Direction in degrees for linear / multicolor gradients.
    """
    w, h = clamp_dimensions(width, height)
    kind = validate_choice(kind, GRADIENT_KINDS, "kind")
    theta = math.radians(clamp_float(angle, -360.0, 360.0, "angle"))
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 5 if kind == "multicolor" else 2)
    xs, ys = _grid(w, h)
    xs, ys = xs - w / 2, ys - h / 2
    if kind == "radial":
        t = np.hypot(xs, ys) / (math.hypot(w, h) / 2)
    else:
        dx, dy = math.cos(theta), math.sin(theta)
        extent = max(abs(w * dx) + abs(h * dy), 1e-6)
        t = (xs * dx + ys * dy) / extent + 0.5
    rgb = _lerp_palette(t, palette)
    rgb += rng.random(rgb.shape, dtype=np.float32) - 0.5
    return _to_rgb_image(rgb)


def _value_noise(rng: np.random.Generator, h: int, w: int, cell: int) -> np.ndarray:
    """Smooth value noise in 0\N{TWO DOT LEADER}1: a coarse random grid upsampled bicubically."""
    gh, gw = h // cell + 3, w // cell + 3
    grid = rng.random((gh, gw), dtype=np.float32)
    big = Image.fromarray(grid).resize((gw * cell, gh * cell), Image.Resampling.BICUBIC)
    return np.clip(np.asarray(big, dtype=np.float32)[:h, :w], 0.0, 1.0)


def noise(
    width: int = 768,
    height: int = 768,
    kind: str = "fractal",
    scale: int = 48,
    octaves: int = 4,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Random or smooth noise textures.

    Args:
        kind: ``gray`` / ``color`` (per-pixel static), ``value`` (smooth blobs) or
            ``fractal`` (layered smooth noise).
        scale: Feature size in pixels for ``value``/``fractal`` (2\N{TWO DOT LEADER}256).
        octaves: Layers for ``fractal`` (1\N{TWO DOT LEADER}8).
        colors: Optional palette for ``value``/``fractal`` (default grayscale).
    """
    w, h = clamp_dimensions(width, height)
    kind = validate_choice(kind, NOISE_KINDS, "kind")
    rng = make_rng(seed)
    if kind == "gray":
        return Image.fromarray(rng.integers(0, 256, (h, w), dtype=np.uint8)).convert("RGB")
    if kind == "color":
        return Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8))
    cell0 = clamp_int(scale, 2, 256, "scale")
    layers = 1 if kind == "value" else clamp_int(octaves, 1, 8, "octaves")
    field = np.zeros((h, w), dtype=np.float32)
    amplitude, total = 1.0, 0.0
    for octave in range(layers):
        field += amplitude * _value_noise(rng, h, w, max(2, cell0 // (2**octave)))
        total += amplitude
        amplitude *= 0.5
    field /= total
    lo, hi = float(field.min()), float(field.max())
    if hi - lo > 1e-6:
        field = (field - lo) / (hi - lo)
    if colors:
        return _to_rgb_image(_lerp_palette(field, _resolve_palette(colors, rng, 2)))
    return _to_rgb_image(np.repeat(field[..., None] * 255, 3, axis=2))


def plasma(
    width: int = 768,
    height: int = 768,
    complexity: int = 5,
    scale: float = 1.0,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Classic plasma: a sum of random sine waves and radial ripples.

    Args:
        complexity: Number of wave terms (1\N{TWO DOT LEADER}12).
        scale: Frequency multiplier (0.25\N{TWO DOT LEADER}8).
        colors: Optional palette; otherwise a seeded cosine palette is used.
    """
    w, h = clamp_dimensions(width, height)
    n = clamp_int(complexity, 1, 12, "complexity")
    sc = clamp_float(scale, 0.25, 8.0, "scale")
    rng = make_rng(seed)
    xs, ys = _grid(w, h)
    u, v = xs / max(w, h), ys / max(w, h)
    field = np.zeros((h, w), dtype=np.float32)
    tau = 2 * math.pi * sc
    for _ in range(n):
        fx, fy, phase = rng.uniform(1.0, 6.0), rng.uniform(1.0, 6.0), rng.uniform(0, tau)
        field += np.sin(tau * (fx * u + fy * v) + phase)
    for _ in range(n // 2 + 1):
        cx, cy = rng.uniform(0.0, w / max(w, h)), rng.uniform(0.0, h / max(w, h))
        f, phase = rng.uniform(1.0, 5.0), rng.uniform(0, tau)
        field += np.sin(tau * f * np.hypot(u - cx, v - cy) + phase)
    lo, hi = float(field.min()), float(field.max())
    field = (field - lo) / (hi - lo) if hi - lo > 1e-6 else np.zeros_like(field)
    if colors:
        ping_pong = 1.0 - np.abs(2.0 * field - 1.0)
        return _to_rgb_image(_lerp_palette(ping_pong, _resolve_palette(colors, rng, 2)))
    return _to_rgb_image(_cosine_palette(field, rng))


def fractal(
    width: int = 768,
    height: int = 768,
    kind: str = "mandelbrot",
    iterations: int = 100,
    zoom: float = 1.0,
    center: tuple[float, float] | None = None,
    julia_c: tuple[float, float] | None = None,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Mandelbrot or Julia fractal with smooth (band-free) colouring.

    Only still-iterating points are updated each step, so cost shrinks as pixels
    escape. The interior of the set is black.

    Args:
        iterations: 10\N{TWO DOT LEADER}400 maximum iterations.
        zoom: 0.1\N{TWO DOT LEADER}100000 magnification around ``center``.
        center: View centre ``(re, im)``; defaults depend on ``kind``.
        julia_c: Julia constant; chosen from famous values using ``seed`` if omitted.
    """
    w, h = clamp_dimensions(width, height, max_dim=MAX_HEAVY_DIMENSION)
    kind = validate_choice(kind, FRACTAL_KINDS, "kind")
    max_iter = clamp_int(iterations, 10, 400, "iterations")
    zoom_f = clamp_float(zoom, 0.1, 100_000.0, "zoom")
    rng = make_rng(seed)
    default_center = (-0.5, 0.0) if kind == "mandelbrot" else (0.0, 0.0)
    cx, cy = center if center is not None else default_center
    cx, cy = clamp_float(cx, -4.0, 4.0, "center"), clamp_float(cy, -4.0, 4.0, "center")
    half_w = 1.5 / zoom_f
    half_h = half_w * h / w
    xs = np.linspace(cx - half_w, cx + half_w, w)
    ys = np.linspace(cy - half_h, cy + half_h, h)
    grid = (xs[None, :] + 1j * ys[:, None]).ravel()

    is_mandelbrot = kind == "mandelbrot"
    if is_mandelbrot:
        z, c = np.zeros_like(grid), grid.copy()
    else:
        const = julia_c if julia_c is not None else _JULIA_CONSTANTS[int(rng.integers(len(_JULIA_CONSTANTS)))]
        z, c = grid.copy(), complex(clamp_float(const[0], -2, 2, "julia_c"), clamp_float(const[1], -2, 2, "julia_c"))

    smooth = np.zeros(grid.size, dtype=np.float32)
    inside = np.ones(grid.size, dtype=bool)
    idx = np.arange(grid.size)
    for i in range(max_iter):
        z = z * z + c
        mag2 = z.real * z.real + z.imag * z.imag
        escaped = mag2 > 256.0
        if escaped.any():
            hit = idx[escaped]
            smooth[hit] = i + 1 - np.log2(0.5 * np.log(mag2[escaped]))
            inside[hit] = False
            keep = ~escaped
            idx, z = idx[keep], z[keep]
            if is_mandelbrot:
                c = c[keep]
            if idx.size == 0:
                break

    t = np.clip(np.sqrt(np.clip(smooth, 0, None) / max_iter), 0.0, 1.0)
    if colors:
        palette = _resolve_palette(colors, rng, 2)
        rgb = _lerp_palette(1.0 - np.abs(2.0 * ((t * 3.0) % 1.0) - 1.0), palette)
    else:
        rgb = _cosine_palette(t * 2.5, rng)
    rgb[inside] = 0
    return _to_rgb_image(rgb.reshape(h, w, 3))


def voronoi(
    width: int = 768,
    height: int = 768,
    points: int = 40,
    colors: Sequence[Color] | None = None,
    edges: bool = True,
    seed: int | None = None,
) -> Image.Image:
    """Voronoi cell pattern.

    Args:
        points: Number of seed points (2\N{TWO DOT LEADER}300).
        colors: Palette cells are drawn from (random harmonious palette otherwise).
        edges: Darken cell borders.
    """
    w, h = clamp_dimensions(width, height, max_dim=MAX_HEAVY_DIMENSION)
    n = clamp_int(points, 2, 300, "points")
    rng = make_rng(seed)
    palette = np.asarray(_resolve_palette(colors, rng, min(n, 8)), dtype=np.float32)
    px = rng.uniform(0, w, n).astype(np.float32)
    py = rng.uniform(0, h, n).astype(np.float32)
    xs, ys = _grid(w, h)
    best = np.full((h, w), np.inf, dtype=np.float32)
    label = np.zeros((h, w), dtype=np.int32)
    for i in range(n):
        dist = (xs - px[i]) ** 2 + (ys - py[i]) ** 2
        closer = dist < best
        best = np.where(closer, dist, best)
        label = np.where(closer, i, label)
    cell_colors = palette[rng.integers(0, len(palette), n)]
    cell_colors = cell_colors * rng.uniform(0.8, 1.1, (n, 1)).astype(np.float32)
    rgb = cell_colors[label]
    if edges:
        border = np.zeros((h, w), dtype=bool)
        border[:, 1:] |= label[:, 1:] != label[:, :-1]
        border[1:, :] |= label[1:, :] != label[:-1, :]
        rgb[border] *= 0.3
    return _to_rgb_image(rgb)


def geometric(
    width: int = 768,
    height: int = 768,
    shapes: int = 28,
    symmetry: str = "radial",
    folds: int = 6,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Abstract geometric art with kaleidoscopic symmetry.

    Random circles, rectangles, polygons, rings and bars are drawn on a layer,
    then rotated / mirrored copies are alpha-composited over a dark background.

    Args:
        shapes: 1\N{TWO DOT LEADER}200 shapes.
        symmetry: ``radial`` (rotations + mirror), ``mirror`` (4-way) or ``none``.
        folds: Rotation count for radial symmetry (2\N{TWO DOT LEADER}16).
    """
    w, h = clamp_dimensions(width, height)
    count = clamp_int(shapes, 1, 200, "shapes")
    sym = validate_choice(symmetry, SYMMETRIES, "symmetry")
    n_folds = clamp_int(folds, 2, 16, "folds")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 5)
    unit = min(w, h)

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(count):
        cx, cy = float(rng.uniform(0, w)), float(rng.uniform(0, h))
        r = float(rng.uniform(0.03, 0.22)) * unit
        base = palette[int(rng.integers(len(palette)))]
        fill = (*base, int(rng.integers(130, 256)))
        kind = int(rng.integers(0, 5))
        if kind == 0:
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
        elif kind == 1:
            rw, rh = r * float(rng.uniform(0.5, 1.6)), r * float(rng.uniform(0.5, 1.6))
            draw.rectangle((cx - rw, cy - rh, cx + rw, cy + rh), fill=fill)
        elif kind == 2:
            draw.regular_polygon((cx, cy, r), int(rng.integers(3, 8)), rotation=float(rng.uniform(0, 360)), fill=fill)
        elif kind == 3:
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=fill, width=max(2, int(r * 0.18)))
        else:
            ang = float(rng.uniform(0, 2 * math.pi))
            draw.line(
                (cx, cy, cx + math.cos(ang) * r * 2, cy + math.sin(ang) * r * 2),
                fill=fill,
                width=max(2, int(r * 0.2)),
            )

    background = tuple(int(c * 0.18) for c in palette[0])
    canvas = Image.new("RGBA", (w, h), (*background, 255))
    if sym == "none":
        canvas.alpha_composite(layer)
    elif sym == "mirror":
        # Exact 4-way symmetry: render once, then reflect the top-left quadrant.
        canvas.alpha_composite(layer)
        pixels = np.asarray(canvas.convert("RGB"))
        rows = np.minimum(np.arange(h), h - 1 - np.arange(h))
        cols = np.minimum(np.arange(w), w - 1 - np.arange(w))
        return Image.fromarray(np.ascontiguousarray(pixels[rows][:, cols]))
    else:
        flipped = layer.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        for k in range(n_folds):
            for source in (layer, flipped):
                canvas.alpha_composite(source.rotate(360.0 / n_folds * k, resample=Image.Resampling.BICUBIC))
    return canvas.convert("RGB")


def pattern(
    width: int = 768,
    height: int = 768,
    kind: str = "checkerboard",
    cell_size: int = 64,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Tiled patterns: checkerboard, waves, concentric rings or motif tiles.

    Args:
        cell_size: Cell / wavelength / ring width in pixels (4\N{TWO DOT LEADER}256).
        colors: Palette (default: 2-3 random harmonious colours).
    """
    w, h = clamp_dimensions(width, height)
    kind = validate_choice(kind, PATTERN_KINDS, "kind")
    cs = clamp_int(cell_size, 4, 256, "cell_size")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 3 if kind in ("concentric", "tiles") else 2)
    pal = np.asarray(palette, dtype=np.float32)
    xs, ys = _grid(w, h)
    if kind == "checkerboard":
        idx = (np.floor(xs / cs) + np.floor(ys / cs)).astype(np.int64) % len(pal)
        rgb = pal[idx]
    elif kind == "concentric":
        r = np.hypot(xs - w / 2, ys - h / 2)
        rgb = pal[(np.floor(r / cs).astype(np.int64)) % len(pal)]
    elif kind == "waves":
        amp = float(rng.uniform(1.0, 3.0))
        phase = 2 * math.pi * (ys / cs + 0.35 * np.sin(2 * math.pi * xs / (cs * 2.0)) * amp)
        rgb = _lerp_palette(0.5 + 0.5 * np.sin(phase), palette)
    else:
        tile = Image.new("RGB", (cs, cs), tuple(palette[0]))
        d = ImageDraw.Draw(tile)
        motif = int(rng.integers(0, 3))
        inner, accent = tuple(palette[1 % len(palette)]), tuple(palette[2 % len(palette)])
        m = cs / 2
        if motif == 0:
            d.ellipse((cs * 0.15, cs * 0.15, cs * 0.85, cs * 0.85), fill=inner)
            d.ellipse((cs * 0.35, cs * 0.35, cs * 0.65, cs * 0.65), fill=accent)
        elif motif == 1:
            d.polygon([(m, cs * 0.05), (cs * 0.95, m), (m, cs * 0.95), (cs * 0.05, m)], fill=inner)
            d.rectangle((cs * 0.4, cs * 0.4, cs * 0.6, cs * 0.6), fill=accent)
        else:
            d.rectangle((cs * 0.4, 0, cs * 0.6, cs), fill=inner)
            d.rectangle((0, cs * 0.4, cs, cs * 0.6), fill=inner)
            d.ellipse((cs * 0.38, cs * 0.38, cs * 0.62, cs * 0.62), fill=accent)
        reps = (math.ceil(h / cs), math.ceil(w / cs), 1)
        rgb = np.tile(np.asarray(tile, dtype=np.float32), reps)[:h, :w]
    return _to_rgb_image(rgb)


GENERATORS: dict[str, Callable[..., Image.Image]] = {
    "gradient": gradient,
    "noise": noise,
    "plasma": plasma,
    "fractal": fractal,
    "voronoi": voronoi,
    "geometric": geometric,
    "pattern": pattern,
}


def _ring_mask(size: int, outer: float, inner: float, supersample: int = 4) -> Image.Image:
    big = size * supersample
    mask = Image.new("L", (big, big), 0)
    d = ImageDraw.Draw(mask)
    c = big / 2
    for diameter, value in ((outer, 255), (inner, 0)):
        rad = diameter * supersample / 2
        d.ellipse((c - rad, c - rad, c + rad, c + rad), fill=value)
    return mask.resize((size, size), Image.Resampling.LANCZOS)


def avatar_frame(
    avatar: Image.Image,
    style: str = "neon",
    size: int = 512,
    seed: int | None = None,
) -> Image.Image:
    """Place a circular avatar inside a decorated, generated frame.

    Args:
        style: ``neon`` (glowing ring), ``plasma``, ``geometric``, ``rainbow`` or ``gold``.
        size: Output edge length (128\N{TWO DOT LEADER}1024).
    Returns:
        An opaque-background RGBA ``size \N{MULTIPLICATION SIGN} size`` image.
    """
    style = validate_choice(style, FRAME_STYLES, "style")
    s = clamp_int(size, 128, 1024, "size")

    if style == "plasma":
        bg = plasma(s, s, seed=seed)
    elif style == "geometric":
        bg = geometric(s, s, shapes=24, seed=seed)
    elif style == "rainbow":
        bg = gradient(s, s, "radial", colors=[(60, 25, 100), (12, 8, 30)], seed=seed)
    elif style == "gold":
        bg = gradient(s, s, "linear", colors=[(46, 34, 12), (10, 8, 4)], angle=45, seed=seed)
    else:
        bg = gradient(s, s, "radial", colors=[(30, 30, 64), (5, 5, 16)], seed=seed)
    canvas = bg.convert("RGBA")

    diameter = int(s * 0.66)
    ring_w = max(4, int(s * 0.035))
    outer = diameter + 2 * ring_w
    xs, ys = _grid(s, s)
    if style == "rainbow":
        t = (np.arctan2(ys - s / 2, xs - s / 2) / (2 * math.pi)) % 1.0
        rainbow = [(255, 40, 40), (255, 200, 0), (40, 230, 120), (0, 160, 255), (170, 0, 255), (255, 40, 40)]
        fill = Image.fromarray(np.clip(np.rint(_lerp_palette(t, rainbow)), 0, 255).astype(np.uint8)).convert("RGBA")
    elif style == "gold":
        t = (xs + ys) / (2 * s)
        gold = [(255, 236, 150), (201, 150, 40), (255, 225, 120), (150, 100, 20), (255, 236, 150)]
        fill = Image.fromarray(np.clip(np.rint(_lerp_palette(t, gold)), 0, 255).astype(np.uint8)).convert("RGBA")
    elif style == "neon":
        fill = Image.new("RGBA", (s, s), (0, 255, 230, 255))
    else:
        fill = Image.new("RGBA", (s, s), (255, 255, 255, 255))
    ring = apply_mask(fill, _ring_mask(s, outer, diameter))
    if style == "neon":
        glow = ring.filter(ImageFilter.GaussianBlur(s * 0.025))
        canvas.alpha_composite(glow)
        canvas.alpha_composite(glow)
    canvas.alpha_composite(ring)
    offset = (s - diameter) // 2
    canvas.alpha_composite(crop_circle(avatar, diameter), dest=(offset, offset))
    return canvas


def _grid_positions(n: int, cols: int, tile: int, gap: int) -> tuple[list[tuple[int, int]], tuple[int, int]]:
    rows = math.ceil(n / cols)
    positions = []
    for i in range(n):
        r, c = divmod(i, cols)
        in_row = cols if r < rows - 1 else n - (rows - 1) * cols
        x0 = gap + (cols - in_row) * (tile + gap) // 2
        positions.append((x0 + c * (tile + gap), gap + r * (tile + gap)))
    return positions, (cols * tile + (cols + 1) * gap, rows * tile + (rows + 1) * gap)


def _layout(n: int, layout: str, tile: int, gap: int) -> tuple[list[tuple[int, int]], tuple[int, int]]:
    if layout == "row":
        return _grid_positions(n, n, tile, gap)
    if layout == "column":
        return _grid_positions(n, 1, tile, gap)
    if layout == "grid":
        return _grid_positions(n, math.ceil(math.sqrt(n)), tile, gap)
    radius = 0.0 if n == 1 else max(tile * 0.9, (tile + gap) * n / (2 * math.pi))
    side = int(2 * radius + tile + 2 * gap)
    centre = side / 2
    positions = [
        (
            round(centre + radius * math.cos(-math.pi / 2 + 2 * math.pi * i / n) - tile / 2),
            round(centre + radius * math.sin(-math.pi / 2 + 2 * math.pi * i / n) - tile / 2),
        )
        for i in range(n)
    ]
    return positions, (side, side)


def pfp_collage(
    images: Sequence[Image.Image],
    layout: str = "grid",
    tile: int = 256,
    gap: int = 8,
    background: Color = (24, 24, 30),
    shuffle: bool = False,
    seed: int | None = None,
) -> Image.Image:
    """Combine up to 36 avatars into a collage with rounded tiles.

    The tile size shrinks automatically so the canvas never exceeds the output
    dimension limit.

    Args:
        layout: ``grid`` (last row centred), ``row``, ``column`` or ``circle``.
        shuffle: Randomise order using ``seed``.
    """
    if not images:
        msg = "At least one image is required for a collage."
        raise ImageValidationError(msg)
    if len(images) > MAX_COLLAGE_IMAGES:
        msg = f"A collage can contain at most {MAX_COLLAGE_IMAGES} images."
        raise ImageValidationError(msg)
    layout = validate_choice(layout, COLLAGE_LAYOUTS, "layout")
    tile_px = clamp_int(tile, 32, 512, "tile")
    gap_px = clamp_int(gap, 0, 64, "gap")
    bg = tuple(clamp_int(c, 0, 255, "background") for c in background)
    order = list(range(len(images)))
    if shuffle:
        make_rng(seed).shuffle(order)
    n = len(images)
    positions, (cw, ch) = _layout(n, layout, tile_px, gap_px)
    while max(cw, ch) > MAX_OUTPUT_DIMENSION and tile_px > 32:
        tile_px = max(32, int(tile_px * 0.85))
        positions, (cw, ch) = _layout(n, layout, tile_px, gap_px)
    canvas = Image.new("RGBA", (cw, ch), (*bg, 255))
    mask = rounded_mask(tile_px, tile_px * 0.2)
    for slot, source_index in enumerate(order):
        thumb = resize_rgba(center_crop_square(images[source_index]), (tile_px, tile_px))
        canvas.alpha_composite(apply_mask(thumb, mask), dest=positions[slot])
    return canvas


def render_generator(name: str, params: dict[str, object] | None = None) -> EncodedImage:
    """Run a registered generator and encode the result as PNG."""
    try:
        func = GENERATORS[name]
    except KeyError:
        msg = f"Unknown generator {name!r}."
        raise ImageValidationError(msg) from None
    return encode_image(func(**(params or {})))


def render_avatar_frame(data: bytes, style: str = "neon", seed: int | None = None) -> EncodedImage:
    """Decode avatar bytes (first frame), frame it and encode PNG."""
    avatar = load_image(data)
    return encode_image(avatar_frame(avatar, style=style, seed=seed))


def render_collage(
    datas: Sequence[bytes],
    layout: str = "grid",
    seed: int | None = None,
) -> EncodedImage:
    """Decode several avatars and encode a collage as PNG."""
    images = [load_image(d, max_dim=512) for d in datas]
    return encode_image(pfp_collage(images, layout=layout, shuffle=seed is not None, seed=seed))
