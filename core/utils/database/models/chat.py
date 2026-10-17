from __future__ import annotations

from typing import TypedDict


class GlobalChatConfig(TypedDict):
    enabled: bool
    channel_id: int | None
    webhook_uri: str | None


class TelephoneConfig(TypedDict):
    enabled: bool
    channel_id: int | None
    blocked_servers: list[int]


class TicketConfig(TypedDict):
    enabled: bool
    channel_id: int | None

    bot_message_id: int | None
    bot_channel_channel_id: int | None
