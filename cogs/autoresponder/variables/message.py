from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .channel import JinjaChannel
    from .guild import JinjaGuild
    from .member import JinjaMember

import discord


class JinjaMessage:
    def __init__(self, *, message: discord.Message) -> None:
        self.__message = message

    def __repr__(self) -> str:
        return f"<JinjaMessage {self.__message.jump_url}>"

    @property
    def id(self):
        """Get message id."""
        return self.__message.id

    @property
    def content(self):
        """Get message content."""
        return self.__message.content

    @property
    def author(self):
        """Get message author."""
        return JinjaMember(member=self.__message.author)

    @property
    def channel(self):
        """Get message channel."""
        return JinjaChannel(channel=self.__message.channel)  # type: ignore

    @property
    def guild(self) -> JinjaGuild:
        """Get message guild."""
        from .guild import JinjaGuild

        return JinjaGuild(guild=self.__message.guild)  # type: ignore

    def _has_perms(self, **perms: bool) -> bool:
        """Check if bot has permissions to do actions on message."""
        permissions = discord.Permissions(**perms)
        return (
            self.__message.guild.me.guild_permissions >= permissions  # type: ignore
            and self.__message.guild.me.top_role > self.__message.author.top_role  # type: ignore
        )

    async def delete(self, *, delay: int = 0):
        """Delete message."""
        if not self._has_perms(manage_messages=True):
            return
        await self.__message.delete(delay=delay)

    async def pin(self):
        """Pin message."""
        if not self._has_perms(manage_messages=True):
            return
        await self.__message.pin()
