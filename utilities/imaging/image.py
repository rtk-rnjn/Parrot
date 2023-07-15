from __future__ import annotations

import asyncio
import time
from io import BytesIO
from itertools import cycle
from math import ceil
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Concatenate,
    Final,
    Iterable,
    Optional,
    ParamSpec,
    TypeAlias,
    TypeVar,
)

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageSequence
from wand.drawing import Drawing
from wand.image import Image as WandImage
from wand.sequence import Sequence

import discord
from discord.ext import commands

from ..converters import ImageConverter, ToAsync
from ..exceptions import TooManyFrames

if TYPE_CHECKING:
    from core import Context

    IT = TypeVar('IT')

    P = ParamSpec('P')
    C = TypeVar('C', Context)
    I = TypeVar('I', Image.Image)
    R = TypeVar('R', Image.Image, list[Image.Image], BytesIO)

    I_ = TypeVar('I_', WandImage)
    R_ = TypeVar('R_', WandImage, list[WandImage], BytesIO)

    CMD = TypeVar('CMD', bound=commands.Command)

    PillowParams: TypeAlias = Concatenate[C, I, P]
    PillowFunction: TypeAlias = Callable[PillowParams, R]
    PillowThreaded: TypeAlias = Callable[PillowParams, Awaitable[R]]

    WandParams: TypeAlias = Concatenate[C, I_, P]
    WandFunction: TypeAlias = Callable[WandParams, R_]
    WandThreaded: TypeAlias = Callable[WandParams, Awaitable[R_]]

    GraphFn: TypeAlias = Callable[Concatenate[C, P], Awaitable[discord.File]]

    Duration: TypeAlias = list[int] | int | None

__all__: tuple[str, ...] = (
    'check_frame_amount',
    'svg_to_png',
    'process_gif',
    'get_closest_color',
    'wand_circle_mask',
    'pil_circle_mask',
    'wand_circular',
    'pil_circular',
    'resize_pil_prop',
    'resize_wand_prop',
    'resize_cv_prop',
    'process_wand_gif',
    'wand_save_list',
    'save_wand_image',
    'save_pil_image',
    'pil_image',
    'wand_image',
    'to_array',
    'do_command',
)

MAX_FRAMES: Final[int] = 200
FORMATS: Final[tuple[str, ...]] = ('png', 'gif')


@ToAsync()
def svg_to_png(
    svg_bytes: bytes,
    *,
    width: int = 500,
    height: int = 500,
) -> bytes:
    with WandImage(
        blob=svg_bytes,
        format='svg',
        width=width,
        height=height,
        background='none',
    ) as asset:
        return asset.make_blob('png')


async def run_threaded(func: Callable[[BytesIO], R | R_], argument: BytesIO, *, timeout: int = 600) -> R | R_:
    return await asyncio.wait_for(
        asyncio.to_thread(func, argument),
        timeout=timeout,
    )


def check_frame_amount(img: Image.Image | WandImage, max_frames: int = MAX_FRAMES) -> None:
    if isinstance(img, Image.Image):
        n_frames = getattr(img, 'n_frames', 1)
    elif isinstance(img, WandImage):
        n_frames = len(img.sequence)
    else:
        n_frames = len(img)

    if n_frames > max_frames:
        raise TooManyFrames(n_frames, max_frames)


def process_gif(
    img: WandImage | Image.Image,
    iterable: Iterable[IT],
) -> Iterable[tuple[WandImage | Image.Image, IT]]:
    if isinstance(img, WandImage):
        seq = img.sequence
    else:
        seq = ImageSequence.Iterator(img)
    return zip(cycle(seq), iterable)


def get_closest_color(px: tuple[int, ...], sample: list | np.ndarray, *, reverse: bool = False) -> tuple[int, ...]:
    if not isinstance(sample, np.ndarray):
        sample = np.array(sample)

    distances = np.sqrt(np.sum((sample - px) ** 2, axis=1))
    fn = (np.amin, np.amax)[reverse]
    idx = np.where(distances == fn(distances))
    return tuple(sample[idx][0])


