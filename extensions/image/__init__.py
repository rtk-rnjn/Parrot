from __future__ import annotations

import asyncio
import io
import logging
import random
import secrets
from typing import TYPE_CHECKING, Annotated, Literal

import discord
from discord.ext import commands

from .utils.image_effects import (
    EFFECT_REGISTRY,
    ascii_from_bytes,
    braille_from_bytes,
    colored_ascii_from_bytes,
    emoji_mosaic_from_bytes,
    process_effect_chain,
    process_image_bytes,
    render_animated_effect,
    render_before_after,
    render_contact_sheet,
)
from .utils.image_generator import (
    CARD_STYLES,
    GENERATORS,
    palette_wallpaper_from_bytes,
    render_avatar_frame,
    render_avatar_swap,
    render_barcode,
    render_card_template,
    render_collage,
    render_colorblind_sim,
    render_colorinfo,
    render_compare,
    render_contrast_checker,
    render_generator,
    render_meme,
    render_palette_swatches,
    render_photomosaic,
    render_pride_overlay,
    render_profile_card,
    render_qrcode,
    render_quote_card,
    render_ship,
    render_speech_bubble,
)
from .utils.image_utils import (
    EncodedImage,
    compress_image_bytes,
    convert_image_bytes,
    crop_image_bytes,
    extract_frames_sheet,
    resize_image_bytes,
    reverse_gif_bytes,
    speed_gif_bytes,
    stack_images_bytes,
)
from .utils.image_validators import MAX_DOWNLOAD_BYTES, ImageValidationError, clamp_float, clamp_int, inspect_image, parse_color_list, parse_hex_color

if TYPE_CHECKING:
    from core import Bot

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT = 15.0
DEFAULT_UPLOAD_LIMIT = 8 * 1024 * 1024
ASCII_MAX_CHARS = 1900

MAX_CONCURRENT_JOBS = 3
MAX_QUEUED_JOBS = 8
JOB_TIMEOUT = 25.0
USER_COOLDOWN = 4.0
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


def _num(name: str, value: object):
    """Clamp ``value`` using the ``_RANGES`` table (int if the bounds are ints)."""
    lo, hi = _RANGES[name]
    if isinstance(lo, int) and isinstance(hi, int):
        return clamp_int(value, lo, hi, name.split("_", maxsplit=1)[0])
    return clamp_float(value, lo, hi, name.split("_", maxsplit=1)[0])


def _dims(width: object, height: object, heavy: bool = False) -> tuple[int, int]:
    top = 1024 if heavy else 2048
    return clamp_int(width, 16, top, "width"), clamp_int(height, 16, top, "height")


class ImageCogBase:
    """Shared base pipeline for all Image Cog extension mixins.

    Automatically detects attachments on the invoking message OR on a replied-to
    message before falling back to the target user's display avatar.
    """

    bot: Bot

    async def _fetch_avatar(self, member: discord.abc.User, *, animated: bool, size: int) -> tuple[bytes, bool]:
        """Download ``member``'s display avatar. Returns ``(bytes, is_animated_gif)``."""
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

    async def _resolve_context_attachment(
        self,
        ctx: commands.Context[Bot],
        explicit: discord.Attachment | None = None,
    ) -> discord.Attachment | None:
        """Return an explicit attachment, a message attachment, or a replied-to message's image attachment."""
        if explicit is not None:
            return explicit

        if ctx is None or ctx.message is None:
            return None

        if ctx.message.attachments:
            return ctx.message.attachments[0]

        ref = ctx.message.reference
        if ref is not None:
            resolved = ref.resolved
            if resolved is None and ref.message_id and ctx.channel:
                try:
                    resolved = await ctx.channel.fetch_message(ref.message_id)
                except discord.HTTPException:
                    resolved = None

            if isinstance(resolved, discord.Message) and resolved.attachments:
                return resolved.attachments[0]

        return None

    async def _load_source(
        self,
        target: discord.abc.User,
        attachment: discord.Attachment | None = None,
        *,
        animated: bool,
        ctx: commands.Context[Bot],
    ) -> tuple[bytes, bool]:
        """Return image bytes from an attachment/reply (if no explicit member override) or target's avatar."""
        resolved_att = await self._resolve_context_attachment(ctx, attachment)

        use_attachment = attachment is not None or (resolved_att is not None and (ctx is None or target.id == ctx.author.id))
        if not use_attachment or resolved_att is None:
            return await self._fetch_avatar(target, animated=animated, size=256 if animated else 512)

        if resolved_att.size > MAX_DOWNLOAD_BYTES:
            msg = f"That attachment is too large (limit {MAX_DOWNLOAD_BYTES // 1024 // 1024} MB)."
            raise ImageValidationError(msg)

        kind = (resolved_att.content_type or "").split(";")[0].strip().lower()
        if kind and not kind.startswith("image/"):
            msg = "That attachment is not an image."
            raise ImageValidationError(msg)

        data = await asyncio.wait_for(resolved_att.read(), DOWNLOAD_TIMEOUT)
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
        member: discord.Member | discord.User | None,
        effect: str,
        title: str,
        params: dict[str, object],
        display: dict[str, object],
    ) -> None:
        """Shared pipeline for every avatar/attachment/reply effect command."""
        await ctx.typing()
        target = member or ctx.author
        if "seed" in params:
            if params["seed"] is None:
                params["seed"] = secrets.randbelow(2**31)
            display["Seed"] = params["seed"]
        data, animated = await self._load_source(target, animated=True, ctx=ctx)
        note = None
        try:
            enc = await asyncio.to_thread(process_image_bytes, data, effect, params)
            self._check_upload_size(ctx, enc)
        except ImageValidationError as exc:
            if not animated:
                raise
            logger.info("Animated avatar fallback for %s: %s", effect, exc)
            data, _ = await self._load_source(target, None, animated=False, ctx=ctx)
            enc = await asyncio.to_thread(process_image_bytes, data, effect, params)
            note = "The animated source was too heavy to process, so its first frame was used."
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


