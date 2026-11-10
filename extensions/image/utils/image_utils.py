from __future__ import annotations

import io
import math
import pathlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass

lazy import numpy as np
lazy from PIL import Image, ImageChops, ImageDraw, ImageFont

from .image_validators import (
    MAX_OUTPUT_BYTES,
    MAX_OUTPUT_DIMENSION,
    MAX_OUTPUT_FRAMES,
    MAX_WORKING_DIMENSION,
    Color,
    ImageValidationError,
    clamp_float,
    clamp_int,
    inspect_image,
    normalize_seed,
    validate_choice,
)

_LANCZOS = Image.Resampling.LANCZOS


def make_rng(seed: int | None) -> np.random.Generator:
    """Return an isolated :class:`numpy.random.Generator` (never global state)."""
    return np.random.default_rng(normalize_seed(seed))


def load_font(size: int = 20, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a scalable TrueType font with fallback to Pillow's built-in font."""
    path = pathlib.Path("assets") / ("Poppins-Bold.ttf" if bold else "Poppins-Regular.ttf")
    try:
        return ImageFont.truetype(path, size=max(8, int(size)))
    except OSError:
        pass
    try:
        return ImageFont.load_default(size=max(8, int(size)))
    except TypeError:
        return ImageFont.load_default()


def _scalar_to_rgba(img: Image.Image) -> Image.Image:
    """Convert 16-bit / 32-bit integer / float images to RGBA by scaling."""
    data = np.nan_to_num(np.asarray(img, dtype=np.float32))
    if img.mode.startswith("I;16"):
        peak = 65535.0
    elif img.mode == "I":
        peak = max(float(data.max()), 255.0)
    else:  # "F"
        peak = 1.0 if float(data.max()) <= 1.0 else 255.0
    gray = np.clip(data / peak * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(gray).convert("RGBA")


def to_rgba(img: Image.Image) -> Image.Image:
    """Return a **new** RGBA copy of ``img`` (handles L, LA, P, 1, CMYK, I;16 ...)."""
    if not isinstance(img, Image.Image):
        msg = "Expected a Pillow image."
        raise ImageValidationError(msg)
    mode = img.mode
    try:
        if mode == "RGBA":
            return img.copy()
        if mode.startswith("I;16") or mode in {"I", "F"}:
            return _scalar_to_rgba(img)
        return img.convert("RGBA")
    except (ValueError, OSError, KeyError) as exc:
        msg = f"Unsupported image mode {mode!r}."
        raise ImageValidationError(msg) from exc


def to_array(img: Image.Image) -> np.ndarray:
    """Return a writable ``(H, W, 4)`` uint8 array copy of ``img``."""
    return np.array(to_rgba(img), dtype=np.uint8)


def from_array(arr: np.ndarray) -> Image.Image:
    """Convert an ``(H, W[, 1|3|4])`` array into an RGBA image.

    Float arrays are rounded and clipped to 0..255. Empty or malformed arrays
    raise :class:`ImageValidationError`.
    """
    a = np.asarray(arr)
    if a.size == 0 or a.ndim not in (2, 3) or min(a.shape[:2]) < 1:
        msg = "Cannot build an image from an empty or malformed array."
        raise ImageValidationError(msg)
    if a.ndim == 2:
        a = a[..., None]
    if a.shape[2] not in (1, 3, 4):
        msg = "Image arrays must have 1, 3 or 4 channels."
        raise ImageValidationError(msg)
    if a.dtype != np.uint8:
        a = np.clip(np.rint(np.nan_to_num(a.astype(np.float64))), 0, 255).astype(np.uint8)
    if a.shape[2] == 1:
        a = np.repeat(a, 3, axis=2)
    if a.shape[2] == 3:
        alpha = np.full((*a.shape[:2], 1), 255, dtype=np.uint8)
        a = np.concatenate([a, alpha], axis=2)
    return Image.fromarray(np.ascontiguousarray(a))


def join_rgb_alpha(rgb: np.ndarray, alpha: np.ndarray) -> Image.Image:
    """Combine ``(H, W, 3)`` colour and ``(H, W)`` alpha arrays into an RGBA image."""
    return from_array(np.concatenate([rgb, alpha[..., None]], axis=2))


def resize_rgba(img: Image.Image, size: tuple[int, int], resample: Image.Resampling = _LANCZOS) -> Image.Image:
    """Resize with **premultiplied alpha** so transparent edges do not bleed dark."""
    width, height = int(size[0]), int(size[1])
    if width < 1 or height < 1:
        msg = "Target size must be at least 1x1."
        raise ImageValidationError(msg)
    rgba = to_rgba(img)
    if resample == Image.Resampling.NEAREST:
        return rgba.resize((width, height), resample)
    return rgba.convert("RGBa").resize((width, height), resample).convert("RGBA")


def fit_within(img: Image.Image, max_dim: int = MAX_WORKING_DIMENSION) -> Image.Image:
    """Return a copy no larger than ``max_dim`` on either side (aspect preserved)."""
    rgba = to_rgba(img)
    longest = max(rgba.size)
    if longest <= max_dim:
        return rgba
    scale = max_dim / longest
    new_size = (max(1, round(rgba.width * scale)), max(1, round(rgba.height * scale)))
    return resize_rgba(rgba, new_size)


def center_crop_square(img: Image.Image) -> Image.Image:
    """Crop the largest centred square from ``img``."""
    rgba = to_rgba(img)
    side = min(rgba.size)
    left = (rgba.width - side) // 2
    top = (rgba.height - side) // 2
    return rgba.crop((left, top, left + side, top + side))


def rounded_mask(size: int, radius: float, supersample: int = 4) -> Image.Image:
    """Anti-aliased ``L`` mask of a rounded square (``radius = size/2`` -> circle)."""
    size = max(1, int(size))
    big_size = size * supersample
    radius = max(0.0, min(float(radius), size / 2))
    big = Image.new("L", (big_size, big_size), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, big_size - 1, big_size - 1),
        radius=radius * supersample,
        fill=255,
    )
    return big.resize((size, size), _LANCZOS)


def rounded_rect_mask(width: int, height: int, radius: float, supersample: int = 4) -> Image.Image:
    """Anti-aliased ``L`` mask for an arbitrary rectangle with rounded corners."""
    width, height = max(1, int(width)), max(1, int(height))
    bw, bh = width * supersample, height * supersample
    max_r = min(width, height) / 2.0
    r = max(0.0, min(float(radius), max_r))
    big = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, bw - 1, bh - 1),
        radius=r * supersample,
        fill=255,
    )
    return big.resize((width, height), _LANCZOS)


