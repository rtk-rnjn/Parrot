"""The `kontests` command: upcoming and ongoing contests on every supported site, one tab each."""

from __future__ import annotations

import asyncio
import datetime
import functools
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core.utils import PaginationLayout
from core.utils.formats import format_duration

from ._kontests import PLATFORMS, Contest, Platform

if TYPE_CHECKING:
    from core import Bot

log = logging.getLogger(__name__)

CACHE_TTL = datetime.timedelta(minutes=15)
ERROR_TTL = datetime.timedelta(minutes=1)  # retry a site that failed soon, without hammering it
VIEW_TIMEOUT = 600
PER_PAGE = 4  # 4 sections with link buttons keep the message under Discord's 40-component limit


@dataclass(frozen=True, slots=True)
class Snapshot:
    """One site's listing at one moment, ongoing contests first."""

    platform: Platform
    contests: list[Contest]
    fetched_at: datetime.datetime
    error: str | None = None

    @property
    def expired(self) -> bool:
        ttl = ERROR_TTL if self.error else CACHE_TTL
        return datetime.datetime.now(datetime.UTC) - self.fetched_at > ttl


def order(contests: list[Contest], now: datetime.datetime) -> list[Contest]:
    far = datetime.datetime.max.replace(tzinfo=datetime.UTC)
    live = [contest for contest in contests if contest.status(now) != "ended"]
    return sorted(live, key=lambda contest: (contest.status(now) != "ongoing", contest.start or far))


def describe(contest: Contest, now: datetime.datetime) -> str:
    name = discord.utils.escape_markdown(contest.name)
    url = contest.url.replace("(", "%28").replace(")", "%29")
    lines = [f"**[{name}]({url})**"]
    meta = " \N{MIDDLE DOT} ".join(part for part in (contest.kind, contest.rated, contest.host) if part)
    if meta:
        lines.append(f"-# {meta}")

    if contest.start is None:
        lines.append("Start time to be announced")
    elif contest.status(now) == "ongoing":
        ends = f", ends {discord.utils.format_dt(contest.end, 'R')}" if contest.end is not None else ""
        lines.append(f"**Ongoing** since {discord.utils.format_dt(contest.start, 'R')}{ends}")
    else:
        when = f"Starts {discord.utils.format_dt(contest.start, 'R')} ({discord.utils.format_dt(contest.start, 'f')})"
        if contest.duration is not None:
            when += f", lasts {format_duration(contest.duration.total_seconds())}"
        lines.append(when)

    if contest.description:
        lines.append(contest.description)
    return "\n".join(lines)


class KontestsView(PaginationLayout):
    """The house paginator with a row of platform tabs above the page."""

    def __init__(self, author: discord.User | discord.Member, snapshots: list[Snapshot]) -> None:
        self.snapshots = snapshots
        self.active = 0
        now = datetime.datetime.now(datetime.UTC)
        self.pages = [self.pages_for(snapshot, now) for snapshot in snapshots]
        super().__init__(
            author,
            header=discord.ui.TextDisplay(""),  # replaced on every render; the base class wants one up front
            footer=discord.ui.TextDisplay(""),
            items=self.pages[0],
            hide_skip_button=True,
            timeout=VIEW_TIMEOUT,
        )

    @staticmethod
    def pages_for(snapshot: Snapshot, now: datetime.datetime) -> list[list[discord.ui.Item]]:
        if snapshot.error:
            return [[discord.ui.TextDisplay(f"Bot could not read {snapshot.platform.name}'s contest list. {snapshot.error}")]]
        if not snapshot.contests:
            return [[discord.ui.TextDisplay(f"No upcoming contests on {snapshot.platform.name} right now.")]]
        return [
            [
                discord.ui.Section(discord.ui.TextDisplay(describe(contest, now)), accessory=discord.ui.Button(label="Open", url=contest.url))
                for contest in chunk
            ]
            for chunk in discord.utils.as_chunks(snapshot.contests, PER_PAGE)
        ]

    def tabs(self) -> discord.ui.ActionRow:
        row = discord.ui.ActionRow()
        for index, snapshot in enumerate(self.snapshots):
            active = index == self.active
            button = discord.ui.Button(
                label=snapshot.platform.name,
                style=discord.ButtonStyle.primary if active else discord.ButtonStyle.secondary,
                disabled=active,
            )
            button.callback = functools.partial(self.select_tab, index)
            row.add_item(button)
        return row

    def _update_container(self) -> None:
        snapshot = self.snapshots[self.active]
        now = datetime.datetime.now(datetime.UTC)
        ongoing = sum(contest.status(now) == "ongoing" for contest in snapshot.contests)
        upcoming = len(snapshot.contests) - ongoing
        summary = " \N{MIDDLE DOT} ".join(part for part in (f"{ongoing} ongoing" if ongoing else "", f"{upcoming} upcoming") if part)

        self.container.clear_items()
        self.container.accent_colour = discord.Colour(snapshot.platform.colour)
        self.container.add_item(discord.ui.TextDisplay(f"## {snapshot.platform.name} contests\n-# {summary}"))
        self.container.add_item(self.tabs())
        self.container.add_item(discord.ui.Separator())
        for item in self.items[self.current_index]:
            self.container.add_item(item)
        self.container.add_item(discord.ui.Separator())
        fetched = discord.utils.format_dt(snapshot.fetched_at, "R")
        self.container.add_item(
            discord.ui.TextDisplay(f"-# Fetched {fetched} \N{MIDDLE DOT} [All {snapshot.platform.name} contests]({snapshot.platform.url})")
        )

    async def select_tab(self, index: int, interaction: discord.Interaction[Bot]) -> None:
        self.active = index
        self.items = self.pages[index]
        self.current_index = 0
        await self.update_page(interaction)


class Kontests(commands.Cog, name="Contests"):
    """Upcoming competitive-programming contests, fetched from each site and cached for a few minutes."""

    help_category = "Developer"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._cache: dict[str, Snapshot] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def snapshot(self, platform: Platform) -> Snapshot:
        cached = self._cache.get(platform.key)
        if cached is not None and not cached.expired:
            return cached
        async with self._locks[platform.key]:
            cached = self._cache.get(platform.key)
            if cached is not None and not cached.expired:  # another caller refreshed it first
                return cached
            now = datetime.datetime.now(datetime.UTC)
            try:
                contests = await platform.fetch(self.bot.http_session)
            except Exception:  # one site changing its markup must not take the others down
                log.exception("%s: fetching contests failed", platform.key)
                fresh = Snapshot(platform, [], now, error="The site did not answer as expected; try again in a minute.")
            else:
                fresh = Snapshot(platform, order(contests, now), now)
            self._cache[platform.key] = fresh
            return fresh

    @commands.command(name="kontests", aliases=["contests"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def kontests(self, ctx: commands.Context[Bot]) -> None:
        """Upcoming and ongoing contests on Codeforces, AtCoder, HackerRank, HackerEarth and CS Academy, one tab each."""
        async with ctx.typing():
            snapshots = await asyncio.gather(*(self.snapshot(platform) for platform in PLATFORMS))
        view = KontestsView(ctx.author, list(snapshots))
        await view.start(ctx)

    @commands.command(name="kontest-reload", hidden=True)
    @commands.is_owner()
    async def kontest_reload(self, ctx: commands.Context[Bot]) -> None:
        """Forget the cached contest listings so the next `kontests` fetches every site again."""
        self._cache.clear()
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
