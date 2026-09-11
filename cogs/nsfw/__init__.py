from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import discord
from discord.ext import commands

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


class NSFW(commands.Cog):
    """Mature Content. 18+ only."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.url = "https://nekobot.xyz/api/image"

        _log.info("Cog loaded: %s", self.__class__.__name__)

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
        response = await self.bot.http_session.get(self.url, params={"type": type_str})
        if response.status != 200:
            msg = "Something went wrong with the API"
            raise commands.CommandError(msg)
        else:
            url = (await response.json())["message"]

        embed = discord.Embed().set_image(url=url)
        return embed

    async def command_endpoint_method(self, ctx: commands.Context[Parrot]) -> None:
        assert ctx.command is not None
        await ctx.typing()
        embed = await self.get_embed(ctx.command.qualified_name)
        await ctx.reply(embed=embed)

    def command_loader(self) -> None:
        for end_point in ENDPOINTS:
            command = commands.Command(
                NSFW.command_endpoint_method,
                enabled=True,
                name=end_point,
            )
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
        """Mature Content. 18+ only Please."""
        await ctx.typing()
        r = await self.bot.http_session.get(f"https://scathach.redsplit.org/v3/nsfw/{endpoint}/")
        if r.status == 200:
            res = await r.json()
            await ctx.reply(embed=discord.Embed().set_image(url=res["url"]))
        else:
            await ctx.reply(f"{ctx.author.mention} something not right? This is not us but the API")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(NSFW(bot))
