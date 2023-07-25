from __future__ import annotations

import discord
from core import Cog, Parrot

from .settings import DEFCON_SETTINGS


class DefconListeners(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.settings = bot.guild_configurations_cache

    async def defcon_broadcast(self, message: str | discord.Embed, *, guild: discord.Guild, level: int) -> None:
        if self.has_defcon_in(guild) is False:
            await self.bot.guild_configurations.update_one(
                {"_id": guild.id},
                {"$set": {"default_defcon.level": level}},
                upsert=True,
            )
            self.settings[guild.id]["default_defcon"] = {"level": level, "broadcast": {"enabled": True, "channel": None}}

        if "broadcast" not in self.settings[guild.id]["default_defcon"]:
            return

        if not self.settings[guild.id]["default_defcon"]["broadcast"]["enabled"]:
            return

        channel = guild.get_channel(self.settings[guild.id]["default_defcon"]["broadcast"]["channel"] or 0)
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
        self,
        guild: discord.Guild | discord.Object | discord.PartialInviteGuild | None,
    ) -> bool | int:
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

    @Cog.listener("on_audit_log_entry_create")
    async def audit_member_update(self, entry: discord.AuditLogEntry) -> None:
        if entry.action != discord.AuditLogAction.member_role_update:
            return

        defcon = self.has_defcon_in(entry.guild)
        if defcon is False:
            return

        settings = DEFCON_SETTINGS[defcon]["SETTINGS"]
        if settings.get("LOCK_ASSIGN_ROLES", False):
            return

        mod = await self.bot.get_or_fetch_member(entry.guild, entry.user_id)
        if mod is None:
            return

        if mod.bot:
            return

        if not isinstance(entry.target, discord.Member):
            return

        before_roles = sorted(set(entry.before.roles))
        after_roles = sorted(set(entry.after.roles))

        if before_roles == after_roles:
            return

        if len(after_roles) > len(before_roles):
            added = [r for r in after_roles if r not in before_roles]
            removed = []
        else:
            added = []
            removed = [r for r in before_roles if r not in after_roles]

        if added:
            try:
                await entry.target.remove_roles(
                    *added,
                    reason=f"DEFCON is active and does not allow role adds. LEVEL {defcon}",
                )
            except discord.Forbidden:
                pass
            else:
                await self.defcon_broadcast(
                    f"Roles added to **{entry.target}** (`{getattr(entry.target, 'id', 'ID Not Found')}`) were removed for DEFCON level {defcon}",
                    guild=entry.guild,
                    level=defcon,
                )

        if removed:
            try:
                await entry.target.add_roles(
                    *removed,
                    reason=f"DEFCON is active and does not allow role removals. LEVEL {defcon}",
                )
            except discord.Forbidden:
                pass
            else:
                await self.defcon_broadcast(
                    f"Roles removed from **{entry.target}** (`{getattr(entry.target, 'id', 'ID Not Found')}`) were added back for DEFCON level {defcon}",
                    guild=entry.guild,
                    level=defcon,
                )

    async def defon_role_create(self, role: discord.Role, level: int) -> None:
        settings = DEFCON_SETTINGS[level]["SETTINGS"]
        if settings.get("ALLOW_CREATE_ROLE", True):
            return

        try:
            await role.delete(reason=f"DEFCON is active and does not allow role creation. LEVEL {level}")
        except discord.Forbidden:
            pass
        else:
            await self.defcon_broadcast(
                f"Role created by **{role}** (`{getattr(role, 'id', 'ID Not Found')}`) was deleted for DEFCON level {level}",
                guild=role.guild,
                level=level,
            )

    @Cog.listener("on_audit_log_entry_create")
    async def audit_role_create(self, entry: discord.AuditLogEntry) -> None:
        if entry.action != discord.AuditLogAction.role_create:
            return

        defcon = self.has_defcon_in(entry.guild)
        if defcon is False:
            return

        mod = await self.bot.get_or_fetch_member(entry.guild, entry.user_id)
        if mod is None:
            return

        if mod.bot:
            return

        if not isinstance(entry.target, discord.Role):
            return

        await self.defon_role_create(entry.target, defcon)

    @Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        defcon = self.has_defcon_in(invite.guild)
        if defcon is False:
            return

        await self.defcon_on_invite_create(invite, defcon)
