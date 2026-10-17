from __future__ import annotations

import discord

from .base import Interaction, NoticeLevel, Page, PageModal, channel_text, preview, role_text, role_warning, status_text

__all__ = ("WelcomePage",)

MESSAGE_MAX_LENGTH = 800
PLACEHOLDERS = "`$member_mention` `$member_name` `$member_display_name` `$server_name` `$count`"


class WelcomeMessagesModal(PageModal):
    def __init__(self, page: WelcomePage) -> None:
        super().__init__(page, title="Welcome and leave messages")
        welcome = page.config["welcome_config"]

        self.join_input = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            placeholder="Welcome $member_mention to $server_name! You are member #$count.",
            default=welcome.get("on_member_join_message") or None,
            required=False,
            max_length=MESSAGE_MAX_LENGTH,
        )
        self.leave_input = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            placeholder="$member_name has left $server_name.",
            default=welcome.get("on_member_leave_message") or None,
            required=False,
            max_length=MESSAGE_MAX_LENGTH,
        )
        self.add_item(discord.ui.Label(text="Join message", description="Leave blank to send nothing when someone joins.", component=self.join_input))
        self.add_item(
            discord.ui.Label(text="Leave message", description="Leave blank to send nothing when someone leaves.", component=self.leave_input)
        )
        self.add_item(discord.ui.TextDisplay(f"-# Placeholders: {PLACEHOLDERS}"))

    async def on_submit(self, interaction: Interaction) -> None:
        await self.page.db.edit_welcome_config(
            guild_id=self.page.guild.id,
            on_member_join_message=self.join_input.value.strip() or None,
            on_member_leave_message=self.leave_input.value.strip() or None,
        )
        await self.page.commit(interaction, "Welcome and leave messages updated.")


class WelcomePage(Page):
    key = "welcome"
    label = "Welcome & Leave"
    emoji = "\N{WAVING HAND SIGN}"
    description = "Greet new members, give them a starting role, and say goodbye when they leave."
    section = "welcome_config"

    @property
    def enabled(self) -> bool:
        return bool(self.config["welcome_config"].get("enabled"))

    def summary(self) -> str:
        welcome = self.config["welcome_config"]
        text = status_text(self.enabled)
        if welcome.get("on_member_join_channel_id"):
            text += f" \N{MIDDLE DOT} greets in {channel_text(self.guild, welcome['on_member_join_channel_id'])}"
        return text

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if self.enabled else discord.Colour.dark_grey()

    def build(self) -> list[discord.ui.Item]:
        welcome = self.config["welcome_config"]
        join_role_id = welcome.get("on_member_join_role_id")
        return [
            self.status(
                [
                    ("Status", status_text(self.enabled)),
                    ("Join channel", channel_text(self.guild, welcome.get("on_member_join_channel_id"))),
                    ("Join message", preview(welcome.get("on_member_join_message"))),
                    ("Join role", role_text(self.guild, welcome.get("on_member_join_role_id"))),
                    ("Leave channel", channel_text(self.guild, welcome.get("on_member_leave_channel_id"))),
                    ("Leave message", preview(welcome.get("on_member_leave_message"))),
                ]
            ),
            self.text(f"-# Message placeholders: {PLACEHOLDERS}"),
            self.row(
                self.toggle(self.enabled, self.set_enabled),
                self.button("Edit messages\N{HORIZONTAL ELLIPSIS}", self.open_messages_modal, style=discord.ButtonStyle.primary, emoji="\N{PENCIL}"),
                self.reset_button(),
            ),
            self.row(
                self.channel_select(
                    "Join message channel\N{HORIZONTAL ELLIPSIS}", self.set_join_channel, current=welcome.get("on_member_join_channel_id")
                )
            ),
            self.row(
                self.role_select(
                    "Role given on join\N{HORIZONTAL ELLIPSIS}",
                    self.set_join_role,
                    current=[join_role_id] if join_role_id else (),
                )
            ),
            self.row(
                self.channel_select(
                    "Leave message channel\N{HORIZONTAL ELLIPSIS}", self.set_leave_channel, current=welcome.get("on_member_leave_channel_id")
                )
            ),
        ]

    async def open_messages_modal(self, interaction: Interaction) -> None:
        await interaction.response.send_modal(WelcomeMessagesModal(self))

    async def set_enabled(self, interaction: Interaction, enabled: bool) -> None:
        await self.db.edit_welcome_config(guild_id=self.guild.id, enabled=enabled)
        if not enabled:
            await self.commit(interaction, "Welcome and leave messages disabled.")
            return

        welcome = self.config["welcome_config"]
        configured = any(welcome.get(field) for field in ("on_member_join_channel_id", "on_member_join_role_id", "on_member_leave_channel_id"))
        if configured:
            await self.commit(interaction, "Welcome and leave messages enabled.")
        else:
            await self.commit(interaction, "Enabled, but nothing is set up yet. Pick a channel or a join role below.", level=NoticeLevel.WARNING)

    async def set_join_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        await self.db.edit_welcome_config(guild_id=self.guild.id, on_member_join_channel_id=channel_id)
        await self.commit(
            interaction, "Join channel cleared." if channel_id is None else f"Join messages go to {channel_text(self.guild, channel_id)}."
        )

    async def set_leave_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        await self.db.edit_welcome_config(guild_id=self.guild.id, on_member_leave_channel_id=channel_id)
        await self.commit(
            interaction, "Leave channel cleared." if channel_id is None else f"Leave messages go to {channel_text(self.guild, channel_id)}."
        )

    async def set_join_role(self, interaction: Interaction, roles: list[discord.Role]) -> None:
        role = roles[0] if roles else None
        await self.db.edit_welcome_config(guild_id=self.guild.id, on_member_join_role_id=role.id if role else None)
        if role is None:
            await self.commit(interaction, "Join role cleared.")
            return

        warning = role_warning(self.guild, role)
        if warning:
            await self.commit(interaction, f"Join role saved, but {warning}", level=NoticeLevel.WARNING)
        else:
            await self.commit(interaction, f"New members will receive {role.mention}.")
