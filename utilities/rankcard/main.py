from __future__ import annotations

import requests
from PIL import Image, ImageFont, ImageOps, ImageDraw
from io import BytesIO
import discord
from utilities.converters import ToAsync


@ToAsync()
def rank_card(
    level: int, rank: int, member: discord.Member, *, current_xp: int, custom_background: str, xp_color: str, next_level_xp: int
):
    # create backdrop

    img = Image.new('RGB', (934, 282), color = custom_background)

    response = requests.get(member.display_avatar.url) # get avatar picture
    img_avatar = Image.open(BytesIO(response.content)).convert("RGBA")

    # create circle mask
    bigsize = (img_avatar.size[0] * 3, img_avatar.size[1] * 3)
    mask = Image.new('L', bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(img_avatar.size)
    img_avatar.putalpha(mask)
    img_avatar = img_avatar.resize((170, 170))
    img.paste(img_avatar, (50, 50))
    d = ImageDraw.Draw(img)
    
    x, y, w, h, progress = 260, 180, 575, 40, current_xp/next_level_xp
    bg="#484B4E"
    fg=xp_color
    # draw background
    d.ellipse((x+w, y, x+h+w, y+h), fill=bg)
    d.ellipse((x, y, x+h, y+h), fill=bg)
    d.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=bg)

    # draw progress bar
    w *= progress
    d.ellipse((x+w, y, x+h+w, y+h),fill=fg)
    d.ellipse((x, y, x+h, y+h),fill=fg)
    d.rectangle((x+(h/2), y, x+w+(h/2), y+h),fill=fg)

    font = ImageFont.truetype(font=r"extra/fonts/Montserrat-Regular.ttf", size=40)
    font2 = ImageFont.truetype(font=r"extra/fonts/Montserrat-Regular.ttf", size=25)

    d.text((260, 100), member.name, (255, 255, 255), font=font)
    d.text((740, 130), f"{current_xp}/{next_level_xp} XP", (255, 255, 255), font=font2)
    d.text((650, 50), f"LEVEL {level}", xp_color, font=font)
    d.text((260, 50), f"RANK #{rank}", (255,255,255), font=font2)

    bufferIO = BytesIO()
    img.save(bufferIO, format="PNG")
    bufferIO.seek(0)
    return discord.File(bufferIO, filename="image.png")
