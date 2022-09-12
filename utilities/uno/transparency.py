# Code from https://gist.github.com/egocarib/ea022799cca8a102d14c54a22c45efe0

from collections import defaultdict
from itertools import chain
from random import randrange
from typing import List, Tuple, Union

from PIL.Image import Image


class TransparentAnimatedGifConverter:
    _PALETTE_SLOTSET = set(range(256))

    def __init__(self, img_rgba: Image, alpha_threshold: int = 0) -> None:
        self._img_rgba = img_rgba
        self._alpha_threshold = alpha_threshold

        self._img_p = None
        self._img_p_data = None
        self._palette_replaces = None

    def _process_pixels(self) -> None:
        self._transparent_pixels = {
            idx
            for idx, alpha in enumerate(
                self._img_rgba.getchannel(channel="A").getdata()
            )
            if alpha <= self._alpha_threshold
        }

    def _set_parsed_palette(self) -> None:
        palette = self._img_p.getpalette()
        self._img_p_used_palette_idxs = {
            idx
            for pal_idx, idx in enumerate(self._img_p_data)
            if pal_idx not in self._transparent_pixels
        }

        self._img_p_parsedpalette = {
            idx: tuple(palette[idx * 3 : idx * 3 + 3])
            for idx in self._img_p_used_palette_idxs
        }

    def _get_similar_color_idx(self):
        old_color = self._img_p_parsedpalette[0]
        dict_distance = defaultdict(list)

        for idx in range(1, 256):
            color_item = self._img_p_parsedpalette[idx]
            if color_item == old_color:
                return idx

            distance = sum(
                (
                    abs(old_color[0] - color_item[0]),
                    abs(old_color[1] - color_item[1]),
                    abs(old_color[2] - color_item[2]),
                )
            )
            dict_distance[distance].append(idx)

        return dict_distance[sorted(dict_distance)[0]][0]

    def _remap_palette_idx_zero(self) -> None:
        free_slots = self._PALETTE_SLOTSET - self._img_p_used_palette_idxs
        new_idx = free_slots.pop() if free_slots else self._get_similar_color_idx()

        self._img_p_used_palette_idxs.add(new_idx)
        self._palette_replaces["idx_from"].append(0)
        self._palette_replaces["idx_to"].append(new_idx)
        self._img_p_parsedpalette[new_idx] = self._img_p_parsedpalette[0]

        del self._img_p_parsedpalette[0]

    def _get_unused_color(self) -> Tuple[int, int, int]:
        used_colors = set(self._img_p_parsedpalette.values())
        while True:
            new_color = randrange(256), randrange(256), randrange(256)
            if new_color not in used_colors:
                return new_color

    def _process_palette(self) -> None:
        self._set_parsed_palette()
        if 0 in self._img_p_used_palette_idxs:
            self._remap_palette_idx_zero()

        self._img_p_parsedpalette[0] = self._get_unused_color()

    def _adjust_pixels(self) -> None:
        if self._palette_replaces["idx_from"]:
            trans_table = bytearray.maketrans(
                bytes(self._palette_replaces["idx_from"]),
                bytes(self._palette_replaces["idx_to"]),
            )
            self._img_p_data = self._img_p_data.translate(trans_table)

        for idx_pixel in self._transparent_pixels:
            self._img_p_data[idx_pixel] = 0

        self._img_p.frombytes(data=bytes(self._img_p_data))

    def _adjust_palette(self) -> None:
        unused_color = self._get_unused_color()
        final_palette = chain.from_iterable(
            self._img_p_parsedpalette.get(x, unused_color) for x in range(256)
        )
        self._img_p.putpalette(data=final_palette)

    def process(self) -> Image:
        self._img_p = self._img_rgba.convert(mode="P")
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._palette_replaces = dict(idx_from=[], idx_to=[])
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info["transparency"] = 0
        self._img_p.info["background"] = 0
        return self._img_p


def _create_animated_gif(
    images: List[Image], durations: Union[int, List[int]]
) -> Tuple[Image, dict]:
    save_kwargs = {}
    new_images: List[Image] = []

    for frame in images:
        thumbnail = frame.copy()
        thumbnail_rgba = thumbnail.convert(mode="RGBA")
        thumbnail_rgba.thumbnail(size=frame.size, reducing_gap=3.0)
        converter = TransparentAnimatedGifConverter(img_rgba=thumbnail_rgba)
        thumbnail_p = converter.process()
        new_images.append(thumbnail_p)

    output_image = new_images[0]
    save_kwargs.update(
        format="GIF",
        save_all=True,
        optimize=False,
        append_images=new_images[1:],
        duration=durations,
        disposal=2,  # Other disposals don't work
        loop=0,
    )
    return output_image, save_kwargs


def save_transparent_gif(
    images: List[Image], durations: Union[int, List[int]], save_file
) -> None:
    root_frame, save_args = _create_animated_gif(images, durations)
    root_frame.save(save_file, **save_args)
