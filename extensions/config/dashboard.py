from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import discord

from core.utils import BaseLayoutView

from .pages import PAGES, OverviewPage
from .pages.base import Button, Interaction, NoticeLevel, Page

if TYPE_CHECKING:
    from discord.ext import commands

    from core import Bot
    from core.utils.database.models import GuildConfiguration

__all__ = ("ConfigDashboard",)

TIMEOUT_SECONDS = 10 * 60  # below the 15-minute interaction token lifetime so the timeout render still goes through
DEFAULT_ACCENT = discord.Colour.blurple()
RESET_ACCENT = discord.Colour.red()


class NavigationSelect(discord.ui.Select):
    """The category menu at the top of the dashboard."""

    def __init__(self, dashboard: ConfigDashboard) -> None:
        self.dashboard = dashboard
        super().__init__(
            placeholder="Open a settings category\N{HORIZONTAL ELLIPSIS}",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=page.label, value=page.key, emoji=page.emoji) for page in dashboard.pages.values()],
        )

    def sync(self) -> None:
        for option in self.options:
            option.default = option.value == self.dashboard.current_key

    async def callback(self, interaction: Interaction) -> None:
        await self.dashboard.open_page(interaction, self.values[0])


class ConfigDashboard(BaseLayoutView):
    """A single components v2 message that edits every server setting in place.

    The view keeps a cached copy of the guild document. Every control writes through the
    database, then calls :meth:`commit`, which reloads the document, re-renders the current
    page and edits the message that the interaction came from.
    """

    def __init__(self, author: discord.Member | discord.User, *, bot: Bot, guild: discord.Guild, config: GuildConfiguration) -> None:
        super().__init__(author, timeout=TIMEOUT_SECONDS, required_permission=discord.Permissions(administrator=True))
        self.bot = bot
        self.guild = guild
        self.config = config

        self.pages: dict[str, Page] = {}
        for PageClass in PAGES:
            self.pages[PageClass.key] = PageClass(self)

        self.current_key = OverviewPage.key
        self.notice: str | None = None
        self.pending_reset = False
        self._last_interaction: Interaction | None = None

        self.navigation = NavigationSelect(self)
        self.container = discord.ui.Container(accent_colour=DEFAULT_ACCENT)
        self.refresh_button = Button(self._refresh_pressed, label="Refresh", emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
        self.close_button = Button(self._close_pressed, label="Close", emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}")

        self.add_item(discord.ui.ActionRow(self.navigation))
        self.add_item(self.container)
        self.add_item(discord.ui.ActionRow(self.refresh_button, self.close_button))

    @property
    def page(self) -> Page:
        return self.pages[self.current_key]

    def render(self) -> None:
        page = self.page
        self.navigation.sync()
        self.container.clear_items()
        self.container.accent_colour = RESET_ACCENT if self.pending_reset else page.accent() or DEFAULT_ACCENT

        self.container.add_item(discord.ui.TextDisplay(f"## {page.emoji} {page.label}\n-# {page.description}"))
        self.container.add_item(discord.ui.Separator())

        if self.pending_reset:
            self._render_reset_prompt(page)
        else:
            for item in page.build():
                self.container.add_item(item)

        if self.notice:
            self.container.add_item(discord.ui.Separator())
            self.container.add_item(discord.ui.TextDisplay(f"-# {self.notice}"))

    def _render_reset_prompt(self, page: Page) -> None:
        self.container.add_item(
            discord.ui.TextDisplay(
                f"### \N{WARNING SIGN}\N{VARIATION SELECTOR-16} Reset {page.label}?\nThis restores the defaults for {page.reset_summary()}. It cannot be undone."
            )
        )
        self.container.add_item(
            discord.ui.ActionRow(
                Button(self._confirm_reset, label="Yes, reset", style=discord.ButtonStyle.danger),
                Button(self._cancel_reset, label="Keep my settings", style=discord.ButtonStyle.secondary),
            )
        )

    async def start(self, ctx: commands.Context[Bot]) -> discord.Message:
        await self.page.prepare()
        self.render()
        self.message = await ctx.reply(view=self, ephemeral=True)
        return self.message

    async def reload(self) -> None:
        self.config = await self.bot.database.get_guild_settings(self.guild.id)

    async def respond(self, interaction: Interaction) -> None:
        """Push the current render to the dashboard message, whatever stage the interaction is at."""
        self._last_interaction = interaction
        if interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        else:
            await interaction.response.edit_message(view=self)

    @staticmethod
    async def acknowledge(interaction: Interaction) -> None:
        """Answer within Discord's 3-second window before doing anything that may be slow.

        A deferred update shows no loading state, and :meth:`respond` then edits the message
        through the interaction token, which stays valid for 15 minutes.
        """
        if not interaction.response.is_done():
            await interaction.response.defer()

    async def commit(self, interaction: Interaction, notice: str | None = None, *, level: NoticeLevel = NoticeLevel.OK) -> None:
        """Reload the guild document, show ``notice`` and re-render the current page."""
        await self.acknowledge(interaction)
        await self.reload()
        await self.page.prepare()
        self.notice = f"{level.value} {notice}" if notice else None
        self.pending_reset = False
        self.render()
        await self.respond(interaction)

    async def open_page(self, interaction: Interaction, key: str) -> None:
        await self.acknowledge(interaction)
        self.current_key = key
        self.notice = None
        self.pending_reset = False
        await self.reload()
        await self.page.prepare()
        self.render()
        await self.respond(interaction)

    async def request_reset(self, interaction: Interaction) -> None:
        self.pending_reset = True
        self.notice = None
        self.render()
        await self.respond(interaction)

    async def _confirm_reset(self, interaction: Interaction) -> None:
        await self.acknowledge(interaction)
        await self.page.reset()
        await self.commit(interaction, f"{self.page.label} settings were reset to their defaults.")

    async def _cancel_reset(self, interaction: Interaction) -> None:
        self.pending_reset = False
        self.render()
        await self.respond(interaction)

    async def _refresh_pressed(self, interaction: Interaction) -> None:
        await self.commit(interaction, "Reloaded the latest settings.", level=NoticeLevel.INFO)

    async def _close_pressed(self, interaction: Interaction) -> None:
        self.stop()
        await interaction.response.defer()
        with contextlib.suppress(discord.HTTPException):
            await interaction.delete_original_response()

    async def on_timeout(self) -> None:
        self.notice = "This dashboard timed out. Run the command again to keep editing."
        self.render()
        self.disable_all_items()

        if self._last_interaction is not None:
            with contextlib.suppress(discord.HTTPException):
                await self._last_interaction.edit_original_response(view=self)
                return

        await self.update_message()
