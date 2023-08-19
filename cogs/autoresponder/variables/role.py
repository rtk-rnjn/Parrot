from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Self

    from .guild import JinjaGuild
    from .member import JinjaMember

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

    @property
    def guild(self) -> JinjaGuild:
        """Get role guild."""
        return JinjaGuild(guild=self.__role.guild)

    @property
    def members(self) -> list[JinjaMember]:
        """Get role members."""
        return [JinjaMember(member=member) for member in self.__role.members]

    async def delete(self, *, reason: str = None):
        """Delete role."""
        if not self.__role.guild.me.guild_permissions.manage_roles:
            return
        await self.__role.delete(reason=reason)

    async def edit(
        self,
        *,
        reason: str = None,
        permissions: discord.Permissions = discord.utils.MISSING,
        color: discord.Color = discord.utils.MISSING,
        hoist: bool = discord.utils.MISSING,
        mentionable: bool = discord.utils.MISSING,
        name: str = discord.utils.MISSING,
    ) -> Self | None:
        """Edit role."""
        if not self.__role.guild.me.guild_permissions.manage_roles:
            return
        role = await self.__role.edit(
            reason=reason,
            permissions=permissions,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
            name=name,
        )
        return JinjaRole(role=role) if role else None
