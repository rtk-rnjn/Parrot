from __future__ import annotations

import asyncio
import io
import logging
from collections import OrderedDict
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Literal

import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

Kind = Literal["join", "leave"]
Style = Literal["text", "embed", "card"]

FONT_DIR = Path("assets")
FONT_BOLD = FONT_DIR / "Poppins-Bold.ttf"
FONT_REGULAR = FONT_DIR / "Poppins-Regular.ttf"

CARD_SIZE = (1000, 360)
DEFAULT_JOIN_COLOR = 0x5865F2
DEFAULT_LEAVE_COLOR = 0xED4245
MAX_BACKGROUND_BYTES = 8 * 1024 * 1024
BACKGROUND_CACHE_SIZE = 16


def _rgb(color: int) -> tuple[int, int, int]:
    return (color >> 16) & 255, (color >> 8) & 255, color & 255


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        # Pillow >= 10.1 can scale its built-in font.
        return ImageFont.load_default(size=size)


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    path: Path,
    max_width: int,
    start: int,
    minimum: int = 30,
) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, str]:
    """Shrink the font until `text` fits, then fall back to truncation."""
    for size in range(start, minimum - 1, -2):
        font = _font(path, size)
        if draw.textlength(text, font=font) <= max_width:
            return font, text

    font = _font(path, minimum)
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return font, text + "…"


def _tracked_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, ...],
    tracking: int = 6,
) -> None:
    """Draw text with letter spacing (for the small caps label)."""
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill, anchor="ls")
        x += draw.textlength(char, font=font) + tracking


