from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

import aiohttp
import arrow
import discord
from discord.ext import commands

from core.utils import PaginationView

from .pinporn import PinPorn, Video
from .sexdotcom import Pin, SexDotComGif, SexDotComPics

if TYPE_CHECKING:
    from core import Parrot

ENDPOINTS = [
    "hentai",
    "holo",
    "hneko",
    "hkitsune",
    "kemonomimi",
    "pgif",
    "4k",
    "kanna",
    "ass",
    "pussy",
    "thigh",
    "hthigh",
    "paizuri",
    "tentacle",
    "boobs",
    "hboobs",
    "yaoi",
    "hmidriff",
    "hass",
    "anal",
    "gonewild",
    "hanal",
]

_log = logging.getLogger("bot.cogs.nsfw")


class NSFW(commands.Cog, command_attrs={"hidden": True}):
    """Mature Content. 18+ only."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.nekobot_image_url = "https://nekobot.xyz/api/image"

        _log.info("Cog loaded: %s", self.__class__.__name__)

        self._sexdotcomgif = SexDotComGif(session=self.bot.http_session)
        self._sexdotcompics = SexDotComPics(session=self.bot.http_session)
        self._pinporn = PinPorn(session=self.bot.http_session)

    async def is_user_allowed(self, ctx: commands.Context[Parrot]) -> bool:
        if ctx.author.id in (self.bot.owner_ids or {}):
            return True

        if ctx.author.id == self.bot.owner_id:
            return True

        birthday = await self.bot.database.get_user_birthday(ctx.author.id)
        if birthday is None:
            return False

        birthday_date = arrow.get(birthday)
        today = arrow.utcnow()
        age = today.year - birthday_date.year - ((today.month, today.day) < (birthday_date.month, birthday_date.day))
        return age >= 18

    async def cog_load(self):
        self.command_loader()

    async def cog_unload(self):

        for end_point in ENDPOINTS:
            self.bot.remove_command(end_point)

    async def cog_check(self, ctx: commands.Context[Parrot]) -> bool | None:
        assert isinstance(ctx.channel, discord.abc.GuildChannel)

        if not ctx.channel.nsfw:
            raise commands.NSFWChannelRequired(ctx.channel)
        return True

    async def get_embed(self, type_str: str) -> discord.Embed:
        response = await self.bot.http_session.get(self.nekobot_image_url, params={"type": type_str})
        if response.status != 200:
            msg = "Something went wrong with the API"
            raise commands.CommandError(msg)
        url = (await response.json())["message"]

        return discord.Embed().set_image(url=url)

    async def send_command_response(self, ctx: commands.Context[Parrot]) -> None:
        assert ctx.command is not None
        await ctx.typing()
        embed = await self.get_embed(ctx.command.qualified_name)
        await ctx.reply(embed=embed)

    def command_loader(self) -> None:
        for end_point in ENDPOINTS:
            command = commands.Command(NSFW.send_command_response, enabled=True, name=end_point)
            command.cog = self

            self.bot.add_command(command)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def n(
        self,
        ctx: commands.Context[Parrot],
        *,
        endpoint: Literal["gif", "jav", "rb", "ahegao", "twitter"] = "gif",
    ) -> None:
        """Mature Content. 18+ only Please.

        This command has a cooldown of 5 seconds per user.
        """
        await ctx.typing()
        r = await self.bot.http_session.get(f"https://scathach.redsplit.org/v3/nsfw/{endpoint}/")
        if r.status == 200:
            res = await r.json()
            await ctx.reply(embed=discord.Embed().set_image(url=res["url"]))
        else:
            await ctx.reply(f"{ctx.author.mention} something not right? This is not us but the API")

    async def _paginate_results[I: Pin | Video](
        self,
        ctx: commands.Context[Parrot],
        *,
        fetch,
        search: str,
        embed_factory: Callable[[I], discord.Embed],
        error_message: str = "Couldn't reach the site. Try again later.",
    ) -> None:
        await ctx.typing()

        try:
            result = await fetch(search)
        except aiohttp.ClientError, TimeoutError:
            _log.exception("API request failed")
            await ctx.reply(error_message)
            return

        items = getattr(result, "pins", None) or getattr(result, "videos", None)

        if not items:
            escaped = discord.utils.escape_markdown(search)
            await ctx.reply(f"No results for `{escaped}`.")
            return

        embeds = [embed_factory(item) for item in items]
        view = PaginationView(author=ctx.author, items=embeds)
        await view.start(ctx)

    def _sex_embed(self, item: Pin) -> discord.Embed:
        embed = discord.Embed(title=item.title, url=item.url)
        embed.set_image(url=item.url)
        return embed

    def _pin_video_embed(self, video: Video) -> discord.Embed:
        embed = discord.Embed(title=video.title, url=video.url)
        embed.set_image(url=video.thumbnail)
        embed.set_footer(text=f"{video.uploader} · \N{THUMBS UP SIGN} {video.rating} · pin.porn")

        data = embed.to_dict()
        data["video"] = {
            "url": video.url,
            "height": 720,
            "width": 1280,
        }

        return discord.Embed.from_dict(data)

    @commands.group(name="sex", aliases=["sexdotcom", "sex.com"], invoke_without_command=True)
    @commands.is_nsfw()
    async def sexdotcom(self, ctx: commands.Context[Parrot]) -> None:
        """Mature Content. 18+ only please.

        This command has no cooldown.
        """
        await ctx.send_help(ctx.command)

    @sexdotcom.command(name="gif")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def _sex_gif(self, ctx: commands.Context[Parrot], *, search: str) -> None:
        """Mature Content. 18+ only please.

        This command has max concurrency of 1 per user.
        This command has a cooldown of 5 seconds per user.
        """
        await self._paginate_results(
            ctx,
            fetch=self._sexdotcomgif.fetch,
            search=search,
            embed_factory=self._sex_embed,
        )

    @sexdotcom.command(name="pics", aliases=["pic", "image", "images"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def _sex_pics(self, ctx: commands.Context[Parrot], *, search: str) -> None:
        """Mature Content. 18+ only please.

        This command has max concurrency of 1 per user.
        This command has a cooldown of 5 seconds per user.
        """
        await self._paginate_results(
            ctx,
            fetch=self._sexdotcompics.fetch,
            search=search,
            embed_factory=self._sex_embed,
        )

    @sexdotcom.command(name="video", aliases=["vid", "pin"])
    @commands.cooldown(1, 8, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def _pin_video(self, ctx: commands.Context[Parrot], *, search: str) -> None:
        """Random video clip from pin.porn. 18+ only please.

        This command has max concurrency of 1 per user.
        This command has a cooldown of 8 seconds per user.
        """
        await self._paginate_results(
            ctx,
            fetch=self._pinporn.search,
            search=search,
            embed_factory=self._pin_video_embed,
        )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(NSFW(bot))
