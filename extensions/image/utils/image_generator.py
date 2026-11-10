from __future__ import annotations

import colorsys
import hashlib
import math
import textwrap
from collections.abc import Callable, Sequence

lazy import numpy as np
lazy from PIL import Image, ImageDraw, ImageFilter

from .image_utils import (
    EncodedImage,
    apply_mask,
    center_crop_square,
    crop_circle,
    encode_image,
    extract_dominant_palette,
    fit_within,
    from_array,
    join_rgb_alpha,
    load_font,
    load_image,
    make_rng,
    resize_rgba,
    rounded_mask,
    to_array,
)
from .image_validators import (
    MAX_HEAVY_DIMENSION,
    MAX_OUTPUT_DIMENSION,
    Color,
    ImageValidationError,
    clamp_dimensions,
    clamp_float,
    clamp_int,
    parse_hex_color,
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
    """Map ``t`` in 0..1 onto evenly spaced colour stops -> float32 ``(..., 3)``."""
    cols = np.asarray(colors, dtype=np.float32)
    if len(cols) == 1:
        cols = np.repeat(cols, 2, axis=0)
    stops = np.linspace(0.0, 1.0, len(cols))
    t = np.clip(t, 0.0, 1.0)
    return np.stack([np.interp(t, stops, cols[:, i]) for i in range(3)], axis=-1).astype(np.float32)


def _cosine_palette(t: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Smooth cyclic palette ``a + b*cos(2*pi*(c*t + d))`` with seeded coefficients."""
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
    """Linear, radial or multicolour gradient with light dithering."""
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
    """Smooth value noise in 0..1: a coarse random grid upsampled bicubically."""
    gh, gw = h // cell + 3, w // cell + 3
    grid = rng.random((gh, gw), dtype=np.float32)
    big = Image.fromarray(grid).resize((gw * cell, gh * cell), Image.Resampling.BICUBIC)
    return np.clip(np.asarray(big, dtype=np.float32)[:h, :w], 0.0, 1.0)


def _fbm_noise(rng: np.random.Generator, h: int, w: int, scale: int = 48, octaves: int = 4) -> np.ndarray:
    field = np.zeros((h, w), dtype=np.float32)
    amplitude, total = 1.0, 0.0
    for octave in range(octaves):
        field += amplitude * _value_noise(rng, h, w, max(2, scale // (2**octave)))
        total += amplitude
        amplitude *= 0.5
    field /= max(total, 1e-6)
    lo, hi = float(field.min()), float(field.max())
    return (field - lo) / (hi - lo) if hi - lo > 1e-6 else field


def noise(
    width: int = 768,
    height: int = 768,
    kind: str = "fractal",
    scale: int = 48,
    octaves: int = 4,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Random or smooth noise textures."""
    w, h = clamp_dimensions(width, height)
    kind = validate_choice(kind, NOISE_KINDS, "kind")
    rng = make_rng(seed)
    if kind == "gray":
        return Image.fromarray(rng.integers(0, 256, (h, w), dtype=np.uint8)).convert("RGB")
    if kind == "color":
        return Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8))
    cell0 = clamp_int(scale, 2, 256, "scale")
    layers = 1 if kind == "value" else clamp_int(octaves, 1, 8, "octaves")
    field = _fbm_noise(rng, h, w, cell0, layers)
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
    """Classic plasma: a sum of random sine waves and radial ripples."""
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
    """Mandelbrot or Julia fractal with smooth colouring."""
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
    """Voronoi cell pattern."""
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
    """Abstract geometric art with kaleidoscopic symmetry."""
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
    """Tiled patterns: checkerboard, waves, concentric rings or motif tiles."""
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


