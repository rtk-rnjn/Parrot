from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Iterator
from io import BytesIO
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, Union

from aiohttp import ClientResponse, ClientSession
from lru import LRU

import discord

if TYPE_CHECKING:
    from core import Context, Parrot

from discord.ext import commands

from .config import LRU_CACHE
from .exceptions import ImageTooLarge
from .regex import IMGUR_PAGE_REGEX, TENOR_GIF_REGEX, TENOR_PAGE_REGEX

KT = TypeVar("KT", bound=Any)
VT = TypeVar("VT", bound=Any)


def convert_bool(text: str | bool | Any) -> bool:
    """True/False converter."""
    return str(text).lower() in {"yes", "y", "true", "t", "1", "enable", "on", "o", "ok", "sure", "yeah", "yup"}


class ActionReason(commands.Converter):
    """Action reason converter."""

    async def convert(self, ctx: Context, argument: str | None = None) -> str:
        """Convert the argument to a action string."""
        ret = f"Action requested by {ctx.author} (ID: {ctx.author.id}) | Reason: {argument or 'no reason provided'}"

        LEN = 0 if argument is None else len(argument)
        if len(ret) > 512:
            reason_max = 512 - len(ret) + LEN
            msg = f"Reason is too long ({LEN}/{reason_max})"
            raise commands.BadArgument(msg)
        return ret


class BannedMember(commands.Converter):
    """A coverter that is used for fetching Banned Member of Guild."""

    async def convert(self, ctx: Context, argument: str) -> discord.User | None:
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                ban_entry = await ctx.guild.fetch_ban(discord.Object(id=member_id))
                return ban_entry.user
            except discord.NotFound:
                msg = "User Not Found! Probably this member has not been banned before."
                raise commands.BadArgument(msg) from None

        async for entry in ctx.guild.bans():
            if argument in (entry.user.name, str(entry.user)):
                return entry.user
            if str(entry.user) == argument:
                return entry.user

        msg = "User Not Found! Probably this member has not been banned before."
        raise commands.BadArgument(msg) from None


class WrappedMessageConverter(commands.MessageConverter):
    """A converter that handles embed-suppressed  like <http://example.com>."""

    async def convert(self, ctx: Context, argument: str) -> discord.Message:
        """Wrap the commands.MessageConverter to handle <> delimited message ."""
        # It's possible to wrap a message in [<>] as well, and it's supported because its easy
        if argument.startswith("[") and argument.endswith("]"):
            argument = argument[1:-1]
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]

        return await super().convert(ctx, argument)


def can_execute_action(ctx: Context, user: discord.Member, target: discord.Member) -> bool:
    return user.id in ctx.bot.owner_ids or user == ctx.guild.owner or user.top_role > target.top_role


class MemberID(commands.Converter):
    """A converter that handles user mentions and user IDs."""

    async def convert(self, ctx: Context, argument: str) -> discord.Member | None:
        """Convert a user mention or ID to a member object."""
        try:
            m: discord.Member | None = await commands.MemberConverter().convert(ctx, argument)  # type: ignore
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                msg = f"{argument} is not a valid member or member ID."
                raise commands.BadArgument(msg) from None
            else:
                m: discord.Member | discord.User | None = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
                if m is None:
                    # hackban case
                    return type(  # type: ignore
                        "_Hackban",
                        (),
                        {"id": member_id, "__str__": lambda s: f"Member ID {s.id}"},
                    )()

        if not can_execute_action(ctx, ctx.author, m):
            msg = f"{ctx.author.mention} can not {ctx.command.qualified_name} the {m}, as the their's role is above you"
            raise commands.BadArgument(
                msg,
            )
        return m


class UserID(commands.Converter):
    """A converter that handles user mentions and user IDs."""

    async def convert(self, ctx: Context, argument: str) -> discord.Member | discord.User | None:
        try:
            u: discord.Member | discord.User | None = await commands.UserConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                user_id = int(argument, base=10)
            except ValueError:
                msg = f"{argument} is not a valid user or user ID."
                raise commands.BadArgument(msg) from None
            else:
                u: discord.Member | discord.User | None = await ctx.bot.get_or_fetch_member(
                    ctx.guild,
                    user_id,
                    in_guild=False,
                )
                if u is None:
                    return type(  # type: ignore
                        "_User",
                        (),
                        {"id": user_id, "__str__": lambda s: f"User ID {s.id}"},
                    )()

        return u


