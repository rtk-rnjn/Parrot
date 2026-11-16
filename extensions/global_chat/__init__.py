from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

PROFANE_WORDS_PATH = Path("assets") / "profane_words.json"
COMMAND_PREFIXES = (".", "!", "$", "?", "-", "+")
CONFIG_TTL = 60
MAX_CONCURRENT_SENDS = 10


class ProfaneWord(TypedDict):
    word: str
    categories: list[str]
    intensity: int


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Casefold + strip accents, keeping a map from each normalized char back to its original index."""
    chars: list[str] = []
    index_map: list[int] = []
    for i, original in enumerate(text):
        for char in unicodedata.normalize("NFKD", original.casefold()):
            if not unicodedata.combining(char):
                chars.append(char)
                index_map.append(i)
    return "".join(chars), index_map


def _build_profanity_pattern() -> re.Pattern[str] | None:
    with PROFANE_WORDS_PATH.open(encoding="utf-8") as file:
        entries: list[ProfaneWord] = json.load(file)

    words = {_normalize_with_map(entry["word"])[0] for entry in entries if entry["word"].strip()}
    if not words:
        return None

    # Longest first so "assassin" wins over "ass" when both are listed.
    ordered = sorted(words, key=len, reverse=True)
    return re.compile("|".join(map(re.escape, ordered)))


PROFANITY_PATTERN = _build_profanity_pattern()


class GlobalChat(commands.Cog):
    """Relays one channel to the global chat shared between opted-in servers."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.channel_cooldown = commands.CooldownMapping.from_cooldown(5, 5, commands.BucketType.channel)
        self._config_cache: dict[int, tuple[int | None, float]] = {}
        self._send_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SENDS)

    def invalidate_config(self, guild_id: int) -> None:
        """Call this from your setup/toggle commands when a guild's settings change."""
        self._config_cache.pop(guild_id, None)

    async def _get_relay_channel_id(self, guild_id: int) -> int | None:
        now = time.monotonic()
        cached = self._config_cache.get(guild_id)
        if cached and cached[1] > now:
            return cached[0]

        channel_id = None
        if await self.bot.database.is_global_chat_enabled(guild_id):
            channel_id = await self.bot.database.get_global_chat_channel_id(guild_id)

        self._config_cache[guild_id] = (channel_id, now + CONFIG_TTL)
        return channel_id

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None or not isinstance(message.channel, discord.TextChannel):
            return

        if not message.content.strip() or message.content.startswith(COMMAND_PREFIXES):
            return

        if message.channel.id != await self._get_relay_channel_id(message.guild.id):
            return

        bucket = self.channel_cooldown.get_bucket(message)
        if bucket is not None and bucket.update_rate_limit():
            return

        content = self._moderate(message.content)[:2000]
        username = message.author.display_name[:80]
        avatar_url = message.author.display_avatar.url

        tasks = [
            self._relay(guild_id, webhook_url, content, username, avatar_url)
            async for guild_id, webhook_url in self.bot.database.fetch_active_global_chat_webhooks()
            if guild_id != message.guild.id and webhook_url is not None
        ]
        await asyncio.gather(*tasks)

    async def _relay(self, guild_id: int, webhook_url: str, content: str, username: str, avatar_url: str) -> None:
        webhook = discord.Webhook.from_url(webhook_url, client=self.bot)
        async with self._send_semaphore:
            try:
                await webhook.send(
                    content=content,
                    username=username,
                    avatar_url=avatar_url,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.NotFound:
                _log.warning("Global chat webhook for guild %s was deleted; consider disabling it.", guild_id)
            except discord.HTTPException:
                _log.warning("Failed to relay global chat message to guild %s", guild_id, exc_info=True)

    @staticmethod
    def _moderate(content: str) -> str:
        if PROFANITY_PATTERN is not None:
            normalized, index_map = _normalize_with_map(content)
            censored = list(content)
            for match in PROFANITY_PATTERN.finditer(normalized):
                start = index_map[match.start()]
                end = index_map[match.end() - 1] + 1
                censored[start:end] = "*" * (end - start)
            content = "".join(censored)

        return discord.utils.escape_mentions(discord.utils.escape_markdown(content))


async def setup(bot: Bot) -> None:
    await bot.add_cog(GlobalChat(bot))
