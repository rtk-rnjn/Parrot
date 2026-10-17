from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import discord
import re2 as re
from discord.ext import commands

from core.utils import BaseLayoutView, NoticeLayout, plural, truncate

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)
EMBED_DESCRIPTION_LIMIT = 4096
MAX_LIST_LENGTH = 3800


class HighlightListView(BaseLayoutView):
    """A public count of trigger words with a button that reveals them privately."""

    def __init__(self, author: discord.Member | discord.User, words: list[str]) -> None:
        super().__init__(author, timeout=120)
        self.words = sorted(words, key=str.casefold)

        button = discord.ui.Button(label="Show my trigger words", style=discord.ButtonStyle.primary, emoji="\N{BELL}")
        button.callback = self.show
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"### Highlights\n{author.mention} has {plural(len(self.words)):trigger word} in this server."),
                discord.ui.ActionRow(button),
            )
        )

    async def show(self, interaction: discord.Interaction[Bot]) -> None:
        if not self.words:
            await interaction.response.send_message(view=NoticeLayout.info("You have no trigger words in this server."), ephemeral=True)
            return

        lines = "\n".join(f"{index}. {discord.utils.escape_markdown(word)}" for index, word in enumerate(self.words, start=1))
        await interaction.response.send_message(view=NoticeLayout.info(truncate(lines, MAX_LIST_LENGTH), title="Your trigger words"), ephemeral=True)


class Highlights(commands.Cog):
    """Get a message from Bot when someone posts one of your trigger word."""

    help_emoji = "\N{BELL}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    @commands.group(name="highlight", aliases=["highlights", "hl"], invoke_without_command=True)
    async def highlight(self, ctx: commands.Context[Bot]) -> None:
        """Manage the words that trigger a notification for you.

        When another member posts a trigger word in this server, Bot sends you the message with some context.
        Use the subcommands to add or remove words and to ignore specific users.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @highlight.command(name="add", aliases=["create", "new", "+", "+="])
    async def add_highlight(
        self,
        ctx: commands.Context[Bot],
        *,
        trigger: str = commands.parameter(description="The word or phrase to watch for"),
    ) -> None:
        """Add a trigger word. Bot deletes your message afterwards so the word stays private."""
        assert ctx.guild is not None

        await self.bot.database.add_user_highlight(guild_id=ctx.guild.id, user_id=ctx.author.id, words=[trigger])
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.message.delete(delay=0)

    @highlight.command(name="remove", aliases=["delete", "del", "rm"])
    async def remove_highlight(
        self,
        ctx: commands.Context[Bot],
        *,
        trigger: str = commands.parameter(description="The word or phrase to stop watching"),
    ) -> None:
        """Remove a trigger word."""
        assert ctx.guild is not None

        await self.bot.database.remove_user_highlight(guild_id=ctx.guild.id, user_id=ctx.author.id, words=[trigger])

        if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.message.delete(delay=0)

    @highlight.command(name="list", aliases=["ls"])
    async def list_highlights(self, ctx: commands.Context[Bot]) -> None:
        """Show how many trigger words you have, with a button that lists them privately."""
        assert ctx.guild is not None

        highlights = await self.bot.database.get_user_highlights(guild_id=ctx.guild.id, user_id=ctx.author.id)
        view = HighlightListView(ctx.author, list(highlights or []))
        view.message = await ctx.reply(view=view)

    @highlight.command(name="block", aliases=["ignore"])
    async def block_user(
        self,
        ctx: commands.Context[Bot],
        *,
        user: discord.Member | discord.User = commands.parameter(description="The user to ignore"),  # noqa: B008
    ) -> None:
        """Stop a user's messages from triggering your highlights."""
        await self.bot.database.add_user_highlight_ignored_user(user_id=ctx.author.id, ignored_user_id=user.id)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @highlight.command(name="unblock", aliases=["unignore"])
    async def unblock_user(
        self,
        ctx: commands.Context[Bot],
        *,
        user: discord.Member | discord.User = commands.parameter(description="The user to stop ignoring"),  # noqa: B008
    ) -> None:
        """Let a user's messages trigger your highlights again."""
        await self.bot.database.remove_user_highlight_ignored_user(user_id=ctx.author.id, ignored_user_id=user.id)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        await self.bot.wait_until_ready()
        self.bot.dispatch("user_activity", message.channel, message.author)

    @commands.Cog.listener()
    async def on_typing(self, channel: discord.abc.Messageable, user: discord.User, _: datetime.datetime):
        self.bot.dispatch("user_activity", channel, user)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        self.bot.dispatch("user_activity", reaction.message.channel, user)

    @commands.Cog.listener("on_message")
    async def on_highlight(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        notified_users = []

        for member in message.guild.members:
            if member.bot or member == message.author:
                continue

            highlights = await self.bot.database.get_user_highlights(guild_id=message.guild.id, user_id=member.id)
            ignored_users = await self.bot.database.get_user_highlight_ignored_users(user_id=member.id)

            if not highlights or (ignored_users and message.author.id in ignored_users):
                continue

            for highlight in highlights:
                if re.search(highlight.lower(), message.content.lower()) and member not in notified_users:
                    self.bot.dispatch("highlight", message, member, highlight)
                    notified_users.append(member)

    @commands.Cog.listener("on_highlight")
    async def _send_highlight_notification(self, message: discord.Message, member: discord.Member, highlight: str) -> None:
        if TYPE_CHECKING:
            assert isinstance(message.channel, discord.abc.GuildChannel)
            assert message.guild is not None

        initial_description = f"In {message.channel.mention} for `{(message.guild.name)}`you were highlighted with the word **{highlight}**\n\n"

        em = (
            discord.Embed(description="", timestamp=message.created_at)
            .set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url,
            )
            .set_footer(text="Triggered")
        )

        def escape_and_highlight(string: str) -> str:
            st: str = discord.utils.escape_markdown(string)
            return st.replace(f"{highlight}", f"**{highlight}**")

        content = escape_and_highlight(message.content)[:2000]
        relative_time = discord.utils.format_dt(message.created_at, style="R")
        em.description = f"{relative_time} `@{message.author!s}`: {content}"

        try:
            async for ms in message.channel.history(limit=3, before=message):
                content = escape_and_highlight(ms.content)
                relative_time = discord.utils.format_dt(ms.created_at, style="R")
                text = f"{relative_time} `@{ms.author!s}`: {escape_and_highlight(content)}\n"
                if len(initial_description + em.description + text) <= EMBED_DESCRIPTION_LIMIT:
                    em.description = text + em.description
        except discord.HTTPException:
            pass

        em.description = initial_description + em.description
        try:
            await member.send(embed=em)
        except discord.Forbidden:
            _log.warning("Could not send highlight notification to %s", member)

    @commands.Cog.listener("on_highlight")
    async def on_highlight_notify(self, message: discord.Message, member: discord.Member, *, highlight: str) -> None:
        try:
            await self.bot.wait_for(
                "user_activity",
                check=lambda channel, user: message.channel == channel and user == member,
                timeout=30,
            )
            return
        except TimeoutError:
            pass

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if member in message.mentions:
            return

        await self._send_highlight_notification(message, member, highlight)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Highlights(bot))
