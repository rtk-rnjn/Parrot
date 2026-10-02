from __future__ import annotations

from dataclasses import dataclass

import discord

__all__ = ("Channel",)


@dataclass(frozen=True, slots=True)
class BaseChannel:
    _channel: discord.abc.MessageableChannel | discord.abc.GuildChannel

    @property
    def id(self) -> int:
        return self._channel.id

    @property
    def jump_url(self) -> str:
        return self._channel.jump_url


@dataclass(frozen=True, slots=True)
class Channel(BaseChannel):
    _channel: discord.abc.GuildChannel

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        return self._channel.name

    @property
    def mention(self) -> str:
        return self._channel.mention

    @property
    def position(self) -> int:
        return self._channel.position

    @property
    def category(self) -> Channel | None:
        category = self._channel.category
        return Channel(_channel=category) if category else None

    @property
    def type(self) -> str:
        return self._channel.type.name
