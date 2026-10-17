from __future__ import annotations

import discord

from .base import Interaction, NoticeLevel, Page, channel_text, status_text

__all__ = ("TicketPage",)


class TicketPage(Page):
    key = "ticket"
    label = "Tickets"
    emoji = "\N{TICKET}"
    description = "Members open private support threads from a panel message."
    section = "ticket_config"

    @property
    def enabled(self) -> bool:
        return bool(self.config["ticket_config"].get("enabled"))

    @property
    def channel_id(self) -> int | None:
        return self.config["ticket_config"].get("channel_id")

    def _panel_text(self) -> str:
        ticket = self.config["ticket_config"]
        message_id = ticket.get("bot_message_id")
        channel_id = ticket.get("bot_channel_channel_id")
        if not message_id or not channel_id:
            return "*Not posted yet* \N{MIDDLE DOT} run the `ticket setup` command"
        return f"[Jump to panel](https://discord.com/channels/{self.guild.id}/{channel_id}/{message_id}) in {channel_text(self.guild, channel_id)}"

    def summary(self) -> str:
        text = status_text(self.enabled)
        if self.channel_id:
            text += f" \N{MIDDLE DOT} threads in {channel_text(self.guild, self.channel_id)}"
        return text

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if self.enabled else discord.Colour.dark_grey()

    def reset_summary(self) -> str:
        return "the ticket toggle, channel and panel reference (the panel message itself is left in place)"

    def build(self) -> list[discord.ui.Item]:
        return [
            self.status(
                [
                    ("Status", status_text(self.enabled)),
                    ("Ticket channel", channel_text(self.guild, self.channel_id)),
                    ("Panel message", self._panel_text()),
                ]
            ),
            self.text("-# New tickets are created as private threads under the ticket channel."),
            self.row(self.toggle(self.enabled, self.set_enabled), self.reset_button()),
            self.row(self.channel_select("Ticket channel\N{HORIZONTAL ELLIPSIS}", self.set_channel, current=self.channel_id)),
        ]

    async def set_enabled(self, interaction: Interaction, enabled: bool) -> None:
        if enabled and self.channel_id is None:
            await self.commit(interaction, "Pick a ticket channel first, then enable tickets.", level=NoticeLevel.ERROR)
            return
        await self.db.edit_ticket_config(guild_id=self.guild.id, enabled=enabled)
        await self.commit(interaction, "Tickets enabled." if enabled else "Tickets disabled.")

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        if channel_id is None:
            await self.db.edit_ticket_config(guild_id=self.guild.id, enabled=False, channel_id=None)
            await self.commit(interaction, "Ticket channel cleared and tickets disabled.")
            return

        await self.db.edit_ticket_config(guild_id=self.guild.id, channel_id=channel_id)
        await self.commit(
            interaction, f"Tickets will open under {channel_text(self.guild, channel_id)}. Run `ticket setup` there to post a fresh panel."
        )
