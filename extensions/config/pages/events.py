from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from core.utils.database import EVENT_NAMES

from .base import NOT_SET, Interaction, NoticeLevel, Page, channel_text, status_text
from .webhooks import can_manage_webhooks, create_webhook, delete_webhook, resolve_webhook_channels

if TYPE_CHECKING:
    from core.utils.database.guild.events import EVENT_NAME

    from ..dashboard import ConfigDashboard

__all__ = ("EventsPage",)

WEBHOOK_NAME = "Parrot Event Logs"
ON = "\N{LARGE GREEN CIRCLE}"
OFF = "\N{MEDIUM WHITE CIRCLE}"
OPTION_DESCRIPTION_LENGTH = 100

EVENT_INFO: dict[str, tuple[str, str, str]] = {
    "on_member_join": ("Members", "Member joined", "A member joins the server."),
    "on_member_leave": ("Members", "Member left", "A member leaves or is kicked. Bans trigger this as well."),
    "on_member_ban": ("Members", "Member banned", "A member is banned from the server."),
    "on_member_unban": ("Members", "Member unbanned", "A ban is lifted."),
    "on_message_delete": ("Messages", "Message deleted", "A message is deleted. Bot messages are not tracked."),
    "on_message_edit": ("Messages", "Message edited", "The content of a message changes. Bot messages are not tracked."),
    "on_channel_create": ("Channels", "Channel created", "A channel is created."),
    "on_channel_delete": ("Channels", "Channel deleted", "A channel is deleted."),
    "on_channel_update": ("Channels", "Channel updated", "A channel's name, topic or settings change."),
    "on_thread_create": ("Threads", "Thread created", "A thread is created."),
    "on_thread_delete": ("Threads", "Thread deleted", "A thread is deleted."),
    "on_thread_update": ("Threads", "Thread updated", "A thread is renamed, archived or otherwise changed."),
    "on_server_update": ("Server", "Server updated", "The server's name, icon or settings change."),
    "on_role_create": ("Roles", "Role created", "A role is created."),
    "on_role_delete": ("Roles", "Role deleted", "A role is deleted."),
    "on_role_update": ("Roles", "Role updated", "A role's name, colour or permissions change."),
    "on_member_join_voice": ("Voice", "Joined voice", "A member joins a voice channel. Bots are not tracked."),
    "on_member_leave_voice": ("Voice", "Left voice", "A member leaves a voice channel. Bots are not tracked."),
    "on_member_move_voice": ("Voice", "Moved voice", "A member moves between voice channels. Bots are not tracked."),
}
GROUP_ORDER = ("Members", "Messages", "Channels", "Threads", "Server", "Roles", "Voice")


def event_label(name: str) -> str:
    return EVENT_INFO[name][1] if name in EVENT_INFO else name.removeprefix("on_").replace("_", " ").capitalize()