def lru_callback(k, v) -> None:
    pass


class Cache(Generic[KT, VT]):
    def __init__(
        self,
        bot: Parrot | None = None,
        cache_size: int | None = 2 ** 5,
        *,
        callback: Callable[[KT, VT], None] | None = None,
    ) -> None:
        self.cache_size: int = cache_size or LRU_CACHE
        self.bot = bot
        self.__internal_cache: LRU = LRU(self.cache_size, callback=callback or lru_callback)

        self.items: Callable[[], list[tuple[int, Any]]] = self.__internal_cache.items
        self.peek_first_item: Callable[[], tuple[int, Any] | None] = self.__internal_cache.peek_first_item
        self.peek_last_item: Callable[[], tuple[int, Any] | None] = self.__internal_cache.peek_last_item
        self.get_size: Callable[[], int] = self.__internal_cache.get_size
        self.set_size: Callable[[int], None] = self.__internal_cache.set_size
        self.has_key: Callable[[object], bool] = self.__internal_cache.has_key
        self.values: Callable[[], list[Any]] = self.__internal_cache.values
        self.keys: Callable[[], list[Any]] = self.__internal_cache.keys
        self.get: Callable[[object], Any] = self.__internal_cache.get
        self.pop: Callable[[object], Any] = self.__internal_cache.pop
        self.get_stats: Callable[[], tuple[int, int]] = self.__internal_cache.get_stats
        self.set_callback: Callable[[Callable[[KT, VT], Any]], None] = self.__internal_cache.set_callback

    def __repr__(self) -> str:
        return repr(self.__internal_cache)

    def __len__(self) -> int:
        return len(self.__internal_cache)

    def __getitem__(self, __k: KT) -> VT:
        return self.__internal_cache[__k]

    def __delitem__(self, __v: KT) -> None:
        del self.__internal_cache[__v]

    def __contains__(self, __o: object) -> bool:
        return self.has_key(__o)

    def __setitem__(self, __k: KT, __v: VT) -> None:
        self.__internal_cache[__k] = __v

    def clear(self) -> None:
        return self.__internal_cache.clear()

    def update(self, *args, **kwargs) -> None:
        return self.__internal_cache.update(*args, **kwargs)

    def setdefault(self, *args, **kwargs) -> None:
        return self.__internal_cache.setdefault(*args, **kwargs)

    def __iter__(self) -> Iterator:
        return iter(self.__internal_cache)


def text_to_list(text: str, *, number_of_lines: int, prefix: str = "```\n", suffix: str = "\n```") -> list[str]:
    texts = text.split("\n")
    ls = []
    temp = ""
    for index, text in enumerate(texts):
        if index % number_of_lines == 0 and index != 0:
            ls.append(prefix + temp + suffix)
            temp = ""
        temp += text + "\n"

    return ls


# fmt: off
CHARACTER_VALUES = {
    200: "\N{PEOPLE HUGGING}",
    50 : "\N{SPARKLING HEART}",
    10 : "\N{SPARKLES}",
    5  : "\N{FACE WITH PLEADING EYES}",
    1  : ",",
    0  : "\N{HEAVY BLACK HEART}",
}
# fmt: on

SECTION_SEPERATOR = "\N{WHITE RIGHT POINTING BACKHAND INDEX}\N{WHITE LEFT POINTING BACKHAND INDEX}"


def to_bottom(text: str) -> str:
    out = bytearray()

    for char in text.encode():
        while char != 0:
            for value, emoji in CHARACTER_VALUES.items():
                if char >= value:
                    char -= value
                    out += emoji.encode()
                    break

        out += SECTION_SEPERATOR.encode()

    return out.decode("utf-8")


