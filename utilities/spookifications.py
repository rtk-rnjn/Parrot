from __future__ import annotations

from random import choice, randint

from PIL import Image, ImageOps


def inversion(im: Image) -> Image:
    """
    Inverts the image.
    Returns an inverted image when supplied with an Image object.
    """
    im = im.convert("RGB")
    return ImageOps.invert(im)


def pentagram(im: Image) -> Image:
    """Adds pentagram to the image."""
    im = im.convert("RGB")
    wt, ht = im.size
    penta = Image.open(r"extra/halloween/bloody-pentagram.png")
    penta = penta.resize((wt, ht))
    im.paste(penta, (0, 0), penta)
    return im


def bat(im: Image) -> Image:
    """
    Adds a bat silhoutte to the image.
    The bat silhoutte is of a size at least one-fifths that of the original image and may be rotated
    up to 90 degrees anti-clockwise.
    """
    im = im.convert("RGB")
    wt, ht = im.size
    bat = Image.open(r"extra/halloween/bat-clipart.png")
    bat_size = randint(wt // 10, wt // 7)
    rot = randint(0, 90)
    bat = bat.resize((bat_size, bat_size))
    bat = bat.rotate(rot)
    x = randint(wt - (bat_size * 3), wt - bat_size)
    y = randint(10, bat_size)
    im.paste(bat, (x, y), bat)
    im.paste(bat, (x + bat_size, y + (bat_size // 4)), bat)
    im.paste(bat, (x - bat_size, y - (bat_size // 2)), bat)
    return im


def get_random_effect(im: Image) -> Image:
    """Randomly selects and applies an effect."""
    effects = [inversion, pentagram, bat]
    effect = choice(effects)
    return effect(im)