def apply_mask(img: Image.Image, mask: Image.Image) -> Image.Image:
    """Multiply ``img``'s alpha by ``mask`` (same size) and return a new image."""
    out = to_rgba(img)
    if mask.size != out.size:
        msg = "Mask size does not match the image."
        raise ImageValidationError(msg)
    out.putalpha(ImageChops.multiply(out.getchannel("A"), mask.convert("L")))
    return out


def crop_circle(img: Image.Image, diameter: int) -> Image.Image:
    """Centre-crop to a square, resize to ``diameter`` and clip to a circle."""
    diameter = max(1, int(diameter))
    square = resize_rgba(center_crop_square(img), (diameter, diameter))
    return apply_mask(square, rounded_mask(diameter, diameter / 2))


def extract_dominant_palette(img: Image.Image, count: int = 6) -> list[Color]:
    """Extract ``count`` dominant RGB colours from visible pixels using Pillow quantization."""
    count = clamp_int(count, 1, 16, "count")
    rgba = fit_within(to_rgba(img), 256)
    arr = np.asarray(rgba, dtype=np.uint8)
    visible = arr[arr[..., 3] >= 32][:, :3]
    if visible.size == 0:
        return [(128, 128, 128)] * count
    sample_w = max(1, math.isqrt(len(visible)))
    sample_pixels = visible[: sample_w * sample_w].reshape(sample_w, sample_w, 3)
    pil_rgb = Image.fromarray(sample_pixels, mode="RGB")
    quantized = pil_rgb.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    raw_palette = quantized.getpalette() or []
    counts = sorted(quantized.getcolors() or [], reverse=True)
    result: list[Color] = []
    for _, idx in counts[:count]:
        base = idx * 3
        if base + 2 < len(raw_palette):
            result.append((int(raw_palette[base]), int(raw_palette[base + 1]), int(raw_palette[base + 2])))
    while len(result) < count:
        result.append(result[-1] if result else (128, 128, 128))
    return result


