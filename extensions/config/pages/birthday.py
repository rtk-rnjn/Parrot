from __future__ import annotations

import discord

from .base import Interaction, NoticeLevel, Page, channel_text, status_text

__all__ = ("BirthdayPage",)


class BirthdayPage(Page):
    key = "birthday"
    label = "Birthdays"
    emoji = "\N{BIRTHDAY CAKE}"
    description = "Celebrate members' birthdays with an announcement. Members set their own date with the birthday command."
    section = "birthday_config"

    @property
    def enabled(self) -> bool:
        return bool(self.config["birthday_config"].get("enabled"))

    @property
    def channel_id(self) -> int | None:
        return self.config["birthday_config"].get("channel_id")

    def summary(self) -> str:
        text = status_text(self.enabled)
        if self.channel_id:
            text += f" \N{MIDDLE DOT} announced in {channel_text(self.guild, self.channel_id)}"
        return text

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if self.enabled else discord.Colour.dark_grey()

    def build(self) -> list[discord.ui.Item]:
        return [
            self.status([("Status", status_text(self.enabled)), ("Announcement channel", channel_text(self.guild, self.channel_id))]),
            self.row(self.toggle(self.enabled, self.set_enabled), self.reset_button()),
            self.row(self.channel_select("Birthday announcement channel\N{HORIZONTAL ELLIPSIS}", self.set_channel, current=self.channel_id)),
        ]

    async def set_enabled(self, interaction: Interaction, enabled: bool) -> None:
        if enabled and self.channel_id is None:
            await self.commit(interaction, "Pick an announcement channel first, then enable birthdays.", level=NoticeLevel.ERROR)
            return
        await self.db.edit_birthday_config(guild_id=self.guild.id, enabled=enabled)
        await self.commit(interaction, "Birthday announcements enabled." if enabled else "Birthday announcements disabled.")

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        if channel_id is None:
            await self.db.edit_birthday_config(guild_id=self.guild.id, enabled=False, channel_id=None)
            await self.commit(interaction, "Birthday channel cleared and announcements disabled.")
            return

        await self.db.edit_birthday_config(guild_id=self.guild.id, channel_id=channel_id)
        hint = "" if self.enabled else " Press Enable to start announcing."
        await self.commit(interaction, f"Birthdays will be announced in {channel_text(self.guild, channel_id)}.{hint}")