def _circle_crop(image: Image.Image, size: int) -> Image.Image:
    """Square-fit and crop to an anti-aliased circle."""
    image = ImageOps.fit(image.convert("RGBA"), (size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    image.putalpha(mask.resize((size, size), Image.Resampling.LANCZOS))
    return image


def _translucent_rounded(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
    width: int = 2,
) -> Image.Image:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)
    return Image.alpha_composite(canvas, layer)


def _make_background(accent: tuple[int, int, int], background: bytes | None) -> Image.Image:
    _, height = CARD_SIZE

    if background:
        try:
            with Image.open(io.BytesIO(background)) as raw:
                base = ImageOps.fit(raw.convert("RGB"), CARD_SIZE, Image.Resampling.LANCZOS)
            base = base.filter(ImageFilter.GaussianBlur(1.5)).convert("RGBA")
            return Image.alpha_composite(base, Image.new("RGBA", CARD_SIZE, (8, 8, 12, 120)))
        except Exception:
            _log.warning("Could not decode custom welcome background; using gradient.", exc_info=True)

    dark = tuple(int(c * 0.16) for c in accent)
    mid = tuple(int(c * 0.55) for c in accent)
    mask = Image.linear_gradient("L").rotate(90).resize(CARD_SIZE)
    base = Image.composite(
        Image.new("RGB", CARD_SIZE, mid),
        Image.new("RGB", CARD_SIZE, dark),
        mask,
    ).convert("RGBA")

    # Soft glow behind the avatar.
    glow = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    cx, cy = 190, height // 2
    ImageDraw.Draw(glow).ellipse((cx - 170, cy - 170, cx + 170, cy + 170), fill=(*accent, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    return Image.alpha_composite(base, glow)


def render_card(
    *,
    kind: Kind,
    name: str,
    subtitle: str,
    pill: str,
    accent: int,
    avatar: bytes,
    background: bytes | None = None,
) -> io.BytesIO:
    """Render the welcome / goodbye banner and return it as a PNG buffer."""
    width, height = CARD_SIZE
    accent_rgb = _rgb(accent)
    light_accent = tuple(min(255, int(c + (255 - c) * 0.45)) for c in accent_rgb)

    canvas = _make_background(accent_rgb, background)

    # Glass panel
    margin = 28
    canvas = _translucent_rounded(
        canvas,
        (margin, margin, width - margin, height - margin),
        radius=32,
        fill=(10, 10, 16, 105),
        outline=(*accent_rgb, 110),
        width=2,
    )

    # Avatar with accent ring
    avatar_size, ring = 210, 10
    ring_size = avatar_size + ring * 2
    ax = 75
    ay = (height - ring_size) // 2

    ring_img = Image.new("RGBA", (ring_size, ring_size), (*accent_rgb, 255))
    ring_mask = Image.new("L", (ring_size * 4, ring_size * 4), 0)
    ImageDraw.Draw(ring_mask).ellipse((0, 0, ring_size * 4 - 1, ring_size * 4 - 1), fill=255)
    ring_img.putalpha(ring_mask.resize((ring_size, ring_size), Image.Resampling.LANCZOS))
    canvas.alpha_composite(ring_img, (ax, ay))

    with Image.open(io.BytesIO(avatar)) as raw:
        canvas.alpha_composite(_circle_crop(raw, avatar_size), (ax + ring, ay + ring))

    # Text block
    draw = ImageDraw.Draw(canvas)
    tx = ax + ring_size + 50
    max_text_width = width - tx - margin - 30

    label = "WELCOME" if kind == "join" else "GOODBYE"
    _tracked_text(draw, (tx, 104), label, _font(FONT_BOLD, 28), (*light_accent, 255), tracking=7)

    name_font, name_text = _fit_text(draw, name, FONT_BOLD, max_text_width, start=68)
    draw.text((tx, 182), name_text, font=name_font, fill=(255, 255, 255, 255), anchor="ls")

    sub_font, sub_text = _fit_text(draw, subtitle, FONT_REGULAR, max_text_width, start=32, minimum=20)
    draw.text((tx, 228), sub_text, font=sub_font, fill=(214, 218, 230, 255), anchor="ls")

    # Member-count pill
    pill_font = _font(FONT_BOLD, 22)
    pill_w = int(draw.textlength(pill, font=pill_font)) + 44
    pill_box = (tx, 258, tx + pill_w, 302)
    canvas = _translucent_rounded(
        canvas,
        pill_box,
        radius=22,
        fill=(*accent_rgb, 70),
        outline=(*light_accent, 170),  # pyright: ignore[reportArgumentType]
        width=2,
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (tx + pill_w // 2, (pill_box[1] + pill_box[3]) // 2 + 1),
        pill,
        font=pill_font,
        fill=(255, 255, 255, 255),
        anchor="mm",
    )

    buffer = io.BytesIO()
    canvas.convert("RGB").save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer


class Welcomer(commands.Cog):
    """Send configured messages when members join or leave a guild."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._background_cache: OrderedDict[str, bytes] = OrderedDict()
        _log.debug("Cog loaded: %s", type(self).__name__)

    @commands.Cog.listener("on_member_join")
    async def member_welcome(self, member: discord.Member) -> None:
        await self._announce(member, "join")

    @commands.Cog.listener("on_member_join")
    async def member_join_role(self, member: discord.Member) -> None:
        if not await self.bot.database.is_welcome_enabled(member.guild.id):
            return

        role_id = await self.bot.database.get_welcome_join_role_id(member.guild.id)
        if role_id is None:
            return

        role = member.guild.get_role(role_id)
        me = member.guild.me
        if role is None or me is None or not me.guild_permissions.manage_roles:
            return
        if not role.is_assignable():
            _log.warning(
                "Cannot assign join role %s to member %s in guild %s: role is above the bot's top role or managed.",
                role.id,
                member.id,
                member.guild.id,
            )
            return

        try:
            await member.add_roles(role, reason="Join role configured in Welcomer cog.")
        except discord.Forbidden:
            _log.warning(
                "Cannot assign join role %s to member %s in guild %s: missing permissions.",
                role.id,
                member.id,
                member.guild.id,
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self._announce(member, "leave")

    async def _announce(self, member: discord.Member, kind: Kind) -> None:  # noqa: PLR0912
        guild = member.guild
        db = self.bot.database

        if not await db.is_welcome_enabled(guild.id):
            return

        if kind == "join":
            channel_id, message, style = await asyncio.gather(
                db.get_welcome_join_channel_id(guild.id),
                db.get_welcome_join_message(guild.id),
                db.get_welcome_join_style(guild.id),  # "text" | "embed" | "card"
            )
        else:
            channel_id, message, style = await asyncio.gather(
                db.get_welcome_leave_channel_id(guild.id),
                db.get_welcome_leave_message(guild.id),
                db.get_welcome_leave_style(guild.id),
            )
        if channel_id is None:
            return

        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            return
        me = guild.me
        if me is None:
            return
        perms = channel.permissions_for(me)
        if not perms.send_messages:
            return

        text = self._format_message(message, member)

        # Degrade gracefully if the bot lacks permissions for the chosen style.
        style = style or "card"
        if style == "card" and not (perms.attach_files and perms.embed_links):
            style = "embed"
        if style == "embed" and not perms.embed_links:
            style = "text"

        if style == "text" and text is not None:
            await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
            return

        accent = await self._accent_color(guild.id, kind)
        embed = discord.Embed(description=text, colour=accent, timestamp=discord.utils.utcnow())
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)

        count = guild.member_count or len(guild.members)
        embed.set_footer(text=f"Member #{count:,}" if kind == "join" else f"{count:,} members remaining")

        file: discord.File | None = None
        if style == "card":
            file = await self._build_card(member, kind, accent)

        if file is not None:
            embed.set_image(url=f"attachment://{file.filename}")
        else:
            embed.title = f"Welcome, {member.display_name}!" if kind == "join" else f"{member.display_name} has left"
            embed.set_thumbnail(url=member.display_avatar.url)

        kwargs = {"embed": embed, "allowed_mentions": discord.AllowedMentions.none()}
        kwargs["file"] = file or discord.utils.MISSING
        args = []
        if text is not None:
            args.append(text)

        await channel.send(*args, **kwargs)

    async def _accent_color(self, guild_id: int, kind: Kind) -> int:
        if kind == "leave":
            return DEFAULT_LEAVE_COLOR
        color = await self.bot.database.get_welcome_accent_color(guild_id)  # int | None
        return color if color is not None else DEFAULT_JOIN_COLOR

    async def _build_card(self, member: discord.Member, kind: Kind, accent: int) -> discord.File | None:
        guild = member.guild
        count = guild.member_count or len(guild.members)

        try:
            avatar = await member.display_avatar.replace(size=256, static_format="png").read()
        except discord.DiscordException:
            _log.warning("Could not fetch avatar for %s; falling back to embed.", member.id, exc_info=True)
            return None

        background_url = await self.bot.database.get_welcome_banner_url(guild.id)  # str | None
        background = await self._fetch_background(background_url) if background_url else None

        subtitle = f"to {guild.name}" if kind == "join" else f"from {guild.name}"
        pill = f"Member #{count:,}" if kind == "join" else f"{count:,} members left"

        try:
            buffer = await asyncio.to_thread(
                render_card,
                kind=kind,
                name=member.display_name,
                subtitle=subtitle,
                pill=pill,
                accent=accent,
                avatar=avatar,
                background=background,
            )
        except Exception:
            _log.warning("Failed to render welcome card in guild %s.", guild.id, exc_info=True)
            return None

        return discord.File(buffer, filename="welcome.png")

    async def _fetch_background(self, url: str) -> bytes | None:
        cached = self._background_cache.get(url)
        if cached is not None:
            self._background_cache.move_to_end(url)
            return cached

        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with self.bot.http_session.get(url, timeout=timeout) as resp:
                resp.raise_for_status()
                data = await resp.content.read(MAX_BACKGROUND_BYTES + 1)
        except TimeoutError, aiohttp.ClientError:
            _log.warning("Could not download welcome background %s.", url, exc_info=True)
            return None

        if len(data) > MAX_BACKGROUND_BYTES:
            _log.warning("Welcome background %s exceeds %d bytes; ignoring.", url, MAX_BACKGROUND_BYTES)
            return None

        self._background_cache[url] = data
        if len(self._background_cache) > BACKGROUND_CACHE_SIZE:
            self._background_cache.popitem(last=False)
        return data

    @staticmethod
    def _format_message(message: str | None, member: discord.Member) -> str | None:
        if message is None:
            return None
        try:
            return Template(message).safe_substitute(
                member_mention=member.mention,
                member_name=member.name,
                member_display_name=member.display_name,
                server_name=member.guild.name,
                count=member.guild.member_count,
                member_id=member.id,
                server_id=member.guild.id,
            )
        except KeyError, ValueError:
            _log.warning(
                "Invalid welcome message format in guild %s",
                member.guild.id,
                exc_info=True,
            )
            return message

    @commands.command(name="testwelcome", aliases=["testgoodbye"], hidden=True)
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx: commands.Context) -> None:
        """Test the welcome / goodbye message in this channel."""
        if TYPE_CHECKING:
            assert isinstance(ctx.author, discord.Member)

        kind = "join" if ctx.invoked_with == "testwelcome" else "leave"
        await self._announce(ctx.author, kind)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Welcomer(bot))
