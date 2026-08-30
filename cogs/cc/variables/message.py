from __future__ import annotations

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
