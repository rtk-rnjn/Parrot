from __future__ import annotations

import discord

from .base import NOT_SET, Interaction, NoticeLevel, Page, channel_text, role_text, role_warning

__all__ = ("ModerationPage",)

MAX_MODERATOR_ROLES = 25
MAX_LISTED_ROLES = 10


class ModerationPage(Page):
    key = "moderation"
    label = "Moderation"
    emoji = "\N{SHIELD}"
    description = "The mute role, who counts as a moderator, and where moderation cases are logged."
    section = "moderator_config"

    @property
    def mute_role_id(self) -> int | None:
        return self.config["moderator_config"].get("mute_role_id")

    @property
    def moderator_role_ids(self) -> list[int]:
        return list(self.config["moderator_config"].get("moderator_role_ids") or [])

    @property
    def logs_channel_id(self) -> int | None:
        return self.config["moderator_config"].get("moderator_logs_channel_id")

    def summary(self) -> str:
        parts = [
            f"mute role {role_text(self.guild, self.mute_role_id)}" if self.mute_role_id else "no mute role",
            f"{len(self.moderator_role_ids)} moderator role{'' if len(self.moderator_role_ids) == 1 else 's'}",
            f"logs in {channel_text(self.guild, self.logs_channel_id)}" if self.logs_channel_id else "no log channel",
        ]
        return " \N{MIDDLE DOT} ".join(parts)

    def _moderator_roles_text(self) -> str:
        role_ids = self.moderator_role_ids
        if not role_ids:
            return NOT_SET
        shown = ", ".join(role_text(self.guild, role_id) for role_id in role_ids[:MAX_LISTED_ROLES])
        hidden = len(role_ids) - MAX_LISTED_ROLES
        return f"{shown} and {hidden} more" if hidden > 0 else shown

    def build(self) -> list[discord.ui.Item]:
        return [
            self.status(
                [
                    ("Mute role", role_text(self.guild, self.mute_role_id)),
                    ("Moderator roles", self._moderator_roles_text()),
                    ("Mod log channel", channel_text(self.guild, self.logs_channel_id)),
                ]
            ),
            self.text("-# Automod rules have their own builder: use the `automod` command."),
            self.row(self.channel_select("Mod log channel\N{HORIZONTAL ELLIPSIS}", self.set_logs_channel, current=self.logs_channel_id)),
            self.row(
                self.role_select("Mute role\N{HORIZONTAL ELLIPSIS}", self.set_mute_role, current=[self.mute_role_id] if self.mute_role_id else ())
            ),
            self.row(
                self.role_select(
                    "Moderator roles\N{HORIZONTAL ELLIPSIS}",
                    self.set_moderator_roles,
                    current=self.moderator_role_ids,
                    max_values=MAX_MODERATOR_ROLES,
                )
            ),
            self.row(self.reset_button()),
        ]

    async def set_logs_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        await self.db.edit_moderator_config(guild_id=self.guild.id, moderator_logs_channel_id=channel_id)
        if channel_id is None:
            await self.commit(interaction, "Mod log channel cleared. Cases are still recorded, just not posted.")
        else:
            await self.commit(interaction, f"Moderation cases will be posted in {channel_text(self.guild, channel_id)}.")

    async def set_mute_role(self, interaction: Interaction, roles: list[discord.Role]) -> None:
        if not roles:
            await self.db.delete_mute_role(guild_id=self.guild.id)
            await self.commit(interaction, "Mute role cleared. The list of muted members was cleared with it.")
            return

        role = roles[0]
        await self.db.edit_mute_config(guild_id=self.guild.id, mute_role_id=role.id)
        warning = role_warning(self.guild, role)
        if warning:
            await self.commit(interaction, f"Mute role saved, but {warning}", level=NoticeLevel.WARNING)
        else:
            await self.commit(interaction, f"Mute role set to {role.mention}.")

    async def set_moderator_roles(self, interaction: Interaction, roles: list[discord.Role]) -> None:
        await self.db.edit_moderator_config(guild_id=self.guild.id, moderator_role_ids=[role.id for role in roles])
        if not roles:
            await self.commit(interaction, "Moderator roles cleared.")
        else:
            await self.commit(interaction, f"Moderator roles: {', '.join(role.mention for role in roles)}.")
