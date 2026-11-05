from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

import discord
import humanize
from discord.ext import commands

from core.utils import NoticeLayout, truncate

from .arch import ArchScraper, ArchScraperError, AURPackage, NotFoundError, Package

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

MAX_CHOICES = 25
MAX_EMBED_TITLE_LENGTH = 256
MAX_EMBED_FIELD_LENGTH = 1024
MAX_SELECT_TEXT_LENGTH = 100
MAX_WIKI_SUMMARY_LENGTH = 1000
MAX_NEWS_SUMMARY_LENGTH = 200
ARCH_NEWS_URL = "https://archlinux.org/news/"


def _join(items: tuple[str, ...], limit: int = MAX_EMBED_FIELD_LENGTH) -> str:
    return truncate(", ".join(items), limit) if items else "None"


def _package_option(package: Package) -> discord.SelectOption:
    return discord.SelectOption(
        label=truncate(f"{package.repo}/{package.name} {package.version}", MAX_SELECT_TEXT_LENGTH),
        description=truncate(package.description, MAX_SELECT_TEXT_LENGTH) or None,
    )


def _aur_option(package: AURPackage) -> discord.SelectOption:
    details = f"{package.votes} votes \N{MIDDLE DOT} {package.description}"
    return discord.SelectOption(
        label=truncate(f"{package.name} {package.version}", MAX_SELECT_TEXT_LENGTH),
        description=truncate(details, MAX_SELECT_TEXT_LENGTH),
    )


def package_embed(package: Package, *, color: discord.Colour) -> discord.Embed:
    embed = discord.Embed(
        title=truncate(f"{package.repo}/{package.name} {package.version}", MAX_EMBED_TITLE_LENGTH),
        url=package.url,
        description=package.description or "No description.",
        color=color,
    )
    embed.add_field(name="Architecture", value=package.arch)
    embed.add_field(name="Upstream", value=package.upstream_url or "None")
    embed.add_field(name="Licenses", value=_join(package.licenses))
    embed.add_field(
        name="Size",
        value=(
            f"{humanize.naturalsize(package.compressed_size, binary=True)} download, "
            f"{humanize.naturalsize(package.installed_size, binary=True)} installed"
        ),
    )
    if package.last_update:
        embed.add_field(name="Last updated", value=discord.utils.format_dt(package.last_update, "R"))
    if package.flagged_at:
        embed.add_field(name="\N{WARNING SIGN} Flagged out of date", value=discord.utils.format_dt(package.flagged_at, "R"))

    embed.add_field(name="Depends", value=_join(package.depends), inline=False)
    if package.optdepends:
        embed.add_field(name="Optional", value=_join(package.optdepends), inline=False)

    embed.add_field(name="Install", value=f"`sudo pacman -S {package.name}`", inline=False)
    if package.packager:
        embed.set_footer(text=f"Packager: {package.packager}")

    return embed


def aur_embed(package: AURPackage, *, color: discord.Colour) -> discord.Embed:
    embed = discord.Embed(
        title=truncate(f"aur/{package.name} {package.version}", MAX_EMBED_TITLE_LENGTH),
        url=package.url,
        description=package.description or "No description.",
        color=color,
    )
    embed.add_field(name="Votes", value=str(package.votes))
    embed.add_field(name="Popularity", value=f"{package.popularity:.2f}")
    embed.add_field(name="Maintainer", value=package.maintainer or "Orphaned")
    embed.add_field(name="Upstream", value=package.upstream_url or "None")
    if package.last_modified:
        embed.add_field(name="Last modified", value=discord.utils.format_dt(package.last_modified, "R"))
    if package.out_of_date:
        embed.add_field(name="\N{WARNING SIGN} Flagged out of date", value=discord.utils.format_dt(package.out_of_date, "R"))

    if package.depends:
        embed.add_field(name="Depends", value=_join(package.depends), inline=False)
    if package.make_depends:
        embed.add_field(name="Make depends", value=_join(package.make_depends), inline=False)

    embed.add_field(name="Clone", value=f"`git clone {package.git_url}`", inline=False)
    return embed


async def _reply_unavailable(ctx: commands.Context[Bot]) -> discord.Message:
    notice = NoticeLayout.error("Arch Linux's servers did not respond. Please try again shortly.", title="Lookup failed")
    return await ctx.reply(view=notice)


