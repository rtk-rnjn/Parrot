from __future__ import annotations

from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from .guild import JinjaGuild
    from .message import JinjaMessage

import discord


class JinjaChannelBase:
    @overload
    def __init__(self, *, channel: discord.abc.MessageableChannel) -> None:
        ...

    @overload
    def __init__(self, *, channel: discord.abc.GuildChannel) -> None:
        ...

    def __init__(self, *, channel: discord.abc.MessageableChannel | discord.abc.GuildChannel) -> None:
        self.__channel = channel

    @property
    def id(self) -> int:
        """Get channel id."""
        return self.__channel.id

    @property
    def guild(self) -> JinjaGuild | None:
        """Get channel guild."""
        from .guild import JinjaGuild

        return JinjaGuild(guild=self.__channel.guild) if self.__channel.guild else None

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

    def _check_perms(self, **perms: bool) -> bool:
        """Check if bot has permissions to do actions on channel."""
        permissions = discord.Permissions(**perms)
        return self.__channel.permissions_for(self.__channel.guild.me) >= permissions

    async def delete(self) -> None:
        """Delete channel."""
        if not self._check_perms(manage_channels=True):
            return
        await self.__channel.delete()

    async def send(self, *args, **kwargs) -> JinjaMessage | None:
        """Send message to channel."""
        from .message import JinjaMessage

        if not self._check_perms(send_messages=True):
            return
        msg = await self.__channel.send(*args, **kwargs)  # type: ignore
        return JinjaMessage(message=msg)
