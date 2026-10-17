"""Loading, conversion, resizing, cropping and encoding helpers.

All functions are pure with respect to their arguments: caller-owned
``PIL.Image.Image`` objects are never modified; a new image is returned.
Everything is normalised to **RGBA / uint8** before NumPy work happens.
"""

from __future__ import annotations

import io
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from .image_validators import MAX_OUTPUT_BYTES, MAX_OUTPUT_FRAMES, MAX_WORKING_DIMENSION, ImageValidationError, inspect_image, normalize_seed

_LANCZOS = Image.Resampling.LANCZOS


def make_rng(seed: int | None) -> np.random.Generator:
    """Return an isolated :class:`numpy.random.Generator` (never global state)."""
    return np.random.default_rng(normalize_seed(seed))


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
    """Return a **new** RGBA copy of ``img`` (handles L, LA, P, 1, CMYK, I;16 \N{HORIZONTAL ELLIPSIS})."""
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

    Float arrays are rounded and clipped to 0\N{TWO DOT LEADER}255. Empty or malformed arrays
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
    """Anti-aliased ``L`` mask of a rounded square (``radius = size/2`` \N{RIGHTWARDS ARROW} circle)."""
    size = max(1, int(size))
    big_size = size * supersample
    radius = max(0.0, min(float(radius), size / 2))
    big = Image.new("L", (big_size, big_size), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, big_size - 1, big_size - 1), radius=radius * supersample, fill=255)
    return big.resize((size, size), _LANCZOS)


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
    """Apply ``fn(image, index)`` to every frame, checking the deadline between frames."""
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
        return {"PNG": "png", "GIF": "gif", "WEBP": "webp"}[self.format]

    @property
    def content_type(self) -> str:
        return f"image/{self.extension}"

    def to_buffer(self) -> io.BytesIO:
        """Return a fresh, rewound :class:`io.BytesIO` over the encoded bytes."""
        return io.BytesIO(self.data)


def _check_output_size(data: bytes, max_bytes: int) -> None:
    if len(data) > max_bytes:
        msg = f"The result is too large to upload ({len(data) / 1024 / 1024:.1f} MB). Try a smaller size or fewer effects."
        raise ImageValidationError(msg)


def encode_image(img: Image.Image, fmt: str = "PNG", *, max_bytes: int = MAX_OUTPUT_BYTES) -> EncodedImage:
    """Encode ``img`` as PNG or lossless WebP, enforcing ``max_bytes``."""
    fmt = fmt.upper()
    if fmt not in {"PNG", "WEBP"}:
        msg = "Output format must be PNG or WEBP."
        raise ImageValidationError(msg)
    rgba = to_rgba(img)
    buf = io.BytesIO()
    if fmt == "PNG":
        rgba.save(buf, "PNG", compress_level=6)
    else:
        rgba.save(buf, "WEBP", lossless=True)
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
        duration=[f.duration_ms for f in frames],
        loop=0,
        disposal=2,
        optimize=False,
    )
    data = buf.getvalue()
    _check_output_size(data, max_bytes)
    return EncodedImage(data, "GIF", images[0].width, images[0].height, len(images))
