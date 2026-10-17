from __future__ import annotations

import discord

from .base import Page

__all__ = ("OverviewPage",)


class OverviewPage(Page):
    key = "overview"
    label = "Overview"
    emoji = "\N{HOUSE BUILDING}"
    description = "A snapshot of every module. Pick a category from the menu above to change its settings."

    def summary(self) -> str:
        return ""

    def accent(self) -> discord.Colour | None:
        return discord.Colour.blurple()

    def build(self) -> list[discord.ui.Item]:
        lines = [f"{page.emoji} **{page.label}** - {page.summary()}" for page in self.dashboard.pages.values() if page is not self]
        guild = self.guild
        footer = f"-# {guild.name} \N{MIDDLE DOT} {guild.member_count or 0:,} members \N{MIDDLE DOT} Server ID `{guild.id}`"
        return [self.text("\n".join(lines)), discord.ui.Separator(), self.text(footer)]
