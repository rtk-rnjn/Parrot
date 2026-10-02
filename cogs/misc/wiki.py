from __future__ import annotations

import asyncio
import contextlib
import html
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import quote

import aiohttp
import discord
import wikipediaapi
from discord.ext import commands

from core.utils import BaseLayoutView

if TYPE_CHECKING:
    from core import Parrot

USER_AGENT = "Parrot/1.0.0 (https://github.com/rtk-rnjn/Parrot; ritik0ranjan@gmail.com)"
HTTP_OK = 200

ACCENT = discord.Colour.from_rgb(51, 102, 204)
TAG_RE = re.compile(r"<[^>]+>")
LANG_RE = re.compile(r"(?:^|\s)(?:--lang|-l)[\s=]+([a-z]{2,3}(?:-[a-z]+)*)(?=\s|$)", re.I)

NETWORK_ERRORS = (aiohttp.ClientError, asyncio.TimeoutError)


def clip(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def split_lang(text: str) -> tuple[str, str]:
    """Pull an optional `--lang xx` / `-l xx` flag out of the text. Returns (text, lang)."""
    m = LANG_RE.search(text)
    if not m:
        return text.strip(), "en"
    return LANG_RE.sub(" ", text, count=1).strip(), m.group(1).lower()


@dataclass
class PageData:
    title: str
    url: str
    summary: str
    sections: list[tuple[str, str]] = field(default_factory=list)  # (title, text)
    description: str | None = None
    thumbnail: str | None = None


class WikiClient:
    """Wraps wikipedia-api (sync, run in threads) and the MediaWiki HTTP API."""

    def __init__(self, user_agent: str = USER_AGENT):
        self.user_agent = user_agent
        self._wikis: dict[str, wikipediaapi.Wikipedia] = {}
        self.session: aiohttp.ClientSession | None = None

    def _wiki(self, lang: str) -> wikipediaapi.Wikipedia:
        if lang not in self._wikis:
            self._wikis[lang] = wikipediaapi.Wikipedia(user_agent=self.user_agent, language=lang)
        return self._wikis[lang]

    async def _api(self, lang: str, **params) -> dict:
        assert self.session
        params["format"] = "json"
        async with self.session.get(f"https://{lang}.wikipedia.org/w/api.php", params=params) as r:
            r.raise_for_status()
            return await r.json()

    def _fetch_page_sync(self, lang: str, title: str) -> PageData | None:
        page = self._wiki(lang).page(title)
        if not page.exists():
            return None
        return PageData(
            title=page.title,
            url=page.fullurl,
            summary=page.summary or "",
            sections=[(s.title, s.text) for s in page.sections],
        )

    async def get_page(self, lang: str, title: str) -> PageData | None:
        data = await asyncio.to_thread(self._fetch_page_sync, lang, title)
        if data is None:
            return None
        # Thumbnail + short description via the REST summary endpoint (best effort).
        try:
            assert self.session
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(data.title, safe='')}"
            async with self.session.get(url) as response:
                if response.status == HTTP_OK:
                    summary_response = await response.json()
                    data.description = summary_response.get("description")
                    data.thumbnail = (summary_response.get("thumbnail") or {}).get("source")
        except NETWORK_ERRORS:
            pass
        return data

    async def search(self, lang: str, query: str, limit: int = 5) -> list[tuple[str, str]]:
        response_data = await self._api(
            lang,
            action="query",
            list="search",
            srsearch=query,
            srlimit=limit,
            srprop="snippet",
        )
        out = []
        for item in response_data.get("query", {}).get("search", []):
            snippet = html.unescape(TAG_RE.sub("", item.get("snippet", "")))
            out.append((item["title"], snippet))
        return out

    async def random_title(self, lang: str) -> str | None:
        response_data = await self._api(lang, action="query", list="random", rnnamespace=0, rnlimit=1)
        rows = response_data.get("query", {}).get("random", [])
        return rows[0]["title"] if rows else None


class OwnedView(BaseLayoutView):
    """Base view: only the invoker can interact; disables itself on timeout."""

    def __init__(self, author_id: int, *, timeout: float = 180):
        super().__init__(author=discord.Object(author_id), timeout=timeout)  # pyright: ignore[reportArgumentType]
        self.author_id = author_id
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You can not interact with this view.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.walk_children():
            if hasattr(item, "disabled"):
                item.disabled = True  # type: ignore[attr-defined]
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)


