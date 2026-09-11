from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import discord
import re2 as re
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot

_log = logging.getLogger("bot.cogs.highlights")


class Highlights(commands.Cog):
    """Highlight a message based on a trigger word.

    Highlights are basically notifications that are sent to a user when a message containing a specific trigger word is sent in a channel.
    """

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.group(name="highlights", aliases=["hl", "highlight"], invoke_without_command=True)
    async def highlight(self, ctx: commands.Context[Parrot]) -> None:
        """Highlight a message based on a trigger word.

        This command group allows users to manage their message highlights. Users can add, remove, and list their highlight trigger words, as well as block or unblock users from triggering their highlights.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @highlight.command(name="add", aliases=["create", "new"])
    async def add_highlight(
        self,
        ctx: commands.Context[Parrot],
        *,
        trigger: str = commands.parameter(description="The trigger word for the highlight"),
    ) -> None:
        """Add a new highlight.

        This command allows users to add a new highlight trigger word. When a message containing this trigger word is sent in a channel, the user will receive a notification.
        """
        assert ctx.guild is not None

        await self.bot.database.add_user_highlight(
            guild_id=ctx.guild.id,
            user_id=ctx.author.id,
            words=[trigger],
        )
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @highlight.command(name="remove", aliases=["delete", "del", "rm"])
    async def remove_highlight(
        self,
        ctx: commands.Context[Parrot],
        *,
        trigger: str = commands.parameter(description="The trigger word for the highlight"),
    ) -> None:
        """Remove an existing highlight."""
        assert ctx.guild is not None

        await self.bot.database.remove_user_highlight(
            guild_id=ctx.guild.id,
            user_id=ctx.author.id,
            words=[trigger],
        )

    @highlight.command(name="list", aliases=["ls"])
    async def list_highlights(self, ctx: commands.Context[Parrot]) -> None:
        """List all highlights."""
        assert ctx.guild is not None

        highlights = await self.bot.database.get_user_highlights(
            guild_id=ctx.guild.id,
            user_id=ctx.author.id,
        )

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Highlights",
            description=f"There are total of {len(highlights or [])} highlights.",
        )

        view = discord.ui.View()
        button = discord.ui.Button(label="View Highlights", style=discord.ButtonStyle.primary)
        button.callback = self._view_highlights_callback(ctx.author, highlights)

        await ctx.reply(embed=embed, view=view)

    @highlight.command(name="block", aliases=["ignore"])
    async def block_user(
        self,
        ctx: commands.Context[Parrot],
        *,
        user: discord.Member | discord.User = commands.parameter(description="The user to block from triggering your highlights"),  # noqa: B008
    ) -> None:
        """Block a user from triggering your highlights."""
        await self.bot.database.add_user_highlight_ignored_user(
            user_id=ctx.author.id,
            ignored_user_id=user.id,
        )
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @highlight.command(name="unblock", aliases=["unignore"])
    async def unblock_user(
        self,
        ctx: commands.Context[Parrot],
        *,
        user: discord.Member | discord.User = commands.parameter(description="The user to block from triggering your highlights"),  # noqa: B008
    ) -> None:
        """Unblock a user from triggering your highlights."""
        await self.bot.database.remove_user_highlight_ignored_user(
            user_id=ctx.author.id,
            ignored_user_id=user.id,
        )
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    def _view_highlights_callback(self, author: discord.User | discord.Member, highlights: set[str] | None):
        async def callback(interaction: discord.Interaction[Parrot]):
            if interaction.user != author:
                await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
                return

            if not highlights:
                await interaction.response.send_message("You have no highlights.", ephemeral=True)
                return

            pages = []
            for index, highlight in enumerate(highlights, start=1):
                pages.append(f"{index}. {highlight}")

            ctx = await commands.Context.from_interaction(interaction)
            await interaction.client.paginate(
                ctx,
                embed=True,
                pages=pages,
            )

            return interaction

        return callback

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        await self.bot.wait_until_ready()
        self.bot.dispatch("user_activity", message.channel, message.author)

    @commands.Cog.listener()
    async def on_typing(
        self,
        channel: discord.abc.Messageable,
        user: discord.User,
        _: datetime.datetime,
    ):
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
        initial_description = f"In {message.channel.mention} for `{(message.guild.name)}`you were highlighted with the word **{highlight}**\n\n"

        em = (
            discord.Embed(description="", timestamp=message.created_at)
            .set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            .set_footer(text="Triggered")
        )

        def esc(string: str) -> str:
            st = discord.utils.escape_markdown(string)
            return string.replace(f"{highlight}", f"**{highlight}**")

        content = esc(message.content)[:2000]
        relative_time = discord.utils.format_dt(message.created_at, style="R")
        em.description = f"{relative_time} `@{str(message.author)}`: {content}"

        try:
            async for ms in message.channel.history(limit=3, before=message):
                content = esc(ms.content)
                relative_time = discord.utils.format_dt(ms.created_at, style="R")
                text = f"{relative_time} `@{str(ms.author)}`: {esc(content)}\n"
                if len(initial_description + em.description + text) <= 4096:
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


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Highlights(bot))
