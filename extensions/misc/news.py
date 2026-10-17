from __future__ import annotations

import os
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.utils import BaseLayoutView, truncate

if TYPE_CHECKING:
    from core import Bot

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2"
NEWS_LANGUAGE = "en"
NEWS_LIMIT = 25
NEWS_TTL = 600
NEWS_TABS = (
    ("Top", None),
    ("Business", "business"),
    ("Technology", "technology"),
    ("Science", "science"),
    ("Sports", "sports"),
)
NEWS_CATEGORIES = ["business", "entertainment", "general", "health", "science", "sports", "technology"]
NEWS_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


class NewsError(Exception):
    pass


def news_clean(text: str | None) -> str:
    return discord.utils.escape_mentions((text or "").replace("[", "(").replace("]", ")").strip())


def news_time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


async def fetch_news(*, topic: str | None, session: aiohttp.ClientSession) -> list[dict[str, Any]]:

    if topic is None:
        endpoint, params = "top-headlines", {}
    elif topic in NEWS_CATEGORIES:
        endpoint, params = "top-headlines", {"category": topic}
    else:
        endpoint, params = "everything", {"q": topic[:100], "sortBy": "publishedAt", "language": NEWS_LANGUAGE}
    params["pageSize"] = str(NEWS_LIMIT + 5)

    key = f"{endpoint}:{sorted(params.items())}"
    cached = NEWS_CACHE.get(key)
    if cached is not None and time.monotonic() - cached[0] < NEWS_TTL:
        return cached[1]

    try:
        async with session.get(f"{NEWS_API_URL}/{endpoint}", params=params, headers={"X-Api-Key": NEWS_API_KEY or ""}) as response:
            data = await response.json(content_type=None)
            status = response.status
    except (aiohttp.ClientError, TimeoutError) as exc:
        msg = "Bot couldn't reach the news service. Please try again later."
        raise NewsError(msg) from exc

    if status != 200 or data.get("status") != "ok":
        code = data.get("code", "")
        if code == "rateLimited" or status == 429:
            msg = "The daily news limit has been reached. Please try again later."
            raise NewsError(msg)
        if code.startswith("apiKey"):
            msg = "The news service is not configured correctly."
            raise NewsError(msg)
        msg = "The news service returned an error."
        raise NewsError(msg)

    articles = [a for a in data.get("articles", []) if a.get("title") and a.get("url") and a["title"] != "[Removed]"][:NEWS_LIMIT]
    NEWS_CACHE[key] = (time.monotonic(), articles)
    return articles


class NewsView(BaseLayoutView):
    def __init__(self, ctx: commands.Context, topic: str | None, articles: list[dict[str, Any]]) -> None:
        super().__init__(ctx.author, timeout=300)
        self.topic = topic
        self.articles = articles
        self.index = 0
        self.container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        self.add_item(self.container)
        self.render()

    @property
    def heading(self) -> str:
        if self.topic is None:
            return "Top headlines"
        if self.topic in NEWS_CATEGORIES:
            return f"{self.topic.title()} headlines"
        return f"News about {news_clean(self.topic)}"

    def switch(self, key: str | None):
        async def callback(interaction: discord.Interaction[Bot]) -> None:
            await interaction.response.defer()
            try:
                articles = await fetch_news(topic=key, session=interaction.client.http_session)
            except NewsError as exc:
                await interaction.followup.send(str(exc), ephemeral=True)
                return
            self.topic = key
            self.articles = articles
            self.index = 0
            self.render()
            await interaction.edit_original_response(view=self)

        return callback

    def step(self, offset: int):
        async def callback(interaction: discord.Interaction) -> None:
            self.index += offset
            self.render()
            await interaction.response.edit_message(view=self)

        return callback

    async def pick(self, interaction: discord.Interaction) -> None:
        self.index = int(self.select.values[0])
        self.render()
        await interaction.response.edit_message(view=self)

    def render(self) -> None:
        self.container.clear_items()
        self.container.add_item(discord.ui.TextDisplay(f"## \N{NEWSPAPER} {self.heading}"))

        tabs = []
        for label, key in NEWS_TABS:
            active = key == self.topic
            tab = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.primary if active else discord.ButtonStyle.secondary,
                disabled=active,
            )
            tab.callback = self.switch(key)
            tabs.append(tab)
        self.container.add_item(discord.ui.ActionRow(*tabs))
        self.container.add_item(discord.ui.Separator())

        if not self.articles:
            self.container.add_item(discord.ui.TextDisplay("No stories found."))
            return

        article = self.articles[self.index]
        source = news_clean((article.get("source") or {}).get("name")) or "Unknown source"
        title = news_clean(article["title"]).removesuffix(f" - {source}")
        published = news_time(article.get("publishedAt"))
        meta = source + (f" \N{MIDDLE DOT} {discord.utils.format_dt(published, 'R')}" if published else "")

        self.container.add_item(discord.ui.TextDisplay(f"### [{truncate(title, 250)}]({article['url']})\n-# {meta}"))
        if description := news_clean(article.get("description")):
            self.container.add_item(discord.ui.TextDisplay(truncate(description, 1200)))

        image = article.get("urlToImage")
        if isinstance(image, str) and image.startswith(("http://", "https://")):
            self.container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(image, description=truncate(title, 100))))

        self.container.add_item(discord.ui.ActionRow(discord.ui.Button(label="Read full article", emoji="\N{NEWSPAPER}", url=article["url"])))
        self.container.add_item(discord.ui.Separator())

        options = [
            discord.SelectOption(
                label=truncate(news_clean(item["title"]), 100),
                value=str(i),
                description=truncate(news_clean((item.get("source") or {}).get("name")), 100) or None,
                default=i == self.index,
            )
            for i, item in enumerate(self.articles)
        ]
        self.select = discord.ui.Select(placeholder="Jump to a story", options=options)
        self.select.callback = self.pick
        self.container.add_item(discord.ui.ActionRow(self.select))

        previous = discord.ui.Button(label="Previous", emoji="\N{BLACK LEFT-POINTING TRIANGLE}", disabled=self.index == 0)
        counter = discord.ui.Button(label=f"{self.index + 1} / {len(self.articles)}", disabled=True)
        following = discord.ui.Button(label="Next", emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", disabled=self.index >= len(self.articles) - 1)
        previous.callback = self.step(-1)
        following.callback = self.step(1)
        self.container.add_item(discord.ui.ActionRow(previous, counter, following))
