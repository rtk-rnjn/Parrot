from __future__ import annotations

from typing import overload

import discord


class JinjaChannelBase:
    @overload
    def __init__(self, *, channel: discord.abc.MessageableChannel) -> None: ...

    @overload
    def __init__(self, *, channel: discord.abc.GuildChannel) -> None: ...

    def __init__(self, *, channel: discord.abc.MessageableChannel | discord.abc.GuildChannel) -> None:
        self.__channel = channel

    @property
    def id(self) -> int:
        """Get channel id."""
        return self.__channel.id

    @property
    def jump_url(self) -> str:
        """Get channel jump url."""
        return self.__channel.jump_url


class JinjaChannel(JinjaChannelBase):
    def __init__(self, *, channel: discord.abc.GuildChannel) -> None:
        super().__init__(channel=channel)
        self.__channel = channel

    def __repr__(self) -> str:
        return f"<JinjaChannel id={self.id} name={self.name} type={self.type}>"

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        """Get channel name."""
        return self.__channel.name

    @property
    def mention(self) -> str:
        """Get channel mention."""
        return self.__channel.mention

    @property
    def position(self) -> int:
        """Get channel position."""
        return self.__channel.position

    @property
    def category(self) -> JinjaChannel | None:
        """Get channel category."""
        return JinjaChannel(channel=self.__channel.category) if self.__channel.category else None

    @property
    def type(self) -> str:
        """Get channel type."""
        return self.__channel.type.name