@dataclass(frozen=True)
class Frame:
    """One animation frame (single images use a one-element list)."""

    image: Image.Image
    duration_ms: int = 100


_EXIF_ORIENTATION = 0x0112
_ORIENTATION_OPS = {
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_270,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_90,
}


def _read_orientation(img: Image.Image) -> int:
    try:
        return int(img.getexif().get(_EXIF_ORIENTATION, 1))
    except Exception:
        return 1


def load_frames(
    data: bytes,
    *,
    max_frames: int = 1,
    max_dim: int = MAX_WORKING_DIMENSION,
) -> list[Frame]:
    """Decode untrusted bytes into RGBA frames.

    The data is validated first (:func:`inspect_image`). EXIF orientation is
    applied to every frame and frames are downscaled to ``max_dim``. Animations
    longer than ``max_frames`` are evenly sub-sampled (durations are scaled so
    playback speed is preserved). ``max_frames=1`` returns only the first frame.
    """
    info = inspect_image(data)
    max_frames = max(1, int(max_frames))
    step = 1 if max_frames == 1 else max(1, math.ceil(info.frames / max_frames))
    indices = [0] if max_frames == 1 else list(range(0, info.frames, step))
    frames: list[Frame] = []
    try:
        with Image.open(io.BytesIO(data)) as img:
            orientation = _read_orientation(img)
            for index in indices:
                if index:
                    img.seek(index)
                duration = int(img.info.get("duration", 100) or 100) * step
                frame = to_rgba(img)
                op = _ORIENTATION_OPS.get(orientation)
                if op is not None:
                    frame = frame.transpose(op)
                frames.append(Frame(fit_within(frame, max_dim), max(20, min(duration, 2000))))
    except (OSError, SyntaxError, ValueError, EOFError, Image.DecompressionBombError) as exc:
        msg = "The image appears to be corrupt or truncated."
        raise ImageValidationError(msg) from exc
    if not frames:
        msg = "The image contains no readable frames."
        raise ImageValidationError(msg)
    return frames


def load_image(data: bytes, *, max_dim: int = MAX_WORKING_DIMENSION) -> Image.Image:
    """Decode the first frame of untrusted bytes into an RGBA image."""
    return load_frames(data, max_frames=1, max_dim=max_dim)[0].image


def map_frames(
    frames: Sequence[Frame],
    fn: Callable[[Image.Image, int], Image.Image],
) -> list[Frame]:
    """Apply ``fn(image, index)`` to every frame."""
    out: list[Frame] = []
    for index, frame in enumerate(frames):
        out.append(Frame(to_rgba(fn(frame.image, index)), frame.duration_ms))
    return out


@dataclass(frozen=True)
class EncodedImage:
    """Encoded output ready to be wrapped in ``discord.File``."""

    data: bytes
    format: str
    width: int
    height: int
    frame_count: int = 1

    @property
    def extension(self) -> str:
        return {"PNG": "png", "GIF": "gif", "WEBP": "webp", "JPEG": "jpg"}[self.format]

    @property
    def content_type(self) -> str:
        ext = "jpeg" if self.format == "JPEG" else self.extension
        return f"image/{ext}"

    def to_buffer(self) -> io.BytesIO:
        """Return a fresh, rewound :class:`io.BytesIO` over the encoded bytes."""
        return io.BytesIO(self.data)


def _check_output_size(data: bytes, max_bytes: int) -> None:
    if len(data) > max_bytes:
        msg = f"The result is too large to upload ({len(data) / 1024 / 1024:.1f} MB). Try a smaller size or fewer effects."
        raise ImageValidationError(msg)


def encode_image(
    img: Image.Image,
    fmt: str = "PNG",
    *,
    quality: int = 85,
    lossless: bool = True,
    max_bytes: int = MAX_OUTPUT_BYTES,
) -> EncodedImage:
    """Encode ``img`` as PNG, WEBP, JPEG, or single-frame GIF, enforcing ``max_bytes``."""
    fmt = fmt.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    if fmt not in {"PNG", "WEBP", "JPEG", "GIF"}:
        msg = "Output format must be PNG, WEBP, JPEG or GIF."
        raise ImageValidationError(msg)
    rgba = to_rgba(img)
    buf = io.BytesIO()
    q = clamp_int(quality, 1, 100, "quality")
    if fmt == "PNG":
        rgba.save(buf, "PNG", compress_level=6)
    elif fmt == "WEBP":
        rgba.save(buf, "WEBP", lossless=lossless, quality=q)
    elif fmt == "JPEG":
        bg = Image.new("RGB", rgba.size, (24, 24, 30))
        bg.paste(rgba, mask=rgba.getchannel("A"))
        bg.save(buf, "JPEG", quality=q, optimize=True)
    else:
        rgba.save(buf, "GIF")
    data = buf.getvalue()
    _check_output_size(data, max_bytes)
    return EncodedImage(data, fmt, rgba.width, rgba.height, 1)


