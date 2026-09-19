from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, TypedDict

import discord
import logging
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot

loads = discord.utils._from_json

_log = logging.getLogger("bot.cogs.global_chat")


class ProfaneWord(TypedDict):
    word: str
    categories: list[str]
    intensity: int


with open("assets/profane_words.json") as file:
    profane_words: list[ProfaneWord] = loads(file.read())


class GlobalChat(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.channel_cooldown = commands.CooldownMapping.from_cooldown(5, 5, commands.BucketType.channel)
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None or not isinstance(message.channel, discord.TextChannel):
            return

        assert isinstance(message.author, discord.Member)

        is_global_chat_enabled = await self.bot.database.is_global_chat_enabled(message.guild.id)
        global_chat_channel_id = await self.bot.database.get_global_chat_channel_id(message.guild.id)

        if not is_global_chat_enabled:
            _log.debug("Global chat is not enabled for guild %s", message.guild.id)
            return

        if global_chat_channel_id is None:
            _log.debug("Global chat channel is not set for guild %s", message.guild.id)
            return

        if message.channel.id != global_chat_channel_id:
            _log.debug("Message is not in the global chat channel for guild %s", message.guild.id)
            return

        if message.content.startswith((".", "!", "$", "?", "-", "+")) or not message.content.strip():
            _log.debug("Message is a command or empty, ignoring.")
            return

        channel_bucket = self.channel_cooldown.get_bucket(message)
        channel_retry_after = channel_bucket.update_rate_limit() if channel_bucket is not None else None
        if channel_retry_after:
            _log.debug("Message is being sent too quickly in channel %s, ignoring.", message.channel.id)
            return

        async for guild_id, webhook_uri in self.bot.database.fetch_active_global_chat_webhooks():
            if guild_id == message.guild.id or webhook_uri is None:
                continue

            guild = self.bot.get_guild(guild_id)
            if guild is None:
                _log.warning("Guild with ID %s not found in bot cache.", guild_id)
                continue

            webhook = discord.Webhook.from_url(webhook_uri, client=self.bot)
            content = self._moderate_message(message)
            await webhook.send(
                content=content[:2000],
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    def _normalize_for_comparison(self, text: str) -> str:
        return "".join(char for char in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(char))

    def _moderate_message(self, message: discord.Message) -> str:
        content = message.content
        normalized_content = self._normalize_for_comparison(content)

        for profane_word in profane_words:
            word = profane_word["word"]
            normalized_word = self._normalize_for_comparison(word)

            if normalized_word in normalized_content:
                content = content.replace(word, "*" * len(word))

        content = discord.utils.escape_markdown(content)
        content = discord.utils.escape_mentions(content)

        return content


async def setup(bot: Parrot) -> None:
    await bot.add_cog(GlobalChat(bot))