class PageView(OwnedView):
    def __init__(
        self,
        client: WikiClient,
        author_id: int,
        page: PageData,
        lang: str,
        parent: OwnedView | None = None,
    ):
        super().__init__(author_id)
        self.client = client
        self.page = page
        self.lang = lang
        self.parent = parent
        self.section_index: int | None = None  # None = summary
        self.build()

    def build(self) -> None:
        self.clear_items()
        page = self.page

        header = f"# {page.title}"
        if page.description:
            header += f"\n-# {page.description}"
        if page.thumbnail:
            top: discord.ui.Item = discord.ui.Section(
                discord.ui.TextDisplay(header),
                accessory=discord.ui.Thumbnail(page.thumbnail, description=page.title),
            )
        else:
            top = discord.ui.TextDisplay(header)

        if self.section_index is None:
            body = clip(page.summary, 1500) or "*No summary available.*"
        else:
            title, text = page.sections[self.section_index]
            body = f"### {clip(title, 200)}\n" + (clip(text, 1500) if text.strip() else "*This section only contains subsections.*")

        children: list[discord.ui.Item] = [
            top,
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(body),
        ]

        # Section picker (Discord caps selects at 25 options)
        if page.sections:
            options = [
                discord.SelectOption(
                    label="Summary",
                    value="summary",
                    emoji="\N{OPEN BOOK}",
                    default=self.section_index is None,
                )
            ]
            for i, (title, _) in enumerate(page.sections[:24]):
                options.append(
                    discord.SelectOption(
                        label=clip(title, 100) or "Untitled",
                        value=str(i),
                        default=self.section_index == i,
                    )
                )
            select = discord.ui.Select(placeholder="Jump to a section\N{HORIZONTAL ELLIPSIS}", options=options)
            select.callback = self.on_select
            children += [
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(select),
            ]

        # Buttons
        buttons: list[discord.ui.Button] = []
        if self.parent is not None:
            back = discord.ui.Button(label="Back", emoji="\N{BLACK LEFT-POINTING TRIANGLE}", style=discord.ButtonStyle.secondary)
            back.callback = self.on_back
            buttons.append(back)
        buttons.append(discord.ui.Button(label="Read on Wikipedia", url=page.url))
        children.append(discord.ui.ActionRow(*buttons))

        self.add_item(discord.ui.Container(*children, accent_colour=ACCENT))

    async def on_select(self, interaction: discord.Interaction) -> None:
        value = interaction.data["values"][0]  # type: ignore[index]
        self.section_index = None if value == "summary" else int(value)
        self.build()
        await interaction.response.edit_message(view=self)

    async def on_back(self, interaction: discord.Interaction) -> None:
        assert self.parent is not None
        self.parent.message = interaction.message
        self.stop()
        await interaction.response.edit_message(view=self.parent)


class SearchView(OwnedView):
    def __init__(
        self,
        client: WikiClient,
        author_id: int,
        query: str,
        lang: str,
        results: list[tuple[str, str]],
    ):
        super().__init__(author_id)
        self.client = client
        self.lang = lang

        children: list[discord.ui.Item] = [
            discord.ui.TextDisplay(f"## \N{RIGHT-POINTING MAGNIFYING GLASS} Results for “{clip(query, 100)}”"),
            discord.ui.Separator(),
        ]
        for i, (title, snippet) in enumerate(results):
            btn = discord.ui.Button(label="Open", style=discord.ButtonStyle.primary)
            btn.callback = self._make_open(title)  # type: ignore[method-assign]
            children.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(f"**{clip(title, 200)}**\n{clip(snippet, 200)}"),
                    accessory=btn,
                )
            )
            if i < len(results) - 1:
                children.append(discord.ui.Separator(visible=False))

        self.add_item(discord.ui.Container(*children, accent_colour=ACCENT))

    def _make_open(self, title: str) -> Callable[[discord.Interaction], Awaitable[None]]:
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            try:
                page = await self.client.get_page(self.lang, title)
            except NETWORK_ERRORS:
                await interaction.followup.send("\N{WARNING SIGN} Couldn't reach Wikipedia.", ephemeral=True)
                return
            if page is None:
                await interaction.followup.send("That page no longer exists.", ephemeral=True)
                return
            view = PageView(self.client, self.author_id, page, self.lang, parent=self)
            view.message = interaction.message
            await interaction.edit_original_response(view=view)

        return callback


