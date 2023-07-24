from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from io import BytesIO
from textwrap import dedent, indent
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont

import discord

from .cards import Card, CardType, Emojis, cards
from .enums import Color
from .transparency import save_transparent_gif

COLORS = {
    Color.red: (255, 69, 69),
    Color.yellow: (255, 199, 69),
    Color.blue: (69, 137, 255),
    Color.green: (83, 194, 109),
    Color.wild: (13, 13, 13),
}


def _create_rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    factor = 5
    radius *= factor  # For anti-alias

    with Image.new("RGBA", (size[0] * factor, size[1] * factor), (0, 0, 0, 0)) as image:
        with Image.new("RGBA", (radius, radius), (0, 0, 0, 0)) as corner:
            draw = ImageDraw.Draw(corner)

            draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=(50, 50, 50))
            mx, my = (size[0] * factor, size[1] * factor)

            image.paste(corner, (0, 0), corner)
            image.paste(corner.rotate(90), (0, my - radius), corner.rotate(90))
            image.paste(corner.rotate(180), (mx - radius, my - radius), corner.rotate(180))
            image.paste(corner.rotate(270), (mx - radius, 0), corner.rotate(270))

        draw = ImageDraw.Draw(image)
        draw.rectangle([(radius, 0), (mx - radius, my)], fill=(50, 50, 50))
        draw.rectangle([(0, radius), (mx, my - radius)], fill=(50, 50, 50))
        image = image.resize(size, Image.Resampling.LANCZOS)

        return image


def _create_sample(card: Card, *, animated: bool = False) -> Optional[BytesIO]:
    with Image.new("RGBA", (256, 256)) as image:
        if card.color is not Color.wild:
            _ = Image.new("RGBA", image.size, COLORS[card.color])
        elif card.type is CardType.plus_4:
            _ = Image.open("./utilities/uno/assets/wild.png").resize(image.size)
        elif card.type is CardType.wild:
            _ = Image.open("./utilities/uno/assets/full_wild.png").resize(image.size)
        else:
            return

        with _ as bg:
            with _create_rounded_mask(bg.size, 26) as mask:
                image.paste(bg, (0, 0), mask)

        if card.type not in (CardType.reverse, CardType.skip):
            if card.type is CardType.number:
                text = str(card.value)
            elif card.type is CardType.plus_2:
                text = "+2"
            elif card.type is CardType.plus_4:
                text = "+4"
            elif card.type is CardType.wild:
                text = ""
            else:
                return

            draw = ImageDraw.Draw(image)

            with open(
                "./utilities/uno/assets/font.ttf",
                "rb",
                encoding="utf-8",
                errors="ignore",
            ) as fp:
                font = ImageFont.truetype(BytesIO(fp.read()), size=210)

            _l, _t, _r, _b = font.getbbox(text)
            w, _ = _r - _l, _b - _t
            x, y = 128 - int(w / 2), -14

            extra = {"stroke_width": 4, "stroke_fill": (0, 0, 0)}

            draw.text((x + 5, y + 5), text, (0, 0, 0), font, **extra)
            draw.text((x, y), text, (255, 255, 255), font, **extra)

        else:
            if card.type is CardType.reverse:
                path = "./utilities/uno/assets/reverse.png"
            elif card.type is CardType.skip:
                path = "./utilities/uno/assets/skip.png"
            else:
                return

            with Image.open(path) as asset:
                x, y = 128 - int(asset.width / 2), 128 - int(asset.height / 2)

                with Image.new("RGBA", asset.size, (0, 0, 0, 255)) as temp:
                    image.paste(temp, (x + 5, y + 5), asset)
                image.paste(asset, (x, y), asset)

        buffer = BytesIO()

        if animated:
            with image.copy() as clone:
                clone.putpixel((0, 0), (255, 255, 255, 1))

            save_transparent_gif([image, clone], [20000, 10], buffer)
        else:
            image.save(buffer, "png")

        buffer.seek(0)
        return buffer


def create_sample(card: Card, *, animated: bool = False) -> Awaitable[BytesIO]:
    return asyncio.to_thread(_create_sample, card, animated=animated)


async def fill_emojis(guild: discord.Guild) -> str:
    # Make room for new emojis
    for emoji in guild.emojis:
        await emoji.delete()

    done = []

    for card in cards:
        if card in done:
            continue

        if card.type is CardType.number:
            name = f"{card.color.name}_{card.value}"
        else:
            name = f"{card.color.name}_{card.type.name}"

        animated = len(done) >= guild.emoji_limit
        buffer = await create_sample(card, animated=animated)
        emoji = str(await guild.create_custom_emoji(name=name, image=buffer.read()))

        if card.color is Color.wild:
            setattr(Emojis, card.type.name, emoji)
        elif card.type is CardType.number:
            getattr(Emojis, card.color.name).numbers[card.value] = emoji
        else:
            setattr(getattr(Emojis, card.color.name), card.type.name, emoji)

        done.append(card)

    # This will usually be done in eval -
    # so return a class representation
    # of the emojis.

    fmt = dedent(
        """
    class Emojis:
        class red:
            numbers = [{}
            ]

            plus_2 = {!r}
            reverse = {!r}
            skip = {!r}

        class yellow:
            numbers = [{}
            ]

            plus_2 = {!r}
            reverse = {!r}
            skip = {!r}

        class blue:
            numbers = [{}
            ]

            plus_2 = {!r}
            reverse = {!r}
            skip = {!r}

        class green:
            numbers = [{}
            ]

            plus_2 = {!r}
            reverse = {!r}
            skip = {!r}

        wild = {!r}
        plus_4 = {!r}
    """,
    )

    def _(sink: Any) -> tuple:
        return (
            indent("\n" + ",\n".join(map(repr, sink.numbers)), " " * 12),
            sink.plus_2,
            sink.reverse,
            sink.skip,
        )

    return fmt.format(
        *_(Emojis.red),
        *_(Emojis.yellow),
        *_(Emojis.blue),
        *_(Emojis.green),
        Emojis.wild,
        Emojis.plus_4,
    ).strip()
