from __future__ import annotations

from dataclasses import dataclass, field

import discord


@dataclass(frozen=True, slots=True)
class Member:
    _member: discord.Member = field(repr=False)

    def __str__(self) -> str:
        return self.name

    @property
    def id(self) -> int:
        """Get member id."""
        return self._member.id

    @property
    def name(self) -> str:
        """Get member name."""
        return self._member.name

    @property
    def mention(self) -> str:
        """Get member mention."""
        return self._member.mention

    @property
    def nick(self) -> str | None:
        """Get member nickname."""
        return self._member.nick

    @property
    def display_name(self) -> str:
        """Get member display name."""
        return self._member.display_name

    @property
    def avatar_url(self) -> str:
        """Get member avatar URL."""
        return self._member.display_avatar.url

    async def __check_perms(self, **perms: bool) -> bool:
        """Check if the bot has permissions to act on the member."""
        permissions = discord.Permissions(**perms)

        me = self._member.guild.me
        if me is None:
            return False

        return me.guild_permissions >= permissions and me.top_role > self._member.top_role

    async def kick(self, *, reason: str | None = None) -> None:
        """Kick member from guild."""
        if not await self.__check_perms(kick_members=True):
            return

        await self._member.kick(reason=reason)

    async def ban(self, *, reason: str | None = None, delete_message_days: int = discord.utils.MISSING) -> None:
        """Ban member from guild."""
        if not await self.__check_perms(ban_members=True):
            return

        await self._member.ban(reason=reason, delete_message_days=delete_message_days)

    async def unban(self, *, reason: str | None = None) -> None:
        """Unban member from guild."""
        if not await self.__check_perms(ban_members=True):
            return

        await self._member.unban(reason=reason)

    async def add_role(self, *, role: discord.Object, reason: str | None = None) -> None:
        """Add role to member."""
        if not await self.__check_perms(manage_roles=True):
            return

        await self._member.add_roles(role, reason=reason)

    async def remove_role(self, *, role: discord.Object, reason: str | None = None) -> None:
        """Remove role from member."""
        if not await self.__check_perms(manage_roles=True):
            return

        await self._member.remove_roles(role, reason=reason)