class Arch(commands.Cog):
    """Arch Linux lookups: official packages, the AUR, the Arch Wiki and the news feed."""

    bot: Bot

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.arch_scraper: ArchScraper = ArchScraper(self.bot.http_session)

    @commands.group(invoke_without_command=True, aliases=["archlinux"])
    async def arch(self, ctx: commands.Context[Bot]) -> None:
        """Look things up on Arch Linux: packages, the AUR, the wiki and the news."""
        await ctx.send_help(ctx.command)

    @arch.command(name="package", aliases=["pkg"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def arch_package(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The package name or search terms."),
    ) -> discord.Message:
        """Look up a package in the official repositories."""
        try:
            async with ctx.typing():
                results = await self.arch_scraper.search_packages(query, limit=MAX_CHOICES)
        except ArchScraperError:
            _log.warning("Arch package search failed for %r", query, exc_info=True)
            return await _reply_unavailable(ctx)

        if not results:
            return await ctx.reply(f"No packages found for `{query}`.")

        if results[0].name.lower() == query.lower():
            package = results[0]
        else:
            package = await self.bot.disambiguate(ctx, matches=results, entry=_package_option)

        return await ctx.reply(embed=package_embed(package, color=ctx.author.color))

    @arch.command(name="aur")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def arch_aur(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The package name or search terms."),
    ) -> discord.Message:
        """Look up a package in the Arch User Repository."""
        try:
            async with ctx.typing():
                results = await self.arch_scraper.search_aur(query, limit=MAX_CHOICES)
        except ArchScraperError:
            _log.warning("AUR search failed for %r", query, exc_info=True)
            return await _reply_unavailable(ctx)

        if not results:
            return await ctx.reply(f"No AUR packages found for `{query}`.")

        if results[0].name.lower() == query.lower():
            package = results[0]
        else:
            package = await self.bot.disambiguate(ctx, matches=results, entry=_aur_option)

        # Search results leave out dependencies, so ask for the full record and fall back to what we have.
        async with ctx.typing():
            with contextlib.suppress(ArchScraperError):
                package = await self.arch_scraper.get_aur_package(package.name)

        return await ctx.reply(embed=aur_embed(package, color=ctx.author.color))

    @arch.command(name="wiki", aliases=["w"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def arch_wiki(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look up on the Arch Wiki."),
    ) -> discord.Message:
        """Search the Arch Wiki and show the best match."""
        try:
            async with ctx.typing():
                results = await self.arch_scraper.search_wiki(query, limit=5)
                top = results[0] if results else None
                summary = ""
                if top is not None:
                    with contextlib.suppress(NotFoundError):
                        summary = (await self.arch_scraper.get_wiki_summary(top.title)).summary
        except ArchScraperError:
            _log.warning("Arch Wiki search failed for %r", query, exc_info=True)
            return await _reply_unavailable(ctx)

        if top is None:
            return await ctx.reply(f"No wiki pages found for `{query}`.")

        embed = discord.Embed(
            title=truncate(top.title, MAX_EMBED_TITLE_LENGTH),
            url=top.url,
            description=truncate(summary or top.snippet, MAX_WIKI_SUMMARY_LENGTH),
            color=ctx.author.color,
        )
        if len(results) > 1:
            see_also = "\n".join(f"[{result.title}]({result.url})" for result in results[1:])
            embed.add_field(name="See also", value=truncate(see_also, MAX_EMBED_FIELD_LENGTH), inline=False)

        return await ctx.reply(embed=embed)

    @arch.command(name="news")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def arch_news(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show the latest news from archlinux.org."""
        try:
            async with ctx.typing():
                items = await self.arch_scraper.get_news(limit=5)
        except ArchScraperError:
            _log.warning("Arch news fetch failed", exc_info=True)
            return await _reply_unavailable(ctx)

        if not items:
            return await ctx.reply("No news items found.")

        embed = discord.Embed(title="Arch Linux News", url=ARCH_NEWS_URL, color=ctx.author.color)
        for item in items:
            published = f"{discord.utils.format_dt(item.published, 'D')} \N{MIDDLE DOT} " if item.published else ""
            summary = truncate(item.summary, MAX_NEWS_SUMMARY_LENGTH)
            embed.add_field(
                name=truncate(item.title, MAX_EMBED_TITLE_LENGTH),
                value=truncate(f"{published}[Read more]({item.link})\n{summary}", MAX_EMBED_FIELD_LENGTH),
                inline=False,
            )

        return await ctx.reply(embed=embed)
