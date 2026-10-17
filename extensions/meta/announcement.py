from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.utils.paginator import PaginationView

load_dotenv()

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

ANNOUNCEMENT_CHANNEL_ID = os.getenv("ANNOUNCEMENT_CHANNEL_ID")
CHANGELOG_CHANNEL_ID = os.getenv("CHANGELOG_CHANNEL_ID")

CHANGELOG_LIMIT = 50
CACHE_TTL = 300

EMBED_DESCRIPTION_LIMIT = 4000


def _short(text: str, limit: int, tail: str = "\N{HORIZONTAL ELLIPSIS}") -> str:
    return text if len(text) <= limit else text[: limit - len(tail)].rstrip() + tail


def message_text(message: discord.Message) -> str:
    """The message body, falling back to the first embed if the message is embed-only."""
    if message.content:
        return message.content
    for embed in message.embeds:
        parts = [part for part in (embed.title, embed.description) if part]
        if parts:
            return "\n\n".join(parts)
    return ""


def message_to_embed(message: discord.Message, *, title: str, colour: discord.Colour) -> discord.Embed:
    text = _short(message_text(message), EMBED_DESCRIPTION_LIMIT, tail=f"\N{HORIZONTAL ELLIPSIS}\n\n[Read the full post]({message.jump_url})")
    embed = discord.Embed(
        title=title,
        url=message.jump_url,
        description=text,
        colour=colour,
        timestamp=message.created_at,
    )
    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)

    image = next(
        (a for a in message.attachments if a.content_type and a.content_type.startswith("image/")),
        None,
    )
    if image is not None:
        embed.set_image(url=image.url)

    others = [a for a in message.attachments if a is not image]
    if others:
        embed.add_field(name="Attachments", value="\n".join(f"[{a.filename}]({a.url})" for a in others)[:1024], inline=False)
    return embed


class Announcements(commands.Cog, command_attrs={"hidden": True}):
    """Read the latest announcements and change logs without leaving Discord."""

    help_emoji = "\N{PUBLIC ADDRESS LOUDSPEAKER}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._cache: dict[int, tuple[float, list[discord.Message]]] = {}

    async def _recent_messages(self, channel_id: int, limit: int) -> list[discord.Message]:
        """Newest-first messages with something to show. Cached briefly. Raises discord errors on failure."""
        cached = self._cache.get(channel_id)
        if cached is not None and time.monotonic() - cached[0] < CACHE_TTL and len(cached[1]) >= min(limit, len(cached[1])):
            return cached[1][:limit]

        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            msg = f"Channel {channel_id} is not a messageable channel."
            raise TypeError(msg)

        messages = [m async for m in channel.history(limit=limit) if message_text(m)]
        self._cache[channel_id] = (time.monotonic(), messages)
        return messages

    @commands.command(name="announcement", aliases=["announcements"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def announcement(self, ctx: commands.Context[Bot]) -> None:
        """Show the most recent announcement."""
        if ANNOUNCEMENT_CHANNEL_ID is None:
            await ctx.reply("The announcement channel is not configured.")
            return

        try:
            async with ctx.typing():
                messages = await self._recent_messages(int(ANNOUNCEMENT_CHANNEL_ID), limit=10)
        except discord.Forbidden, discord.NotFound, TypeError:
            _log.exception("Cannot read announcement channel %s", ANNOUNCEMENT_CHANNEL_ID)
            await ctx.reply("Can't read the announcement channel right now.")
            return
        except discord.HTTPException:
            await ctx.reply("Discord had a problem fetching announcements. Try again in a moment.")
            return

        if not messages:
            await ctx.reply("There are no announcements yet.")
            return

        embed = message_to_embed(messages[0], title="\N{PUBLIC ADDRESS LOUDSPEAKER} Latest announcement", colour=discord.Colour.gold())
        await ctx.reply(embed=embed)

    @commands.command(name="changelog", aliases=["changelogs", "updates", "whatsnew"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def changelog(self, ctx: commands.Context[Bot]) -> None:
        """Browse recent change logs, newest first."""
        if CHANGELOG_CHANNEL_ID is None:
            await ctx.reply("The change log channel is not configured.")
            return

        try:
            async with ctx.typing():
                messages = await self._recent_messages(int(CHANGELOG_CHANNEL_ID), limit=CHANGELOG_LIMIT)
        except discord.Forbidden, discord.NotFound, TypeError:
            _log.exception("Cannot read changelog channel %s", CHANGELOG_CHANNEL_ID)
            await ctx.reply("Can't read the change log channel right now.")
            return
        except discord.HTTPException:
            await ctx.reply("Discord had a problem fetching the change log. Try again in a moment.")
            return

        if not messages:
            await ctx.reply("There are no change logs yet.")
            return

        embeds = [message_to_embed(message, title="\N{MEMO} Change log", colour=discord.Colour.blurple()) for message in messages]
        view = PaginationView(author=ctx.author, items=embeds, timeout=300)
        await view.start(ctx)
