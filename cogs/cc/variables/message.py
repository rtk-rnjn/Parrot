from __future__ import annotations

from dataclasses import dataclass, field

import discord


@dataclass(frozen=True, slots=True)
class Message:
    _message: discord.Message = field(repr=False)

    @property
    def id(self) -> int:
        """Get message id."""
        return self._message.id

    @property
    def content(self) -> str:
        """Get message content."""
        return self._message.content
