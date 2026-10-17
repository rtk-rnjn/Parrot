from __future__ import annotations

import discord

from .base import Interaction, Page, channel_text

__all__ = ("SuggestionPage",)


class SuggestionPage(Page):
    key = "suggestion"
    label = "Suggestions"
    emoji = "\N{ELECTRIC LIGHT BULB}"
    description = "Every message posted in the suggestion channel becomes a suggestion with its own voting thread."

    @property
    def channel_id(self) -> int | None:
        return self.config.get("suggestion_channel_id")

    def summary(self) -> str:
        return f"collected in {channel_text(self.guild, self.channel_id)}" if self.channel_id else "no channel"

    def build(self) -> list[discord.ui.Item]:
        return [
            self.status([("Suggestion channel", channel_text(self.guild, self.channel_id))]),
            self.text("-# Clear the selection below to stop collecting suggestions."),
            self.row(self.channel_select("Suggestion channel\N{HORIZONTAL ELLIPSIS}", self.set_channel, current=self.channel_id)),
        ]

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        await self.db.edit_suggestion_config(guild_id=self.guild.id, suggestion_channel_id=channel_id)
        await self.commit(
            interaction,
            "Suggestion channel cleared." if channel_id is None else f"Suggestions are collected in {channel_text(self.guild, channel_id)}.",
        )
