"""Components V2 layout + interactive view (``discord.ui.LayoutView``).

Behaviour
---------
* Controls are **invoker-only**: other users get an ephemeral explanation.
* Every callback calls ``interaction.response.defer()`` first (3 s deadline), does the work,
  then edits the *existing* message via ``edit_original_response``.
* Charts travel as attachments referenced with ``attachment://<name>`` in a ``MediaGallery``.
* No interaction objects are stored; only ``self.message`` (a channel message) is kept so the
  timeout handler can disable the controls (bot-token edit; works after the 15-min token expiry).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Protocol

import discord

from .reports import Report
from .repository import PERIODS, Period

log = logging.getLogger(__name__)
NO_MENTIONS = discord.AllowedMentions.none()
MAX_TEXT = 3500


class Provider(Protocol):
    tabs: Sequence[tuple[str, str]]
    default_tab: str

    async def build(self, tab: str, period: Period) -> Report: ...


def _clip(text: str) -> str:
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "\N{HORIZONTAL ELLIPSIS}"


class _SwitchButton(discord.ui.Button["StatsView"]):
    def __init__(self, *, label: str, active: bool, disabled: bool, tab: str | None = None, period: str | None = None) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary if active else discord.ButtonStyle.secondary, disabled=disabled)
        self.tab, self.period = tab, period

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.switch(interaction, tab=self.tab, period=self.period)


def build_container(
    report: Report,
    tabs: Sequence[tuple[str, str]],
    active_tab: str,
    active_period: str,
    *,
    show_periods: bool = True,
    disabled: bool = False,
) -> discord.ui.Container:
    """Pure layout builder (also used by tests)."""
    children: list[discord.ui.Item] = [
        discord.ui.TextDisplay(_clip(f"## {report.title}\n{report.summary}")),
        discord.ui.Separator(),
        discord.ui.TextDisplay(_clip("\n".join(report.metrics))),
    ]
    if report.chart_png:
        children += [
            discord.ui.Separator(),
            discord.ui.MediaGallery().add_item(media=f"attachment://{report.chart_name}", description=report.chart_alt[:1024] or None),
        ]
    children.append(discord.ui.Separator())
    if len(tabs) > 1:
        children.append(
            discord.ui.ActionRow(*[_SwitchButton(label=label, tab=key, active=key == active_tab, disabled=disabled) for key, label in tabs])
        )
    if show_periods:
        children.append(
            discord.ui.ActionRow(
                *[
                    _SwitchButton(label=p.label.replace("Last ", ""), period=p.key, active=p.key == active_period, disabled=disabled)
                    for p in PERIODS.values()
                ]
            )
        )
    children.append(discord.ui.TextDisplay(f"-# {report.footer}"))
    return discord.ui.Container(*children, accent_colour=report.accent)


class StatsView(discord.ui.LayoutView):
    def __init__(
        self,
        provider: Provider,
        *,
        invoker_id: int,
        tab: str | None = None,
        period: Period | None = None,
        timeout: float = 300.0,
        show_periods: bool = True,
    ) -> None:
        super().__init__(timeout=timeout)
        self.provider, self.invoker_id, self.show_periods = provider, invoker_id, show_periods
        self.tab = tab or provider.default_tab
        self.period = period or PERIODS["7d"]
        self.message: discord.Message | None = None
        self.report: Report | None = None
        self._busy = asyncio.Lock()

    def set_report(self, report: Report, *, disabled: bool = False) -> None:
        self.report = report
        self.clear_items()
        self.add_item(build_container(report, self.provider.tabs, self.tab, self.period.key, show_periods=self.show_periods, disabled=disabled))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.invoker_id:
            return True
        try:
            await interaction.response.send_message(
                "These controls belong to the member who ran the command. Run it yourself to get your own view.", ephemeral=True
            )
        except discord.HTTPException:
            log.debug("could not notify non-invoker", exc_info=True)
        return False

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        log.error("stats view callback failed", exc_info=error)

    async def on_timeout(self) -> None:
        if self.report is None or self.message is None:
            return
        self.set_report(self.report, disabled=True)
        try:
            await self.message.edit(view=self, allowed_mentions=NO_MENTIONS)
        except discord.HTTPException:
            log.debug("could not disable expired stats view", exc_info=True)

    async def switch(self, interaction: discord.Interaction, *, tab: str | None = None, period: str | None = None) -> None:
        try:
            await interaction.response.defer()  # ack inside the 3 s window, before any I/O
        except discord.HTTPException:
            log.debug("interaction expired before defer", exc_info=True)
            return
        new_tab, new_period = tab or self.tab, PERIODS[period] if period else self.period
        if self._busy.locked() or (new_tab, new_period) == (self.tab, self.period):
            return  # already updating / nothing to change
        async with self._busy:
            try:
                report = await self.provider.build(new_tab, new_period)
            except Exception:
                log.exception("failed to build stats report")
                await self._notify(interaction, "Bot could not load those statistics. Try again shortly.")
                return
            self.tab, self.period = new_tab, new_period
            self.set_report(report)
            file = report.file()
            try:
                await interaction.edit_original_response(view=self, attachments=[file] if file else [], allowed_mentions=NO_MENTIONS)
            except discord.HTTPException:
                log.info("stats message could not be edited; stopping view", exc_info=True)
                self.stop()

    @staticmethod
    async def _notify(interaction: discord.Interaction, text: str) -> None:
        try:
            await interaction.followup.send(text, ephemeral=True)
        except discord.HTTPException:
            log.debug("followup failed", exc_info=True)


def notice_view(text: str, *, title: str | None = None) -> discord.ui.LayoutView:
    """Static (non-interactive) Components V2 message for errors and admin output."""
    view = discord.ui.LayoutView(timeout=None)
    body = f"## {title}\n{text}" if title else text
    view.add_item(discord.ui.Container(discord.ui.TextDisplay(_clip(body)), accent_colour=0x5865F2))
    return view
