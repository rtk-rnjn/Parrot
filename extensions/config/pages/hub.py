from __future__ import annotations

import discord

from .base import Interaction, Page, channel_text

__all__ = ("HubPage",)


class HubPage(Page):
    key = "hub"
    label = "Voice Hub"
    emoji = "\N{SPEAKER WITH THREE SOUND WAVES}"
    description = "Join-to-create voice. Joining the hub channel spins up a personal voice channel that is removed once it empties."

    @property
    def channel_id(self) -> int | None:
        return self.config.get("hub_channel_id")

    def summary(self) -> str:
        return f"hub is {channel_text(self.guild, self.channel_id)}" if self.channel_id else "no hub channel"

    def build(self) -> list[discord.ui.Item]:
        return [
            self.status([("Hub channel", channel_text(self.guild, self.channel_id))]),
            self.text("-# Temporary channels are created in the same category as the hub. Clear the selection to turn the hub off."),
            self.row(
                self.channel_select(
                    "Hub voice channel\N{HORIZONTAL ELLIPSIS}",
                    self.set_channel,
                    current=self.channel_id,
                    channel_types=(discord.ChannelType.voice,),
                )
            ),
        ]

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        await self.db.edit_hub_config(guild_id=self.guild.id, hub_channel_id=channel_id)
        await self.commit(
            interaction, "Voice hub turned off." if channel_id is None else f"{channel_text(self.guild, channel_id)} is now the voice hub."
        )
