from __future__ import annotations

import logging

from topgg.types import BotVoteData

import discord
from core import Cog, Parrot

log = logging.getLogger("events.topgg")


class TopggEventListener(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_autopost_success(self) -> None:
        st = f"[{self.bot.user.name.title()}] Posted server count ({self.bot.topgg.guild_count}), shard count ({self.bot.shard_count})"
        await self.bot._execute_webhook(
            self.bot._startup_log_token,
            content=f"```css\n{st}```",
        )
        log.info(
            "Posted server count (%s), shard count (%s)",
            self.bot.topgg.guild_count,
            self.bot.shard_count,
        )

    @Cog.listener()
    async def on_autopost_error(self, exception: Exception) -> None:
        await self.bot._execute_webhook(
            self.bot._error_log_token,
            content=f"```css\n{exception}```",
        )
        log.error("Failed to post server count (%s)", exception, exc_info=True)

    @Cog.listener()
    async def on_dbl_vote(self, data: BotVoteData) -> None:
        if data["type"] == "test":
            self.bot.dispatch("dbl_test", data)
            return

        user: discord.User | None = self.bot.get_user(int(data["user"]))
        user = user.name if user is not None else "Unknown User"

        await self.bot._execute_webhook(
            self.bot._vote_log_token,
            content=f"```css\n{user} ({data['user']}) has upvoted the bot```",
        )

    @Cog.listener()
    async def on_dbl_test(self, data: BotVoteData) -> None:
        await self.bot._execute_webhook(
            self.bot._vote_log_token,
            content=f"```css\nReceived a test vote from {data['user']} ({data['user']})```",
        )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(TopggEventListener(bot))
