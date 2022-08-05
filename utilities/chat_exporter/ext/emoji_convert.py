from __future__ import annotations

import unicodedata
from grapheme import graphemes
import emojis
import aiohttp

from ..ext.cache import cache


cdn_fmt = "https://twemoji.maxcdn.com/v/latest/72x72/{codepoint}.png"

@cache()
async def valid_src(src):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(src) as resp:
                return resp.status == 200
    except aiohttp.ClientConnectorError:
        return False


def valid_category(char):
    try:
        return unicodedata.category(char) == "So"
    except TypeError:
        return False


async def codepoint(codes):
    # See https://github.com/twitter/twemoji/issues/419#issuecomment-637360325
    if "200d" not in codes:
        return "-".join([c for c in codes if c != "fe0f"])
    return "-".join(codes)


async def convert(char):
    if valid_category(char):
        name = unicodedata.name(char).title()
    else:
        if len(char) == 1:
            return char

        shortcode = emojis.decode(char)
        name = shortcode.replace(":", "").replace("_", " ").replace("selector", "").title()

    src = cdn_fmt.format(codepoint=await codepoint(["{cp:x}".format(cp=ord(c)) for c in char]))

    if await valid_src(src):
        return f'<img class="emoji emoji--small" src="{src}" alt="{char}" title="{name}" aria-label="Emoji: {name}">'
    else:
        return char


async def convert_emoji(string):
    x = []
    for ch in graphemes(string):
        x.append(await convert(ch))
    return "".join(x)