from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import feedparser
from discord.utils import MISSING

import discord
from core import Cog, Context, Parrot
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from typing_extensions import Self


class RSSItem:
    feed: feedparser.FeedParserDict

    def __init__(self, raw_data: dict, *, bot: Parrot) -> None:
        self._raw_data = raw_data
        self.bot = bot
        self.cog: RSS = self.bot.get_cog("RSS")

        self.channel_id: int = raw_data["channel_id"]
        self.webhook_url: str = raw_data["webhook_url"]
        self.link: str = raw_data["link"]

        self._last_entry: str | None = raw_data.get("last_entry")

    @property
    def channel(self) -> discord.TextChannel | None:
        return self.bot.get_channel(self.channel_id)

    @property
    def webhook(self) -> discord.Webhook:
        return discord.Webhook.from_url(self.webhook_url, session=self.bot.http_session)

    async def prepare(self) -> None:
        self.feed = await self.cog.check_feed(self.link)

    async def send(self, guild_id: int) -> None:
        if getattr(self, "feed", None) is None:
            await self.prepare()

        if not self.feed.entries:
            return

        if self._last_entry == self.feed.entries[0].link:
            return

        await self.bot._execute_webhook(self.webhook, embed=self.embed, username="RSS Feed")
        await self.update(guild_id, last_entry=self.feed.entries[0].link)

    @property
    def embed(self) -> discord.Embed:
        first_entry = self.feed.entries[0]
        return discord.Embed(
            title=first_entry.title,
            description=first_entry.description,
            url=first_entry.link,
            color=discord.Color.blurple(),
        )

    async def update(
        self,
        _id: int,
        *,
        webhook_url: str | None = MISSING,
        channel_id: int | None = MISSING,
        link: str | None = MISSING,
        last_entry: str | None = MISSING,
    ) -> None:
        payload = {}
        old_channel_id = self.channel_id
        if webhook_url is not MISSING:
            payload["rss.$[rss].webhook_url"] = webhook_url
            self.webhook_url = webhook_url

        if channel_id is not MISSING:
            payload["rss.$[rss].channel_id"] = channel_id
            self.channel_id = channel_id

        if link is not MISSING:
            payload["rss.$[rss].link"] = link
            self.link = link

        if last_entry is not MISSING:
            payload["rss.$[rss].last_entry"] = last_entry
            self._last_entry = last_entry

        if not payload:
            return

        await self.bot.guild_collections_ind.update_one(
            {"_id": _id},
            {
                "$set": {**payload},
            },
            array_filters=[{"rss.channel_id": old_channel_id}],
        )

    async def delete(self, _id: int) -> None:
        await self.bot.guild_collections_ind.update_one(
            {"_id": _id},
            {
                "$pull": {
                    "rss": {"channel_id": self.channel_id},
                },
            },
        )

    async def add(self, _id: int) -> None:
        await self.bot.guild_collections_ind.update_one(
            {"_id": _id},
            {
                "$addToSet": {
                    "rss": {"channel_id": self.channel_id, "webhook_url": self.webhook_url, "link": self.link},
                },
            },
            upsert=True,
        )

    @classmethod
    def from_raw_data(
        cls,
        *,
        bot: Parrot,
        webhook: discord.Webhook,
        link: str,
        channel: discord.abc.MessageableChannel,
    ) -> Self:
        raw_data = {
            "webhook_url": webhook.url,
            "link": link,
            "channel_id": channel.id,
        }
        return cls(raw_data, bot=bot)

    @staticmethod
    async def factory_delete(_id: int, bot: Parrot, **kw) -> None:
        await bot.guild_collections_ind.update_one(
            {"_id": _id},
            {
                "$pull": {"rss": {**kw}},
            },
        )


class RSS(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{SATELLITE}")

    async def cog_load(self) -> None:
        self.rss_loop.start()

    async def cog_unload(self) -> None:
        if self.rss_loop.is_running():
            self.rss_loop.cancel()

    async def cog_check(self, ctx: Context) -> bool:
        if not isinstance(ctx.channel, discord.TextChannel):
            msg = "RSS Feeds can only be added to text channels."
            raise commands.BadArgument(msg)
        return True

    @commands.group(name="rss", aliases=["rssfeed"])
    async def rss(self, ctx: Context) -> None:
        """RSS Feed Management"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    async def check_feed(self, link: str) -> feedparser.FeedParserDict:
        try:
            d = await asyncio.to_thread(feedparser.parse, link)
        except Exception as e:
            msg = f"Failed to add RSS Feed: {e}"
            raise commands.BadArgument(msg) from e

        if not d.feed:
            msg = "Invalid RSS Feed"
            raise commands.BadArgument(msg)

        return d

    @rss.command(name="add")
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_guild=True, manage_channels=True)
    async def rss_add(self, ctx: Context, *, link: str) -> None:
        """Add a new RSS Feed"""
        webhook = await ctx.channel.create_webhook(name="RSS Feed")

        await self.check_feed(link)
        item = RSSItem.from_raw_data(bot=self.bot, webhook=webhook, link=link, channel=ctx.channel)
        await item.add(ctx.guild.id)

        await ctx.reply(f"{ctx.author.mention} RSS Feed added.")

    @rss.command(name="remove")
    @commands.has_permissions(manage_guild=True, manage_channels=True)
    async def rss_remove(self, ctx: Context, *, link: str = None):
        """Remove an existing RSS Feed"""
        data = await self.bot.guild_collections_ind.find_one({"_id": ctx.guild.id, "rss": {"$exists": True}})
        if not data:
            return await ctx.reply(f"{ctx.author.mention} No RSS Feeds found.")

        await RSSItem.factory_delete(ctx.guild.id, bot=self.bot, link=link)
        await ctx.reply(f"{ctx.author.mention} RSS Feed removed.")

    @rss.command(name="list")
    @commands.has_permissions(manage_guild=True, manage_channels=True)
    async def rss_list(self, ctx: Context):
        """List all RSS Feeds"""
        data = await self.bot.guild_collections_ind.find_one({"_id": ctx.guild.id})
        if not data:
            return await ctx.reply(f"{ctx.author.mention} No RSS Feeds found.")

        if ls := [f"**Channel:** <#{feed['channel_id']}> | **Link:** {feed['link']}" for feed in data["rss"]]:
            await ctx.paginate(ls, module="JishakuPaginatorEmbedInterface", max_size=1000, prefix="", suffix="")
        else:
            await ctx.reply(f"{ctx.author.mention} No RSS Feeds found.")

    @tasks.loop(hours=12)
    async def rss_loop(self) -> None:
        async for data in self.bot.guild_collections_ind.find({"rss": {"$exists": True}}):
            for feed in data["rss"]:
                channel = self.bot.get_channel(feed["channel_id"])
                if not channel:
                    continue
                webhook = discord.Webhook.from_url(feed["webhook_url"], session=self.bot.http_session)
                item = RSSItem.from_raw_data(bot=self.bot, webhook=webhook, link=feed["link"], channel=channel)
                await item.send(data["_id"])