def encode_animation(frames: Sequence[Frame], *, max_bytes: int = MAX_OUTPUT_BYTES) -> EncodedImage:
    """Encode frames as an infinitely looping GIF (1-bit transparency).

    GIF cannot store partial alpha, so semi-transparent pixels are thresholded
    by Pillow's palette conversion. Frames beyond ``MAX_OUTPUT_FRAMES`` are
    rejected rather than silently dropped.
    """
    if not frames:
        msg = "No frames to encode."
        raise ImageValidationError(msg)
    if len(frames) > MAX_OUTPUT_FRAMES:
        msg = "Too many frames to encode."
        raise ImageValidationError(msg)
    images = [to_rgba(f.image) for f in frames]
    buf = io.BytesIO()
    images[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=images[1:],
        duration=[max(20, int(f.duration_ms)) for f in frames],
        loop=0,
        disposal=2,
        optimize=False,
    )
    data = buf.getvalue()
    _check_output_size(data, max_bytes)
    return EncodedImage(data, "GIF", images[0].width, images[0].height, len(images))


def resize_image_bytes(data: bytes, width: int, height: int) -> EncodedImage:
    """Resize static or animated image bytes to ``(width, height)``."""
    w = clamp_int(width, 16, MAX_OUTPUT_DIMENSION, "width")
    h = clamp_int(height, 16, MAX_OUTPUT_DIMENSION, "height")
    frames = load_frames(data, max_frames=MAX_OUTPUT_FRAMES)
    out = [Frame(resize_rgba(f.image, (w, h)), f.duration_ms) for f in frames]
    return encode_image(out[0].image) if len(out) == 1 else encode_animation(out)


def crop_image_bytes(
    data: bytes,
    aspect: str = "1:1",
    anchor: str = "center",
) -> EncodedImage:
    """Crop an image to a target aspect ratio (`1:1`, `16:9`, `4:3`, `9:16`, `3:4`)."""
    ratios = {"1:1": (1, 1), "16:9": (16, 9), "4:3": (4, 3), "9:16": (9, 16), "3:4": (3, 4)}
    aspect = validate_choice(aspect, tuple(ratios.keys()), "aspect")
    anchor = validate_choice(anchor, ("center", "top", "bottom", "left", "right"), "anchor")
    rw, rh = ratios[aspect]
    frames = load_frames(data, max_frames=MAX_OUTPUT_FRAMES)

    def _crop_one(img: Image.Image) -> Image.Image:
        w, h = img.size
        target_w = min(w, int(h * rw / rh))
        target_h = min(h, int(target_w * rh / rw))
        if anchor == "left":
            left = 0
        elif anchor == "right":
            left = w - target_w
        else:
            left = (w - target_w) // 2
        if anchor == "top":
            top = 0
        elif anchor == "bottom":
            top = h - target_h
        else:
            top = (h - target_h) // 2
        return img.crop((left, top, left + target_w, top + target_h))

    out = [Frame(_crop_one(f.image), f.duration_ms) for f in frames]
    return encode_image(out[0].image) if len(out) == 1 else encode_animation(out)


def convert_image_bytes(data: bytes, fmt: str = "PNG", quality: int = 85) -> EncodedImage:
    """Convert image bytes to PNG, WEBP, JPEG, or GIF."""
    fmt = validate_choice(fmt, ("png", "webp", "jpeg", "jpg", "gif"), "format").upper()
    if fmt == "JPG":
        fmt = "JPEG"
    if fmt == "GIF":
        frames = load_frames(data, max_frames=MAX_OUTPUT_FRAMES)
        return encode_animation(frames)
    img = load_image(data, max_dim=MAX_OUTPUT_DIMENSION)
    return encode_image(img, fmt=fmt, quality=quality, lossless=(fmt == "PNG"))


