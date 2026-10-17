from __future__ import annotations

from dataclasses import dataclass, field

import discord

from .role import Role

_DANGEROUS_ROLE_PERMS = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "ban_members",
    "kick_members",
    "moderate_members",
)


@dataclass(frozen=True, slots=True)
class Member:
    _member: discord.Member = field(repr=False)

    def __str__(self) -> str:
        return self.name

    @property
    def id(self) -> int:
        return self._member.id

    @property
    def name(self) -> str:
        return self._member.name

    @property
    def mention(self) -> str:
        return self._member.mention

    @property
    def nick(self) -> str | None:
        return self._member.nick

    @property
    def display_name(self) -> str:
        return self._member.display_name

    @property
    def avatar_url(self) -> str:
        return self._member.display_avatar.url

    @property
    def roles(self) -> list[Role]:
        return [Role(_role=role) for role in self._member.roles if not role.is_default()]

    def _can_moderate_member(self, **perms: bool) -> bool:
        me = self._member.guild.me
        if me is None or self._member == self._member.guild.owner:
            return False
        required = discord.Permissions(**perms)
        return me.guild_permissions >= required and me.top_role > self._member.top_role

    def _resolve_assignable_role(self, role: Role | discord.Object | int | str) -> discord.Role | None:
        me = self._member.guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return None

        role_id = role.id if isinstance(role, (Role, discord.Object)) else int(role)
        target = self._member.guild.get_role(role_id)
        if target is None or target.is_default() or target.managed or target >= me.top_role:
            return None
        if any(getattr(target.permissions, perm, False) for perm in _DANGEROUS_ROLE_PERMS):
            return None
        return target

    async def kick(self, *, reason: str | None = None) -> None:
        if not self._can_moderate_member(kick_members=True):
            return
        await self._member.kick(reason=reason)

    async def ban(self, *, reason: str | None = None, delete_message_days: int = 0) -> None:
        if not self._can_moderate_member(ban_members=True):
            return
        seconds = max(0, min(int(delete_message_days), 7)) * 86400
        await self._member.ban(reason=reason, delete_message_seconds=seconds)

    async def add_role(self, role: Role | discord.Object | int | str, *, reason: str | None = None) -> None:
        target = self._resolve_assignable_role(role)
        if target is not None:
            await self._member.add_roles(target, reason=reason)

    async def remove_role(self, role: Role | discord.Object | int | str, *, reason: str | None = None) -> None:
        target = self._resolve_assignable_role(role)
        if target is not None:
            await self._member.remove_roles(target, reason=reason)