class ImageCog(ImageCogBase, commands.Cog, name="Image"):
    """Avatar effects, procedural art, animations, cards, utilities, and avatar compositions."""

    help_emoji = "\N{FRAME WITH PICTURE}\N{VARIATION SELECTOR-16}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

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
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
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
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
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

        fetched = await asyncio.gather(*(self._fetch_avatar(m, animated=False, size=256) for m in members[:MAX_COLLAGE_MEMBERS]))
        enc = await asyncio.to_thread(render_collage, [data for data, _ in fetched], layout, seed)
        fields: dict[str, object] = {"Layout": layout, "Avatars": len(fetched)}
        if seed is not None:
            fields["Seed"] = seed
        await self._send_image(ctx, enc, "Avatar collage", fields, stem="pfpcollage")

    @commands.command(name="gaussian")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def gaussian_cmd(
        self,
        ctx: commands.Context[Bot],
        radius: Annotated[float, commands.Range[float, 0.5, 32.0]] = commands.parameter(description="Blur radius (0.5-32)", default=6.0),
        *,
        member: discord.Member = commands.parameter(description="Whose avatar to use", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Apply a smooth Gaussian blur."""
        r = clamp_float(radius, 0.5, 32.0, "radius")
        await self._run_effect(ctx, member, "gaussian", "Gaussian Blur", {"radius": r}, {"Radius": f"{r:g}px"})

    @commands.command(name="motionblur")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def motionblur_cmd(
        self,
        ctx: commands.Context[Bot],
        size: Annotated[int, commands.Range[int, 3, 45]] = commands.parameter(description="Streak length in pixels (3-45)", default=15),
        angle: Annotated[float, commands.Range[float, -180.0, 180.0]] = commands.parameter(description="Direction in degrees", default=0.0),
        *,
        member: discord.Member = commands.parameter(description="Whose avatar to use", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Apply directional motion blur."""
        await self._run_effect(ctx, member, "motionblur", "Motion Blur", {"size": size, "angle": angle}, {"Size": size, "Angle": f"{angle:g}°"})

    @commands.command(name="zoomblur")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def zoomblur_cmd(
        self,
        ctx: commands.Context[Bot],
        strength: Annotated[float, commands.Range[float, 0.01, 0.5]] = commands.parameter(description="Zoom blur intensity (0.01-0.5)", default=0.15),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply a radial centre zoom blur."""
        await self._run_effect(ctx, member, "zoomblur", "Zoom Blur", {"strength": strength}, {"Strength": f"{strength:.2f}"})

    @commands.command(name="radialblur")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def radialblur_cmd(
        self,
        ctx: commands.Context[Bot],
        angle: Annotated[float, commands.Range[float, 1.0, 45.0]] = commands.parameter(description="Spin blur arc in degrees (1-45)", default=12.0),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply a rotational spin blur."""
        await self._run_effect(ctx, member, "radialblur", "Radial Blur", {"angle": angle}, {"Angle": f"{angle:g}°"})

    @commands.command(name="tiltshift")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def tiltshift_cmd(
        self,
        ctx: commands.Context[Bot],
        focus_y: Annotated[float, commands.Range[float, 0.0, 1.0]] = commands.parameter(description="Vertical focus position (0.0-1.0)", default=0.5),
        dof: Annotated[float, commands.Range[float, 0.05, 0.6]] = commands.parameter(description="Sharp band width (0.05-0.6)", default=0.25),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply a miniature tilt-shift focus effect."""
        await self._run_effect(
            ctx, member, "tiltshift", "Tilt-Shift", {"focus_y": focus_y, "dof": dof}, {"Focus Y": f"{focus_y:.2f}", "DOF": f"{dof:.2f}"}
        )

    @commands.command(name="swirl", aliases=["twirl"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def swirl_cmd(
        self,
        ctx: commands.Context[Bot],
        strength: Annotated[float, commands.Range[float, -12.0, 12.0]] = commands.parameter(description="Twirl strength (-12 to 12)", default=3.0),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Swirl / twirl the centre of an image."""
        await self._run_effect(ctx, member, "swirl", "Swirl", {"strength": strength}, {"Strength": f"{strength:g}"})

    @commands.command(name="bulge", aliases=["pinch"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def bulge_cmd(
        self,
        ctx: commands.Context[Bot],
        strength: Annotated[float, commands.Range[float, -0.9, 1.5]] = commands.parameter(
            description="Positive = bulge, negative = pinch (-0.9 to 1.5)",
            default=0.5,
        ),
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Bulge or pinch an image."""
        await self._run_effect(ctx, member, "bulge", "Bulge / Pinch", {"strength": strength}, {"Strength": f"{strength:g}"})

    @commands.command(name="fisheye")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def fisheye_cmd(
        self,
        ctx: commands.Context[Bot],
        strength: Annotated[float, commands.Range[float, 0.1, 2.5]] = commands.parameter(description="Lens curvature (0.1-2.5)", default=1.0),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply a wide-angle fisheye lens distortion."""
        await self._run_effect(ctx, member, "fisheye", "Fisheye", {"strength": strength}, {"Strength": f"{strength:g}"})

    @commands.command(name="ripple", aliases=["wave"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def ripple_cmd(
        self,
        ctx: commands.Context[Bot],
        amplitude: Annotated[float, commands.Range[float, 1.0, 40.0]] = commands.parameter(description="Wave height in pixels (1-40)", default=10.0),
        wavelength: Annotated[float, commands.Range[float, 8.0, 160.0]] = commands.parameter(
            description="Wave spacing in pixels (8-160)", default=48.0
        ),
        mode: Literal["both", "horizontal", "vertical"] = commands.parameter(description="Wave axis", default="both"),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Distort an image with sinusoidal ripples."""
        await self._run_effect(
            ctx,
            member,
            "ripple",
            "Ripple",
            {"amplitude": amplitude, "wavelength": wavelength, "mode": mode},
            {"Amplitude": f"{amplitude:g}px", "Wavelength": f"{wavelength:g}px", "Mode": mode},
        )

    @commands.command(name="melt")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def melt_cmd(
        self,
        ctx: commands.Context[Bot],
        intensity: Annotated[float, commands.Range[float, 0.05, 1.0]] = commands.parameter(description="Melt amount (0.05-1.0)", default=0.4),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Melt vertical columns downward."""
        await self._run_effect(ctx, member, "melt", "Melt", {"intensity": intensity, "seed": seed}, {"Intensity": f"{intensity:.2f}"})

    @commands.command(name="crt")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def crt_cmd(
        self,
        ctx: commands.Context[Bot],
        scanline: Annotated[float, commands.Range[float, 0.05, 0.9]] = commands.parameter(description="Scanline darkness (0.05-0.9)", default=0.45),
        curvature: Annotated[float, commands.Range[float, 0.0, 0.4]] = commands.parameter(description="Screen barrel curve (0.0-0.4)", default=0.12),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Simulate a vintage CRT monitor with phosphor scanlines."""
        await self._run_effect(
            ctx,
            member,
            "crt",
            "CRT Monitor",
            {"scanline": scanline, "curvature": curvature},
            {"Scanline": f"{scanline:.2f}", "Curvature": f"{curvature:.2f}"},
        )

    @commands.command(name="vhs")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def vhs_cmd(
        self,
        ctx: commands.Context[Bot],
        intensity: Annotated[float, commands.Range[float, 0.1, 1.0]] = commands.parameter(description="Tape wear intensity (0.1-1.0)", default=0.5),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply retro VHS tape tracking and chroma bleed."""
        await self._run_effect(ctx, member, "vhs", "VHS Tape", {"intensity": intensity, "seed": seed}, {"Intensity": f"{intensity:.2f}"})

    @commands.command(name="chromatic", aliases=["rgbsplit"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def chromatic_cmd(
        self,
        ctx: commands.Context,
        shift_x: commands.Range[int, -48, 48] = commands.parameter(description="Horizontal RGB split in pixels (-48 to 48)", default=8),  # noqa: B008
        shift_y: commands.Range[int, -48, 48] = commands.parameter(description="Vertical RGB split in pixels (-48 to 48)", default=3),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply chromatic aberration (RGB channel split)."""
        await self._run_effect(
            ctx,
            member,
            "chromatic",
            "Chromatic Aberration",
            {"shift_x": shift_x, "shift_y": shift_y},
            {"Shift X": f"{shift_x}px", "Shift Y": f"{shift_y}px"},
        )

    @commands.command(name="halftone")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def halftone_cmd(
        self,
        ctx: commands.Context,
        dot_size: commands.Range[int, 4, 24] = commands.parameter(description="Cell size in pixels (4-24)", default=8),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Render a comic-book halftone dot pattern."""
        await self._run_effect(ctx, member, "halftone", "Halftone", {"dot_size": dot_size}, {"Dot size": f"{dot_size}px"})

    @commands.command(name="dither")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def dither_cmd(
        self,
        ctx: commands.Context,
        mode: Literal["bayer", "floyd"] = commands.parameter(description="Bayer ordered matrix or Floyd-Steinberg", default="bayer"),
        levels: commands.Range[int, 2, 8] = commands.parameter(description="Levels per channel (2-8)", default=3),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply retro Bayer or Floyd-Steinberg dithering."""
        await self._run_effect(ctx, member, "dither", "Dither", {"mode": mode, "levels": levels}, {"Mode": mode, "Levels": levels})

    @commands.command(name="gameboy")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def gameboy_cmd(
        self,
        ctx: commands.Context,
        palette_kind: Literal["dmg", "pocket", "light"] = commands.parameter(description="Game Boy model palette", default="dmg"),
        pixel_size: commands.Range[int, 1, 12] = commands.parameter(description="Pixel block size (1-12)", default=3),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Render in classic 4-shade Game Boy colours."""
        await self._run_effect(
            ctx,
            member,
            "gameboy",
            "Game Boy",
            {"palette_kind": palette_kind, "pixel_size": pixel_size},
            {"Palette": palette_kind, "Pixel size": pixel_size},
        )

    @commands.command(name="cartoon", aliases=["toon"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def cartoon_cmd(
        self,
        ctx: commands.Context,
        levels: commands.Range[int, 3, 12] = commands.parameter(description="Colour bands (3-12)", default=6),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Stylize an image with toon shading and ink outlines."""
        await self._run_effect(ctx, member, "cartoon", "Cartoon / Toon", {"levels": levels}, {"Levels": levels})

    @commands.command(name="sketch")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def sketch_cmd(
        self,
        ctx: commands.Context,
        shade: commands.Range[float, 0.1, 1.0] = commands.parameter(description="Pencil stroke softness (0.1-1.0)", default=0.5),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Convert an image into a pencil sketch."""
        await self._run_effect(ctx, member, "sketch", "Pencil Sketch", {"shade": shade}, {"Shade": f"{shade:.2f}"})

    @commands.command(name="oilpaint")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def oilpaint_cmd(
        self,
        ctx: commands.Context,
        radius: commands.Range[int, 1, 7] = commands.parameter(description="Brush size (1-7)", default=3),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Give an image an oil-painting texture."""
        await self._run_effect(ctx, member, "oilpaint", "Oil Paint", {"radius": radius}, {"Brush radius": radius})

    @commands.command(name="emboss")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def emboss_cmd(
        self,
        ctx: commands.Context,
        strength: commands.Range[float, 0.5, 4.0] = commands.parameter(description="Relief depth (0.5-4.0)", default=1.5),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Carve an image into a raised relief emboss."""
        await self._run_effect(ctx, member, "emboss", "Emboss", {"strength": strength}, {"Strength": f"{strength:g}"})

    @commands.command(name="sepia")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def sepia_cmd(
        self,
        ctx: commands.Context,
        intensity: commands.Range[float, 0.1, 1.0] = commands.parameter(description="Sepia warmth (0.1-1.0)", default=1.0),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply a warm vintage sepia tone."""
        await self._run_effect(ctx, member, "sepia", "Sepia", {"intensity": intensity}, {"Intensity": f"{intensity:.2f}"})

    @commands.command(name="solarize")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def solarize_cmd(
        self,
        ctx: commands.Context,
        threshold: commands.Range[int, 0, 255] = commands.parameter(description="Inversion cutoff (0-255)", default=128),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Solarize tones above the given threshold."""
        await self._run_effect(ctx, member, "solarize", "Solarize", {"threshold": threshold}, {"Threshold": threshold})

    @commands.command(name="thermal", aliases=["heatmap"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def thermal_cmd(
        self,
        ctx: commands.Context,
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Map image luminance to an infrared thermal camera palette."""
        await self._run_effect(ctx, member, "thermal", "Thermal Heatmap", {}, {})

    @commands.command(name="neon")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def neon_cmd(
        self,
        ctx: commands.Context,
        glow: commands.Range[float, 0.5, 5.0] = commands.parameter(description="Edge glow multiplier (0.5-5.0)", default=2.0),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Render glowing cyberpunk neon edges."""
        await self._run_effect(ctx, member, "neon", "Neon Glow Edges", {"glow": glow}, {"Glow": f"{glow:g}"})

    @commands.command(name="hueshift")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def hueshift_cmd(
        self,
        ctx: commands.Context,
        degrees: commands.Range[float, -360.0, 360.0] = commands.parameter(description="Hue rotation in degrees (-360 to 360)", default=90.0),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Shift all colours around the hue wheel."""
        await self._run_effect(ctx, member, "hueshift", "Hue Shift", {"degrees": degrees}, {"Degrees": f"{degrees:g}°"})

    @commands.command(name="bcs")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def bcs_cmd(
        self,
        ctx: commands.Context,
        brightness: commands.Range[float, 0.1, 3.0] = commands.parameter(description="Brightness multiplier (0.1-3.0)", default=1.0),  # noqa: B008
        contrast: commands.Range[float, 0.1, 3.0] = commands.parameter(description="Contrast multiplier (0.1-3.0)", default=1.2),  # noqa: B008
        saturation: commands.Range[float, 0.0, 3.0] = commands.parameter(description="Saturation multiplier (0.0-3.0)", default=1.3),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Adjust Brightness, Contrast, and Saturation."""
        await self._run_effect(
            ctx,
            member,
            "bcs",
            "Brightness / Contrast / Saturation",
            {"brightness": brightness, "contrast": contrast, "saturation": saturation},
            {"Brightness": f"{brightness:g}", "Contrast": f"{contrast:g}", "Saturation": f"{saturation:g}"},
        )

    @commands.command(name="channelswap")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def channelswap_cmd(
        self,
        ctx: commands.Context,
        order: Literal["gbr", "brg", "bgr", "rbg", "grb"] = commands.parameter(description="New RGB channel order", default="gbr"),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Swap the Red, Green, and Blue colour channels."""
        await self._run_effect(ctx, member, "channelswap", "Channel Swap", {"order": order}, {"Order": order.upper()})

    @commands.command(name="threshold")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def threshold_cmd(
        self,
        ctx: commands.Context,
        cutoff: commands.Range[int, 1, 254] = commands.parameter(description="Luminance cutoff (1-254)", default=128),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Convert to stark 1-bit black and white."""
        await self._run_effect(ctx, member, "threshold", "Threshold", {"cutoff": cutoff}, {"Cutoff": cutoff})

    @commands.command(name="colorize", aliases=["tint"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def colorize_cmd(
        self,
        ctx: commands.Context,
        color: str = commands.parameter(description="Hex colour or name, e.g. #00c8ff", default="#00c8ff"),
        strength: commands.Range[float, 0.05, 1.0] = commands.parameter(description="Tint strength (0.05-1.0)", default=0.7),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Tint an image toward a chosen colour."""
        rgb = parse_hex_color(color, "color")
        await self._run_effect(
            ctx,
            member,
            "colorize",
            "Colorize",
            {"color": rgb, "strength": strength},
            {"Color": "#{:02x}{:02x}{:02x}".format(*rgb), "Strength": f"{strength:.2f}"},
        )

    @commands.command(name="pixelsort")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pixelsort_cmd(
        self,
        ctx: commands.Context,
        direction: Literal["horizontal", "vertical"] = commands.parameter(description="Sort axis", default="horizontal"),
        low: commands.Range[int, 0, 220] = commands.parameter(description="Lower luminance threshold (0-220)", default=55),  # noqa: B008
        high: commands.Range[int, 40, 255] = commands.parameter(description="Upper luminance threshold (40-255)", default=210),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Glitch-sort contiguous pixel spans by luminance."""
        await self._run_effect(
            ctx,
            member,
            "pixelsort",
            "Pixel Sort",
            {"direction": direction, "low": low, "high": high},
            {"Direction": direction, "Range": f"{low}..{high}"},
        )

    @commands.command(name="datamosh")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def datamosh_cmd(
        self,
        ctx: commands.Context,
        blocks: commands.Range[int, 4, 80] = commands.parameter(description="Number of displaced macroblocks (4-80)", default=24),  # noqa: B008
        shift: commands.Range[int, 4, 96] = commands.parameter(description="Max shift distance (4-96)", default=28),  # noqa: B008
        seed: int | None = commands.parameter(description="Optional seed", default=None),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Apply macroblock datamosh displacement."""
        await self._run_effect(
            ctx, member, "datamosh", "Datamosh", {"blocks": blocks, "shift": shift, "seed": seed}, {"Blocks": blocks, "Shift": f"{shift}px"}
        )

    @commands.command(name="jpegcrush")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def jpegcrush_cmd(
        self,
        ctx: commands.Context,
        quality: commands.Range[int, 1, 35] = commands.parameter(description="JPEG quality (1-35)", default=6),  # noqa: B008
        passes: commands.Range[int, 1, 6] = commands.parameter(description="Compression passes (1-6)", default=3),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Heavily compress an image with multi-pass JPEG artifacts."""
        await self._run_effect(ctx, member, "jpegcrush", "JPEG Crush", {"quality": quality, "passes": passes}, {"Quality": quality, "Passes": passes})

    @commands.command(name="deepfry")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def deepfry_cmd(
        self,
        ctx: commands.Context,
        intensity: commands.Range[float, 0.1, 1.0] = commands.parameter(description="Deep-fry intensity (0.1-1.0)", default=0.7),  # noqa: B008
        seed: int | None = commands.parameter(description="Optional seed", default=None),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Deep-fry an image with extreme contrast, saturation, and crunch."""
        await self._run_effect(ctx, member, "deepfry", "Deep Fry", {"intensity": intensity, "seed": seed}, {"Intensity": f"{intensity:.2f}"})

    @commands.command(name="kaleidoscope")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def kaleidoscope_cmd(
        self,
        ctx: commands.Context,
        folds: commands.Range[int, 2, 16] = commands.parameter(description="Symmetry folds (2-16)", default=6),  # noqa: B008
        angle: commands.Range[float, -360.0, 360.0] = commands.parameter(description="Wedge rotation angle", default=0.0),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Reflect an image through a multi-fold kaleidoscope."""
        await self._run_effect(
            ctx, member, "kaleidoscope", "Kaleidoscope", {"folds": folds, "angle": angle}, {"Folds": folds, "Angle": f"{angle:g}°"}
        )

    @commands.command(name="tile")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def tile_cmd(
        self,
        ctx: commands.Context,
        tiles: commands.Range[int, 2, 8] = commands.parameter(description="Grid repetitions per side (2-8)", default=3),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Repeat an image in a NxN tiled grid."""
        await self._run_effect(ctx, member, "tile", "Tile Repeat", {"tiles": tiles}, {"Grid": f"{tiles}\N{MULTIPLICATION SIGN}{tiles}"})

    @commands.command(name="lowpoly")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def lowpoly_cmd(
        self,
        ctx: commands.Context,
        points: commands.Range[int, 20, 400] = commands.parameter(description="Mesh complexity (20-400)", default=120),  # noqa: B008
        seed: int | None = commands.parameter(description="Optional seed", default=None),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Render a triangulated low-poly mesh of the image."""
        await self._run_effect(ctx, member, "lowpoly", "Low-Poly Mesh", {"points": points, "seed": seed}, {"Points": points})

    @commands.command(name="stainedglass")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def stainedglass_cmd(
        self,
        ctx: commands.Context,
        cells: commands.Range[int, 16, 250] = commands.parameter(description="Number of Voronoi glass cells (16-250)", default=80),  # noqa: B008
        border: commands.Range[int, 0, 4] = commands.parameter(description="Lead border thickness (0-4)", default=1),  # noqa: B008
        seed: int | None = commands.parameter(description="Optional seed", default=None),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Turn an image into a Voronoi stained-glass window."""
        await self._run_effect(
            ctx, member, "stainedglass", "Stained Glass", {"cells": cells, "border": border, "seed": seed}, {"Cells": cells, "Border": f"{border}px"}
        )

    @commands.command(name="circlecrop")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def circlecrop_cmd(
        self,
        ctx: commands.Context,
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Crop an image into a clean anti-aliased circle."""
        await self._run_effect(ctx, member, "circlecrop", "Circle Cutout", {}, {})

    @commands.command(name="rounded")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def rounded_cmd(
        self,
        ctx: commands.Context,
        radius_ratio: commands.Range[float, 0.02, 0.5] = commands.parameter(description="Corner radius ratio (0.02-0.5)", default=0.22),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Clip an image with smooth rounded corners."""
        await self._run_effect(ctx, member, "rounded", "Rounded Corners", {"radius_ratio": radius_ratio}, {"Radius": f"{radius_ratio:.2f}"})

    @commands.command(name="sticker")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def sticker_cmd(
        self,
        ctx: commands.Context,
        outline: commands.Range[int, 2, 24] = commands.parameter(description="Outline thickness in pixels (2-24)", default=8),  # noqa: B008
        color: str = commands.parameter(description="Outline colour, e.g. #ffffff", default="#ffffff"),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Turn an avatar or cutout into a die-cut sticker with drop shadow."""
        rgb = parse_hex_color(color, "color")
        await self._run_effect(
            ctx,
            member,
            "sticker",
            "Die-Cut Sticker",
            {"outline": outline, "color": rgb, "shadow": True},
            {"Outline": f"{outline}px", "Color": "#{:02x}{:02x}{:02x}".format(*rgb)},
        )

    @commands.command(name="bgremove")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def bgremove_cmd(
        self,
        ctx: commands.Context,
        tolerance: commands.Range[int, 8, 140] = commands.parameter(description="Corner colour match tolerance (8-140)", default=42),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Remove a solid/uniform background based on corner colour sampling."""
        await self._run_effect(ctx, member, "bgremove", "Background Removal", {"tolerance": tolerance}, {"Tolerance": tolerance})

    @commands.command(name="colorascii")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def colorascii_cmd(
        self,
        ctx: commands.Context,
        columns: commands.Range[int, 8, 56] = commands.parameter(description="Width in characters (8-56)", default=38),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Render ANSI-coloured ASCII art inside a Discord code block."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        text = await asyncio.to_thread(colored_ascii_from_bytes, data, columns)
        await ctx.send(f"```ansi\n{text}\n```", allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="braille")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def braille_cmd(
        self,
        ctx: commands.Context,
        columns: commands.Range[int, 8, 80] = commands.parameter(description="Width in characters (8-80)", default=44),  # noqa: B008
        invert: bool = commands.parameter(description="Invert dot threshold", default=False),
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Render high-resolution Unicode Braille dot art."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        text = await asyncio.to_thread(braille_from_bytes, data, columns, invert, ASCII_MAX_CHARS)
        await ctx.send(f"```\n{text}\n```", allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="emojimosaic")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def emojimosaic_cmd(
        self,
        ctx: commands.Context,
        columns: commands.Range[int, 6, 30] = commands.parameter(description="Grid width in emojis (6-30)", default=18),  # noqa: B008
        *,
        member: discord.Member | None = commands.parameter(description="Whose avatar to use", default=None),  # noqa: B008
    ) -> None:
        """Render an image as a colour-square emoji mosaic."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        text = await asyncio.to_thread(emoji_mosaic_from_bytes, data, columns)
        await ctx.send(text[:2000], allowed_mentions=discord.AllowedMentions.none())

    async def _run_anim(
        self,
        ctx: commands.Context,
        member: discord.Member | None,
        kind: str,
        title: str,
        *,
        sweep_effect: str = "glitch",
    ) -> None:
        await ctx.typing()
        target = member or ctx.author
        data, _ = await self._load_source(target, animated=True, ctx=ctx)
        seed = secrets.randbelow(2**31)
        enc = await asyncio.to_thread(render_animated_effect, data, kind, sweep_effect=sweep_effect, seed=seed)
        fields: dict[str, object] = {"Animation": kind, "Frames": enc.frame_count}
        if kind == "sweep":
            fields["Effect"] = sweep_effect
        await self._send_image(ctx, enc, title, fields, stem=f"{kind}_anim")

    @commands.command(name="spingif")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def spingif_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Continuously rotate an avatar in a smooth looping GIF."""
        await self._run_anim(ctx, member, "spin", "Spinning GIF")

    @commands.command(name="pixelpulse")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pixelpulse_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Pixelate in and out in a looping GIF."""
        await self._run_anim(ctx, member, "pixelate", "Pixelate In/Out")

    @commands.command(name="rainbowgif", aliases=["party"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def rainbowgif_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Cycle an avatar through a full 360° rainbow hue rotation."""
        await self._run_anim(ctx, member, "rainbow", "Rainbow Hue GIF")

    @commands.command(name="shake", aliases=["triggered"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def shake_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Vibrate / shake an avatar rapidly."""
        await self._run_anim(ctx, member, "shake", "Shake GIF")

    @commands.command(name="bounce")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def bounce_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Bounce an avatar with squash-and-stretch physics."""
        await self._run_anim(ctx, member, "bounce", "Bounce GIF")

    @commands.command(name="pulse", aliases=["heartbeat"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pulse_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Animate a rhythmic heartbeat pulse."""
        await self._run_anim(ctx, member, "pulse", "Heartbeat Pulse")

    @commands.command(name="petpet", aliases=["pat"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def petpet_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Pet-pet style patting animation."""
        await self._run_anim(ctx, member, "petpet", "Pet-Pet")

    @commands.command(name="wiggle")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def wiggle_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Wiggle an image like a sine wave."""
        await self._run_anim(ctx, member, "wiggle", "Wiggle GIF")

    @commands.command(name="zoomgif")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def zoomgif_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Dramatically zoom into the centre of an avatar."""
        await self._run_anim(ctx, member, "zoom", "Zoom-In GIF")

    @commands.command(name="sweep")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def sweep_cmd(
        self,
        ctx: commands.Context,
        effect: Literal["glitch", "swirl", "pixelate", "hue"] = commands.parameter(description="Effect to ramp", default="glitch"),
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Animate a parameter sweep ramping an effect up and down."""
        await self._run_anim(ctx, member, "sweep", f"Parameter Sweep: {effect}", sweep_effect=effect)

    @commands.command(name="flowfield")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def flowfield_cmd(
        self,
        ctx: commands.Context,
        particles: commands.Range[int, 50, 2000] = commands.parameter(description="Streamline count (50-2000)", default=700),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate Perlin/value-noise driven flow field streamlines."""
        params = {"particles": particles, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "flowfield", "Flow Field", params, {"Particles": particles})

    @commands.command(name="cellular")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def cellular_cmd(
        self,
        ctx: commands.Context,
        kind: Literal["rule30", "rule110", "rule90", "life"] = commands.parameter(description="Automaton rule", default="rule30"),
        cell_size: commands.Range[int, 2, 32] = commands.parameter(description="Cell size in pixels (2-32)", default=6),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate Cellular Automata (Rule 30/90/110 or Conway's Game of Life)."""
        params = {"kind": kind, "cell_size": cell_size, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "cellular", f"Cellular Automaton: {kind}", params, {"Rule": kind, "Cell size": cell_size})

    @commands.command(name="spirograph", aliases=["lissajous"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def spirograph_cmd(
        self,
        ctx: commands.Context,
        kind: Literal["spirograph", "lissajous"] = commands.parameter(description="Curve family", default="spirograph"),
        petals: commands.Range[int, 2, 24] = commands.parameter(description="Harmoniclobes / petals (2-24)", default=7),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate Spirograph or Lissajous harmonic curves."""
        params = {"kind": kind, "petals": petals, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "spirograph", kind.title(), params, {"Kind": kind, "Petals": petals})

    @commands.command(name="truchet")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def truchet_cmd(
        self,
        ctx: commands.Context,
        cell_size: commands.Range[int, 16, 160] = commands.parameter(description="Tile size in pixels (16-160)", default=48),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate quarter-circle Truchet tiles."""
        params = {"cell_size": cell_size, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "truchet", "Truchet Tiles", params, {"Cell size": cell_size})

    @commands.command(name="maze")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def maze_cmd(
        self,
        ctx: commands.Context,
        cell_size: commands.Range[int, 12, 64] = commands.parameter(description="Corridor width (12-64)", default=24),  # noqa: B008
        solve: bool = commands.parameter(description="Highlight solution path", default=True),
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate a solvable procedural maze."""
        params = {"cell_size": cell_size, "solve": solve, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "maze", "Procedural Maze", params, {"Cell size": cell_size, "Solution": "shown" if solve else "hidden"})

    @commands.command(name="circlepack")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def circlepack_cmd(
        self,
        ctx: commands.Context,
        count: commands.Range[int, 20, 500] = commands.parameter(description="Circle count (20-500)", default=180),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate a non-overlapping circle packing composition."""
        params = {"count": count, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "circlepack", "Circle Packing", params, {"Circles": count})

    @commands.command(name="hexgrid")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def hexgrid_cmd(
        self,
        ctx: commands.Context,
        cell_size: commands.Range[int, 12, 120] = commands.parameter(description="Hexagon radius (12-120)", default=36),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate a shaded hexagonal honeycomb tessellation."""
        params = {"cell_size": cell_size, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "hexgrid", "Hex Grid", params, {"Hex radius": cell_size})

    @commands.command(name="lsystem", aliases=["sierpinski"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def lsystem_cmd(
        self,
        ctx: commands.Context,
        kind: Literal["tree", "sierpinski"] = commands.parameter(description="Fractal structure", default="tree"),
        depth: commands.Range[int, 3, 9] = commands.parameter(description="Recursion depth (3-9)", default=7),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate a fractal L-system tree or Sierpinski triangle."""
        params = {"kind": kind, "depth": depth, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "lsystem", f"L-System: {kind.title()}", params, {"Kind": kind, "Depth": depth})

    @commands.command(name="starfield")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def starfield_cmd(
        self,
        ctx: commands.Context,
        stars: commands.Range[int, 50, 1200] = commands.parameter(description="Number of stars (50-1200)", default=350),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional nebula palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate a deep-space nebula and starfield."""
        params = {"stars": stars, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "starfield", "Starfield & Nebula", params, {"Stars": stars})

    @commands.command(name="sunburst")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def sunburst_cmd(
        self,
        ctx: commands.Context,
        rays: commands.Range[int, 4, 96] = commands.parameter(description="Number of rays (4-96)", default=24),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate radial sunburst rays."""
        params = {"rays": rays, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "sunburst", "Sunburst Rays", params, {"Rays": rays})

    @commands.command(name="moire")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def moire_cmd(
        self,
        ctx: commands.Context,
        wavelength: commands.Range[float, 4.0, 64.0] = commands.parameter(description="Ring spacing (4-64)", default=14.0),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate wave interference moiré patterns."""
        params = {"wavelength": wavelength, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "moire", "Moiré Interference", params, {"Wavelength": f"{wavelength:g}px"})

    @commands.command(name="topographic")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def topographic_cmd(
        self,
        ctx: commands.Context,
        levels: commands.Range[int, 4, 36] = commands.parameter(description="Elevation contour bands (4-36)", default=14),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate a topographic elevation contour map."""
        params = {"levels": levels, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "topographic", "Topographic Contours", params, {"Levels": levels})

    @commands.command(name="reaction")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def reaction_cmd(
        self,
        ctx: commands.Context,
        steps: commands.Range[int, 40, 300] = commands.parameter(description="Simulation steps (40-300)", default=160),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate Gray-Scott reaction-diffusion Turing patterns."""
        params = {"steps": steps, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "reaction", "Reaction-Diffusion", params, {"Steps": steps})

    @commands.command(name="mesh")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def mesh_cmd(
        self,
        ctx: commands.Context,
        anchors: commands.Range[int, 3, 12] = commands.parameter(description="Colour anchor points (3-12)", default=6),  # noqa: B008
        colors: str | None = commands.parameter(description="Optional hex palette", default=None),
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate a smooth multi-anchor gradient mesh wallpaper."""
        params = {"anchors": anchors, "colors": parse_color_list(colors, min_count=2) or None, "seed": seed}
        await self._run_generator(ctx, "mesh", "Gradient Mesh Wallpaper", params, {"Anchors": anchors})

    @commands.command(name="avatarwallpaper")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def avatarwallpaper_cmd(
        self,
        ctx: commands.Context,
        style: Literal["mesh", "plasma", "topographic", "flowfield", "waves"] = commands.parameter(
            description="Wallpaper generator style", default="mesh"
        ),
        member: discord.Member | None = commands.parameter(description="Whose avatar palette to sample", default=None),  # noqa: B008
        seed: int | None = commands.parameter(description="Optional seed", default=None),
    ) -> None:
        """Generate a 16:9 wallpaper using colours extracted from an avatar."""
        await ctx.typing()
        if seed is None:
            seed = secrets.randbelow(2**31)
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(palette_wallpaper_from_bytes, data, 1024, 576, style, seed)
        await self._send_image(ctx, enc, "Avatar Palette Wallpaper", {"Style": style, "Seed": seed}, stem="wallpaper")

    @commands.command(name="ship")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def ship_cmd(
        self,
        ctx: commands.Context,
        member_a: discord.Member,
        member_b: discord.Member = commands.parameter(default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Ship two members together with a compatibility score."""
        await ctx.typing()
        user_a = member_a
        user_b = member_b or ctx.author
        (data_a, _), (data_b, _) = await asyncio.gather(
            self._fetch_avatar(user_a, animated=False, size=256),
            self._fetch_avatar(user_b, animated=False, size=256),
        )
        enc = await asyncio.to_thread(render_ship, data_a, data_b, user_a.display_name, user_b.display_name)
        await self._send_image(ctx, enc, "Ship Compatibility", {"Pair": f"{user_a.display_name} ❤️ {user_b.display_name}"}, stem="ship")

    @commands.command(name="compare", aliases=["versus", "vs"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def compare_cmd(
        self,
        ctx: commands.Context,
        member_a: discord.Member,
        member_b: discord.Member | None = None,
    ) -> None:
        """Place two avatars side-by-side in a VS matchup card."""
        await ctx.typing()
        user_a = member_a
        user_b = member_b or ctx.author
        (data_a, _), (data_b, _) = await asyncio.gather(
            self._fetch_avatar(user_a, animated=False, size=256),
            self._fetch_avatar(user_b, animated=False, size=256),
        )
        enc = await asyncio.to_thread(render_compare, data_a, data_b, user_a.display_name, user_b.display_name)
        await self._send_image(ctx, enc, "VS Matchup", {"Match": f"{user_a.display_name} vs {user_b.display_name}"}, stem="versus")

    @commands.command(name="profilecard")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def profilecard_cmd(
        self,
        ctx: commands.Context,
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Render a custom profile card with avatar, roles, join date, and account age."""
        await ctx.typing()
        target = member or ctx.author
        data, _ = await self._fetch_avatar(target, animated=False, size=256)
        roles = [r.name for r in reversed(getattr(target, "roles", []))] if isinstance(target, discord.Member) else []
        roles = [r for r in roles if r != "@everyone"]
        joined = target.joined_at.strftime("%Y-%m-%d") if isinstance(target, discord.Member) and target.joined_at else "N/A"
        created = target.created_at.strftime("%Y-%m-%d")
        accent = target.colour.to_rgb() if isinstance(target, discord.Member) and target.colour.value else None
        enc = await asyncio.to_thread(
            render_profile_card,
            data,
            target.name,
            target.display_name,
            roles,
            joined,
            created,
            accent,
        )
        await self._send_image(ctx, enc, f"Profile: {target.display_name}", {"Roles": len(roles), "Created": created}, stem="profilecard")

    @commands.command(name="card", aliases=["wanted", "idcard", "tradingcard", "polaroid", "magazine"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def card_cmd(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(description="Target member", default=None),  # noqa: B008
        *,
        subtitle: str = commands.parameter(description="Custom caption or reward text", default="DEAD OR ALIVE • $1,000,000,000"),
    ) -> None:
        """Place an avatar into a Wanted poster, ID card, Trading card, Polaroid, or Magazine cover."""
        await ctx.typing()
        invoked = (ctx.invoked_with or "").lower()
        if invoked in CARD_STYLES:
            style = invoked
        elif invoked == "tradingcard":
            style = "trading"
        else:
            style = "wanted"
        target = member or ctx.author
        data, _ = await self._load_source(target, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(render_card_template, data, style, target.display_name, subtitle)
        await self._send_image(ctx, enc, f"Card: {style.title()}", {"Style": style, "Subject": target.display_name}, stem=style)

    @commands.command(name="photomosaic", aliases=["servermosaic"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def photomosaic_cmd(
        self,
        ctx: commands.Context,
        target_kind: Literal["avatar", "server"] = commands.parameter(description="Rebuild your avatar or the server icon", default="avatar"),
        role: discord.Role | None = commands.parameter(description="Optional role to filter member tiles", default=None),  # noqa: B008
    ) -> None:
        """Rebuild an avatar or the server icon as a photomosaic made of member avatars."""
        await ctx.typing()
        if target_kind == "server" and ctx.guild and ctx.guild.icon:
            target_data = await asyncio.wait_for(ctx.guild.icon.replace(size=256, format="png").read(), DOWNLOAD_TIMEOUT)
        else:
            target_data, _ = await self._load_source(ctx.author, animated=False, ctx=ctx)
        pool = list(role.members) if role is not None else (list(ctx.guild.members) if ctx.guild else [ctx.author])
        pool = [m for m in pool if not m.bot] or [ctx.author]
        sample = random.sample(pool, min(20, len(pool)))
        fetched = await asyncio.gather(*(self._fetch_avatar(m, animated=False, size=128) for m in sample))
        enc = await asyncio.to_thread(render_photomosaic, target_data, [d for d, _ in fetched])
        await self._send_image(ctx, enc, "Avatar Photomosaic", {"Target": target_kind, "Tiles sampled": len(sample)}, stem="photomosaic")

    @commands.command(name="avatarswap")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def avatarswap_cmd(
        self,
        ctx: commands.Context,
        other: discord.Member = commands.parameter(description="Other member to swap avatars with"),  # noqa: B008
    ) -> None:
        """Swap two users' avatars into each other's styled frames and nameplates."""
        await ctx.typing()
        (data_a, _), (data_b, _) = await asyncio.gather(
            self._fetch_avatar(ctx.author, animated=False, size=256),
            self._fetch_avatar(other, animated=False, size=256),
        )
        enc = await asyncio.to_thread(render_avatar_swap, data_a, data_b, ctx.author.display_name, other.display_name)
        await self._send_image(ctx, enc, "Avatar Swap", {"Swapped": f"{ctx.author.display_name} ↔ {other.display_name}"}, stem="avatarswap")

    @commands.command(name="pride")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pride_cmd(
        self,
        ctx: commands.Context,
        flag: Literal["rainbow", "trans", "bi", "pan", "nonbinary", "lesbian", "ace"] = commands.parameter(
            description="Pride flag palette", default="rainbow"
        ),
        mode: Literal["ring", "overlay"] = commands.parameter(description="Border ring or full translucent overlay", default="ring"),
        opacity: commands.Range[float, 0.1, 0.9] = commands.parameter(description="Ring thickness or overlay opacity (0.1-0.9)", default=0.45),  # noqa: B008
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Add a pride flag ring or translucent overlay to an avatar."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(render_pride_overlay, data, flag, opacity, mode)
        await self._send_image(ctx, enc, f"Pride: {flag.title()}", {"Flag": flag, "Mode": mode, "Opacity": f"{opacity:.2f}"}, stem="pride")

    @commands.command(name="meme")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def meme_cmd(
        self,
        ctx: commands.Context,
        *,
        caption: str = commands.parameter(description="Use 'Top Text | Bottom Text'"),
    ) -> None:
        """Add classic top and bottom meme text (separate with `|`)."""
        await ctx.typing()
        parts = [p.strip() for p in caption.split("|", maxsplit=1)]
        top = parts[0]
        bottom = parts[1] if len(parts) > 1 else ""
        data, _ = await self._load_source(ctx.author, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(render_meme, data, top, bottom)
        await self._send_image(ctx, enc, "Meme Caption", {"Top": top or "—", "Bottom": bottom or "—"}, stem="meme")

    @commands.command(name="speechbubble")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def speechbubble_cmd(
        self,
        ctx: commands.Context,
        *,
        text: str = commands.parameter(description="Optional text inside the speech bubble", default=""),
    ) -> None:
        """Add a comic speech bubble above an avatar or attached image."""
        await ctx.typing()
        data, _ = await self._load_source(ctx.author, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(render_speech_bubble, data, text)
        await self._send_image(ctx, enc, "Speech Bubble", {"Text": text[:60] if text else "(blank)"}, stem="speechbubble")

    @commands.command(name="quotecard")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def quotecard_cmd(
        self,
        ctx: commands.Context,
        member: discord.Member | None = commands.parameter(description="Quoted member", default=None),  # noqa: B008
        *,
        quote: str = commands.parameter(description="Quote text"),
    ) -> None:
        """Render a dramatic quote card for a member."""
        await ctx.typing()
        target = member or ctx.author
        data, _ = await self._fetch_avatar(target, animated=False, size=256)
        enc = await asyncio.to_thread(render_quote_card, data, quote, target.display_name)
        await self._send_image(ctx, enc, "Quote Card", {"Author": target.display_name}, stem="quotecard")

    @commands.command(name="colorinfo")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def colorinfo_cmd(
        self,
        ctx: commands.Context,
        color: str = commands.parameter(description="Hex colour or CSS name, e.g. #5865f2"),
    ) -> None:
        """Inspect a colour with RGB, HSL, complement, and analogous swatches."""
        await ctx.typing()
        enc, info = await asyncio.to_thread(render_colorinfo, color)
        await self._send_image(ctx, enc, f"Colour Info: {info['Hex']}", info, stem="colorinfo")

    @commands.command(name="palette")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def palette_cmd(
        self,
        ctx: commands.Context,
        count: commands.Range[int, 2, 10] = commands.parameter(description="Number of swatches (2-10)", default=6),  # noqa: B008
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Extract dominant colours from an avatar or attachment."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        enc, hexes = await asyncio.to_thread(render_palette_swatches, data, count)
        await self._send_image(ctx, enc, "Dominant Palette", {"Colours": ", ".join(hexes)}, stem="palette")

    @commands.command(name="imageinfo")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def imageinfo_cmd(
        self,
        ctx: commands.Context,
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Inspect dimensions, format, frame count, and byte size of an image or avatar."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=True, ctx=ctx)
        info = await asyncio.to_thread(inspect_image, data)
        embed = (
            discord.Embed(title="Image Inspector", colour=discord.Colour.blurple())
            .add_field(name="Format", value=info.format, inline=True)
            .add_field(name="Dimensions", value=f"{info.width}\N{MULTIPLICATION SIGN}{info.height}", inline=True)
            .add_field(name="Frames", value=str(info.frames), inline=True)
            .add_field(name="Mode", value=info.mode, inline=True)
            .add_field(name="Size", value=f"{info.size_bytes / 1024:.1f} KB", inline=True)
        )
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="banner")
    async def banner_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Fetch a user's full-resolution profile banner."""
        target = member or ctx.author
        fetched = await self.bot.fetch_user(target.id)
        if not fetched.banner:
            await ctx.send("That user does not have a profile banner set.", allowed_mentions=discord.AllowedMentions.none())
            return
        embed = discord.Embed(title=f"{target.display_name}'s Banner", colour=discord.Colour.blurple())
        embed.set_image(url=fetched.banner.with_size(1024).url)
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="serverpfp", aliases=["servericon"])
    async def serverpfp_cmd(self, ctx: commands.Context) -> None:
        """Fetch this server's full-resolution icon."""
        if not ctx.guild or not ctx.guild.icon:
            await ctx.send("This server does not have an icon.", allowed_mentions=discord.AllowedMentions.none())
            return
        embed = discord.Embed(title=f"{ctx.guild.name} Icon", colour=discord.Colour.blurple())
        embed.set_image(url=ctx.guild.icon.with_size(1024).url)
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="enlargeemoji", aliases=["jumbo"])
    async def enlargeemoji_cmd(self, ctx: commands.Context, emoji: discord.PartialEmoji) -> None:
        """Enlarge a custom Discord emoji to full resolution."""
        embed = discord.Embed(title=f"Emoji: {emoji.name}", colour=discord.Colour.blurple())
        embed.set_image(url=emoji.url)
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="emojify")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def emojify_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Resize an image or avatar down to a crisp 128\N{MULTIPLICATION SIGN}128 Discord-emoji ready asset."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=True, ctx=ctx)
        enc = await asyncio.to_thread(resize_image_bytes, data, 128, 128)
        await self._send_image(ctx, enc, "Emoji-Sized Image (128\N{MULTIPLICATION SIGN}128)", {"Size": "128\N{MULTIPLICATION SIGN}128"}, stem="emoji")

    @commands.command(name="resize")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def resize_cmd(
        self,
        ctx: commands.Context,
        width: commands.Range[int, 16, 2048] = 256,
        height: commands.Range[int, 16, 2048] = 256,
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Resize an image or avatar to exact pixel dimensions."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=True, ctx=ctx)
        enc = await asyncio.to_thread(resize_image_bytes, data, width, height)
        await self._send_image(ctx, enc, "Resized Image", {"Dimensions": f"{width}\N{MULTIPLICATION SIGN}{height}"}, stem="resized")

    @commands.command(name="crop")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def crop_cmd(
        self,
        ctx: commands.Context,
        aspect: Literal["1:1", "16:9", "4:3", "9:16", "3:4"] = "1:1",
        anchor: Literal["center", "top", "bottom", "left", "right"] = "center",
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Crop an image to a standard aspect ratio."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=True, ctx=ctx)
        enc = await asyncio.to_thread(crop_image_bytes, data, aspect, anchor)
        await self._send_image(ctx, enc, "Cropped Image", {"Aspect": aspect, "Anchor": anchor}, stem="cropped")

    @commands.command(name="convert")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def convert_cmd(
        self,
        ctx: commands.Context,
        fmt: Literal["png", "webp", "jpeg", "gif"] = "png",
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Convert an image between PNG, WebP, JPEG, and GIF."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=True, ctx=ctx)
        enc = await asyncio.to_thread(convert_image_bytes, data, fmt)
        await self._send_image(ctx, enc, f"Converted to {fmt.upper()}", {"Format": enc.format}, stem="converted")

    @commands.command(name="compress")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def compress_cmd(
        self,
        ctx: commands.Context,
        quality: commands.Range[int, 1, 95] = 50,
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Compress an image to reduce file size."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(compress_image_bytes, data, quality)
        await self._send_image(ctx, enc, "Compressed JPEG", {"Quality": quality, "Size": f"{len(enc.data) / 1024:.1f} KB"}, stem="compressed")

    @commands.command(name="reversegif")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def reversegif_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Reverse the playback order of an animated GIF."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=True, ctx=ctx)
        enc = await asyncio.to_thread(reverse_gif_bytes, data)
        await self._send_image(ctx, enc, "Reversed Animation", {"Frames": enc.frame_count}, stem="reversed")

    @commands.command(name="speedgif")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def speedgif_cmd(
        self,
        ctx: commands.Context,
        factor: commands.Range[float, 0.25, 4.0] = 2.0,
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Speed up or slow down an animated GIF (0.25x to 4.0x)."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=True, ctx=ctx)
        enc = await asyncio.to_thread(speed_gif_bytes, data, factor)
        await self._send_image(ctx, enc, "Adjusted Animation Speed", {"Speed": f"{factor:g}\N{MULTIPLICATION SIGN}"}, stem="speed")

    @commands.command(name="frames")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def frames_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Extract frames from an animation onto a numbered contact sheet."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=True, ctx=ctx)
        enc = await asyncio.to_thread(extract_frames_sheet, data)
        await self._send_image(ctx, enc, "Extracted Animation Frames", {}, stem="frames")

    @commands.command(name="colorblind")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def colorblind_cmd(
        self,
        ctx: commands.Context,
        kind: Literal["protanopia", "deuteranopia", "tritanopia"] = "deuteranopia",
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Simulate colour-vision deficiency (protanopia, deuteranopia, tritanopia)."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(render_colorblind_sim, data, kind)
        await self._send_image(ctx, enc, f"Colorblind Simulation: {kind.title()}", {"Type": kind}, stem=kind)

    @commands.command(name="contrast")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def contrast_cmd(self, ctx: commands.Context, color_a: str, color_b: str) -> None:
        """Check WCAG contrast ratio between two colours."""
        await ctx.typing()
        enc, info = await asyncio.to_thread(render_contrast_checker, color_a, color_b)
        await self._send_image(ctx, enc, "WCAG Contrast Checker", info, stem="contrast")

    @commands.command(name="qrcode")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def qrcode_cmd(self, ctx: commands.Context, *, text: str) -> None:
        """Generate a 2D QR matrix code for the given text."""
        await ctx.typing()
        enc = await asyncio.to_thread(render_qrcode, text)
        await self._send_image(ctx, enc, "QR Code", {"Content": text[:80]}, stem="qrcode")

    @commands.command(name="barcode")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def barcode_cmd(self, ctx: commands.Context, *, text: str) -> None:
        """Generate a 1D linear barcode for the given text."""
        await ctx.typing()
        enc = await asyncio.to_thread(render_barcode, text)
        await self._send_image(ctx, enc, "Barcode", {"Content": text[:40]}, stem="barcode")

    @commands.command(name="stack")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def stack_cmd(
        self,
        ctx: commands.Context,
        direction: Literal["hstack", "vstack"] = "hstack",
        member_a: discord.Member | None = None,
        member_b: discord.Member | None = None,
    ) -> None:
        """Stack two images or avatars horizontally (`hstack`) or vertically (`vstack`)."""
        await ctx.typing()
        ua = member_a or ctx.author
        ub = member_b or ctx.author
        (da, _), (db, _) = await asyncio.gather(
            self._fetch_avatar(ua, animated=False, size=512),
            self._fetch_avatar(ub, animated=False, size=512),
        )
        enc = await asyncio.to_thread(stack_images_bytes, da, db, direction)
        await self._send_image(ctx, enc, f"Image Stack ({direction})", {"Direction": direction}, stem=direction)

    @commands.command(name="fx", aliases=["chain"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def fx_cmd(
        self,
        ctx: commands.Context,
        *,
        pipeline: str = commands.parameter(description="Pipe-separated chain, e.g. pixelate 8 | duotone | spin 45"),
    ) -> None:
        """Chain multiple effects together using `|` (e.g. `fx pixelate 8 | duotone | spin 45`)."""
        await ctx.typing()
        data, _ = await self._load_source(ctx.author, animated=True, ctx=ctx)
        enc, names = await asyncio.to_thread(process_effect_chain, data, pipeline)
        await self._send_image(ctx, enc, "Effect Chain", {"Pipeline": " → ".join(names)}, stem="fxchain")

    @commands.command(name="surprise", aliases=["randomfx"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def surprise_cmd(
        self,
        ctx: commands.Context,
        kind: Literal["effect", "generator", "any"] = "any",
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Apply a random effect or run a random procedural generator with a fresh seed."""
        rng = random.Random()
        pick_gen = kind == "generator" or (kind == "any" and rng.random() < 0.35)
        if pick_gen:
            gname = rng.choice(list(GENERATORS.keys()))
            await self._run_generator(ctx, gname, f"Surprise Generator: {gname.title()}", {"seed": secrets.randbelow(2**31)}, {"Generator": gname})
        else:
            ename = rng.choice(list(EFFECT_REGISTRY.keys()))
            await self._run_effect(ctx, member, ename, f"Surprise Effect: {ename.title()}", {}, {"Effect": ename})

    @commands.command(name="contactsheet")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def contactsheet_cmd(self, ctx: commands.Context, *, member: discord.Member | None = None) -> None:
        """Render a labeled contact sheet showing your avatar run through 24 effects."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(render_contact_sheet, data)
        await self._send_image(ctx, enc, "Effect Contact Sheet", {"Effects": 24}, stem="contactsheet")

    @commands.command(name="beforeafter")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def beforeafter_cmd(
        self,
        ctx: commands.Context,
        effect: str = commands.parameter(description="Effect name, e.g. cartoon, glitch, neon", default="cartoon"),
        mode: Literal["side", "slider"] = commands.parameter(description="Side-by-side PNG or animated slider GIF", default="side"),
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Compare original and processed images side-by-side or with an animated wipe slider."""
        await ctx.typing()
        data, _ = await self._load_source(member or ctx.author, animated=False, ctx=ctx)
        enc = await asyncio.to_thread(render_before_after, data, effect.lower(), None, mode)
        await self._send_image(ctx, enc, f"Before / After: {effect}", {"Effect": effect, "Mode": mode}, stem="beforeafter")


async def setup(bot: Bot) -> None:
    await bot.add_cog(ImageCog(bot))
