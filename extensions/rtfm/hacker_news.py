from __future__ import annotations

import asyncio
import contextlib
import datetime
import html
import logging
import re
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, Literal, NamedTuple
from urllib.parse import urlparse

import aiohttp
import discord
from discord.ext import commands

from core.utils import BaseLayoutView, NoticeLayout, format_count, truncate
from core.utils.date import HumanDate
from core.utils.paginator import PaginationLayout

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

type Item = dict[str, Any]

API_URL = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_URL = "https://hn.algolia.com/api/v1"
SITE_URL = "https://news.ycombinator.com"

HN_COLOUR = discord.Colour(0xFF6600)
NO_MENTIONS = discord.AllowedMentions.none()


class Feed(NamedTuple):
    endpoint: str
    title: str
    emoji: str
    description: str


FEEDS: dict[str, Feed] = {
    "top": Feed("topstories", "Top stories", "\N{FIRE}", "What's on the front page right now"),
    "new": Feed("newstories", "New", "\N{SQUARED NEW}", "The newest submissions"),
    "best": Feed("beststories", "Best", "\N{TROPHY}", "Highest-voted recent stories"),
    "ask": Feed("askstories", "Ask HN", "\N{BLACK QUESTION MARK ORNAMENT}", "Questions for the community"),
    "show": Feed("showstories", "Show HN", "\N{EYES}", "Projects people have made"),
    "jobs": Feed("jobstories", "Jobs", "\N{BRIEFCASE}", "Jobs from YC companies"),
}

PAGE_SIZE = 5
MAX_STORIES = 30
COMMENT_PREVIEW = 3
VIEW_TIMEOUT = 300
FEED_TTL = 300
ITEM_TTL = 300
USER_TTL = 600
MAX_CACHE_ENTRIES = 2000
MAX_BUTTON_URL = 512

USERNAME_RE = re.compile(r"[A-Za-z0-9_-]{2,15}")
ITEM_ID_RE = re.compile(r"[?&]id=(\d+)")


def item_url(item_id: int) -> str:
    return f"{SITE_URL}/item?id={item_id}"


def user_url(username: str) -> str:
    return f"{SITE_URL}/user?id={username}"


def parse_item_id(argument: str) -> int:
    """Accept a bare item ID or a news.ycombinator.com item link."""
    argument = argument.strip().strip("<>")
    if argument.isdecimal():
        return int(argument)
    if "ycombinator.com" in argument and (match := ITEM_ID_RE.search(argument)):
        return int(match[1])
    msg = "Give me an item ID or a `news.ycombinator.com/item?id=...` link."
    raise commands.BadArgument(msg)


def _escape(text: str) -> str:
    """Escape markdown and mentions in text that comes from Hacker News."""
    text = re.sub(r"([\\*_~|`\[\]])", r"\\\1", text)
    return discord.utils.escape_mentions(text)


def _clean(text: str, limit: int) -> str:
    return _escape(truncate(html.unescape(text), limit))


