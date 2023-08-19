from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .channel import JinjaChannel
    from .member import JinjaMember

import discord


class JinjaMessage:
    def __init__(self, *, message: discord.Message) -> None:
        self.__message = message

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

    async def delete(self, *, delay: int = 0):
        """Delete message."""
        await self.__message.delete(delay=delay)
