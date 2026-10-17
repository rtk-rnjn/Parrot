from __future__ import annotations

from typing import TypedDict


class EventsConfig(TypedDict):
    enabled: bool
    webhook_uri: str | None


class Events(TypedDict):
    # Members
    on_member_join: EventsConfig
    on_member_leave: EventsConfig
    on_member_ban: EventsConfig
    on_member_unban: EventsConfig

    # Messages
    on_message_delete: EventsConfig
    on_message_edit: EventsConfig

    # Channels
    on_channel_delete: EventsConfig
    on_channel_create: EventsConfig
    on_channel_update: EventsConfig
    on_thread_create: EventsConfig
    on_thread_delete: EventsConfig
    on_thread_update: EventsConfig

    # Server itself
    on_server_update: EventsConfig

    # Roles
    on_role_create: EventsConfig
    on_role_delete: EventsConfig
    on_role_update: EventsConfig

    # Voice
    on_member_join_voice: EventsConfig
    on_member_leave_voice: EventsConfig
    on_member_move_voice: EventsConfig
