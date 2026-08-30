from __future__ import annotations

import discord


class JinjaRole:
    def __init__(self, *, role: discord.Role) -> None:
        self.__role = role

    @property
    def id(self) -> int:
        """Get role id."""
        return self.__role.id

    @property
    def name(self) -> str:
        """Get role name."""
        return self.__role.name

    @property
    def mention(self) -> str:
        """Get role mention."""
        return self.__role.mention

    @property
    def color(self) -> discord.Colour:
        """Get role color."""
        return self.__role.color

    @property
    def position(self) -> int:
        """Get role position."""
        return self.__role.position

    @property
    def hoist(self) -> bool:
        """Get role hoist."""
        return self.__role.hoist

    @property
    def managed(self) -> bool:
        """Get role managed."""
        return self.__role.managed

    @property
    def mentionable(self) -> bool:
        """Get role mentionable."""
        return self.__role.mentionable

    @property
    def permissions(self) -> discord.Permissions:
        """Get role permissions."""
        return self.__role.permissions
