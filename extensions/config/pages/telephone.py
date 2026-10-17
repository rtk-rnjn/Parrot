from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from .base import NOT_SET, Interaction, NoticeLevel, Page, PageModal, channel_text, status_text

if TYPE_CHECKING:
    from core import Bot

__all__ = ("TelephonePage",)

MAX_LISTED_BLOCKED = 10
MAX_SELECT_OPTIONS = 25
SNOWFLAKE_MIN_LENGTH = 15
SNOWFLAKE_MAX_LENGTH = 22


class BlockServerModal(PageModal):
    def __init__(self, page: TelephonePage) -> None:
        super().__init__(page, title="Block a server")
        self.server_input = discord.ui.TextInput(placeholder="123456789012345678", min_length=SNOWFLAKE_MIN_LENGTH, max_length=SNOWFLAKE_MAX_LENGTH)
        self.add_item(
            discord.ui.Label(
                text="Server ID",
                description="The blocked server can no longer call this one. Enable Developer Mode in Discord to copy server IDs.",
                component=self.server_input,
            )
        )

    async def on_submit(self, interaction: Interaction) -> None:
        raw = self.server_input.value.strip()
        if not raw.isdigit():
            await self.page.commit(interaction, "A server ID is a number, such as `123456789012345678`.", level=NoticeLevel.ERROR)
            return

        server_id = int(raw)
        if server_id == self.page.guild.id:
            await self.page.commit(interaction, "You cannot block your own server.", level=NoticeLevel.ERROR)
            return

        await self.page.db.add_telephone_blocked_server(guild_id=self.page.guild.id, server_id=server_id)
        await self.page.commit(interaction, f"Blocked {server_label(self.page.bot, server_id)}.")


def server_label(bot: Bot, server_id: int) -> str:
    """Name the server if the bot is in it, otherwise fall back to its id."""
    guild = bot.get_guild(server_id)
    return f"**{discord.utils.escape_markdown(guild.name)}**" if guild is not None else f"server `{server_id}`"


class TelephonePage(Page):
    key = "telephone"
    label = "Telephone"
    emoji = "\N{BLACK TELEPHONE}\N{VARIATION SELECTOR-16}"
    description = "Let members chat with another server through a shared channel, and keep unwanted callers out."
    section = "telephone_config"

    @property
    def enabled(self) -> bool:
        return bool(self.config["telephone_config"].get("enabled"))

    @property
    def channel_id(self) -> int | None:
        return self.config["telephone_config"].get("channel_id")

    @property
    def blocked(self) -> list[int]:
        return [int(server_id) for server_id in self.config["telephone_config"].get("blocked_servers") or []]

    def summary(self) -> str:
        text = status_text(self.enabled)
        if self.channel_id:
            text += f" \N{MIDDLE DOT} line in {channel_text(self.guild, self.channel_id)}"
        if self.blocked:
            text += f" \N{MIDDLE DOT} {len(self.blocked)} blocked"
        return text

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if self.enabled else discord.Colour.dark_grey()

    def reset_summary(self) -> str:
        return "the telephone toggle, channel and block list"

    def _blocked_text(self) -> str:
        blocked = self.blocked
        if not blocked:
            return NOT_SET
        lines = [server_label(self.bot, server_id) for server_id in blocked[:MAX_LISTED_BLOCKED]]
        hidden = len(blocked) - MAX_LISTED_BLOCKED
        if hidden > 0:
            lines.append(f"-# and {hidden} more")
        return "\n".join(lines)

    def _unblock_options(self) -> list[discord.SelectOption]:
        options = []
        for server_id in self.blocked[:MAX_SELECT_OPTIONS]:
            guild = self.bot.get_guild(server_id)
            options.append(
                discord.SelectOption(label=guild.name[:100] if guild else f"Server {server_id}", value=str(server_id), description=str(server_id))
            )
        return options

    def build(self) -> list[discord.ui.Item]:
        options = self._unblock_options()
        return [
            self.status([("Status", status_text(self.enabled)), ("Telephone channel", channel_text(self.guild, self.channel_id))]),
            self.text(f"### Blocked servers\n{self._blocked_text()}"),
            self.row(
                self.toggle(self.enabled, self.set_enabled),
                self.button("Block a server\N{HORIZONTAL ELLIPSIS}", self.open_block_modal, emoji="\N{NO ENTRY SIGN}"),
                self.reset_button(),
            ),
            self.row(self.channel_select("Telephone channel\N{HORIZONTAL ELLIPSIS}", self.set_channel, current=self.channel_id)),
            self.row(
                self.string_select(
                    "Unblock servers\N{HORIZONTAL ELLIPSIS}" if options else "No blocked servers",
                    options or [discord.SelectOption(label="Nothing to unblock", value="none")],
                    self.unblock,
                    max_values=len(options),
                    disabled=not options,
                )
            ),
        ]

    async def set_enabled(self, interaction: Interaction, enabled: bool) -> None:
        if enabled and self.channel_id is None:
            await self.commit(interaction, "Pick a telephone channel first, then enable it.", level=NoticeLevel.ERROR)
            return
        await self.db.edit_telephone_config(guild_id=self.guild.id, enabled=enabled)
        await self.commit(interaction, "Telephone enabled. Other servers can now call." if enabled else "Telephone disabled.")

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        if channel_id is None:
            await self.db.edit_telephone_config(guild_id=self.guild.id, enabled=False, channel_id=None)
            await self.commit(interaction, "Telephone channel cleared and the line disabled.")
            return

        await self.db.edit_telephone_config(guild_id=self.guild.id, channel_id=channel_id)
        hint = "" if self.enabled else " Press Enable to open the line."
        await self.commit(interaction, f"Calls will come through {channel_text(self.guild, channel_id)}.{hint}")

    async def open_block_modal(self, interaction: Interaction) -> None:
        await interaction.response.send_modal(BlockServerModal(self))

    async def unblock(self, interaction: Interaction, values: list[str]) -> None:
        server_ids = [int(value) for value in values if value.isdigit()]
        for server_id in server_ids:
            await self.db.remove_telephone_blocked_server(guild_id=self.guild.id, server_id=server_id)
        names = ", ".join(server_label(self.bot, server_id) for server_id in server_ids)
        await self.commit(interaction, f"Unblocked {names}." if names else "Nothing was unblocked.")
