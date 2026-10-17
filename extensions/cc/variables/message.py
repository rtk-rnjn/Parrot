from __future__ import annotations

from dataclasses import dataclass, field

import discord


@dataclass(frozen=True, slots=True)
class Message:
    _message: discord.Message = field(repr=False)

    @property
    def id(self) -> int:
        return self._message.id

    @property
    def content(self) -> str:
        return self._message.content

    async def add_reaction(self, emoji: str) -> None:
        if self._message.channel.permissions_for(self._message.guild.me).add_reactions:  # pyright: ignore[reportOptionalMemberAccess]
            await self._message.add_reaction(str(emoji).strip())