def compress_image_bytes(data: bytes, quality: int = 50) -> EncodedImage:
    """Compress an image into lossy JPEG at the given quality (1..95)."""
    q = clamp_int(quality, 1, 95, "quality")
    img = load_image(data, max_dim=MAX_OUTPUT_DIMENSION)
    return encode_image(img, fmt="JPEG", quality=q, lossless=False)


def reverse_gif_bytes(data: bytes) -> EncodedImage:
    """Reverse the frame order of an animated image (or mirror a static image horizontally)."""
    frames = load_frames(data, max_frames=MAX_OUTPUT_FRAMES)
    if len(frames) == 1:
        return encode_image(frames[0].image.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
    return encode_animation(list(reversed(frames)))


def speed_gif_bytes(data: bytes, factor: float = 2.0) -> EncodedImage:
    """Speed up or slow down an animated image by ``factor`` (0.25x to 4.0x)."""
    mult = clamp_float(factor, 0.25, 4.0, "factor")
    frames = load_frames(data, max_frames=MAX_OUTPUT_FRAMES)
    if len(frames) == 1:
        frames = [Frame(frames[0].image, int(100 / mult)), Frame(frames[0].image, int(100 / mult))]
    else:
        frames = [Frame(f.image, max(20, min(2000, round(f.duration_ms / mult)))) for f in frames]
    return encode_animation(frames)


def extract_frames_sheet(data: bytes, max_cols: int = 6) -> EncodedImage:
    """Extract animation frames and arrange them into a numbered sprite sheet."""
    frames = load_frames(data, max_frames=MAX_OUTPUT_FRAMES, max_dim=256)
    n = len(frames)
    cols = min(n, clamp_int(max_cols, 1, 10, "max_cols"))
    rows = math.ceil(n / cols)
    fw, fh = frames[0].image.size
    pad = 8
    header_h = 22
    cw = cols * (fw + pad) + pad
    ch = rows * (fh + header_h + pad) + pad
    canvas = Image.new("RGBA", (cw, ch), (20, 22, 28, 255))
    draw = ImageDraw.Draw(canvas)
    font = load_font(13, bold=True)
    for idx, frame in enumerate(frames):
        r, c = divmod(idx, cols)
        x = pad + c * (fw + pad)
        y = pad + r * (fh + header_h + pad)
        draw.text((x + 2, y + 2), f"#{idx + 1} ({frame.duration_ms}ms)", fill=(210, 215, 225, 255), font=font)
        canvas.alpha_composite(frame.image, dest=(x, y + header_h))
    return encode_image(fit_within(canvas, MAX_OUTPUT_DIMENSION))


def stack_images_bytes(
    data_a: bytes,
    data_b: bytes,
    direction: str = "hstack",
    gap: int = 8,
) -> EncodedImage:
    """Stack two images horizontally (`hstack`) or vertically (`vstack`), matching edge size."""
    direction = validate_choice(direction, ("hstack", "vstack", "horizontal", "vertical"), "direction")
    gap_px = clamp_int(gap, 0, 64, "gap")
    img_a = load_image(data_a, max_dim=1024)
    img_b = load_image(data_b, max_dim=1024)
    if direction in ("hstack", "horizontal"):
        h = min(max(img_a.height, img_b.height), 1024)
        wa = max(1, round(img_a.width * (h / img_a.height)))
        wb = max(1, round(img_b.width * (h / img_b.height)))
        ra, rb = resize_rgba(img_a, (wa, h)), resize_rgba(img_b, (wb, h))
        canvas = Image.new("RGBA", (wa + wb + gap_px, h), (20, 22, 28, 255))
        canvas.alpha_composite(ra, (0, 0))
        canvas.alpha_composite(rb, (wa + gap_px, 0))
    else:
        w = min(max(img_a.width, img_b.width), 1024)
        ha = max(1, round(img_a.height * (w / img_a.width)))
        hb = max(1, round(img_b.height * (w / img_b.width)))
        ra, rb = resize_rgba(img_a, (w, ha)), resize_rgba(img_b, (w, hb))
        canvas = Image.new("RGBA", (w, ha + hb + gap_px), (20, 22, 28, 255))
        canvas.alpha_composite(ra, (0, 0))
        canvas.alpha_composite(rb, (0, ha + gap_px))
    return encode_image(fit_within(canvas, MAX_OUTPUT_DIMENSION))
