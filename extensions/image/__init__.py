from __future__ import annotations

import asyncio
import io
import logging
import random
import secrets
from typing import TYPE_CHECKING, Annotated, Literal

import discord
from discord.ext import commands

from .utils.image_effects import ascii_from_bytes, process_image_bytes
from .utils.image_generator import render_avatar_frame, render_collage, render_generator
from .utils.image_utils import EncodedImage
from .utils.image_validators import MAX_DOWNLOAD_BYTES, ImageValidationError, clamp_float, clamp_int, parse_color_list, parse_hex_color

logger = logging.getLogger(__name__)

MAX_CONCURRENT_JOBS = 3
MAX_QUEUED_JOBS = 8
JOB_TIMEOUT = 25.0
DOWNLOAD_TIMEOUT = 15.0
USER_COOLDOWN = 4.0
DEFAULT_UPLOAD_LIMIT = 8 * 1024 * 1024
ASCII_MAX_CHARS = 1900
MAX_COLLAGE_MEMBERS = 16

_RANGES: dict[str, tuple[float, float]] = {
    "pixel_size": (2, 128),
    "intensity": (0.0, 1.0),
    "levels": (2, 32),
    "angle": (-360.0, 360.0),
    "columns": (8, 120),
    "scale_noise": (2, 256),
    "octaves": (1, 8),
    "complexity": (1, 12),
    "scale_plasma": (0.25, 8.0),
    "iterations": (10, 400),
    "zoom": (0.1, 100_000.0),
    "points": (2, 300),
    "shapes": (1, 200),
    "folds": (2, 16),
    "cell_size": (4, 256),
}


class RateLimited(commands.CheckFailure):
    """Raised when a user runs commands too quickly."""

    def __init__(self, retry_after: float) -> None:
        super().__init__(f"Rate limited for {retry_after:.1f}s")
        self.retry_after = retry_after


class BusyError(Exception):
    """Raised when the job queue is full."""


def _num(name: str, value: object):
    """Clamp ``value`` using the ``_RANGES`` table (int if the bounds are ints)."""
    lo, hi = _RANGES[name]
    if isinstance(lo, int) and isinstance(hi, int):
        return clamp_int(value, lo, hi, name.split("_", maxsplit=1)[0])
    return clamp_float(value, lo, hi, name.split("_", maxsplit=1)[0])


def _dims(width: object, height: object, heavy: bool = False) -> tuple[int, int]:
    top = 1024 if heavy else 2048
    return clamp_int(width, 16, top, "width"), clamp_int(height, 16, top, "height")