def flowfield(
    width: int = 768,
    height: int = 768,
    particles: int = 700,
    steps: int = 45,
    scale: int = 64,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Perlin/value-noise driven streamline flow field."""
    w, h = clamp_dimensions(width, height, max_dim=MAX_HEAVY_DIMENSION)
    n_part = clamp_int(particles, 50, 2000, "particles")
    n_steps = clamp_int(steps, 10, 120, "steps")
    sc = clamp_int(scale, 16, 256, "scale")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 5)
    angles = _fbm_noise(rng, h, w, scale=sc, octaves=3) * (4.0 * math.pi)
    bg = tuple(int(c * 0.12) for c in palette[0])
    canvas = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(canvas)
    px = rng.uniform(0, w - 1, n_part).astype(np.float32)
    py = rng.uniform(0, h - 1, n_part).astype(np.float32)
    step_len = max(2.0, min(w, h) * 0.009)
    for i in range(n_part):
        x, y = float(px[i]), float(py[i])
        pts = [(x, y)]
        col = palette[i % len(palette)]
        for _ in range(n_steps):
            ix, iy = int(np.clip(x, 0, w - 1)), int(np.clip(y, 0, h - 1))
            ang = float(angles[iy, ix])
            x += math.cos(ang) * step_len
            y += math.sin(ang) * step_len
            if x < 0 or x >= w or y < 0 or y >= h:
                break
            pts.append((x, y))
        if len(pts) > 1:
            draw.line(pts, fill=col, width=2)
    return canvas


def cellular(
    width: int = 768,
    height: int = 768,
    kind: str = "rule30",
    cell_size: int = 6,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Cellular automata: elementary rules (`rule30`, `rule110`, `rule90`) or Conway's `life`."""
    w, h = clamp_dimensions(width, height, max_dim=MAX_HEAVY_DIMENSION)
    kind = validate_choice(kind, ("rule30", "rule110", "rule90", "life"), "kind")
    cs = clamp_int(cell_size, 2, 32, "cell_size")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 3)
    gw, gh = max(8, w // cs), max(8, h // cs)
    grid = np.zeros((gh, gw), dtype=np.uint8)
    if kind == "life":
        state = (rng.random((gh, gw)) < 0.32).astype(np.uint8)
        age = state.copy().astype(np.float32)
        for _ in range(45):
            nbrs = sum(np.roll(np.roll(state, dy, axis=0), dx, axis=1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0))
            state = (((state == 1) & ((nbrs == 2) | (nbrs == 3))) | ((state == 0) & (nbrs == 3))).astype(np.uint8)
            age = np.where(state > 0, age + 1.0, age * 0.85)
        norm = age / max(float(age.max()), 1.0)
        rgb_small = _lerp_palette(norm, palette)
    else:
        rule_num = {"rule30": 30, "rule110": 110, "rule90": 90}[kind]
        grid[0, gw // 2] = 1
        if rng.random() < 0.35:
            grid[0] = rng.integers(0, 2, size=gw, dtype=np.uint8)
        for r in range(1, gh):
            left = np.roll(grid[r - 1], 1)
            mid = grid[r - 1]
            right = np.roll(grid[r - 1], -1)
            pattern_idx = (left << 2) | (mid << 1) | right
            grid[r] = (rule_num >> pattern_idx) & 1
        bg, fg = np.asarray(palette[0], np.float32) * 0.2, np.asarray(palette[1 % len(palette)], np.float32)
        rgb_small = np.where(grid[..., None] > 0, fg, bg)
    pil_small = _to_rgb_image(rgb_small)
    return pil_small.resize((w, h), Image.Resampling.NEAREST)


def spirograph(
    width: int = 768,
    height: int = 768,
    kind: str = "spirograph",
    petals: int = 7,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Parametric Spirograph hypotrochoid or Lissajous harmonic curves."""
    w, h = clamp_dimensions(width, height)
    kind = validate_choice(kind, ("spirograph", "lissajous"), "kind")
    k_petals = clamp_int(petals, 2, 24, "petals")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 4)
    canvas = Image.new("RGB", (w, h), (12, 14, 22))
    draw = ImageDraw.Draw(canvas)
    cx, cy = w / 2.0, h / 2.0
    radius = min(w, h) * 0.42
    t = np.linspace(0.0, 2.0 * math.pi * k_petals, 4500)
    for layer_idx in range(3):
        col = palette[layer_idx % len(palette)]
        scale = 1.0 - layer_idx * 0.16
        if kind == "lissajous":
            fx = k_petals + layer_idx
            fy = k_petals - 1 if k_petals > 2 else 3
            phase = float(rng.uniform(0, math.pi))
            xs = cx + np.sin(fx * t / k_petals + phase) * radius * scale
            ys = cy + np.sin(fy * t / k_petals) * radius * scale
        else:
            R = radius * scale
            r = R / k_petals * (1.0 + 0.15 * layer_idx)
            d = r * float(rng.uniform(0.6, 1.35))
            xs = cx + (R - r) * np.cos(t) + d * np.cos((R - r) / max(r, 1e-4) * t)
            ys = cy + (R - r) * np.sin(t) - d * np.sin((R - r) / max(r, 1e-4) * t)
        pts = list(zip(xs.tolist(), ys.tolist(), strict=False))
        draw.line(pts, fill=col, width=2)
    return canvas


def truchet(
    width: int = 768,
    height: int = 768,
    cell_size: int = 48,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Quarter-circle Smith Truchet tiling."""
    w, h = clamp_dimensions(width, height)
    cs = clamp_int(cell_size, 16, 160, "cell_size")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 3)
    bg = tuple(int(c * 0.22) for c in palette[0])
    canvas = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(canvas)
    stroke = max(3, cs // 6)
    for y in range(0, h + cs, cs):
        for x in range(0, w + cs, cs):
            col = palette[1 + int(rng.integers(0, len(palette) - 1))] if len(palette) > 1 else palette[0]
            if rng.random() < 0.5:
                draw.arc((x - cs // 2, y - cs // 2, x + cs // 2, y + cs // 2), 0, 90, fill=col, width=stroke)
                draw.arc((x + cs // 2, y + cs // 2, x + 3 * cs // 2, y + 3 * cs // 2), 180, 270, fill=col, width=stroke)
            else:
                draw.arc((x + cs // 2, y - cs // 2, x + 3 * cs // 2, y + cs // 2), 90, 180, fill=col, width=stroke)
                draw.arc((x - cs // 2, y + cs // 2, x + cs // 2, y + 3 * cs // 2), 270, 360, fill=col, width=stroke)
    return canvas


def maze(
    width: int = 768,
    height: int = 768,
    cell_size: int = 24,
    solve: bool = True,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Procedural perfect maze (iterative DFS) with optional highlighted solution path."""
    w, h = clamp_dimensions(width, height, max_dim=MAX_HEAVY_DIMENSION)
    cs = clamp_int(cell_size, 12, 64, "cell_size")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 3)
    cols = max(5, (w // cs) | 1)
    rows = max(5, (h // cs) | 1)
    cw, ch = (cols - 1) // 2, (rows - 1) // 2
    grid = np.zeros((rows, cols), dtype=np.uint8)
    visited = np.zeros((ch, cw), dtype=bool)
    parent: dict[tuple[int, int], tuple[int, int]] = {}
    stack = [(0, 0)]
    visited[0, 0] = True
    grid[1, 1] = 1
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    while stack:
        cy, cx = stack[-1]
        nbrs = []
        for dy, dx in dirs:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < ch and 0 <= nx < cw and not visited[ny, nx]:
                nbrs.append((ny, nx, dy, dx))
        if nbrs:
            ny, nx, dy, dx = nbrs[int(rng.integers(len(nbrs)))]
            visited[ny, nx] = True
            grid[cy * 2 + 1 + dy, cx * 2 + 1 + dx] = 1
            grid[ny * 2 + 1, nx * 2 + 1] = 1
            parent[(ny, nx)] = (cy, cx)
            stack.append((ny, nx))
        else:
            stack.pop()
    if solve and (ch - 1, cw - 1) in parent:
        cur = (ch - 1, cw - 1)
        grid[cur[0] * 2 + 1, cur[1] * 2 + 1] = 2
        while cur in parent:
            prev = parent[cur]
            grid[cur[0] + prev[0] + 1, cur[1] + prev[1] + 1] = 2
            grid[prev[0] * 2 + 1, prev[1] * 2 + 1] = 2
            cur = prev
    wall_c = np.asarray((18, 20, 28), dtype=np.uint8)
    floor_c = np.asarray(palette[0], dtype=np.uint8)
    sol_c = np.asarray(palette[-1], dtype=np.uint8)
    rgb = np.where(grid[..., None] == 0, wall_c, np.where(grid[..., None] == 2, sol_c, floor_c))
    return Image.fromarray(rgb, mode="RGB").resize((w, h), Image.Resampling.NEAREST)


def circlepack(
    width: int = 768,
    height: int = 768,
    count: int = 180,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Non-overlapping multi-scale circle packing."""
    w, h = clamp_dimensions(width, height)
    target = clamp_int(count, 20, 500, "count")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 5)
    canvas = Image.new("RGB", (w, h), (16, 18, 25))
    draw = ImageDraw.Draw(canvas)
    circles: list[tuple[float, float, float]] = []
    max_r = min(w, h) * 0.16
    min_r = 5.0
    for _ in range(target * 12):
        if len(circles) >= target:
            break
        x = float(rng.uniform(min_r, w - min_r))
        y = float(rng.uniform(min_r, h - min_r))
        r = min(x, w - x, y, h - y, max_r)
        for cx, cy, cr in circles:
            d = math.hypot(x - cx, y - cy) - cr - 2.0
            r = min(r, d)
            if r < min_r:
                break
        if r >= min_r:
            circles.append((x, y, r))
            col = palette[len(circles) % len(palette)]
            draw.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=(255, 255, 255), width=max(1, int(r * 0.06)))
    return canvas


def hexgrid(
    width: int = 768,
    height: int = 768,
    cell_size: int = 36,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Honeycomb hexagonal grid with noise-driven colour shading."""
    w, h = clamp_dimensions(width, height)
    r = clamp_int(cell_size, 12, 120, "cell_size")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 5)
    canvas = Image.new("RGB", (w, h), (15, 17, 24))
    draw = ImageDraw.Draw(canvas)
    dx = 1.5 * r
    dy = math.sqrt(3.0) * r
    cols = int(w / dx) + 3
    rows = int(h / dy) + 3
    for col_idx in range(-1, cols):
        for row_idx in range(-1, rows):
            cx = col_idx * dx
            cy = row_idx * dy + (dy * 0.5 if col_idx % 2 else 0.0)
            pts = [(cx + (r - 2) * math.cos(math.radians(60 * k)), cy + (r - 2) * math.sin(math.radians(60 * k))) for k in range(6)]
            c = palette[int(rng.integers(len(palette)))]
            shade = float(rng.uniform(0.7, 1.15))
            fill = tuple(min(255, int(v * shade)) for v in c)
            draw.polygon(pts, fill=fill, outline=(22, 24, 34))
    return canvas


def lsystem(
    width: int = 768,
    height: int = 768,
    kind: str = "tree",
    depth: int = 7,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Recursive fractal canopy tree or Sierpinski triangle."""
    w, h = clamp_dimensions(width, height)
    kind = validate_choice(kind, ("tree", "sierpinski"), "kind")
    d_max = clamp_int(depth, 3, 9, "depth")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 4)
    canvas = Image.new("RGB", (w, h), (14, 16, 24))
    draw = ImageDraw.Draw(canvas)
    if kind == "sierpinski":
        d_max = min(d_max, 7)

        def _tri(p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float], lvl: int) -> None:
            if lvl == 0:
                col = palette[int((p1[0] + p1[1]) / 60) % len(palette)]
                draw.polygon([p1, p2, p3], fill=col)
                return
            m12 = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            m23 = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
            m31 = ((p3[0] + p1[0]) / 2, (p3[1] + p1[1]) / 2)
            _tri(p1, m12, m31, lvl - 1)
            _tri(m12, p2, m23, lvl - 1)
            _tri(m31, m23, p3, lvl - 1)

        pad = min(w, h) * 0.08
        _tri((w / 2, pad), (pad, h - pad), (w - pad, h - pad), d_max)
    else:

        def _branch(x: float, y: float, length: float, angle: float, lvl: int) -> None:
            if lvl <= 0 or length < 2.0:
                return
            nx = x + length * math.cos(angle)
            ny = y - length * math.sin(angle)
            col = palette[(d_max - lvl) % len(palette)]
            draw.line((x, y, nx, ny), fill=col, width=max(1, lvl))
            spread = math.radians(float(rng.uniform(20.0, 34.0)))
            decay = float(rng.uniform(0.68, 0.78))
            _branch(nx, ny, length * decay, angle + spread, lvl - 1)
            _branch(nx, ny, length * decay, angle - spread, lvl - 1)

        _branch(w / 2.0, h * 0.92, min(w, h) * 0.24, math.pi / 2.0, min(d_max, 9))
    return canvas


def starfield(
    width: int = 768,
    height: int = 768,
    stars: int = 350,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Deep-space procedural nebula and multi-layer starfield with diffraction spikes."""
    w, h = clamp_dimensions(width, height)
    n_stars = clamp_int(stars, 50, 1200, "stars")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 3)
    nebula = _fbm_noise(rng, h, w, scale=96, octaves=4)
    bg_stops = [(6, 8, 18), tuple(int(c * 0.45) for c in palette[0]), tuple(int(c * 0.65) for c in palette[-1])]
    canvas = _to_rgb_image(_lerp_palette(nebula**1.6, bg_stops)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    for _ in range(n_stars):
        x, y = float(rng.uniform(0, w)), float(rng.uniform(0, h))
        r = float(rng.exponential(1.2))
        col = palette[int(rng.integers(len(palette)))] if rng.random() < 0.35 else (255, 255, 255)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(*col, 235))
        if r > 2.4:
            spike = r * 3.5
            draw.line((x - spike, y, x + spike, y), fill=(*col, 180), width=1)
            draw.line((x, y - spike, x, y + spike), fill=(*col, 180), width=1)
    return canvas.convert("RGB")


def sunburst(
    width: int = 768,
    height: int = 768,
    rays: int = 24,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Radial sunburst rays with smooth vignette falloff."""
    w, h = clamp_dimensions(width, height)
    n_rays = clamp_int(rays, 4, 96, "rays")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 3)
    xs, ys = _grid(w, h)
    dx, dy = xs - w / 2.0, ys - h / 2.0
    angle = (np.arctan2(dy, dx) + math.pi) / (2.0 * math.pi)
    stripe = (np.floor(angle * n_rays * 2.0).astype(np.int32)) % 2
    dist = np.hypot(dx, dy) / (math.hypot(w, h) * 0.5)
    c0, c1 = np.asarray(palette[0], np.float32), np.asarray(palette[1 % len(palette)], np.float32)
    rgb = np.where(stripe[..., None] == 0, c0, c1) * np.clip(1.15 - dist[..., None] * 0.45, 0.3, 1.0)
    return _to_rgb_image(rgb)


def moire(
    width: int = 768,
    height: int = 768,
    wavelength: float = 14.0,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Optical interference moiré pattern from displaced concentric wave sources."""
    w, h = clamp_dimensions(width, height)
    wl = clamp_float(wavelength, 4.0, 64.0, "wavelength")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 3)
    xs, ys = _grid(w, h)
    offset = min(w, h) * float(rng.uniform(0.08, 0.22))
    ang = float(rng.uniform(0, 2 * math.pi))
    r1 = np.hypot(xs - (w / 2 - math.cos(ang) * offset), ys - (h / 2 - math.sin(ang) * offset))
    r2 = np.hypot(xs - (w / 2 + math.cos(ang) * offset), ys - (h / 2 + math.sin(ang) * offset))
    wave = 0.5 + 0.25 * (np.sin(2 * math.pi * r1 / wl) + np.sin(2 * math.pi * r2 / (wl * 1.05)))
    return _to_rgb_image(_lerp_palette(wave, palette))


def topographic(
    width: int = 768,
    height: int = 768,
    levels: int = 14,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Topographic contour map with hypsometric elevation bands and crisp isolines."""
    w, h = clamp_dimensions(width, height)
    lv = clamp_int(levels, 4, 36, "levels")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 5)
    elev = _fbm_noise(rng, h, w, scale=96, octaves=5)
    quant = np.floor(elev * lv) / lv
    rgb = _lerp_palette(quant, palette)
    band_idx = np.floor(elev * lv).astype(np.int32)
    contour = np.zeros((h, w), dtype=bool)
    contour[:, 1:] |= band_idx[:, 1:] != band_idx[:, :-1]
    contour[1:, :] |= band_idx[1:, :] != band_idx[:-1, :]
    rgb[contour] = rgb[contour] * 0.25
    return _to_rgb_image(rgb)


def reaction(
    width: int = 512,
    height: int = 512,
    steps: int = 160,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Gray-Scott reaction-diffusion Turing pattern generator."""
    w, h = clamp_dimensions(width, height, max_dim=MAX_HEAVY_DIMENSION)
    n_steps = clamp_int(steps, 40, 300, "steps")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, 3)
    sw, sh = max(64, w // 3), max(64, h // 3)
    U = np.ones((sh, sw), dtype=np.float32)
    V = np.zeros((sh, sw), dtype=np.float32)
    for _ in range(12):
        rx, ry = int(rng.integers(4, sw - 12)), int(rng.integers(4, sh - 12))
        U[ry : ry + 8, rx : rx + 8] = 0.5
        V[ry : ry + 8, rx : rx + 8] = 0.25 + rng.uniform(-0.02, 0.02, (8, 8)).astype(np.float32)
    Du, Dv, F, k = 0.16, 0.08, 0.055, 0.062
    for _ in range(n_steps):
        lap_u = np.roll(U, 1, 0) + np.roll(U, -1, 0) + np.roll(U, 1, 1) + np.roll(U, -1, 1) - 4.0 * U
        lap_v = np.roll(V, 1, 0) + np.roll(V, -1, 0) + np.roll(V, 1, 1) + np.roll(V, -1, 1) - 4.0 * V
        uvv = U * V * V
        U = np.clip(U + (Du * lap_u - uvv + F * (1.0 - U)), 0.0, 1.0)
        V = np.clip(V + (Dv * lap_v + uvv - (F + k) * V), 0.0, 1.0)
    norm = (V - float(V.min())) / max(float(np.ptp(V)), 1e-5)
    small_img = _to_rgb_image(_lerp_palette(norm, palette))
    return small_img.resize((w, h), Image.Resampling.BICUBIC)


def mesh(
    width: int = 768,
    height: int = 768,
    anchors: int = 6,
    colors: Sequence[Color] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Smooth multi-anchor inverse-distance gradient mesh wallpaper."""
    w, h = clamp_dimensions(width, height)
    n = clamp_int(anchors, 3, 12, "anchors")
    rng = make_rng(seed)
    palette = _resolve_palette(colors, rng, n)
    xs, ys = _grid(w, h)
    px = rng.uniform(0.1 * w, 0.9 * w, n).astype(np.float32)
    py = rng.uniform(0.1 * h, 0.9 * h, n).astype(np.float32)
    sigma2 = (min(w, h) * 0.45) ** 2
    weights = np.zeros((h, w, n), dtype=np.float32)
    for i in range(n):
        d2 = (xs - px[i]) ** 2 + (ys - py[i]) ** 2
        weights[..., i] = 1.0 / (d2 + sigma2 * 0.15)
    weights /= np.sum(weights, axis=-1, keepdims=True)
    pal = np.asarray([palette[i % len(palette)] for i in range(n)], dtype=np.float32)
    rgb = weights @ pal
    rgb += rng.random(rgb.shape, dtype=np.float32) - 0.5
    return _to_rgb_image(rgb)


def palette_wallpaper_from_bytes(
    data: bytes,
    width: int = 1024,
    height: int = 576,
    style: str = "mesh",
    seed: int | None = None,
) -> EncodedImage:
    """Extract dominant colours from an avatar/image and generate a matching wallpaper."""
    style = validate_choice(style, ("mesh", "plasma", "topographic", "flowfield", "waves"), "style")
    img = load_image(data, max_dim=256)
    colors = extract_dominant_palette(img, count=5)
    if style == "plasma":
        out = plasma(width, height, colors=colors, seed=seed)
    elif style == "topographic":
        out = topographic(width, height, colors=colors, seed=seed)
    elif style == "flowfield":
        out = flowfield(width, height, colors=colors, seed=seed)
    elif style == "waves":
        out = pattern(width, height, kind="waves", colors=colors, seed=seed)
    else:
        out = mesh(width, height, anchors=len(colors), colors=colors, seed=seed)
    return encode_image(out)


GENERATORS: dict[str, Callable[..., Image.Image]] = {
    "gradient": gradient,
    "noise": noise,
    "plasma": plasma,
    "fractal": fractal,
    "voronoi": voronoi,
    "geometric": geometric,
    "pattern": pattern,
    "flowfield": flowfield,
    "cellular": cellular,
    "spirograph": spirograph,
    "truchet": truchet,
    "maze": maze,
    "circlepack": circlepack,
    "hexgrid": hexgrid,
    "lsystem": lsystem,
    "starfield": starfield,
    "sunburst": sunburst,
    "moire": moire,
    "topographic": topographic,
    "reaction": reaction,
    "mesh": mesh,
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
    """Place a circular avatar inside a decorated, generated frame."""
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
    """Combine up to 36 avatars into a collage with rounded tiles."""
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


def render_photomosaic(
    target_data: bytes,
    tile_datas: Sequence[bytes],
    grid_size: int = 24,
    tile_px: int = 28,
) -> EncodedImage:
    """Rebuild ``target_data`` from a library of avatar tiles matched by average RGB colour."""
    if not tile_datas:
        msg = "At least one tile image is required for a photomosaic."
        raise ImageValidationError(msg)
    gs = clamp_int(grid_size, 8, 48, "grid_size")
    t_px = clamp_int(tile_px, 12, 48, "tile_px")
    target = resize_rgba(center_crop_square(load_image(target_data, max_dim=512)), (gs, gs))
    target_arr = to_array(target)[..., :3].astype(np.float32)

    tiles: list[Image.Image] = []
    avgs: list[np.ndarray] = []
    for d in tile_datas[:36]:
        im = resize_rgba(center_crop_square(load_image(d, max_dim=128)), (t_px, t_px))
        tiles.append(im)
        avgs.append(to_array(im)[..., :3].mean(axis=(0, 1)).astype(np.float32))
    avg_mat = np.stack(avgs, axis=0)

    canvas = Image.new("RGBA", (gs * t_px, gs * t_px), (20, 20, 26, 255))
    for r in range(gs):
        for c in range(gs):
            want = target_arr[r, c]
            idx = int(np.argmin(np.sum((avg_mat - want) ** 2, axis=1)))
            tile_arr = to_array(tiles[idx]).astype(np.float32)
            # Blend 55% tile + 45% target colour so mosaic works even with few unique avatars
            tile_arr[..., :3] = tile_arr[..., :3] * 0.55 + want * 0.45
            canvas.paste(from_array(tile_arr), (c * t_px, r * t_px))
    return encode_image(fit_within(canvas, MAX_OUTPUT_DIMENSION))


def render_avatar_swap(data_a: bytes, data_b: bytes, name_a: str, name_b: str) -> EncodedImage:
    """Swap two users' avatars into each other's colour palettes and nameplates."""
    im_a = load_image(data_a, max_dim=256)
    im_b = load_image(data_b, max_dim=256)
    pal_a = extract_dominant_palette(im_a, 2)
    pal_b = extract_dominant_palette(im_b, 2)
    frame_a = avatar_frame(im_b, style="neon", size=340)
    frame_b = avatar_frame(im_a, style="gold", size=340)
    canvas = Image.new("RGBA", (740, 420), (20, 22, 30, 255))
    draw = ImageDraw.Draw(canvas)
    canvas.alpha_composite(frame_a, (25, 20))
    canvas.alpha_composite(frame_b, (375, 20))
    font = load_font(20, bold=True)
    draw.rounded_rectangle((55, 368, 310, 404), radius=12, fill=(*pal_a[0], 220))
    draw.rounded_rectangle((405, 368, 660, 404), radius=12, fill=(*pal_b[0], 220))
    draw.text((182, 386), f"{name_a[:18]} (Swapped)", fill=(255, 255, 255, 255), font=font, anchor="mm")
    draw.text((532, 386), f"{name_b[:18]} (Swapped)", fill=(255, 255, 255, 255), font=font, anchor="mm")
    return encode_image(canvas)


PRIDE_FLAGS: dict[str, list[Color]] = {
    "rainbow": [(228, 3, 3), (255, 140, 0), (255, 237, 0), (0, 128, 38), (0, 77, 255), (117, 7, 135)],
    "trans": [(91, 206, 250), (245, 169, 184), (255, 255, 255), (245, 169, 184), (91, 206, 250)],
    "bi": [(214, 2, 112), (214, 2, 112), (155, 79, 150), (0, 56, 168), (0, 56, 168)],
    "pan": [(255, 33, 140), (255, 216, 0), (33, 177, 255)],
    "nonbinary": [(252, 244, 52), (255, 255, 255), (156, 89, 209), (44, 44, 44)],
    "lesbian": [(213, 45, 0), (239, 118, 39), (255, 154, 86), (255, 255, 255), (209, 98, 164), (181, 86, 144), (163, 2, 98)],
    "ace": [(0, 0, 0), (163, 163, 163), (255, 255, 255), (128, 0, 128)],
}


def render_pride_overlay(
    data: bytes,
    flag: str = "rainbow",
    opacity: float = 0.45,
    mode: str = "ring",
) -> EncodedImage:
    """Apply a pride flag ring or translucent overlay to an avatar."""
    flag = validate_choice(flag, tuple(PRIDE_FLAGS.keys()), "flag")
    mode = validate_choice(mode, ("ring", "overlay"), "mode")
    alpha_f = clamp_float(opacity, 0.1, 0.9, "opacity")
    av = resize_rgba(center_crop_square(load_image(data, max_dim=512)), (512, 512))
    stripes = PRIDE_FLAGS[flag]
    flag_img = Image.new("RGBA", (512, 512))
    draw = ImageDraw.Draw(flag_img)
    n = len(stripes)
    for i, col in enumerate(stripes):
        y0 = round(i * 512 / n)
        y1 = round((i + 1) * 512 / n)
        draw.rectangle((0, y0, 512, y1), fill=(*col, 255))
    if mode == "ring":
        canvas = crop_circle(flag_img, 512)
        inner = crop_circle(av, int(512 * (1.0 - alpha_f * 0.35)))
        offset = (512 - inner.width) // 2
        canvas.alpha_composite(inner, (offset, offset))
        return encode_image(canvas)
    arr_av = to_array(av).astype(np.float32)
    arr_fl = to_array(flag_img).astype(np.float32)
    arr_av[..., :3] = arr_av[..., :3] * (1.0 - alpha_f) + arr_fl[..., :3] * alpha_f
    return encode_image(from_array(arr_av))


def render_meme(data: bytes, top_text: str = "", bottom_text: str = "") -> EncodedImage:
    """Render bold white-with-black-stroke meme captions at the top and bottom of an image."""
    img = load_image(data, max_dim=768).copy()
    w, h = img.size
    draw = ImageDraw.Draw(img)
    font_size = max(20, w // 12)
    font = load_font(font_size, bold=True)
    stroke = max(2, font_size // 10)
    if top_text.strip():
        wrapped = "\n".join(textwrap.wrap(top_text.upper(), width=24)[:3])
        draw.multiline_text(
            (w // 2, 16), wrapped, fill=(255, 255, 255, 255), font=font, anchor="ma", align="center", stroke_width=stroke, stroke_fill=(0, 0, 0, 255)
        )
    if bottom_text.strip():
        wrapped = "\n".join(textwrap.wrap(bottom_text.upper(), width=24)[:3])
        draw.multiline_text(
            (w // 2, h - 16),
            wrapped,
            fill=(255, 255, 255, 255),
            font=font,
            anchor="md",
            align="center",
            stroke_width=stroke,
            stroke_fill=(0, 0, 0, 255),
        )
    return encode_image(img)


def render_speech_bubble(data: bytes, text: str = "") -> EncodedImage:
    """Add a comic speech bubble header above an image."""
    img = load_image(data, max_dim=640)
    w, h = img.size
    bh = max(90, int(h * 0.26))
    canvas = Image.new("RGBA", (w, h + bh), (0, 0, 0, 0))
    canvas.alpha_composite(img, (0, bh))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((8, 8, w - 8, bh - 18), radius=24, fill=(255, 255, 255, 255), outline=(25, 25, 30, 255), width=3)
    draw.polygon([(w // 2 - 18, bh - 20), (w // 2 + 18, bh - 20), (w // 2 - 6, bh + 4)], fill=(255, 255, 255, 255), outline=(25, 25, 30, 255))
    if text.strip():
        font = load_font(max(15, w // 22), bold=True)
        wrapped = "\n".join(textwrap.wrap(text.strip(), width=28)[:2])
        draw.multiline_text((w // 2, (bh - 18) // 2), wrapped, fill=(20, 22, 28, 255), font=font, anchor="mm", align="center")
    return encode_image(canvas)


def render_quote_card(avatar_data: bytes, quote: str, author_name: str) -> EncodedImage:
    """Render an atmospheric quote card with avatar and attribution."""
    w, h = 760, 340
    av = load_image(avatar_data, max_dim=256)
    canvas = Image.new("RGBA", (w, h), (16, 18, 26, 255))
    draw = ImageDraw.Draw(canvas)
    canvas.alpha_composite(crop_circle(av, 180), (44, 80))
    font_q = load_font(22, bold=True)
    font_a = load_font(17)
    wrapped = "\n".join(textwrap.wrap(f'"{quote.strip()}"', width=34)[:5])
    draw.multiline_text((260, 95), wrapped, fill=(240, 244, 252, 255), font=font_q)
    draw.text((260, 265), f"— {author_name[:28]}", fill=(150, 175, 215, 255), font=font_a)
    return encode_image(canvas)


def render_colorinfo(color_str: str) -> tuple[EncodedImage, dict[str, str]]:
    """Render a colour swatch sheet showing Main, Complement, and Analogous colours + metadata."""
    r, g, b = parse_hex_color(color_str, "color")
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)  # noqa: E741

    def _hls_rgb(hue: float) -> Color:
        rr, gg, bb = colorsys.hls_to_rgb(hue % 1.0, l, s)
        return round(rr * 255), round(gg * 255), round(bb * 255)

    comp = _hls_rgb(h + 0.5)
    ana1 = _hls_rgb(h - 1 / 12)
    ana2 = _hls_rgb(h + 1 / 12)
    swatches = [("Primary", (r, g, b)), ("Complement", comp), ("Analogous -30°", ana1), ("Analogous +30°", ana2)]

    canvas = Image.new("RGBA", (640, 240), (20, 22, 30, 255))
    draw = ImageDraw.Draw(canvas)
    font = load_font(14, bold=True)
    for i, (label, col) in enumerate(swatches):
        x0 = 16 + i * 154
        draw.rounded_rectangle((x0, 18, x0 + 142, 165), radius=14, fill=(*col, 255), outline=(255, 255, 255, 60), width=2)
        hex_code = "#{:02x}{:02x}{:02x}".format(*col)
        draw.text((x0 + 71, 184), label, fill=(215, 220, 232, 255), font=font, anchor="mm")
        draw.text((x0 + 71, 208), hex_code, fill=(155, 165, 185, 255), font=font, anchor="mm")

    info = {
        "Hex": f"#{r:02x}{g:02x}{b:02x}",
        "RGB": f"rgb({r}, {g}, {b})",
        "HSL": f"hsl({round(h * 360)}°, {round(s * 100)}%, {round(l * 100)}%)",
        "Complement": "#{:02x}{:02x}{:02x}".format(*comp),
    }
    return encode_image(canvas), info


def render_palette_swatches(data: bytes, count: int = 6) -> tuple[EncodedImage, list[str]]:
    """Extract ``count`` dominant colours from an image and render a swatch card."""
    n = clamp_int(count, 2, 10, "count")
    img = load_image(data, max_dim=256)
    colors = extract_dominant_palette(img, n)
    sw_w = 110
    canvas = Image.new("RGBA", (sw_w * n + 20, 200), (20, 22, 30, 255))
    draw = ImageDraw.Draw(canvas)
    font = load_font(14, bold=True)
    hex_list: list[str] = []
    for i, col in enumerate(colors):
        x0 = 10 + i * sw_w
        hx = "#{:02x}{:02x}{:02x}".format(*col)
        hex_list.append(hx)
        draw.rounded_rectangle((x0 + 4, 14, x0 + sw_w - 4, 146), radius=12, fill=(*col, 255))
        draw.text((x0 + sw_w // 2, 170), hx, fill=(230, 235, 245, 255), font=font, anchor="mm")
    return encode_image(canvas), hex_list


_CB_MATRICES: dict[str, np.ndarray] = {
    "protanopia": np.array([[0.567, 0.433, 0.0], [0.558, 0.442, 0.0], [0.0, 0.242, 0.758]], dtype=np.float32),
    "deuteranopia": np.array([[0.625, 0.375, 0.0], [0.700, 0.300, 0.0], [0.0, 0.300, 0.700]], dtype=np.float32),
    "tritanopia": np.array([[0.950, 0.050, 0.0], [0.0, 0.433, 0.567], [0.0, 0.475, 0.525]], dtype=np.float32),
}


def render_colorblind_sim(data: bytes, kind: str = "deuteranopia") -> EncodedImage:
    """Simulate protanopia, deuteranopia, or tritanopia colour vision deficiency."""
    kind = validate_choice(kind, tuple(_CB_MATRICES.keys()), "kind")
    img = load_image(data)
    arr = to_array(img)
    rgb = np.clip(arr[..., :3].astype(np.float32) @ _CB_MATRICES[kind].T, 0, 255).astype(np.uint8)
    return encode_image(join_rgb_alpha(rgb, arr[..., 3]))


def _rel_luminance(col: Color) -> float:
    def _ch(v: int) -> float:
        x = v / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    return 0.2126 * _ch(col[0]) + 0.7152 * _ch(col[1]) + 0.0722 * _ch(col[2])


def render_contrast_checker(color_a: str, color_b: str) -> tuple[EncodedImage, dict[str, str]]:
    """Calculate WCAG 2.1 contrast ratio between two colours and render a preview card."""
    ca = parse_hex_color(color_a, "color_a")
    cb = parse_hex_color(color_b, "color_b")
    la, lb = _rel_luminance(ca), _rel_luminance(cb)
    ratio = (max(la, lb) + 0.05) / (min(la, lb) + 0.05)
    aa_norm = "PASS" if ratio >= 4.5 else "FAIL"
    aaa_norm = "PASS" if ratio >= 7.0 else "FAIL"
    aa_large = "PASS" if ratio >= 3.0 else "FAIL"

    canvas = Image.new("RGBA", (620, 240), (20, 22, 30, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((20, 20, 300, 220), radius=16, fill=(*ca, 255), outline=(255, 255, 255, 80), width=2)
    draw.text((160, 95), "Sample Text", fill=(*cb, 255), font=load_font(26, bold=True), anchor="mm")
    draw.text((160, 145), f"Ratio {ratio:.2f}:1", fill=(*cb, 255), font=load_font(18, bold=True), anchor="mm")

    draw.text((330, 50), f"Contrast: {ratio:.2f} : 1", fill=(245, 248, 255, 255), font=load_font(22, bold=True))
    draw.text(
        (330, 100),
        f"WCAG AA Normal: {aa_norm}",
        fill=(110, 235, 145, 255) if aa_norm == "PASS" else (255, 110, 110, 255),
        font=load_font(17, bold=True),
    )
    draw.text(
        (330, 138),
        f"WCAG AAA Normal: {aaa_norm}",
        fill=(110, 235, 145, 255) if aaa_norm == "PASS" else (255, 110, 110, 255),
        font=load_font(17, bold=True),
    )
    draw.text(
        (330, 176),
        f"WCAG AA Large: {aa_large}",
        fill=(110, 235, 145, 255) if aa_large == "PASS" else (255, 110, 110, 255),
        font=load_font(17, bold=True),
    )

    return encode_image(canvas), {"Ratio": f"{ratio:.2f}:1", "AA Normal": aa_norm, "AAA Normal": aaa_norm, "AA Large": aa_large}


def render_qrcode(text: str, box_size: int = 12) -> EncodedImage:
    """Render a QR-style 2D matrix code (uses `qrcode` library if installed, else deterministic Version-2 QR matrix)."""
    if not text or not text.strip():
        msg = "Provide non-empty text to encode."
        raise ImageValidationError(msg)
    clean = text.strip()[:256]
    try:
        import qrcode  # type: ignore[import-not-found]  # noqa: PLC0415

        qr = qrcode.QRCode(border=3, box_size=clamp_int(box_size, 4, 20, "box_size"))
        qr.add_data(clean)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.convert("RGBA")
        return encode_image(img)
    except ImportError, AttributeError:
        pass

    # Pure Pillow/NumPy 25x25 Version-2 QR matrix layout with standard finder/alignment/timing patterns
    size = 25
    grid = np.zeros((size, size), dtype=np.uint8)
    reserved = np.zeros((size, size), dtype=bool)

    def _finder(r0: int, c0: int) -> None:
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                rr, cc = r0 + dr, c0 + dc
                if 0 <= rr < size and 0 <= cc < size:
                    reserved[rr, cc] = True
                    in_outer = 0 <= dr <= 6 and (dc in (0, 6) or dr in (0, 6))
                    in_inner = 2 <= dr <= 4 and 2 <= dc <= 4
                    grid[rr, cc] = 1 if (in_outer or in_inner) else 0

    _finder(0, 0)
    _finder(0, size - 7)
    _finder(size - 7, 0)
    # Timing patterns
    for i in range(8, size - 8):
        reserved[6, i] = reserved[i, 6] = True
        grid[6, i] = grid[i, 6] = (i + 1) % 2
    # Alignment pattern at (16, 16)
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            reserved[18 + dr, 18 + dc] = True
            grid[18 + dr, 18 + dc] = 1 if (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0)) else 0

    # Fill payload bits deterministically from UTF-8 bytes + SHA-256 parity
    digest = hashlib.sha256(clean.encode("utf-8")).digest()
    payload = clean.encode("utf-8") + digest
    bits = [(b >> (7 - k)) & 1 for b in payload for k in range(8)]
    bit_idx = 0
    for r in range(size):
        for c in range(size):
            if not reserved[r, c]:
                grid[r, c] = bits[bit_idx % len(bits)] ^ ((r + c) % 2 == 0)
                bit_idx += 1

    pad = 3
    padded = np.zeros((size + pad * 2, size + pad * 2), dtype=np.uint8)
    padded[pad : pad + size, pad : pad + size] = grid
    px = clamp_int(box_size, 6, 20, "box_size")
    rgb = np.where(padded[..., None] == 1, 15, 250).repeat(3, axis=2).astype(np.uint8)
    out = Image.fromarray(rgb, mode="RGB").resize(((size + pad * 2) * px, (size + pad * 2) * px), Image.Resampling.NEAREST)
    return encode_image(out)


def render_barcode(text: str) -> EncodedImage:
    """Render a crisp 1D linear barcode with human-readable caption."""
    clean = (text or "").strip()[:40]
    if not clean:
        msg = "Provide non-empty text for the barcode."
        raise ImageValidationError(msg)
    bits: list[int] = [1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0]  # Start guard
    for ch in clean.encode("utf-8"):
        val = int(ch)
        for shift in range(7, -1, -1):
            bits.extend([1, 1, 0] if ((val >> shift) & 1) else [1, 0])
        bits.append(0)
    bits.extend([1, 1, 0, 1, 0, 1, 1])  # Stop guard
    bar_w = 3
    w = max(320, len(bits) * bar_w + 48)
    h = 160
    canvas = Image.new("RGBA", (w, h), (250, 250, 252, 255))
    draw = ImageDraw.Draw(canvas)
    x0 = (w - len(bits) * bar_w) // 2
    for i, bit in enumerate(bits):
        if bit:
            draw.rectangle((x0 + i * bar_w, 22, x0 + (i + 1) * bar_w - 1, 118), fill=(15, 18, 24, 255))
    draw.text((w // 2, 136), clean, fill=(25, 28, 36, 255), font=load_font(16, bold=True), anchor="mm")
    return encode_image(canvas)