def _safe_url(url: str) -> str:
    """Make a URL safe to put inside ``[label](url)``."""
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def _is_http(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def _timestamp(item: Item, style: Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"] = "R") -> str:
    moment = datetime.datetime.fromtimestamp(item["time"], datetime.UTC)
    return discord.utils.format_dt(moment, style=style)


_PRE_RE = re.compile(r"<pre>\s*<code>(.*?)</code>\s*</pre>", re.DOTALL | re.IGNORECASE)
_ANCHOR_RE = re.compile(r"<a\s+[^>]*?href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
_ITALIC_RE = re.compile(r"<i>(.*?)</i>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def html_to_markdown(text: str) -> str:
    """Convert the small HTML subset Hacker News uses into Discord markdown."""

    def anchor(match: re.Match[str]) -> str:
        href = html.unescape(match[1])
        label = html.unescape(_TAG_RE.sub("", match[2]))
        if label.startswith(("http://", "https://")) or not label.strip():
            return href
        return f"[{label}]({_safe_url(href)})"

    text = _PRE_RE.sub(lambda m: f"\n```\n{html.unescape(m[1]).strip()}\n```\n", text)
    text = _ANCHOR_RE.sub(anchor, text)
    text = _ITALIC_RE.sub(r"*\1*", text)
    text = re.sub(r"<p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = html.unescape(_TAG_RE.sub("", text))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return discord.utils.escape_mentions(text)


def _meta(item: Item) -> str:
    """The small grey line under an item: score, comments, author and age."""
    parts: list[str] = []
    if "score" in item:
        parts.append(f"\N{BLACK UP-POINTING SMALL TRIANGLE} {format_count(item['score'])}")
    if "descendants" in item:
        parts.append(f"\N{SPEECH BALLOON} {format_count(item['descendants'])}")
    if item.get("by"):
        parts.append(f"by {_escape(item['by'])}")
    parts.append(_timestamp(item))
    return " \N{MIDDLE DOT} ".join(parts)


def story_text(rank: int, item: Item) -> str:
    title = _clean(item.get("title", "(untitled)"), 200)
    url = item.get("url")
    link = url if url and _is_http(url) else item_url(item["id"])

    heading = f"**{rank}. [{title}]({_safe_url(link)})**"
    if url and (host := urlparse(url).hostname):
        heading += f" ({_escape(host.removeprefix('www.'))})"
    return f"{heading}\n-# {_meta(item)}"


async def _user_tzinfo(interaction: discord.Interaction[Bot]) -> datetime.tzinfo:
    reminder = getattr(interaction.client, "reminder", None)
    if reminder is None:
        return datetime.UTC
    return await reminder.get_tzinfo(interaction.user.id)


async def _network_error(interaction: discord.Interaction[Bot]) -> None:
    """Tell the user the API is unreachable. Only call this after the interaction was deferred."""
    _log.warning("Hacker News API request failed", exc_info=True)
    await interaction.followup.send(
        view=NoticeLayout.error("Couldn't reach Hacker News right now. Try again in a moment."),
        ephemeral=True,
    )


class HackerNewsClient:
    """A small cached client for the Hacker News Firebase API and the Algolia search API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session
        self._cache: dict[str, tuple[float, Any]] = {}
        self._semaphore = asyncio.Semaphore(10)

    async def _cached(self, key: str, ttl: float, url: str, params: dict[str, str] | None = None) -> Any:
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit is not None and hit[0] > now:
            return hit[1]

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)

        if len(self._cache) >= MAX_CACHE_ENTRIES:
            self._cache = {k: v for k, v in self._cache.items() if v[0] > now}
            if len(self._cache) >= MAX_CACHE_ENTRIES:
                self._cache.clear()
        self._cache[key] = (now + ttl, data)
        return data

    async def feed(self, name: str) -> list[int]:
        url = f"{API_URL}/{FEEDS[name].endpoint}.json"
        return await self._cached(f"feed:{name}", FEED_TTL, url) or []

    async def item(self, item_id: int) -> Item | None:
        return await self._cached(f"item:{item_id}", ITEM_TTL, f"{API_URL}/item/{item_id}.json")

    async def user(self, username: str) -> Item | None:
        return await self._cached(f"user:{username}", USER_TTL, f"{API_URL}/user/{username}.json")

    async def items(self, ids: list[int]) -> list[Item]:
        """Fetch several items concurrently, in order, dropping missing, deleted and dead ones."""

        async def fetch(item_id: int) -> Item | None:
            async with self._semaphore:
                return await self.item(item_id)

        results = await asyncio.gather(*(fetch(item_id) for item_id in ids))
        return [item for item in results if item and not item.get("deleted") and not item.get("dead")]

    async def stories(self, feed: str) -> list[Item]:
        return await self.items((await self.feed(feed))[:MAX_STORIES])

    async def search(self, query: str, *, since: datetime.datetime | None = None) -> list[Item]:
        """Search stories through Algolia, returning items shaped like the Firebase ones."""
        params = {"query": query, "tags": "story", "hitsPerPage": str(MAX_STORIES)}
        if since is not None:
            params["numericFilters"] = f"created_at_i>{int(since.timestamp())}"

        key = f"search:{query.casefold()}:{params.get('numericFilters', '')}"
        data = await self._cached(key, ITEM_TTL, f"{ALGOLIA_URL}/search", params)

        results: list[Item] = []
        for hit in data.get("hits", []):
            if not hit.get("title") or not hit.get("objectID"):
                continue
            item: Item = {
                "id": int(hit["objectID"]),
                "type": "story",
                "title": hit["title"],
                "score": hit.get("points") or 0,
                "descendants": hit.get("num_comments") or 0,
                "time": hit["created_at_i"],
            }
            if hit.get("url"):
                item["url"] = hit["url"]
            if hit.get("author"):
                item["by"] = hit["author"]
            results.append(item)
        return results


class SearchModal(discord.ui.Modal, title="Search Hacker News"):
    query = discord.ui.TextInput(label="Search for", placeholder="e.g. rust async runtime", max_length=100)
    since = discord.ui.TextInput(
        label="Posted since (optional)",
        placeholder="e.g. 1 January 2024, 2024-06-01 or May '25",
        required=False,
        max_length=40,
    )

    def __init__(self, hub: HackerNewsHub) -> None:
        super().__init__()
        self.hub = hub

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        await self.hub.search(interaction, self.query.value, self.since.value)


class ItemModal(discord.ui.Modal, title="Open an item"):
    target = discord.ui.TextInput(
        label="Item ID or link",
        placeholder="8863 or news.ycombinator.com/item?id=8863",
        max_length=200,
    )

    def __init__(self, hub: HackerNewsHub) -> None:
        super().__init__()
        self.hub = hub

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            item_id = parse_item_id(self.target.value)
        except commands.BadArgument as error:
            await interaction.response.send_message(view=NoticeLayout.error(str(error)), ephemeral=True)
            return
        await self.hub.open_item(interaction, item_id)


class UserModal(discord.ui.Modal, title="Look up a user"):
    username = discord.ui.TextInput(
        label="Username (case-sensitive)",
        placeholder="e.g. pg",
        min_length=2,
        max_length=15,
    )

    def __init__(self, hub: HackerNewsHub) -> None:
        super().__init__()
        self.hub = hub

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        name = self.username.value.strip()
        if not USERNAME_RE.fullmatch(name):
            await interaction.response.send_message(view=NoticeLayout.error("That isn't a valid Hacker News username."), ephemeral=True)
            return
        await self.hub.lookup_user(interaction, name)


class ItemView(BaseLayoutView):
    """A single story, job, poll or comment."""

    def __init__(self, author: discord.Member | discord.User, client: HackerNewsClient, item: Item) -> None:
        super().__init__(author, timeout=VIEW_TIMEOUT)
        self.client = client
        self.item = item

        kind = item.get("type", "story")
        discussion = item_url(item["id"])
        url = item.get("url")

        if kind == "comment":
            heading = f"### Comment by {_escape(item.get('by', 'unknown'))}"
        else:
            title = _clean(item.get("title", "(untitled)"), 250)
            link = url if url and _is_http(url) else discussion
            heading = f"### [{title}]({_safe_url(link)})"

        container = discord.ui.Container(discord.ui.TextDisplay(f"{heading}\n-# {_meta(item)}"), accent_colour=HN_COLOUR)

        if text := item.get("text"):
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.TextDisplay(truncate(html_to_markdown(text), 1800)))

        buttons: list[discord.ui.Button] = []
        if url and _is_http(url) and len(url) <= MAX_BUTTON_URL:
            buttons.append(discord.ui.Button(label="Article", url=url))
        buttons.append(discord.ui.Button(label="View on HN" if kind == "comment" else "Discussion", url=discussion))
        if kind == "comment" and item.get("parent"):
            buttons.append(discord.ui.Button(label="Parent", url=item_url(item["parent"])))
        if item.get("kids"):
            replies = discord.ui.Button(
                label="Replies" if kind == "comment" else "Top comments",
                emoji="\N{SPEECH BALLOON}",
                style=discord.ButtonStyle.secondary,
            )
            replies.callback = self.show_comments
            buttons.append(replies)

        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.ActionRow(*buttons))
        self.add_item(container)

    async def show_comments(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            comments = await self.client.items(self.item.get("kids", [])[:COMMENT_PREVIEW])
        except aiohttp.ClientError, TimeoutError:
            await _network_error(interaction)
            return

        if not comments:
            await interaction.followup.send(view=NoticeLayout.info("There's nothing here yet."), ephemeral=True)
            return

        blocks = [
            f"**{_escape(comment.get('by', 'unknown'))}** \N{MIDDLE DOT} {_timestamp(comment)}\n{truncate(html_to_markdown(comment.get('text', '')), 600)}"
            for comment in comments
        ]
        await interaction.followup.send(
            view=NoticeLayout.info("\n\n".join(blocks), title="Replies" if self.item.get("type") == "comment" else "Top comments"),
            ephemeral=True,
            allowed_mentions=NO_MENTIONS,
        )


class HackerNewsHub(PaginationLayout):
    """The whole Hacker News experience in one message.

    A feed select, a paged story list, and buttons that open modals for search, items and users.
    Story pages use the shared paginator; this class only swaps the pages when the content changes.
    """

    def __init__(self, author: discord.Member | discord.User, client: HackerNewsClient) -> None:
        super().__init__(
            author,
            header=discord.ui.TextDisplay("### Hacker News"),
            footer=discord.ui.TextDisplay("-# Data from the Hacker News API \N{MIDDLE DOT} cached for 5 minutes"),
            items=[[discord.ui.TextDisplay("Loading\N{HORIZONTAL ELLIPSIS}")]],
            timeout=VIEW_TIMEOUT,
            hide_quit_button=True,
            hide_skip_button=True,
        )
        self.client = client

        self.feed_select = discord.ui.Select(
            placeholder="Browse a feed\N{HORIZONTAL ELLIPSIS}",
            options=[
                discord.SelectOption(label=feed.title, value=key, description=feed.description, emoji=feed.emoji) for key, feed in FEEDS.items()
            ],
        )
        self.feed_select.callback = self.on_feed_select

        search = discord.ui.Button(label="Search", emoji="\N{LEFT-POINTING MAGNIFYING GLASS}", style=discord.ButtonStyle.primary)
        search.callback = self.on_search_button
        open_item = discord.ui.Button(label="Open item", emoji="\N{LINK SYMBOL}", style=discord.ButtonStyle.secondary)
        open_item.callback = self.on_item_button
        lookup = discord.ui.Button(label="User", emoji="\N{BUST IN SILHOUETTE}", style=discord.ButtonStyle.secondary)
        lookup.callback = self.on_user_button

        self.add_item(discord.ui.ActionRow(self.feed_select))
        self.add_item(discord.ui.ActionRow(search, open_item, lookup))

    def _details_button(self, item_id: int) -> discord.ui.Button:
        button = discord.ui.Button(label="Details", style=discord.ButtonStyle.secondary)

        async def callback(interaction: discord.Interaction[Bot]) -> None:
            await self.open_item(interaction, item_id)

        button.callback = callback
        return button

    def _build_pages(self, stories: list[Item], empty: str) -> list[list[discord.ui.Item]]:
        if not stories:
            return [[discord.ui.TextDisplay(empty)]]

        pages: list[list[discord.ui.Item]] = []
        for start in range(0, len(stories), PAGE_SIZE):
            page: list[discord.ui.Item] = []
            for rank, story in enumerate(stories[start : start + PAGE_SIZE], start=start + 1):
                if page:
                    page.append(discord.ui.Separator())
                page.append(
                    discord.ui.Section(
                        discord.ui.TextDisplay(story_text(rank, story)),
                        accessory=self._details_button(story["id"]),
                    )
                )
            pages.append(page)
        return pages

    def set_stories(self, header: str, stories: list[Item], feed: str | None, *, empty: str = "Nothing to show.") -> None:
        """Replace what the hub shows. The caller is responsible for editing the message afterwards."""
        assert isinstance(self.header, discord.ui.TextDisplay)

        self.header.content = header
        self.items = self._build_pages(stories, empty)
        self.current_index = 0

        self._update_container()
        self._update_pagination_buttons()
        if self.skip_button is not None:
            self.skip_button.disabled = len(self.items) <= 1

        for option in self.feed_select.options:
            option.default = option.value == feed

    async def on_feed_select(self, interaction: discord.Interaction[Bot]) -> None:
        feed = self.feed_select.values[0]
        await interaction.response.defer()

        try:
            stories = await self.client.stories(feed)
        except aiohttp.ClientError, TimeoutError:
            await _network_error(interaction)
            return

        self.set_stories(f"### Hacker News \N{MIDDLE DOT} {FEEDS[feed].title}", stories, feed)
        await interaction.edit_original_response(view=self)

    async def on_search_button(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.send_modal(SearchModal(self))

    async def on_item_button(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.send_modal(ItemModal(self))

    async def on_user_button(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.send_modal(UserModal(self))

    async def search(self, interaction: discord.Interaction[Bot], query: str, since_text: str) -> None:
        query = query.strip()

        since: datetime.datetime | None = None
        if since_text.strip():
            try:
                since = await self._parse_since(interaction, since_text)
            except commands.BadArgument as error:
                await interaction.response.send_message(view=NoticeLayout.error(str(error)), ephemeral=True)
                return

        await interaction.response.defer()
        try:
            stories = await self.client.search(query, since=since)
        except aiohttp.ClientError, TimeoutError:
            await _network_error(interaction)
            return

        shown = _escape(truncate(query, 80))
        subtitle = f"Results for **{shown}**"
        if since is not None:
            subtitle += f" since {discord.utils.format_dt(since, style='D')}"

        self.set_stories(
            f"### Hacker News \N{MIDDLE DOT} Search\n-# {subtitle}",
            stories,
            None,
            empty=f"No stories matched **{shown}**.",
        )
        await interaction.edit_original_response(view=self)

    @staticmethod
    async def _parse_since(interaction: discord.Interaction[Bot], text: str) -> datetime.datetime:
        parsed = HumanDate(text, now=interaction.created_at, tzinfo=await _user_tzinfo(interaction), prefer="past")
        if parsed.remaining:
            leftover = truncate(parsed.remaining.replace("`", "'"), 40)
            msg = f"I didn't understand `{leftover}` after the date."
            raise commands.BadArgument(msg)
        if parsed.datetime > interaction.created_at:
            msg = "That date is in the future."
            raise commands.BadArgument(msg)
        return parsed.datetime

    async def open_item(self, interaction: discord.Interaction[Bot], item_id: int) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            item = await self.client.item(item_id)
        except aiohttp.ClientError, TimeoutError:
            await _network_error(interaction)
            return

        if item is None or item.get("deleted") or item.get("dead"):
            await interaction.followup.send(view=NoticeLayout.warning("I couldn't find that item, or it was deleted."), ephemeral=True)
            return

        view = ItemView(interaction.user, self.client, item)
        view.message = await interaction.followup.send(view=view, ephemeral=True, allowed_mentions=NO_MENTIONS, wait=True)

    async def lookup_user(self, interaction: discord.Interaction[Bot], username: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            user = await self.client.user(username)
        except aiohttp.ClientError, TimeoutError:
            await _network_error(interaction)
            return

        if user is None:
            await interaction.followup.send(
                view=NoticeLayout.warning("I couldn't find that user. Usernames are case-sensitive."),
                ephemeral=True,
            )
            return

        created = datetime.datetime.fromtimestamp(user["created"], datetime.UTC)
        lines = [
            f"**Karma:** {format_count(user.get('karma', 0))}",
            f"**Joined:** {discord.utils.format_dt(created, style='D')} ({discord.utils.format_dt(created, style='R')})",
            f"**Posts and comments:** {format_count(len(user.get('submitted', [])))}",
        ]
        if about := user.get("about"):
            lines.append(f"\n{truncate(html_to_markdown(about), 1000)}")
        lines.append(f"\n[View profile]({user_url(user['id'])})")

        await interaction.followup.send(
            view=NoticeLayout.info("\n".join(lines), title=_escape(user["id"])),
            ephemeral=True,
            allowed_mentions=NO_MENTIONS,
        )


class HackerNews(commands.Cog):
    """Browse Hacker News with buttons, selects and modals."""

    help_emoji = "\N{NEWSPAPER}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.client: HackerNewsClient
        _log.debug("Cog loaded: %s", self.__class__.__name__)

        self._session = self.bot.http_session

    async def cog_load(self) -> None:
        self.client = HackerNewsClient(self._session)

    async def cog_unload(self) -> None:
        await self._session.close()

    @contextlib.asynccontextmanager
    async def _guard(self, ctx: commands.Context[Bot]) -> AsyncGenerator[None]:
        """Turn network failures into a friendly reply; every other error still propagates."""
        try:
            yield
        except aiohttp.ClientError, TimeoutError:
            _log.warning("Hacker News API request failed", exc_info=True)
            await ctx.reply(view=NoticeLayout.error("Couldn't reach Hacker News right now. Try again in a moment."), allowed_mentions=NO_MENTIONS)

    @commands.command(name="hackernews", aliases=["hn"])
    async def hackernews(self, ctx: commands.Context[Bot]) -> None:
        """Browse Hacker News.

        Opens the top stories. Use the menu to switch feeds, and the buttons to search,
        open an item by ID or link, or look up a user.
        """
        async with ctx.typing(), self._guard(ctx):
            stories = await self.client.stories("top")

            hub = HackerNewsHub(ctx.author, self.client)
            hub.set_stories(f"### Hacker News \N{MIDDLE DOT} {FEEDS['top'].title}", stories, "top")
            await hub.start(ctx, allowed_mentions=NO_MENTIONS)


async def setup(bot: Bot) -> None:
    await bot.add_cog(HackerNews(bot))