class ImageCog(commands.Cog, name="Image"):
    """Avatar effects, procedural art and avatar compositions."""

    help_emoji = "\N{FRAME WITH PICTURE}\N{VARIATION SELECTOR-16}"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _fetch_avatar(self, member: discord.abc.User, *, animated: bool, size: int) -> tuple[bytes, bool]:
        """Download ``member``'s display avatar. Returns ``(bytes, is_animated_gif)``.

        Animated avatars are requested as GIF only when ``animated`` is true;
        otherwise (or if the asset cannot be resized) a static PNG is used.
        """
        asset = member.display_avatar
        use_gif = animated and asset.is_animated()
        try:
            asset = asset.replace(size=size, format="gif" if use_gif else "png")
        except ValueError:
            asset, use_gif = member.display_avatar, False
        data = await asyncio.wait_for(asset.read(), DOWNLOAD_TIMEOUT)
        if len(data) > MAX_DOWNLOAD_BYTES:
            msg = "That avatar is too large to process."
            raise ImageValidationError(msg)
        return data, use_gif

    async def _load_source(
        self,
        target: discord.abc.User,
        attachment: discord.Attachment | None = None,
        *,
        animated: bool,
    ) -> tuple[bytes, bool]:
        """Return image bytes from an attachment (preferred) or the target's avatar.

        Remote URLs are never fetched; attachments are downloaded through
        discord.py after checking their declared size and content type. The
        bytes themselves are fully validated again inside ``utils``.
        """
        if attachment is None:
            return await self._fetch_avatar(target, animated=animated, size=256 if animated else 512)
        if attachment.size > MAX_DOWNLOAD_BYTES:
            msg = f"That attachment is too large (limit {MAX_DOWNLOAD_BYTES // 1024 // 1024} MB)."
            raise ImageValidationError(msg)
        kind = (attachment.content_type or "").split(";")[0].strip().lower()
        if kind and not kind.startswith("image/"):
            msg = "That attachment is not an image."
            raise ImageValidationError(msg)
        data = await asyncio.wait_for(attachment.read(), DOWNLOAD_TIMEOUT)
        return data, kind == "image/gif"

    @staticmethod
    def _check_upload_size(ctx: commands.Context, enc: EncodedImage) -> None:
        limit = ctx.guild.filesize_limit if ctx.guild else DEFAULT_UPLOAD_LIMIT
        if len(enc.data) > limit:
            msg = f"The result ({len(enc.data) / 1024 / 1024:.1f} MB) exceeds this server's upload limit."
            raise ImageValidationError(msg)

    async def _send_image(
        self,
        ctx: commands.Context,
        enc: EncodedImage,
        title: str,
        fields: dict[str, object],
        *,
        stem: str,
        note: str | None = None,
    ) -> None:
        """Send ``enc`` as an attachment inside an informative embed."""
        self._check_upload_size(ctx, enc)
        filename = f"{stem}.{enc.extension}"
        file = discord.File(io.BytesIO(enc.data), filename=filename)
        embed = discord.Embed(title=title, description=note, colour=discord.Colour.blurple())
        for name, value in fields.items():
            embed.add_field(name=name, value=str(value)[:1024], inline=True)
        embed.set_image(url=f"attachment://{filename}")
        kind = f"{enc.frame_count} frames" if enc.frame_count > 1 else enc.format
        embed.set_footer(text=f"{enc.width}\N{MULTIPLICATION SIGN}{enc.height} \N{BULLET} {kind}")
        await ctx.send(embed=embed, file=file, allowed_mentions=discord.AllowedMentions.none())

    async def _run_effect(
        self,
        ctx: commands.Context,
        member: discord.Member | None,
        effect: str,
        title: str,
        params: dict[str, object],
        display: dict[str, object],
    ) -> None:
        """Shared pipeline for every avatar/attachment effect command."""
        await ctx.typing()
        target = member or ctx.author
        if "seed" in params:
            if params["seed"] is None:
                params["seed"] = secrets.randbelow(2**31)
            display["Seed"] = params["seed"]
        data, animated = await self._load_source(target, animated=True)
        note = None
        try:
            enc = await asyncio.to_thread(process_image_bytes, data, effect, params)
            self._check_upload_size(ctx, enc)
        except ImageValidationError as exc:
            if not (animated):
                raise
            logger.info("Animated avatar fallback for %s: %s", effect, exc)
            data, _ = await self._load_source(target, None, animated=False)
            enc = await asyncio.to_thread(process_image_bytes, data, effect, params)
            note = "The animated avatar was too heavy to process, so its first frame was used."
        await self._send_image(ctx, enc, title, display, stem=effect, note=note)

    async def _run_generator(
        self,
        ctx: commands.Context,
        name: str,
        title: str,
        params: dict[str, object],
        display: dict[str, object],
    ) -> None:
        """Shared pipeline for every procedural generator command."""
        await ctx.typing()
        if params.get("seed") is None:
            params["seed"] = secrets.randbelow(2**31)
        display["Seed"] = params["seed"]
        enc = await asyncio.to_thread(render_generator, name, params)
        await self._send_image(ctx, enc, title, display, stem=name)

    @commands.command(name="pixelate")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pixelate(
        self,
        ctx: commands.Context,
        pixel_size: commands.Range[int, 2, 128] = commands.parameter(description="Block size in pixels (2-128)", default=8),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Pixelate an avatar or image."""
        size = _num("pixel_size", pixel_size)
        await self._run_effect(ctx, member, "pixelate", "Pixelate", {"pixel_size": size}, {"Pixel size": size})

    @commands.command(name="glitch")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def glitch(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
        intensity: commands.Range[float, 0.0, 1.0] = commands.parameter(description="0.0 (subtle) to 1.0 (heavy)", default=0.5),  # noqa: B008
        seed: int | None = commands.parameter(description="Reuse a seed to reproduce a result", default=None),
    ) -> None:
        """Apply a digital glitch effect."""
        level = _num("intensity", intensity)
        await self._run_effect(ctx, member, "glitch", "Glitch", {"intensity": level, "seed": seed}, {"Intensity": f"{level:.2f}"})

    @commands.command(name="invert")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def invert(
        self,
        ctx: commands.Context,
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Invert colours (transparency is kept)."""
        await self._run_effect(ctx, member, "invert", "Invert", {}, {})

    @commands.command(name="grayscale")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def grayscale(
        self,
        ctx: commands.Context,
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Convert an avatar to grayscale."""
        await self._run_effect(ctx, member, "grayscale", "Grayscale", {}, {})

    @commands.command(name="posterize")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def posterize(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
        levels: commands.Range[int, 2, 32] = commands.parameter(description="Levels per colour channel (2-32)", default=4),  # noqa: B008
    ) -> None:
        """Reduce the number of colour levels."""
        n = _num("levels", levels)
        await self._run_effect(ctx, member, "posterize", "Posterize", {"levels": n}, {"Levels": n})

    @commands.command(name="duotone")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def duotone(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
        shadow_color: str = commands.parameter(description="Dark colour, e.g. #140a3c", default="#140a3c"),
        highlight_color: str = commands.parameter(description="Light colour, e.g. #ffc850", default="#ffc850"),
    ) -> None:
        """Apply a two-colour palette."""
        shadow = parse_hex_color(shadow_color, "shadow_color")
        light = parse_hex_color(highlight_color, "highlight_color")
        await self._run_effect(
            ctx,
            member,
            "duotone",
            "Duotone",
            {"shadow_color": shadow, "highlight_color": light},
            {"Shadow": "#{:02x}{:02x}{:02x}".format(*shadow), "Highlight": "#{:02x}{:02x}{:02x}".format(*light)},
        )

    @commands.command(name="mirror")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def mirror(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
        mode: Literal["left", "right", "top", "bottom", "quad"] = commands.parameter(description="Which half to mirror", default="left"),
    ) -> None:
        """Create a mirrored composition."""
        await self._run_effect(ctx, member, "mirror", "Mirror", {"mode": mode}, {"Mode": mode})

    @commands.command(name="spin")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def spin(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
        angle: commands.Range[float, -360.0, 360.0] = commands.parameter(description="Counter-clockwise degrees (-360 to 360)", default=90.0),  # noqa: B008
    ) -> None:
        """Rotate an avatar with transparent padding."""
        deg = _num("angle", angle)
        await self._run_effect(ctx, member, "spin", "Spin", {"angle": deg, "expand": True}, {"Angle": f"{deg:g}\N{DEGREE SIGN}"})

    @commands.command(name="edge")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def edge(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(  # noqa: B008
            description="Whose avatar to use (default: you)",
            default=lambda ctx: ctx.author,
        ),
    ) -> None:
        """Apply an edge-detection effect."""
        await self._run_effect(ctx, member, "edge", "Edge detection", {}, {})

    @commands.command(name="ascim")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def ascii_command(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(  # noqa: B008
            description="Whose avatar to use (default: you)",
            default=lambda ctx: ctx.author,
        ),
        columns: commands.Range[int, 8, 120] = commands.parameter(  # noqa: B008
            description="Width in characters (8-120)",
            default=60,
        ),
        invert: bool = commands.parameter(
            description="Swap light and dark characters",
            default=False,
        ),
    ) -> None:
        """Convert an image into ASCII art."""
        cols = _num("columns", columns)

        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False)
        text = await asyncio.to_thread(
            ascii_from_bytes,
            data,
            int(cols),
            invert_ramp=bool(invert),
            max_chars=ASCII_MAX_CHARS,
        )
        await ctx.send(
            f"```\n{text}\n```",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.command(name="gradient")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def gradient(
        self,
        ctx: commands.Context,
        kind: Literal["linear", "radial", "multicolor"] = commands.parameter(
            description="Gradient type",
            default="linear",
        ),
        colors: str | None = commands.parameter(
            description="Comma-separated hex colours; random if omitted",
            default=None,
        ),
        angle: commands.Range[float, 0.0, 360.0] = commands.parameter(  # noqa: B008
            description="Direction in degrees",
            default=45.0,
        ),
        width: commands.Range[int, 16, 2048] = commands.parameter(  # noqa: B008
            description="Image width in pixels (16-2048)",
            default=768,
        ),
        height: commands.Range[int, 16, 2048] = commands.parameter(  # noqa: B008
            description="Image height in pixels (16-2048)",
            default=768,
        ),
        seed: int | None = commands.parameter(
            description="Seed for reproducible output",
            default=None,
        ),
    ) -> None:
        """Generate a linear, radial, or multicolour gradient."""
        w, h = _dims(width, height)
        deg = _num("angle", angle)
        palette = parse_color_list(colors, min_count=2)

        params = {
            "width": w,
            "height": h,
            "kind": kind,
            "colors": palette or None,
            "angle": deg,
            "seed": seed,
        }
        await self._run_generator(
            ctx,
            "gradient",
            "Gradient",
            params,
            {
                "Kind": kind,
                "Angle": f"{deg:g}\N{DEGREE SIGN}",
                "Size": f"{w}\N{MULTIPLICATION SIGN}{h}",
            },
        )

    @commands.command(name="noise")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def noise(
        self,
        ctx: commands.Context,
        kind: Literal["gray", "color", "value", "fractal"] = commands.parameter(
            description="Noise type",
            default="fractal",
        ),
        scale: commands.Range[int, 2, 256] = commands.parameter(  # noqa: B008
            description="Feature size (2-256)",
            default=48,
        ),
        octaves: commands.Range[int, 1, 8] = commands.parameter(  # noqa: B008
            description="Detail layers (1-8)",
            default=4,
        ),
        colors: str | None = commands.parameter(
            description="Optional comma-separated colour palette",
            default=None,
        ),
        width: commands.Range[int, 16, 2048] = commands.parameter(  # noqa: B008
            description="Image width in pixels (16-2048)",
            default=768,
        ),
        height: commands.Range[int, 16, 2048] = commands.parameter(  # noqa: B008
            description="Image height in pixels (16-2048)",
            default=768,
        ),
        seed: int | None = commands.parameter(
            description="Seed for reproducible output",
            default=None,
        ),
    ) -> None:
        """Generate random or procedural noise."""
        w, h = _dims(width, height)
        sc = _num("scale_noise", scale)
        octs = _num("octaves", octaves)

        params = {
            "width": w,
            "height": h,
            "kind": kind,
            "scale": sc,
            "octaves": octs,
            "colors": parse_color_list(colors, min_count=2) or None,
            "seed": seed,
        }
        await self._run_generator(
            ctx,
            "noise",
            "Noise",
            params,
            {"Kind": kind, "Scale": sc, "Size": f"{w}\N{MULTIPLICATION SIGN}{h}"},
        )

    @commands.command(name="plasma")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def plasma(
        self,
        ctx: commands.Context,
        complexity: commands.Range[int, 1, 12] = commands.parameter(  # noqa: B008
            description="Number of wave terms (1-12)",
            default=5,
        ),
        scale: commands.Range[float, 0.25, 8.0] = commands.parameter(  # noqa: B008
            description="Frequency multiplier (0.25-8)",
            default=1.0,
        ),
        colors: str | None = commands.parameter(
            description="Optional palette; random if omitted",
            default=None,
        ),
        width: commands.Range[int, 16, 2048] = commands.parameter(  # noqa: B008
            description="Image width in pixels (16-2048)",
            default=768,
        ),
        height: commands.Range[int, 16, 2048] = commands.parameter(  # noqa: B008
            description="Image height in pixels (16-2048)",
            default=768,
        ),
        seed: int | None = commands.parameter(
            description="Seed for reproducible output",
            default=None,
        ),
    ) -> None:
        """Generate a colourful plasma image."""
        w, h = _dims(width, height)
        c = _num("complexity", complexity)
        sc = _num("scale_plasma", scale)

        params = {
            "width": w,
            "height": h,
            "complexity": c,
            "scale": sc,
            "colors": parse_color_list(colors, min_count=2) or None,
            "seed": seed,
        }
        await self._run_generator(
            ctx,
            "plasma",
            "Plasma",
            params,
            {"Complexity": c, "Scale": f"{sc:g}", "Size": f"{w}\N{MULTIPLICATION SIGN}{h}"},
        )

    @commands.command(name="fractal")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def fractal(
        self,
        ctx: commands.Context,
        kind: Literal["mandelbrot", "julia"] = commands.parameter(
            description="Fractal type",
            default="mandelbrot",
        ),
        iterations: commands.Range[int, 10, 400] = commands.parameter(  # noqa: B008
            description="Maximum iterations (10-400)",
            default=100,
        ),
        zoom: commands.Range[float, 0.1, 100000.0] = commands.parameter(  # noqa: B008
            description="Magnification (0.1-100000)",
            default=1.0,
        ),
        colors: str | None = commands.parameter(
            description="Optional colour palette",
            default=None,
        ),
        width: commands.Range[int, 16, 1024] = commands.parameter(  # noqa: B008
            description="Image width in pixels (16-1024)",
            default=768,
        ),
        height: commands.Range[int, 16, 1024] = commands.parameter(  # noqa: B008
            description="Image height in pixels (16-1024)",
            default=768,
        ),
        seed: int | None = commands.parameter(
            description="Seed for Julia parameters and palette",
            default=None,
        ),
    ) -> None:
        """Generate a Mandelbrot or Julia fractal."""
        w, h = _dims(width, height, heavy=True)
        it = _num("iterations", iterations)
        z = _num("zoom", zoom)

        params = {
            "width": w,
            "height": h,
            "kind": kind,
            "iterations": it,
            "zoom": z,
            "colors": parse_color_list(colors, min_count=2) or None,
            "seed": seed,
        }
        await self._run_generator(
            ctx,
            "fractal",
            f"{kind.title()} fractal",
            params,
            {
                "Iterations": it,
                "Zoom": f"{z:g}\N{MULTIPLICATION SIGN}",
                "Size": f"{w}\N{MULTIPLICATION SIGN}{h}",
            },
        )

    @commands.command(name="voronoi")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def voronoi(
        self,
        ctx: commands.Context,
        points: commands.Range[int, 2, 300] = commands.parameter(  # noqa: B008
            description="Number of cells (2-300)",
            default=40,
        ),
        colors: str | None = commands.parameter(
            description="Optional cell colour palette",
            default=None,
        ),
        edges: bool = commands.parameter(
            description="Draw cell borders",
            default=True,
        ),
        width: commands.Range[int, 16, 1024] = commands.parameter(  # noqa: B008
            description="Image width in pixels (16-1024)",
            default=768,
        ),
        height: commands.Range[int, 16, 1024] = commands.parameter(  # noqa: B008
            description="Image height in pixels (16-1024)",
            default=768,
        ),
        seed: int | None = commands.parameter(
            description="Seed for reproducible output",
            default=None,
        ),
    ) -> None:
        """Generate a Voronoi cell pattern."""
        w, h = _dims(width, height, heavy=True)
        n = _num("points", points)

        params = {
            "width": w,
            "height": h,
            "points": n,
            "edges": bool(edges),
            "colors": parse_color_list(colors, min_count=1) or None,
            "seed": seed,
        }
        await self._run_generator(
            ctx,
            "voronoi",
            "Voronoi",
            params,
            {
                "Points": n,
                "Edges": "on" if edges else "off",
                "Size": f"{w}\N{MULTIPLICATION SIGN}{h}",
            },
        )

    @commands.command(name="geometric")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def geometric(
        self,
        ctx: commands.Context,
        shapes: commands.Range[int, 1, 200] = commands.parameter(description="Number of shapes (1-200)", default=28),  # noqa: B008
        symmetry: Literal["radial", "mirror", "none"] = commands.parameter(description="Symmetry mode", default="radial"),
        folds: commands.Range[int, 2, 16] = commands.parameter(description="Rotations for radial symmetry (2-16)", default=6),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional palette", default=None),
        width: commands.Range[int, 16, 2048] = commands.parameter(description="Pixels (16-2048)", default=768),  # noqa: B008
        height: commands.Range[int, 16, 2048] = commands.parameter(description="Pixels (16-2048)", default=768),  # noqa: B008
        seed: int | None = commands.parameter(description="Reuse a seed to reproduce a result", default=None),
    ) -> None:
        """Generate abstract geometric art."""
        w, h = _dims(width, height)
        count, f = _num("shapes", shapes), _num("folds", folds)
        params = {
            "width": w,
            "height": h,
            "shapes": count,
            "symmetry": symmetry,
            "folds": f,
            "colors": parse_color_list(colors, min_count=1) or None,
            "seed": seed,
        }
        await self._run_generator(
            ctx, "geometric", "Geometric art", params, {"Shapes": count, "Symmetry": symmetry, "Size": f"{w}\N{MULTIPLICATION SIGN}{h}"}
        )

    @commands.command(name="pattern")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pattern(
        self,
        ctx: commands.Context,
        kind: Literal["checkerboard", "waves", "concentric", "tiles"] = commands.parameter(description="Pattern type", default="checkerboard"),
        cell_size: commands.Range[int, 4, 256] = commands.parameter(description="Cell / wavelength / ring width in pixels (4-256)", default=64),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional palette", default=None),
        width: commands.Range[int, 16, 2048] = commands.parameter(description="Pixels (16-2048)", default=768),  # noqa: B008
        height: commands.Range[int, 16, 2048] = commands.parameter(description="Pixels (16-2048)", default=768),  # noqa: B008
        seed: int | None = commands.parameter(description="Reuse a seed to reproduce a result", default=None),
    ) -> None:
        """Generate checkerboards, waves, rings or tiles."""
        w, h = _dims(width, height)
        cs = _num("cell_size", cell_size)
        params = {
            "width": w,
            "height": h,
            "kind": kind,
            "cell_size": cs,
            "colors": parse_color_list(colors, min_count=1) or None,
            "seed": seed,
        }
        await self._run_generator(ctx, "pattern", f"Pattern: {kind}", params, {"Cell size": cs, "Size": f"{w}\N{MULTIPLICATION SIGN}{h}"})

    @commands.command(name="avatarframe")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def avatarframe(
        self,
        ctx: commands.Context,
        style: Literal["neon", "plasma", "geometric", "rainbow", "gold"] = commands.parameter(description="Frame style", default="neon"),
        member: discord.Member | None = commands.parameter(description="Whose avatar to use (default: you)", default=lambda ctx: ctx.author),  # noqa: B008
        seed: int | None = commands.parameter(description="Reuse a seed to reproduce plasma / geometric backgrounds", default=None),
    ) -> None:
        """Put an avatar in a decorative generated frame."""
        await ctx.typing()
        if seed is None:
            seed = secrets.randbelow(2**31)
        data, _ = await self._fetch_avatar(member or ctx.author, animated=False, size=512)
        enc = await asyncio.to_thread(render_avatar_frame, data, style, seed)
        await self._send_image(ctx, enc, "Avatar frame", {"Style": style, "Seed": seed}, stem="avatarframe")

    @commands.command(name="pfpcollage")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pfpcollage(
        self,
        ctx: commands.Context,
        layout: Literal["grid", "row", "column", "circle"] = commands.parameter(description="Collage layout", default="grid"),
        members: Annotated[list[discord.Member], commands.Greedy[discord.Member]] = commands.parameter(  # noqa: B008
            description="Mentions or IDs (up to 16). Empty = you plus random members", default=[]
        ),
        seed: int | None = commands.parameter(description="Shuffles order / random picks; reuse to reproduce", default=None),
    ) -> None:
        """Combine server members' avatars into a collage."""
        await ctx.typing()
        guild = ctx.guild
        if TYPE_CHECKING:
            assert guild is not None
            assert isinstance(ctx.author, discord.Member)

        if not members:
            rng = random.Random(seed)
            pool = [m for m in guild.members if not m.bot and m.id != ctx.author.id]
            members = [ctx.author, *rng.sample(pool, min(7, len(pool)))]

        fetched = await asyncio.gather(*(self._fetch_avatar(m, animated=False, size=256) for m in members))
        enc = await asyncio.to_thread(render_collage, [data for data, _ in fetched], layout, seed)
        fields: dict[str, object] = {"Layout": layout, "Avatars": len(members)}
        if seed is not None:
            fields["Seed"] = seed
        await self._send_image(ctx, enc, "Avatar collage", fields, stem="pfpcollage")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ImageCog(bot))
