from __future__ import annotations

import asyncio

import feedparser

import discord
from core import Cog, Context, Parrot
from discord.ext import commands, tasks


class RSS(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._cache = {}

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{SATELLITE}")

    async def prepare_cache(self):
        async for data in self.bot.guild_collections_ind.find():
            for feed in data["rss"]:
                channel = self.bot.get_channel(feed["channel_id"])
                if not channel:
                    continue
                webhook = discord.Webhook.from_url(feed["webhook_url"], session=self.bot.http_session)
                self._cache[channel.id] = {"webhook": webhook, "link": feed["link"]}

    async def cog_load(self) -> None:
        await self.prepare_cache()
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
        self._cache[ctx.channel.id] = {"webhook": webhook, "link": link}

        await self.bot.guild_collections_ind.update_one(
            {"_id": ctx.guild.id},
            {
                "$addToSet": {
                    "rss": {"channel_id": ctx.channel.id, "webhook_url": webhook.url, "link": link},
                },
            },
            upsert=True,
        )
        await ctx.reply(f"{ctx.author.mention} RSS Feed added.")

    async def remove_feed(self, ctx: Context, channel_id: int | None = None) -> None:
        channel_id = channel_id or ctx.channel.id
        del self._cache[channel_id]
        await self.bot.guild_collections_ind.update_one(
            {"_id": ctx.guild.id},
            {
                "$pull": {
                    "rss": {"channel_id": channel_id},
                },
            },
        )

    @rss.command(name="remove")
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_guild=True, manage_channels=True)
    async def rss_remove(self, ctx: Context, *, link: str = None):
        """Remove an existing RSS Feed"""
        if ctx.channel.id in self._cache.copy():
            await self.remove_feed(ctx)
            return await ctx.reply(f"{ctx.author.mention} RSS Feed removed.")

        for channel_id in self._cache.copy():
            if self._cache[channel_id]["link"] == link:
                await self.remove_feed(ctx, channel_id)
                await ctx.reply(f"{ctx.author.mention} RSS Feed removed.")
                return

    @rss.command(name="list")
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_guild=True, manage_channels=True)
    async def rss_list(self, ctx: Context):
        """List all RSS Feeds"""
        data = await self.bot.guild_collections_ind.find_one({"_id": ctx.guild.id})
        if not data:
            return await ctx.reply(f"{ctx.author.mention} No RSS Feeds found.")

        embed = discord.Embed(title="RSS Feeds", color=discord.Color.blurple())
        for feed in data["rss"]:
            channel = ctx.guild.get_channel(feed["channel_id"])
            if not channel:
                continue
            embed.add_field(name=channel.mention, value=feed["link"], inline=False)

        await ctx.reply(embed=embed)

    @tasks.loop(hours=1)
    async def rss_loop(self) -> None:
        for channel_id in self._cache:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            d = await self.check_feed(self._cache[channel_id]["link"])
            if not d.entries:
                continue

            embed = await self.parsed_feed(d)
            webhook = self._cache[channel_id]["webhook"]
            await self.bot._execute_webhook(webhook, embed=embed, username="RSS Feed")

    async def parsed_feed(self, d) -> discord.Embed:
        first_entry = d.entries[0]
        embed = discord.Embed(
            title=first_entry.title,
            description=first_entry.description,
            url=first_entry.link,
            color=discord.Color.blurple(),
        )
        return embed