def message_view(text: str) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView()
    view.add_item(discord.ui.Container(discord.ui.TextDisplay(text), accent_colour=ACCENT))
    return view


class Wikipedia(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.client = WikiClient()

    async def cog_load(self) -> None:
        self.client.session = self.bot.http_session

    async def _reply(self, ctx: commands.Context, view: discord.ui.LayoutView) -> None:
        msg = await ctx.reply(view=view, mention_author=False)
        if isinstance(view, OwnedView):
            view.message = msg

    async def _search_flow(self, ctx: commands.Context, query: str, lang: str) -> None:
        results = await self.client.search(lang, query)
        if not results:
            await self._reply(ctx, message_view(f"\N{CROSS MARK} No results for **{clip(query, 100)}**."))
            return
        await self._reply(ctx, SearchView(self.client, ctx.author.id, query, lang, results))

    async def _page_flow(self, ctx: commands.Context, title: str, lang: str) -> None:
        page = await self.client.get_page(lang, title)
        if page is None:
            # No exact article: fall back to search results.
            await self._search_flow(ctx, title, lang)
            return
        await self._reply(ctx, PageView(self.client, ctx.author.id, page, lang))

    @commands.group(name="wikipedia", aliases=["wiki", "wp"], invoke_without_command=True)
    async def wikipedia(
        self,
        ctx: commands.Context[Parrot],
        *,
        query: str = commands.parameter(description="The article title or search query.", default=""),
    ) -> None:
        """Browse Wikipedia.

        This command has no cooldown.
        """
        if not query.strip():
            p = ctx.clean_prefix
            await self._reply(
                ctx,
                message_view(
                    "## \N{BOOKS} Wikipedia\n"
                    f"`{p}wiki <title>` — open an article\n"
                    f"`{p}wiki search <query>` — search\n"
                    f"`{p}wiki page <title>` — open an article\n"
                    f"`{p}wiki random` — random article\n"
                    "-# Add `--lang xx` (e.g. `--lang hi`) to use another language edition."
                ),
            )
            return
        text, lang = split_lang(query)
        async with ctx.typing():
            try:
                await self._page_flow(ctx, text, lang)
            except NETWORK_ERRORS:
                await self._reply(ctx, message_view("\N{WARNING SIGN} Couldn't reach Wikipedia. Try again shortly."))

    @wikipedia.command(name="search", aliases=["s"])
    async def wikipedia_search(self, ctx: commands.Context[Parrot], *, query: str = commands.parameter(description="The search query.")) -> None:
        """Search Wikipedia and pick a result.

        This command has no cooldown.
        """
        text, lang = split_lang(query)
        if not text:
            await self._reply(ctx, message_view("Give me something to search for."))
            return
        async with ctx.typing():
            try:
                await self._search_flow(ctx, text, lang)
            except NETWORK_ERRORS:
                await self._reply(ctx, message_view("\N{WARNING SIGN} Couldn't reach Wikipedia. Try again shortly."))

    @wikipedia.command(name="page", aliases=["p", "article"])
    async def wikipedia_page(
        self,
        ctx: commands.Context[Parrot],
        *,
        title: str = commands.parameter(description="The article title."),
    ) -> None:
        """Show a Wikipedia article.

        This command has no cooldown.
        """
        text, lang = split_lang(title)
        if not text:
            await self._reply(ctx, message_view("Give me an article title."))
            return
        async with ctx.typing():
            try:
                await self._page_flow(ctx, text, lang)
            except NETWORK_ERRORS:
                await self._reply(ctx, message_view("\N{WARNING SIGN} Couldn't reach Wikipedia. Try again shortly."))

    @wikipedia.command(name="random", aliases=["r"])
    async def wikipedia_random(
        self,
        ctx: commands.Context[Parrot],
        *,
        options: str = commands.parameter(description="Additional options for the random article."),
    ) -> None:
        """Show a random Wikipedia article.

        This command has no cooldown.
        """
        _, lang = split_lang(options)
        async with ctx.typing():
            try:
                title = await self.client.random_title(lang)
                if title is None:
                    await self._reply(ctx, message_view("\N{WARNING SIGN} Couldn't pick a random article."))
                    return
                await self._page_flow(ctx, title, lang)
            except NETWORK_ERRORS:
                await self._reply(ctx, message_view("\N{WARNING SIGN} Couldn't reach Wikipedia. Try again shortly."))


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Wikipedia(bot))
