from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import discord
from core import Cog

if TYPE_CHECKING:
    from core import Parrot


class _MemberJoin(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot: Parrot = bot
        self._cache: Dict[int, List[discord.Invite]] = {}

    @Cog.listener("on_member_remove")
    async def on_member_kick(self, member: discord.Member) -> None:
        RETRY = 3

        guild: discord.Guild = member.guild
        permission: discord.Permissions = guild.me.guild_permissions

        if not (permission.view_audit_log and permission.kick_members):
            return

        if self.bot.is_ws_ratelimited:
            return

        while RETRY != 0:
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.kick, limit=5):
                    if entry.target is not None and entry.target.id == member.id:
                        self.bot.dispatch("member_kick", member, entry)
                        return
            except discord.HTTPException:
                RETRY -= 1

    @Cog.listener("on_member_join")
    async def on_invite(self, member: discord.Member) -> None:
        try:
            premium: bool = self.bot.server_config[member.guild.id]["premium"]
        except KeyError:
            premium: bool = False  # type: ignore

        if not premium:
            return

        RETRY: int = 3
        DISPATCHED: bool = False

        guild = member.guild
        permission: discord.Permissions = guild.me.guild_permissions

        if not (permission.view_audit_log and permission.manage_channels):
            return

        if self.bot.is_ws_ratelimited:
            return

        new_invites: List[discord.Invite] = []

        while RETRY != 0:
            try:
                new_invites: List[discord.Invite] = await guild.invites()  # type: ignore
                break
            except discord.HTTPException:
                RETRY -= 1

        VANITY_INVITE: Optional[discord.Invite] = None

        # check if member is joined from VANITY URL
        if "VANITY_URL" in guild.features:
            VANITY_INVITE: Optional[discord.Invite] = await guild.vanity_invite()  # type: ignore

            if VANITY_INVITE is not None:
                new_invites.append(VANITY_INVITE)

                for invite in reversed(self._cache.get(guild.id, [])):
                    VANITY_USE: int = VANITY_INVITE.uses or 0
                    INVITE_USE: int = invite.uses or 0
                    if VANITY_INVITE.code == invite.code and VANITY_USE == INVITE_USE + 1:
                        self.bot.dispatch("invite", member, invite, VANITY_INVITE)
                        DISPATCHED: bool = True  # type: ignore
                        break

            self._cache[guild.id] = new_invites
            return

        # check if member is joined from normal invite
        for invite in self._cache.get(guild.id, []):
            for _invite in new_invites:
                INVITE_USE: int = invite.uses or 0  # type: ignore
                if _invite.uses == (INVITE_USE + 1):
                    self.bot.dispatch("invite", member, invite, _invite)
                    DISPATCHED: bool = True  # type: ignore
                    break

        self._cache[guild.id] = new_invites
        if not DISPATCHED:
            self.bot.dispatch("invite", member, None, None)

    @Cog.listener("on_invite_create")
    async def on_invite_create(self, invite: discord.Invite) -> None:
        guild:  Union[
            discord.Guild, discord.PartialInviteGuild, discord.Object, None
        ] = invite.guild
        if guild is None:
            return
        try:
            premium: bool = self.bot.server_config[guild.id]["premium"]
        except KeyError:
            premium: bool = False  # type: ignore

        if not premium:
            return

        self._cache.get(guild.id, []).append(invite)

    @Cog.listener("on_invite_delete")
    async def on_invite_delete(self, invite: discord.Invite) -> None:
        guild: Union[
            discord.Guild, discord.PartialInviteGuild, discord.Object, None
        ] = invite.guild
        if guild is None:
            return
        try:
            premium: bool = self.bot.server_config[guild.id]["premium"]
        except KeyError:
            premium: bool = False  # type: ignore

        if not premium:
            return

        for invite in self._cache.get(guild.id, []):
            if invite.code == invite.code:
                self._cache[guild.id].remove(invite)
                break