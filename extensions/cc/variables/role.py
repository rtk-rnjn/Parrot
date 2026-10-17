from __future__ import annotations

from dataclasses import dataclass, field

import discord


@dataclass(frozen=True, slots=True)
class Role:
    _role: discord.Role = field(repr=False)

    @property
    def id(self) -> int:
        """Get role id."""
        return self._role.id

    @property
    def name(self) -> str:
        """Get role name."""
        return self._role.name

    @property
    def mention(self) -> str:
        """Get role mention."""
        return self._role.mention

    @property
    def color(self) -> discord.Colour:
        """Get role color."""
        return self._role.color

    @property
    def position(self) -> int:
        """Get role position."""
        return self._role.position

    @property
    def hoist(self) -> bool:
        """Get role hoist."""
        return self._role.hoist

    @property
    def managed(self) -> bool:
        """Get role managed."""
        return self._role.managed

    @property
    def mentionable(self) -> bool:
        """Get role mentionable."""
        return self._role.mentionable

    @property
    def permissions(self) -> discord.Permissions:
        """Get role permissions."""
        return self._role.permissions