def from_bottom(text: str) -> str:
    out = bytearray()
    text = text.strip().removesuffix(SECTION_SEPERATOR)

    if any(c not in CHARACTER_VALUES.values() for c in text.replace(SECTION_SEPERATOR, "")):
        msg = f"Invalid bottom text: {text}"
        raise TypeError(msg)

    for char in text.split(SECTION_SEPERATOR):
        rev_mapping = {v: k for k, v in CHARACTER_VALUES.items()}

        sub = sum(rev_mapping[emoji] for emoji in char)
        out += sub.to_bytes(1, "big")

    return out.decode()


async def get_default_emoji(bot: Parrot, emoji: str, *, svg: bool = True) -> bytes | None:
    from .imaging import image as image_mod

    try:
        if len(emoji) > 1:
            svg = False
            url = f"https://emojicdn.elk.sh/{emoji}?style=twitter"
        else:
            folder = ("72x72", "svg")[svg]
            ext = ("png", "svg")[svg]
            url = f"https://twemoji.maxcdn.com/v/latest/{folder}/{ord(emoji):x}.{ext}"

        async with bot.http_session.get(url) as r:
            if r.ok:
                byt = await r.read()
                return await asyncio.to_thread(image_mod.svg_to_png, byt) if svg else byt
    except Exception:
        return None


class ToImage(commands.Converter):
    async def convert(self, ctx: Context, argument):
        if argument is None:
            converted_union = None
        else:
            converted_union = await commands.run_converters(
                ctx,
                Union[  # noqa: UP007
                    discord.PartialEmoji,
                    discord.Emoji,
                    discord.Member,
                    discord.User,
                    str,
                ],
                argument,
                ctx.current_parameter,  # type: ignore
            )

        return await ctx.to_image(converted_union)

    @staticmethod
    async def none(ctx: Context):
        return await ctx.to_image(None)


async def valid_src(url: str, session: ClientSession):
    async with session.head(url) as resp:
        status = resp.status
    return status == 200


async def emoji_to_url(char, include_check: bool = True, session: ClientSession = None):
    try:
        url = f"https://twemoji.maxcdn.com/v/latest/72x72/{ord(char[0]):x}.png"
        if not include_check:
            return url

        _session = session or ClientSession()
        is_valid = await valid_src(url, _session)
        if not session:
            await _session.close()
        return url if is_valid else char
    except TypeError:
        return char


class DefaultEmojiConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> bytes:
        emoji = await get_default_emoji(ctx.bot, argument)

        if emoji:
            return emoji
        msg = "Invalid Emoji"
        raise commands.BadArgument(msg)


class UrlConverter(commands.Converter):
    async def find_tenor_gif(self, ctx: Context, response: ClientResponse) -> bytes:
        bad_arg = commands.BadArgument("An Error occured when fetching the tenor GIF")
        try:
            content = await response.text()
            if match := TENOR_GIF_REGEX.search(content):
                async with ctx.bot.http_session.get(match.group()) as gif:
                    if gif.ok:
                        return await gif.read()
                    else:
                        raise bad_arg
            else:
                raise bad_arg
        except Exception as e:
            raise bad_arg from e

    async def find_imgur_img(self, ctx: Context, match: re.Match) -> bytes:
        name = match[2]
        raw_url = f"https://i.imgur.com/{name}.gif"

        bad_arg = commands.BadArgument("An Error occured when fetching the imgur GIF")
        try:
            async with ctx.bot.http_session.get(raw_url) as raw:
                if raw.ok:
                    return await raw.read()
                else:
                    raise bad_arg
        except Exception as e:
            raise bad_arg from e

    async def convert(self, ctx: Context, argument: str) -> bytes:
        from .imaging import image as image_mod

        bad_arg = commands.BadArgument("Invalid image URL")
        argument = argument.strip("<>")
        try:
            async with ctx.bot.http_session.get(argument) as r:
                if r.ok:
                    if r.content_type.startswith("image/"):
                        byt = await r.read()
                        if r.content_type.startswith("image/svg"):
                            byt = await asyncio.to_thread(image_mod.svg_to_png, byt)
                        return byt
                    elif TENOR_PAGE_REGEX.fullmatch(argument):
                        return await self.find_tenor_gif(ctx, r)
                    elif imgur := IMGUR_PAGE_REGEX.fullmatch(argument):
                        return await self.find_imgur_img(ctx, imgur)
                    else:
                        raise bad_arg
                else:
                    raise bad_arg
        except Exception as e:
            raise bad_arg from e


