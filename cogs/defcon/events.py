from __future__ import annotations

from typing import Optional, Union

import discord
from core import Cog, Parrot

from .settings import DEFCON_SETTINGS


class DefconListeners(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.settings = bot.guild_configurations_cache

    async def defcon_broadcast(self, message: Union[str, discord.Embed], *, guild: discord.Guild, level: int) -> None:
        if "broadcast" not in self.settings[guild.id]["default_defcon"]:
            return

        if not self.settings[guild.id]["default_defcon"]["broadcast"]["enabled"]:
            return

        channel = guild.get_channel(self.settings[guild.id]["default_defcon"]["broadcast"]["channel"])
        if not channel:
            return

        if isinstance(message, str):
            embed = discord.Embed(title=f"DEFCON {level}", description=message, color=discord.Color.red())
            embed.set_footer(text="DEFCON is active")
        else:
            embed = message
        await self.bot.wait_until_ready()
        await channel.send(embed=embed)  # type: ignore

    async def defcon_on_member_join(self, member: discord.Member, level: int) -> None:
        settings = DEFCON_SETTINGS[level]["SETTINGS"]
        if settings.get("ALLOW_SERVER_JOIN", True):
            return

        try:
            await member.kick(reason=f"DEFCON is active and does not allow server joins. LEVEL {level}")
        except discord.Forbidden:
            pass
        else:
            joined_at = discord.utils.format_dt(member.joined_at or discord.utils.utcnow(), style="R")
            await self.defcon_broadcast(
                f"{member.mention} - **{member}** (`{member.id}`) has joined the server ({joined_at}) and was kicked for DEFCON level {level}",
                guild=member.guild,
                level=level,
            )

    async def defcon_on_invite_create(self, invite: discord.Invite, level: int) -> None:
        if invite.guild is None:
            return

        settings = DEFCON_SETTINGS[level]["SETTINGS"]
        if settings.get("ALLOW_INVITE_CREATE", True):
            return

        trustables = self.settings[invite.guild.id]["default_defcon"].get("trustables", {})
        if trusted_roles := trustables.get("roles", []):
            for role in getattr(invite.inviter, "roles", []):
                if role.id in trusted_roles:
                    return

        if trusted_users := trustables.get("members", []):
            if getattr(invite.inviter, "id", 0) in trusted_users:
                return

        if (
            not trustables.get("members_with_admin", True)
            and getattr(invite.inviter, "guild_permissions", discord.Permissions()).administrator
        ):
            return

        try:
            await self.bot.wait_until_ready()
            await invite.delete(reason=f"DEFCON is active and does not allow invites. LEVEL {level}")
        except discord.Forbidden:
            pass
        else:
            await self.defcon_broadcast(
                f"Invite created by **{invite.inviter}** (`{getattr(invite.inviter, 'id', 'ID Not Found')}`) was deleted for DEFCON level {level}",
                guild=invite.guild,  # type: ignore
                level=level,
            )

    def has_defcon_in(
        self, guild: Optional[Union[discord.Guild, discord.Object, discord.PartialInviteGuild]]
    ) -> Union[bool, int]:
        if guild is None:
            return False

        if guild.id not in self.settings:
            return False

        if "default_defcon" not in self.settings[guild.id]:
            return False

        level = self.settings[guild.id]["default_defcon"].get("level", -1)
        return False if level == -1 else level

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        defcon = self.has_defcon_in(member.guild)
        if defcon is False:
            return

        await self.defcon_on_member_join(member, defcon)

    @Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        ...

    @Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        defcon = self.has_defcon_in(invite.guild)
        if defcon is False:
            return

        await self.defcon_on_invite_create(invite, defcon)