class EventsPage(Page):
    key = "events"
    label = "Event Logs"
    emoji = "\N{SCROLL}"
    description = "Send server activity to log channels through webhooks. Each event can go to its own channel, or all of them to one."
    section = "events"

    def __init__(self, dashboard: ConfigDashboard) -> None:
        super().__init__(dashboard)
        self.selected: EVENT_NAME | None = None
        self._channels: dict[str, int | None] | None = {}

    def _event(self, name: str) -> dict:
        return self.config["events"].get(name) or {}

    def is_enabled(self, name: str) -> bool:
        return bool(self._event(name).get("enabled"))

    def uri(self, name: str) -> str | None:
        return self._event(name).get("webhook_uri")

    def _all_uris(self) -> set[str]:
        return {uri for name in EVENT_NAMES if (uri := self.uri(name))}

    async def prepare(self) -> None:
        self._channels = await resolve_webhook_channels(self.guild, self._all_uris())

    def destination_text(self, name: str) -> str:
        uri = self.uri(name)
        if uri is None:
            return NOT_SET
        if self._channels is None:
            return "Webhook configured"
        channel_id = self._channels.get(uri)
        if channel_id is None:
            return "\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Webhook was deleted \N{MIDDLE DOT} pick the channel again"
        return channel_text(self.guild, channel_id)

    def _uri_for_channel(self, channel_id: int) -> str | None:
        """Reuse a webhook that already posts to ``channel_id`` instead of creating another."""
        if not self._channels:
            return None
        return next((uri for uri, existing in self._channels.items() if existing == channel_id), None)

    def summary(self) -> str:
        enabled = sum(self.is_enabled(name) for name in EVENT_NAMES)
        return f"{enabled} of {len(EVENT_NAMES)} events logged" if enabled else "nothing logged"

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if any(self.is_enabled(name) for name in EVENT_NAMES) else discord.Colour.dark_grey()

    def reset_summary(self) -> str:
        return "every event (all are turned off and their webhooks deleted)"

    def _overview_text(self) -> str:
        lines = []
        for group in GROUP_ORDER:
            names = [name for name in EVENT_NAMES if EVENT_INFO.get(name, ("",))[0] == group]
            entries = " \N{MIDDLE DOT} ".join(f"{ON if self.is_enabled(name) else OFF} {event_label(name)}" for name in names)
            lines.append(f"**{group}** - {entries}")
        return "\n".join(lines)

    def _event_options(self) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label=event_label(name),
                value=name,
                description=EVENT_INFO[name][2][:OPTION_DESCRIPTION_LENGTH] if name in EVENT_INFO else None,
                emoji=ON if self.is_enabled(name) else OFF,
                default=name == self.selected,
            )
            for name in EVENT_NAMES
        ]

    def build(self) -> list[discord.ui.Item]:
        items: list[discord.ui.Item] = [
            self.text(self._overview_text()),
            self.row(self.string_select("Choose an event to configure\N{HORIZONTAL ELLIPSIS}", self._event_options(), self.select_event)),
        ]

        name = self.selected
        if name is None:
            items.append(self.text("-# Pick an event above to change where it is logged."))
        else:
            enabled = self.is_enabled(name)
            items.extend(
                [
                    self.text(
                        f"### {event_label(name)}\n-# {EVENT_INFO[name][2] if name in EVENT_INFO else ''}\n"
                        f"**Status**: {status_text(enabled)}\n**Logged in**: {self.destination_text(name)}"
                    ),
                    self.row(
                        self.toggle(enabled, self.set_selected_enabled),
                        self.button(
                            "Stop logging", self.clear_selected, emoji="\N{WASTEBASKET}\N{VARIATION SELECTOR-16}", disabled=self.uri(name) is None
                        ),
                    ),
                    self.row(self.channel_select(f"Log {event_label(name).lower()} in\N{HORIZONTAL ELLIPSIS}", self.set_selected_channel)),
                ]
            )

        items.extend(
            [
                discord.ui.Separator(),
                self.text("### Every event at once\n-# Bot needs **Manage Webhooks** in the channel you pick."),
                self.row(self.channel_select("Log every event in\N{HORIZONTAL ELLIPSIS}", self.set_all_channel)),
                self.row(
                    self.button("Enable all", self.enable_all, style=discord.ButtonStyle.success),
                    self.button("Disable all", self.disable_all),
                    self.reset_button(),
                ),
            ]
        )
        return items

    async def select_event(self, interaction: Interaction, values: list[str]) -> None:
        self.selected = values[0] if values and values[0] in EVENT_NAMES else None
        await self.commit(interaction)

    async def set_selected_enabled(self, interaction: Interaction, enabled: bool) -> None:
        name = self.selected
        if name is None:
            await self.commit(interaction, "Pick an event first.", level=NoticeLevel.ERROR)
            return
        if enabled and self.uri(name) is None:
            await self.commit(interaction, f"Pick a channel for **{event_label(name)}** first, then enable it.", level=NoticeLevel.ERROR)
            return

        await self.db.edit_event(self.guild.id, event_name=name, enabled=enabled)
        await self.commit(interaction, f"**{event_label(name)}** is now {'logged' if enabled else 'ignored'}.")

    async def set_selected_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        if self.selected is None:
            await self.commit(interaction, "Pick an event first.", level=NoticeLevel.ERROR)
            return
        await self._assign([self.selected], channel_ids[0] if channel_ids else None, interaction)

    async def clear_selected(self, interaction: Interaction) -> None:
        if self.selected is None:
            await self.commit(interaction, "Pick an event first.", level=NoticeLevel.ERROR)
            return
        await self._assign([self.selected], None, interaction)

    async def set_all_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        await self._assign(list(EVENT_NAMES), channel_ids[0] if channel_ids else None, interaction)

    async def enable_all(self, interaction: Interaction) -> None:
        names: list[EVENT_NAME] = [name for name in EVENT_NAMES if self.uri(name)]
        if not names:
            await self.commit(interaction, "No event has a channel yet. Pick one with **Log every event in** below.", level=NoticeLevel.ERROR)
            return
        await self.db.edit_events(self.guild.id, event_names=names, enabled=True)
        skipped = len(EVENT_NAMES) - len(names)
        note = f" {skipped} without a channel stayed off." if skipped else ""
        await self.commit(interaction, f"Enabled {len(names)} event{'' if len(names) == 1 else 's'}.{note}")

    async def disable_all(self, interaction: Interaction) -> None:
        await self.db.edit_events(self.guild.id, event_names=EVENT_NAMES, enabled=False)
        await self.commit(interaction, "All event logging disabled. Channels are remembered so you can enable them again.")

    async def _assign(self, names: list[EVENT_NAME], channel_id: int | None, interaction: Interaction) -> None:
        await self.dashboard.acknowledge(interaction)
        labels = event_label(names[0]) if len(names) == 1 else f"{len(names)} events"
        previous = {uri for name in names if (uri := self.uri(name))}

        if channel_id is None:
            await self.db.edit_events(self.guild.id, event_names=names, enabled=False, webhook_uri=None)
            await self._release(previous)
            await self.commit(interaction, f"**{labels}** no longer logged.")
            return

        channel = self.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await self.commit(interaction, "Logs need a regular text channel.", level=NoticeLevel.ERROR)
            return

        uri = self._uri_for_channel(channel.id)
        if uri is None:
            if not can_manage_webhooks(channel):
                await self.commit(interaction, f"Bot needs **Manage Webhooks** in {channel.mention} to log there.", level=NoticeLevel.ERROR)
                return
            try:
                uri = (await create_webhook(self.bot, channel, name=WEBHOOK_NAME)).url
            except discord.HTTPException as error:
                await self.commit(
                    interaction, f"Discord refused to create a webhook in {channel.mention}: {error.text or error.status}", level=NoticeLevel.ERROR
                )
                return

        await self.db.edit_events(self.guild.id, event_names=names, enabled=True, webhook_uri=uri)
        await self._release(previous - {uri})
        await self.commit(interaction, f"**{labels}** will be logged in {channel.mention}.")

    async def _release(self, candidates: set[str]) -> None:
        """Delete webhooks that no event (and not global chat) references any more."""
        if not candidates:
            return
        await self.dashboard.reload()
        still_used = self._all_uris() | {self.config["global_chat_config"].get("webhook_uri")}
        for uri in candidates - still_used:
            await delete_webhook(self.bot, uri)

    async def reset(self) -> None:
        previous = self._all_uris()
        await super().reset()
        self.selected = None
        await self._release(previous)
