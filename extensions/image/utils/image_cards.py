from __future__ import annotations

import hashlib
from collections.abc import Sequence

lazy from PIL import Image, ImageDraw

from .image_generator import gradient
from .image_utils import (
    EncodedImage,
    apply_mask,
    center_crop_square,
    crop_circle,
    encode_image,
    extract_dominant_palette,
    load_font,
    load_image,
    resize_rgba,
    rounded_mask,
)
from .image_validators import Color, clamp_int, validate_choice

CARD_STYLES = ("wanted", "idcard", "trading", "polaroid", "magazine")


def render_ship(
    data_a: bytes,
    data_b: bytes,
    name_a: str,
    name_b: str,
    score: int | None = None,
) -> EncodedImage:
    """Render a romantic/friendship ship card with two circular avatars, heart, and compatibility bar."""
    if score is None:
        digest = hashlib.sha256(f"{min(name_a, name_b)}:{max(name_a, name_b)}".encode()).digest()
        pct = digest[0] % 101
    else:
        pct = clamp_int(score, 0, 100, "score")
    bg = gradient(760, 320, "linear", colors=[(48, 18, 62), (95, 22, 72)], angle=25).convert("RGBA")
    draw = ImageDraw.Draw(bg)
    av_a = crop_circle(load_image(data_a, max_dim=256), 168)
    av_b = crop_circle(load_image(data_b, max_dim=256), 168)
    bg.alpha_composite(av_a, (56, 46))
    bg.alpha_composite(av_b, (760 - 56 - 168, 46))
    cx, cy = 380, 125
    heart_col = (255, 75, 125, 255) if pct >= 50 else (180, 110, 150, 255)
    draw.ellipse((cx - 38, cy - 34, cx + 4, cy + 8), fill=heart_col)
    draw.ellipse((cx - 4, cy - 34, cx + 38, cy + 8), fill=heart_col)
    draw.polygon([(cx - 40, cy - 8), (cx + 40, cy - 8), (cx, cy + 44)], fill=heart_col)
    font_big = load_font(26, bold=True)
    font_sm = load_font(17, bold=True)
    draw.text((cx, cy - 4), f"{pct}%", fill=(255, 255, 255, 255), font=font_big, anchor="mm")
    bx0, by0, bx1, by1 = 160, 245, 600, 273
    draw.rounded_rectangle((bx0, by0, bx1, by1), radius=14, fill=(28, 12, 38, 220), outline=(255, 160, 195, 180), width=2)
    fill_w = int((bx1 - bx0 - 6) * (pct / 100.0))
    if fill_w > 8:
        draw.rounded_rectangle((bx0 + 3, by0 + 3, bx0 + 3 + fill_w, by1 - 3), radius=11, fill=(255, 85, 140, 255))
    draw.text((140, 228), name_a[:18], fill=(245, 230, 245, 255), font=font_sm, anchor="mm")
    draw.text((620, 228), name_b[:18], fill=(245, 230, 245, 255), font=font_sm, anchor="mm")
    return encode_image(bg)


