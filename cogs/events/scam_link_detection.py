from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING

import arrow
import discord
from discord.ext import commands, tasks

try:
    from orjson import loads
except ImportError:
    from json import loads

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.scam_link_detection")

LINK_RE = re.compile(r"[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", re.IGNORECASE)

GITHUB_HEADERS = {"Authorization": f"token {os.environ['GITHUB_PERSONAL_ACCESS_TOKEN']}", "Accept": "application/json"}


class ScamLinkManager:
    def __init__(self, bot: Parrot):
        self.bot = bot

        self.scam_links_cache_key = "scam_links_cache"

        self.already_fetched = False
        self.last_updated: arrow.Arrow | None = None

        self.source_uri = "https://raw.githubusercontent.com/Discord-AntiScam/scam-links/main/list.json"
        # The repo is actively maintained by akacdev & ThinLiquid

        self.source_commit_uri = "https://api.github.com/repos/Discord-AntiScam/scam-links/commits/main"
        # The idea is simple. As we don't have IFTTT, n8n like webhook service.
        # We will fetch the latest commit every hour.
        # They kinda commit carefully.
        # Commit message starting with `- <link>` means they removed a link
        # Commit message starting with `+ <link>` means they added a link
        # Other commit messages are ignored. Also to avoid duplicate links getting added or removed, we will be using `last_updated` attribute.

    async def add(self, link: str):
        await self.bot.database.add_scam_link(link)

    async def remove(self, link: str):
        await self.bot.database.remove_scam_link(link)

    async def is_scam_link(self, link: str) -> bool:
        return await self.bot.database.is_scam_link(link)

    async def update_cache(self):
        if self.already_fetched:
            await self.process_latest_commit()
            return

        exists = await self.bot.database.is_scam_links_cache_exists()
        if exists:
            count = await self.bot.database.get_scam_links_count()
            if count and count > 20000:
                await self.fetch_latest_commit()
                self.already_fetched = True
                return

        links = await self.fetch_scam_links_from_source()
        if not links:
            return

        await self.bot.database.invalidate_scam_links_cache()
        await self.bot.database.add_scam_link(*links)

    async def fetch_scam_links_from_source(self) -> list[str]:
        async with self.bot.http_session.get(self.source_uri, headers=GITHUB_HEADERS) as response:
            if response.status != 200:
                return []

            list_text = await response.text()
            return loads(list_text)

    async def fetch_latest_commit(self) -> dict | None:
        async with self.bot.http_session.get(self.source_commit_uri, headers=GITHUB_HEADERS) as response:
            if response.status != 200:
                return None
            data = await response.json()
            if not isinstance(data, dict):
                return None
            return data

    async def process_latest_commit(self):
        commit_data = await self.fetch_latest_commit()
        if commit_data is None:
            return

        commit_sha = commit_data.get("sha")
        commit_date_str = commit_data.get("commit", {}).get("committer", {}).get("date")
        commit_message: str = commit_data.get("commit", {}).get("message", "")

        if not commit_sha or not commit_date_str:
            return

        commit_date = arrow.get(commit_date_str)

        if self.last_updated is not None and commit_date <= self.last_updated:
            return

        self.last_updated = commit_date

        lines: list[str] = commit_message.splitlines()
        for commit in lines:
            line = commit.strip()
            if line.startswith("- "):
                link = line[2:].strip()
                await self.remove(link)

            if line.startswith("+ "):
                link = line[2:].strip()
                await self.add(link)


class ScamLinkDetection(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.scam_links_manager = ScamLinkManager(bot)
        self.global_stop: bool = False
        self.warned_count = 0

        _log.info("Cog loaded: %s", self.__class__.__name__)

    async def cog_load(self) -> None:
        self.update_scam_links_cache.start()

    async def cog_unload(self) -> None:
        self.update_scam_links_cache.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot or self.global_stop:
            return

        assert isinstance(message.author, discord.Member)

        if message.author.guild_permissions.administrator:
            return
        # Hmm. Should we?

        link = re.search(LINK_RE, message.content)
        if link is None:
            return

        link = link.group(0).lower().strip()

        warned_already = await self.warned_already(channel=message.channel, link=link)
        if warned_already:
            return

        if await self.scam_links_manager.is_scam_link(link):
            warning_message = (
                f"\N{WARNING SIGN} Potential scam link detected!\n"
                f"Match: `{link}`\n"
                "-# Please be cautious and avoid clicking on suspicious links. Note that this is an automated message and may not always be accurate."
            )
            if message.channel.permissions_for(message.guild.me).send_messages:
                await message.reply(warning_message)
            await self.mark_warned(channel=message.channel, link=link)
            self.warned_count += 1

    @tasks.loop(seconds=60 * 60)
    async def update_scam_links_cache(self):
        await self.scam_links_manager.update_cache()

    async def warned_already(self, *, channel: discord.abc.MessageableChannel, link: str) -> bool:
        exists = await self.bot.database.check_if_link_warned(link=link, channel_id=channel.id)
        if isinstance(exists, int) and bool(exists):
            return True

        return False

    async def mark_warned(self, *, channel: discord.abc.MessageableChannel, link: str) -> None:
        await self.bot.database.flag_link_as_warned(link=link, channel_id=channel.id)

    @commands.group(name="sl", hidden=True, aliases=["scamlink", "scamlinks", "scam_link", "scam_links"])
    @commands.is_owner()
    async def scam_links_command(self, ctx: commands.Context):
        """Scam links management."""

    @scam_links_command.command(name="update", hidden=True)
    @commands.is_owner()
    async def update_scam_links_command(self, ctx: commands.Context):
        """Update scam links cache."""
        await self.scam_links_manager.update_cache()
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @scam_links_command.command(name="stop", hidden=True)
    @commands.is_owner()
    async def stop_scam_links_command(self, ctx: commands.Context):
        """Stop scam links detection."""
        self.global_stop = True
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @scam_links_command.command(name="start", hidden=True)
    @commands.is_owner()
    async def start_scam_links_command(self, ctx: commands.Context):
        """Start scam links detection."""
        self.global_stop = False
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @scam_links_command.command(name="status", hidden=True)
    @commands.is_owner()
    async def status_scam_links_command(self, ctx: commands.Context):
        """Check scam links detection status."""
        status = "stopped" if self.global_stop else "running"
        await ctx.send(f"Scam links detection is currently **{status}**. Warned count: {self.warned_count}")

    @scam_links_command.command(name="check", hidden=True, aliases=["is_scam", "is_scam_link", "chk"])
    @commands.is_owner()
    async def check_scam_link_command(self, ctx: commands.Context[Parrot], *, link: str):
        """Check if a link is a scam link."""
        is_scam = await self.scam_links_manager.is_scam_link(link=link)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        if is_scam:
            await ctx.message.add_reaction("\N{WARNING SIGN}")
        else:
            await ctx.message.add_reaction("\N{THUMBS UP SIGN}")

        await ctx.message.add_reaction("\N{WASTEBASKET}")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return user == ctx.author and str(reaction.emoji) == "\N{WASTEBASKET}" and reaction.message.id == ctx.message.id

        try:
            await ctx.bot.wait_for("reaction_add", check=check, timeout=30)
            await ctx.message.delete(delay=0)
        except TimeoutError:
            await ctx.message.clear_reaction("\N{WASTEBASKET}")


async def setup(bot: Parrot):
    await bot.add_cog(ScamLinkDetection(bot))
