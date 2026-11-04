from __future__ import annotations

import asyncio
import ipaddress
import string
from typing import Literal
from urllib.parse import urlparse

import discord

from .base import Interaction, NoticeLevel, Page, PageModal, channel_text, preview, role_text, role_warning, status_text

__all__ = ("WelcomePage",)

MESSAGE_MAX_LENGTH = 800
BANNER_URL_MAX_LENGTH = 512
PLACEHOLDERS = "`$member_mention` `$member_name` `$member_display_name` `$server_name` `$count`"

# value -> (label, description, emoji)
STYLES: dict[str, tuple[str, str, str]] = {
    "text": ("Plain text", "Just the message, no embed.", "\N{SPEECH BALLOON}"),
    "embed": ("Embed", "The message in a clean embed with the member's avatar.", "\N{CLIPBOARD}"),
    "card": ("Banner card", "An embed with a generated welcome image.", "\N{FRAME WITH PICTURE}\N{VARIATION SELECTOR-16}"),
}

WelcomeStyle = Literal["text", "embed", "card"]


def parse_color(raw: str) -> int | None:
    """Parse ``#RRGGBB`` / ``RRGGBB`` / ``#RGB`` / ``0xRRGGBB``. Blank means "use the default"."""
    value = raw.strip().removeprefix("#").removeprefix("0x")
    if not value:
        return None
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    if len(value) != 6 or any(char not in string.hexdigits for char in value):
        msg = "Accent color must be a hex code like `#5865F2`."
        raise ValueError(msg)
    return int(value, 16)


def parse_banner_url(raw: str) -> str | None:
    """Validate a banner image URL. Blank means "use the generated gradient"."""
    value = raw.strip()
    if not value:
        return None

    parsed = urlparse(value)
    host = parsed.hostname
    if parsed.scheme != "https" or not host or " " in value:
        msg = "Banner must be a direct `https://` image link."
        raise ValueError(msg)
    if "." not in host:
        msg = "Banner link must point to a public website."
        raise ValueError(msg)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass  # a normal hostname
    else:
        msg = "Banner link must use a domain name, not an IP address."
        raise ValueError(msg)
    return value


def _style_select(current: str) -> discord.ui.Select:
    return discord.ui.Select(
        options=[
            discord.SelectOption(label=label, value=value, description=description, emoji=emoji, default=value == current)
            for value, (label, description, emoji) in STYLES.items()
        ],
    )


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


class WelcomeAppearanceModal(PageModal):
    def __init__(self, page: WelcomePage) -> None:
        super().__init__(page, title="Welcome appearance")
        welcome = page.config["welcome_config"]
        color = welcome.get("accent_color")

        self.join_style = _style_select(page.join_style)
        self.leave_style = _style_select(page.leave_style)
        self.color_input = discord.ui.TextInput(
            placeholder="#5865F2",
            default=f"#{color:06X}" if color is not None else None,
            required=False,
            max_length=8,
        )
        self.banner_input = discord.ui.TextInput(
            placeholder="https://example.com/banner.png",
            default=welcome.get("banner_url") or None,
            required=False,
            max_length=BANNER_URL_MAX_LENGTH,
        )
        self.add_item(discord.ui.Label(text="Join style", description="How new members are greeted.", component=self.join_style))
        self.add_item(discord.ui.Label(text="Leave style", description="How departures are announced.", component=self.leave_style))
        self.add_item(
            discord.ui.Label(
                text="Accent color",
                description="Used on join messages. Leave messages stay red. Blank = Discord blurple.",
                component=self.color_input,
            )
        )
        self.add_item(
            discord.ui.Label(
                text="Banner background", description="Optional image behind the card. Blank = generated gradient.", component=self.banner_input
            )
        )

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            color = parse_color(self.color_input.value)
            banner = parse_banner_url(self.banner_input.value)
        except ValueError as exc:
            await self.page.commit(interaction, f"{exc} Nothing was changed.", level=NoticeLevel.ERROR)
            return

        join_style = self.join_style.values[0]
        leave_style = self.leave_style.values[0]
        await self.page.db.edit_welcome_config(
            guild_id=self.page.guild.id,
            on_member_join_style=join_style,
            on_member_leave_style=leave_style,
            accent_color=color,
            banner_url=banner,
        )

        if banner is not None and "card" not in (join_style, leave_style):
            await self.page.commit(
                interaction,
                "Appearance saved, but the banner is only used by the \N{LEFT DOUBLE QUOTATION MARK}Banner card\N{RIGHT DOUBLE QUOTATION MARK} style.",
                level=NoticeLevel.WARNING,
            )
            return
        await self.page.commit(interaction, "Welcome appearance updated.")


class WelcomePage(Page):
    key = "welcome"
    label = "Welcome & Leave"
    emoji = "\N{WAVING HAND SIGN}"
    description = "Greet new members, give them a starting role, and say goodbye when they leave."
    section = "welcome_config"

    join_style: WelcomeStyle
    leave_style: WelcomeStyle

    async def prepare(self) -> None:
        # The DB getters apply the default style, so it is defined in exactly one place.
        self.join_style, self.leave_style = await asyncio.gather(
            self.db.get_welcome_join_style(self.guild.id),
            self.db.get_welcome_leave_style(self.guild.id),
        )

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
        color = welcome.get("accent_color")
        banner = welcome.get("banner_url")
        return [
            self.status(
                [
                    ("Status", status_text(self.enabled)),
                    ("Join channel", channel_text(self.guild, welcome.get("on_member_join_channel_id"))),
                    ("Join message", preview(welcome.get("on_member_join_message"))),
                    ("Join role", role_text(self.guild, welcome.get("on_member_join_role_id"))),
                    ("Leave channel", channel_text(self.guild, welcome.get("on_member_leave_channel_id"))),
                    ("Leave message", preview(welcome.get("on_member_leave_message"))),
                    ("Join style", STYLES[self.join_style][0]),
                    ("Leave style", STYLES[self.leave_style][0]),
                    ("Accent color", f"`#{color:06X}`" if color is not None else "*Default*"),
                    ("Banner background", f"[Custom image](<{banner}>)" if banner else "*Generated gradient*"),
                ]
            ),
            self.text(f"-# Message placeholders: {PLACEHOLDERS}"),
            self.row(
                self.toggle(self.enabled, self.set_enabled),
                self.button("Edit messages\N{HORIZONTAL ELLIPSIS}", self.open_messages_modal, style=discord.ButtonStyle.primary, emoji="\N{PENCIL}"),
                self.button(
                    "Appearance\N{HORIZONTAL ELLIPSIS}", self.open_appearance_modal, style=discord.ButtonStyle.primary, emoji="\N{ARTIST PALETTE}"
                ),
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
                    current=[welcome["on_member_join_role_id"]] if welcome.get("on_member_join_role_id") else [],
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

    async def open_appearance_modal(self, interaction: Interaction) -> None:
        await interaction.response.send_modal(WelcomeAppearanceModal(self))

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