def wand_circle_mask(width: int, height: int) -> WandImage:
    mask = WandImage(width=width, height=height, background='transparent', colorspace='gray')
    mask.antialias = True
    with Drawing() as draw:
        draw.stroke_color = 'black'
        draw.stroke_width = 1
        draw.fill_color = 'white'
        draw.circle((width // 2, height // 2), (width // 2, 0))
        draw(mask)
    return mask


def pil_circle_mask(width: int, height: int) -> Image.Image:
    mask = Image.new('RGBA', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, width, height), fill='white')
    return mask


def wand_circular(img: I_, *, mask: Optional[WandImage] = None) -> I_:
    if not mask:
        mask = wand_circle_mask(img.width, img.height)

    if mask.size != img.size:
        mask = mask.clone()
        mask.resize(*img.size, filter='lanczos')

    img.composite(mask, left=0, top=0, operator='copy_alpha')
    return img


def pil_circular(img: Image.Image, *, mask: Optional[Image.Image] = None) -> Image.Image:
    if not mask:
        mask = pil_circle_mask(img.width, img.height)

    if mask.size != img.size:
        mask = mask.resize(img.size, Image.Resampling.LANCZOS)

    out = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
    out = ImageChops.darker(img, mask)
    return out


def _get_prop_size(
    image: Image.Image | WandImage | np.ndarray,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> tuple[int, int]:
    if isinstance(image, (Image.Image, WandImage)):
        w, h = image.size
    else:
        h, w, *_ = image.shape

    if width:
        height = ceil((width / w) * h)
    elif height:
        width = ceil((height / h) * w)
    else:
        width, height = image.size

    return width, height


def process_wand_gif(
    image: I_,
    func: WandFunction,
    ctx: Context,
    *args,
    max_frames: int = MAX_FRAMES,
    **kwargs,
) -> I_:
    check_frame_amount(image, max_frames)

    for i, frame in enumerate(image.sequence):
        result = func(ctx, frame, *args, **kwargs)
        result.dispose = 'background'
        image.sequence[i] = result

    image.dispose = 'background'
    image.format = 'GIF'
    return image


def resize_pil_prop(
    image: Image.Image,
    width: Optional[int] = None,
    height: Optional[int] = None,
    *,
    process_gif: bool = True,
    resampling: Image.Resampling = Image.Resampling.LANCZOS,
) -> list[Image.Image] | Image.Image:
    if not (width and height):
        width, height = _get_prop_size(image, width, height)

    def resize_image(img: Image.Image) -> Image.Image:
        return img.resize((width, height), resampling)

    if getattr(image, 'is_animated', False) and process_gif:
        return ImageSequence.all_frames(image, resize_image)
    else:
        return resize_image(image)


def resize_wand_prop(
    image: WandImage,
    width: Optional[int] = None,
    height: Optional[int] = None,
    *,
    resampling: str = 'lanczos',
) -> WandImage:
    if not (width and height):
        width, height = _get_prop_size(image, width, height)

    image.resize(width, height, filter=resampling)
    return image


def resize_cv_prop(
    image: np.ndarray,
    width: Optional[int] = None,
    height: Optional[int] = None,
    *,
    resampling: int = cv2.INTER_LANCZOS4,
) -> np.ndarray:
    if not (width and height):
        width, height = _get_prop_size(image, width, height)

    return cv2.resize(image, (width, height), interpolation=resampling)


def wand_save_list(
    frames: list[Image.Image | WandImage] | ImageSequence.Iterator,
    duration: Duration,
) -> WandImage:
    is_pil = isinstance(frames, ImageSequence.Iterator) or isinstance(frames[0], Image.Image)

    base = WandImage()

    for i, frame in enumerate(frames):
        if is_pil:
            frame = np.asarray(frame.convert('RGBA'))
            frame = WandImage.from_array(frame)

        frame.dispose = 'background'

        if isinstance(duration, list):
            frame.delay = duration[i]
        elif duration is not None:
            frame.delay = duration
        if is_pil:
            frame.delay //= 10
        base.sequence.append(frame)

    base.dispose = 'background'
    base.format = 'GIF'
    return base


def save_wand_image(
    image: WandImage | list[Image.Image | WandImage] | ImageSequence.Iterator,
    *,
    duration: Duration = None,
    file: bool = True,
) -> discord.File | BytesIO:
    is_list = isinstance(image, (list, ImageSequence.Iterator))

    is_gif = is_list or getattr(image, 'format', '').lower() == 'gif' or len(getattr(image, 'sequence', [])) > 1

    if is_list:
        image = wand_save_list(image, duration)

    elif is_gif:
        image.format = 'GIF'
        image.dispose = 'background'

    output = BytesIO()
    image.save(file=output)
    output.seek(0)

    image.close()
    del image

    if file:
        output = discord.File(output, f'output.{FORMATS[is_gif]}')
    return output


def save_pil_image(
    image: Image.Image | list[Image.Image],
    *,
    duration: Optional[int] = None,
    file: bool = True,
) -> discord.File | BytesIO:
    if is_gif := isinstance(image, list):
        return save_wand_image(image, duration=duration)

    elif is_gif := getattr(image, 'is_animated', False):
        return save_wand_image(ImageSequence.Iterator(image), duration=duration)

    output = BytesIO()
    image.save(output, format='PNG')
    output.seek(0)

    image.close()
    del image

    if file:
        output = discord.File(output, f'output.{FORMATS[is_gif]}')
    return output


def pil_image(
    width: Optional[int] = None,
    height: Optional[int] = None,
    *,
    process_all_frames: bool = True,
    duration: Duration = None,
    auto_save: bool = True,
    to_file: bool = True,
    pass_buf: bool = False,
    max_frames: int = MAX_FRAMES,
) -> Callable[[PillowFunction], PillowThreaded]:
    def decorator(func: PillowFunction) -> PillowThreaded:
        async def wrapper(ctx: C, img: I, *args: P.args, **kwargs: P.kwargs) -> R:
            img = await ImageConverter().get_image(ctx, img)

            def inner(image: BytesIO) -> R:
                durations = None
                if not pass_buf:
                    image: Image.Image = Image.open(image)
                    durations = image.info.get('duration')

                    if width or height:
                        image = resize_pil_prop(image, width, height, process_gif=process_all_frames)

                if process_all_frames and (
                    isinstance(image, list) or getattr(image, 'is_animated', False) or str(image.format).lower() == 'gif'
                ):
                    check_frame_amount(image, max_frames)
                    result = ImageSequence.all_frames(image, lambda frame: func(ctx, frame, *args, **kwargs))
                else:
                    result = func(ctx, image, *args, **kwargs)

                if auto_save and isinstance(result, (Image.Image, list, ImageSequence.Iterator)):
                    result = save_pil_image(result, duration=durations or duration, file=to_file)
                return result

            return await run_threaded(inner, img)

        return wrapper

    return decorator


def wand_image(
    width: Optional[int] = None,
    height: Optional[int] = None,
    *,
    process_all_frames: bool = True,
    duration: Duration = None,
    auto_save: bool = True,
    to_file: bool = True,
    pass_buf: bool = False,
    max_frames: int = MAX_FRAMES,
) -> Callable[[WandFunction], WandThreaded]:
    def decorator(func: WandFunction) -> WandThreaded:
        async def wrapper(ctx: C, img: I, *args: P.args, **kwargs: P.kwargs) -> R_:
            img = await ImageConverter().get_image(ctx, img)

            def inner(image: BytesIO) -> R_:
                durations = None
                if not pass_buf:
                    image: WandImage = WandImage(file=image)
                    image.background_color = 'none'

                    durations = [frame.delay for frame in Sequence(image)]

                    if width or height:
                        image = resize_wand_prop(image, width, height)

                if process_all_frames and (
                    isinstance(image, list) or len(image.sequence) > 1 or str(image.format).lower() == 'gif'
                ):
                    result = process_wand_gif(image, func, ctx, *args, max_frames=max_frames, **kwargs)
                else:
                    result = func(ctx, image, *args, **kwargs)

                if auto_save and isinstance(result, (WandImage, list)):
                    result = save_wand_image(result, duration=durations or duration, file=to_file)
                return result

            return await run_threaded(inner, img)

        return wrapper

    return decorator


def _convert_to_arr(
    image: Image.Image | WandImage,
    img_mode: str,
    arr_mode: int,
) -> np.ndarray:
    if image.mode != img_mode.upper():
        if isinstance(image, Image.Image):
            image = image.convert(img_mode.upper())
        elif isinstance(image, WandImage):
            image.transform_colorspace(img_mode.lower())

    arr = np.asarray(image)
    return cv2.cvtColor(arr, arr_mode)


def _convert_from_arr(
    arr: np.ndarray | Any,
    og_image: Image.Image | WandImage,
    arr_mode: int,
) -> Image.Image | WandImage | Any:
    if isinstance(arr, np.ndarray):
        arr = cv2.cvtColor(arr, arr_mode)

        if isinstance(og_image, WandImage):
            arr: WandImage = WandImage.from_array(arr)
            if arr.format == 'MIFF':
                arr.format = 'png'
        elif isinstance(og_image, Image.Image):
            arr = Image.fromarray(arr)
    return arr


def to_array(
    img_mode: str = 'RGB', arr_mode: int = cv2.COLOR_RGB2BGR
) -> Callable[[WandFunction | PillowFunction], WandFunction | PillowFunction]:
    def decorator(func: WandFunction | PillowFunction) -> WandFunction | PillowFunction:
        def inner(ctx: C, image: I | I_ | list[I | I_], *args: P.args, **kwargs: P.kwargs) -> R | R_:
            if isinstance(image, list):
                arr = [_convert_to_arr(frame, img_mode, arr_mode) for frame in image]
            else:
                arr = _convert_to_arr(image, img_mode, arr_mode)

            arr = func(ctx, arr, *args, **kwargs)

            if isinstance(arr, list):
                arr = [_convert_from_arr(frame, image, arr_mode) for frame in arr]
            else:
                arr = _convert_from_arr(arr, image, arr_mode)
            return arr

        return inner

    return decorator


async def _do_command_body(
    ctx: Context,
    image: Any,
    func: WandThreaded | PillowThreaded | GraphFn,
    **kwargs: Any,
) -> None:
    start = time.perf_counter()
    file = await func(ctx, image, **kwargs)
    end = time.perf_counter()
    elapsed = (end - start) * 1000

    await ctx.reply(
        content=f'**Process Time:** `{elapsed:.2f} ms`',
        file=file,
        mention_author=False,
    )


async def do_command(
    ctx: Context,
    image: Any,
    func: WandThreaded | PillowThreaded | GraphFn,
    *,
    load: bool = True,
    **kwargs: Any,
) -> None:
    if not load:
        return await _do_command_body(ctx, image, func=func, **kwargs)
    async with ctx.typing():
        return await _do_command_body(ctx, image, func=func, **kwargs)
