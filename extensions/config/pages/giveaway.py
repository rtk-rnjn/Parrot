from __future__ import annotations

import discord

from .base import Interaction, Page, channel_text, role_text, status_text

__all__ = ("GiveawayPage",)


class GiveawayPage(Page):
    key = "giveaway"
    label = "Giveaways"
    emoji = "\N{PARTY POPPER}"
    description = "Where giveaways are hosted and which role is pinged when one starts."
    section = "giveaway_config"

    @property
    def enabled(self) -> bool:
        return bool(self.config["giveaway_config"].get("enabled"))

    @property
    def channel_id(self) -> int | None:
        return self.config["giveaway_config"].get("giveaway_channel_id")

    @property
    def role_id(self) -> int | None:
        return self.config["giveaway_config"].get("giveaway_role_id")

    def summary(self) -> str:
        text = status_text(self.enabled)
        if self.channel_id:
            text += f" \N{MIDDLE DOT} hosted in {channel_text(self.guild, self.channel_id)}"
        return text

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if self.enabled else discord.Colour.dark_grey()

    def build(self) -> list[discord.ui.Item]:
        return [
            self.status(
                [
                    ("Status", status_text(self.enabled)),
                    ("Giveaway channel", channel_text(self.guild, self.channel_id)),
                    ("Ping role", role_text(self.guild, self.role_id)),
                ]
            ),
            self.row(self.toggle(self.enabled, self.set_enabled), self.reset_button()),
            self.row(self.channel_select("Giveaway channel\N{HORIZONTAL ELLIPSIS}", self.set_channel, current=self.channel_id)),
            self.row(self.role_select("Role to ping\N{HORIZONTAL ELLIPSIS}", self.set_role, current=[self.role_id] if self.role_id else ())),
        ]

    async def set_enabled(self, interaction: Interaction, enabled: bool) -> None:
        await self.db.edit_giveaway_config(guild_id=self.guild.id, enabled=enabled)
        await self.commit(interaction, "Giveaways enabled." if enabled else "Giveaways disabled.")

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        await self.db.edit_giveaway_config(guild_id=self.guild.id, giveaway_channel_id=channel_id)
        await self.commit(
            interaction, "Giveaway channel cleared." if channel_id is None else f"Giveaways will be hosted in {channel_text(self.guild, channel_id)}."
        )

    async def set_role(self, interaction: Interaction, roles: list[discord.Role]) -> None:
        role = roles[0] if roles else None
        await self.db.edit_giveaway_config(guild_id=self.guild.id, giveaway_role_id=role.id if role else None)
        await self.commit(interaction, "Ping role cleared." if role is None else f"{role.mention} will be pinged when a giveaway starts.")