class ImageConverter(commands.Converter):
    """ImageConverter.

    A class for fetching and resolving images within a command, it attempts to fetch, (in order):
        - Member from the command argument, then User if failed
        - A Guild Emoji from the command argument, then default emoji if failed
        - An image url, content-type must be of `image/xx`
        - An attachment from the invocation message
        - A sticker from the invocation message

        If all above fails, it repeats the above for references (replies)
        and also searches for embed thumbnails / images in references

    Raises
    ------
    ImageTooLarge
        The resolved image is too large, possibly a decompression bomb?
    commands.BadArgument
        Failed to fetch anything
    """

    _converters: ClassVar[tuple[type[commands.Converter], ...]] = (
        commands.MemberConverter,
        commands.UserConverter,
        commands.PartialEmojiConverter,
        DefaultEmojiConverter,
        UrlConverter,
    )

    def check_size(self, byt: bytes, *, max_size: int = 15_000_000) -> None:
        if (size := byt.__sizeof__()) > max_size:
            del byt
            raise ImageTooLarge(size, max_size)

    async def converted_to_buffer(self, source: discord.Member | discord.User | discord.PartialEmoji | bytes) -> bytes:
        if isinstance(source, discord.Member | discord.User):
            source = await source.display_avatar.read()

        elif isinstance(source, discord.PartialEmoji):
            source = await source.read()

        return source

    async def get_attachments(self, ctx: Context, message: discord.Message | None = None) -> bytes | None:
        source = None
        message = message or ctx.message

        if files := message.attachments:
            source = await self.get_file_image(files)

        if (st := message.stickers) and source is None:
            source = await self.get_sticker_image(ctx, st)

        if (embeds := message.embeds) and source is None:
            for embed in embeds:
                if img := embed.image.url or embed.thumbnail.url:
                    try:
                        source = await UrlConverter().convert(ctx, img)
                        break
                    except commands.BadArgument:
                        continue
        return source

    async def get_sticker_image(self, ctx: Context, stickers: list[discord.StickerItem]) -> bytes | None:
        for sticker in stickers:
            if sticker.format is not discord.StickerFormatType.lottie:
                try:
                    return await UrlConverter().convert(ctx, sticker.url)
                except commands.BadArgument:
                    continue

    async def get_file_image(self, files: list[discord.Attachment]) -> bytes | None:
        from .imaging import image as image_mod

        for file in files:
            if file.content_type and file.content_type.startswith("image/"):
                byt = await file.read()
                if file.content_type.startswith("image/svg"):
                    byt = await asyncio.to_thread(image_mod.svg_to_png, byt)
                return byt

    async def convert(self, ctx: Context, argument: str, *, raise_on_failure: bool = True) -> bytes | None:
        for converter in self._converters:
            try:
                source = await converter().convert(ctx, argument)
            except commands.BadArgument:
                continue
            else:
                break
        else:
            if not raise_on_failure:
                return None

            msg = "Failed to fetch an image from argument"
            raise commands.BadArgument(msg)
        return await self.converted_to_buffer(source)

    async def get_image(self, ctx: Context, source: str | bytes | None, *, max_size: int = 15_000_000) -> BytesIO:
        if isinstance(source, str):
            source = await self.convert(ctx, source, raise_on_failure=False)

        if source is None:
            source = await self.get_attachments(ctx)

        if (ref := ctx.message.reference) and source is None:
            ref = ref.resolved

            if not isinstance(ref, discord.DeletedReferencedMessage) and ref:
                source = await self.get_attachments(ctx, ref)

                if source is None and ref.content:
                    source = await self.convert(ctx, ref.content.split()[0], raise_on_failure=False)

        if source is None:
            source = await ctx.author.display_avatar.read()

        self.check_size(source, max_size=max_size)
        return BytesIO(source)
