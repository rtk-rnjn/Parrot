from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, TypedDict

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot

loads = discord.utils._from_json


class ProfaneWord(TypedDict):
    word: str
    categories: list[str]
    intensity: int


with open("assets/profane_words.json") as file:
    profane_words: list[ProfaneWord] = loads(file.read())


class GlobalChat(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None or not isinstance(message.channel, discord.TextChannel):
            return

        assert isinstance(message.author, discord.Member)

        is_global_chat_enabled = await self.bot.database.is_global_chat_enabled(message.guild.id)
        global_chat_channel_id = await self.bot.database.get_global_chat_channel_id(message.guild.id)

        if (
            not is_global_chat_enabled
            or global_chat_channel_id is None
            or message.channel.id != global_chat_channel_id
            or message.content.startswith((".", "!", "$", "?", "-", "+"))
            or not message.content.strip()
        ):
            return

        async for guild_id, webhook_uri in self.bot.database.fetch_active_global_chat_webhooks():
            if guild_id == message.guild.id or webhook_uri is None:
                continue

            guild = self.bot.get_guild(guild_id)
            if guild is None:
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