def render_compare(data_a: bytes, data_b: bytes, label_a: str = "Player 1", label_b: str = "Player 2") -> EncodedImage:
    """Render a side-by-side VS comparison card."""
    w, h = 780, 380
    canvas = gradient(w, h, "linear", colors=[(20, 26, 48), (52, 18, 38)], angle=15).convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw.polygon([(w // 2 + 28, 0), (w // 2 - 28, h), (w, h), (w, 0)], fill=(75, 20, 42, 140))
    av_a = apply_mask(resize_rgba(center_crop_square(load_image(data_a, max_dim=320)), (230, 230)), rounded_mask(230, 32))
    av_b = apply_mask(resize_rgba(center_crop_square(load_image(data_b, max_dim=320)), (230, 230)), rounded_mask(230, 32))
    canvas.alpha_composite(av_a, (60, 52))
    canvas.alpha_composite(av_b, (w - 60 - 230, 52))
    draw.ellipse((w // 2 - 42, h // 2 - 42, w // 2 + 42, h // 2 + 42), fill=(255, 185, 35, 255), outline=(255, 255, 255, 255), width=4)
    draw.text((w // 2, h // 2), "VS", fill=(22, 18, 28, 255), font=load_font(30, bold=True), anchor="mm")
    font_lbl = load_font(20, bold=True)
    draw.text((175, 315), label_a[:20], fill=(235, 240, 255, 255), font=font_lbl, anchor="mm")
    draw.text((w - 175, 315), label_b[:20], fill=(255, 230, 235, 255), font=font_lbl, anchor="mm")
    return encode_image(canvas)


def render_profile_card(
    avatar_data: bytes,
    username: str,
    display_name: str,
    roles: Sequence[str],
    joined_str: str,
    created_str: str,
    accent: Color | None = None,
) -> EncodedImage:
    """Render a stylized Discord member profile card."""
    w, h = 760, 320
    av_img = load_image(avatar_data, max_dim=256)
    pal = extract_dominant_palette(av_img, 3)
    primary = accent or pal[0]
    canvas = Image.new("RGBA", (w, h), (20, 22, 30, 255))
    banner = gradient(w, 105, "linear", colors=[primary, pal[1 % len(pal)]], angle=20).convert("RGBA")
    canvas.alpha_composite(banner, (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((34, 42, 174, 182), fill=(20, 22, 30, 255))
    canvas.alpha_composite(crop_circle(av_img, 128), (40, 48))
    draw.text((195, 118), display_name[:26], fill=(255, 255, 255, 255), font=load_font(26, bold=True))
    draw.text((195, 150), f"@{username[:30]}", fill=(165, 175, 195, 255), font=load_font(16))
    draw.text((44, 206), f"Joined Server: {joined_str}", fill=(210, 220, 235, 255), font=load_font(15, bold=True))
    draw.text((44, 234), f"Account Created: {created_str}", fill=(185, 195, 215, 255), font=load_font(15))
    rx, ry = 44, 268
    r_font = load_font(13, bold=True)
    for role in list(roles)[:5]:
        pill_w = max(56, len(role) * 8 + 22)
        if rx + pill_w > w - 24:
            break
        draw.rounded_rectangle((rx, ry, rx + pill_w, ry + 28), radius=14, fill=(*primary, 75), outline=(*primary, 215), width=2)
        draw.text((rx + pill_w // 2, ry + 14), role[:18], fill=(245, 248, 255, 255), font=r_font, anchor="mm")
        rx += pill_w + 10
    return encode_image(canvas)


def render_card_template(  # noqa: PLR0915
    avatar_data: bytes,
    style: str = "wanted",
    title: str = "WANTED",
    subtitle: str = "DEAD OR ALIVE • $1,000,000,000",
) -> EncodedImage:
    """Render an avatar inside a themed card (`wanted`, `idcard`, `trading`, `polaroid`, `magazine`)."""
    style = validate_choice(style, CARD_STYLES, "style")
    av = center_crop_square(load_image(avatar_data, max_dim=512))
    if style == "wanted":
        w, h = 520, 680
        canvas = Image.new("RGBA", (w, h), (228, 204, 162, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((22, 22, w - 22, h - 22), outline=(78, 52, 28, 255), width=5)
        draw.text((w // 2, 72), "WANTED", fill=(68, 40, 20, 255), font=load_font(54, bold=True), anchor="mm")
        photo = resize_rgba(av, (380, 380))
        canvas.alpha_composite(photo, (70, 125))
        draw.rectangle((70, 125, 450, 505), outline=(68, 40, 20, 255), width=4)
        draw.text((w // 2, 548), title[:22].upper(), fill=(58, 34, 16, 255), font=load_font(34, bold=True), anchor="mm")
        draw.text((w // 2, 608), subtitle[:34], fill=(88, 54, 28, 255), font=load_font(20, bold=True), anchor="mm")
        return encode_image(canvas)
    if style == "polaroid":
        w, h = 480, 560
        canvas = Image.new("RGBA", (w, h), (248, 246, 240, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, w - 1, h - 1), outline=(210, 205, 195, 255), width=3)
        canvas.alpha_composite(resize_rgba(av, (420, 420)), (30, 30))
        draw.text((w // 2, 500), title[:28], fill=(35, 38, 45, 255), font=load_font(26, bold=True), anchor="mm")
        return encode_image(canvas)
    if style == "idcard":
        w, h = 680, 400
        canvas = Image.new("RGBA", (w, h), (238, 242, 250, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, w, 76), fill=(28, 64, 148, 255))
        draw.text((28, 38), "OFFICIAL MEMBER IDENTIFICATION", fill=(255, 255, 255, 255), font=load_font(22, bold=True), anchor="lm")
        canvas.alpha_composite(apply_mask(resize_rgba(av, (210, 210)), rounded_mask(210, 18)), (34, 112))
        draw.text((275, 135), f"NAME: {title[:22]}", fill=(24, 30, 45, 255), font=load_font(22, bold=True))
        draw.text((275, 185), f"STATUS: {subtitle[:26]}", fill=(60, 72, 95, 255), font=load_font(18, bold=True))
        draw.text((275, 230), "CLEARANCE: LEVEL 5", fill=(28, 64, 148, 255), font=load_font(18, bold=True))
        for bx in range(275, 620, 6):
            if (bx * 7) % 11 > 3:
                draw.rectangle((bx, 290, bx + 3, 350), fill=(25, 25, 30, 255))
        return encode_image(canvas)
    if style == "trading":
        w, h = 500, 680
        canvas = gradient(w, h, "linear", colors=[(35, 42, 85), (18, 20, 38)], angle=60).convert("RGBA")
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((14, 14, w - 14, h - 14), radius=24, outline=(245, 198, 68, 255), width=8)
        draw.text((40, 48), title[:20], fill=(255, 240, 185, 255), font=load_font(26, bold=True), anchor="lm")
        draw.text((w - 40, 48), "★ 99", fill=(255, 210, 75, 255), font=load_font(24, bold=True), anchor="rm")
        canvas.alpha_composite(resize_rgba(av, (412, 360)), (44, 84))
        draw.rectangle((44, 84, 456, 444), outline=(245, 198, 68, 255), width=4)
        draw.rounded_rectangle((38, 468, w - 38, h - 38), radius=14, fill=(24, 28, 52, 230), outline=(245, 198, 68, 180), width=2)
        draw.text((w // 2, 545), subtitle[:36], fill=(230, 235, 250, 255), font=load_font(18, bold=True), anchor="mm")
        return encode_image(canvas)
    w, h = 540, 700
    canvas = resize_rgba(av, (w, h))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, w, 130), fill=(0, 0, 0, 115))
    draw.rectangle((0, h - 150, w, h), fill=(0, 0, 0, 145))
    draw.text((w // 2, 65), "VOGUE • DISCORD", fill=(255, 255, 255, 245), font=load_font(44, bold=True), anchor="mm")
    draw.text((32, h - 105), title[:22].upper(), fill=(255, 215, 65, 255), font=load_font(32, bold=True))
    draw.text((32, h - 55), subtitle[:36], fill=(240, 240, 245, 255), font=load_font(20, bold=True))
    canvas.alpha_composite(overlay)
    return encode_image(canvas)
