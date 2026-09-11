from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot

_log = logging.getLogger("bot.cogs.hub")


class Hub(commands.Cog):
    """Join-to-create voice channel system."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if before.channel is None and after.channel is not None:
            _log.debug(
                "%s joined voice channel %s in guild %s",
                member,
                after.channel.id,
                member.guild.id,
            )
            await self._handle_join(member, after.channel)

        elif before.channel is not None and after.channel is None:
            _log.debug(
                "%s left voice channel %s in guild %s",
                member,
                before.channel.id,
                member.guild.id,
            )
            await self._handle_leave(member, before.channel)

        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            _log.debug(
                "%s moved from voice channel %s to %s in guild %s",
                member,
                before.channel.id,
                after.channel.id,
                member.guild.id,
            )
            await self._handle_move(
                member,
                before.channel,
                after.channel,
            )

    async def _handle_join(
        self,
        member: discord.Member,
        channel: discord.VoiceChannel,
    ) -> None:
        hub_channel_id = await self.bot.database.get_hub_channel_id(
            guild_id=member.guild.id,
        )

        if hub_channel_id is None:
            return

        if channel.id != hub_channel_id:
            return

        await self._create_personal_channel(member, channel)

    async def _handle_leave(
        self,
        member: discord.Member,
        channel: discord.VoiceChannel,
    ) -> None:
        hub_channel_id = await self.bot.database.get_hub_channel_id(
            guild_id=member.guild.id,
        )

        if hub_channel_id is None:
            return

        # The hub itself should never be deleted.
        if channel.id == hub_channel_id:
            return

        await self._delete_if_empty(channel)

    async def _handle_move(
        self,
        member: discord.Member,
        before: discord.VoiceChannel,
        after: discord.VoiceChannel,
    ) -> None:
        hub_channel_id = await self.bot.database.get_hub_channel_id(
            guild_id=member.guild.id,
        )

        if hub_channel_id is None:
            return

        existing_channel = await self._find_existing_channel(member)
        if existing_channel and after.id == existing_channel.id and before.id == hub_channel_id:
            return

        if after.id == hub_channel_id:
            await self._create_personal_channel(member, after)

            # The previous channel may now be empty.
            if before.id != hub_channel_id:
                await self._delete_if_empty(before)

            return

        if before.id != hub_channel_id:
            await self._delete_if_empty(before)

        owner_id = await self.bot.database.get_hub_channel_owner_id(
            guild_id=member.guild.id,
            channel_id=after.id,
        )

        if owner_id is None:
            return

        # Don't allow users to enter another user's personal channel.
        hub_channel = member.guild.get_channel(hub_channel_id)

        if isinstance(hub_channel, discord.VoiceChannel):
            try:
                await member.move_to(
                    hub_channel,
                    reason=(f"Prevented {member} ({member.id}) from joining another user's temporary channel"),
                )
            except discord.HTTPException:
                _log.exception(
                    "Failed to move %s back to the hub in guild %s",
                    member,
                    member.guild.id,
                )

    async def _find_existing_channel(self, member: discord.Member) -> discord.VoiceChannel | None:
        for voice_channel in member.guild.voice_channels:
            owner_id = await self.bot.database.get_hub_channel_owner_id(
                guild_id=member.guild.id,
                channel_id=voice_channel.id,
            )
            if owner_id != member.id:
                continue
            try:
                await member.move_to(
                    voice_channel,
                    reason="Returning member to their existing temporary channel",
                )
            except discord.HTTPException:
                _log.exception(
                    "Failed to move %s to existing channel %s",
                    member,
                    voice_channel.id,
                )
            return voice_channel
        return None

    async def _create_personal_channel(
        self,
        member: discord.Member,
        hub_channel: discord.VoiceChannel,
    ) -> discord.VoiceChannel | None:
        guild = member.guild

        me = guild.me
        if me is None:
            return None

        if not me.guild_permissions.manage_channels:
            _log.warning(
                "Bot does not have Manage Channels in guild %s (%s)",
                guild.name,
                guild.id,
            )
            return None

        # Prevent duplicate channels if the event fires more than once.
        existing_channel_id = await self.bot.database.get_hub_channel_id(
            guild_id=guild.id,
        )

        if existing_channel_id is None:
            return None

        if existing_channel := await self._find_existing_channel(member):
            return existing_channel

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                connect=False,
                view_channel=True,
            ),
            member: discord.PermissionOverwrite(
                connect=True,
                speak=True,
                view_channel=True,
                manage_channels=True,
                manage_permissions=True,
                move_members=True,
                mute_members=True,
                deafen_members=True,
            ),
        }

        try:
            personal_channel = await guild.create_voice_channel(
                name=f"{member.display_name}'s Channel",
                category=hub_channel.category,
                overwrites=overwrites,
                reason=(f"Join-to-create channel for {member} ({member.id})"),
            )
        except discord.Forbidden:
            _log.exception(
                "Bot cannot create voice channels in guild %s",
                guild.id,
            )
            return None

        except discord.HTTPException:
            _log.exception(
                "Failed to create personal channel for %s in guild %s",
                member,
                guild.id,
            )
            return None

        await self.bot.database.set_hub_channel_owner_id(
            guild_id=guild.id,
            channel_id=personal_channel.id,
            owner_id=member.id,
        )

        try:
            await member.move_to(
                personal_channel,
                reason=(f"Moved {member} into their new join-to-create channel"),
            )
        except discord.HTTPException:
            _log.exception(
                "Failed to move %s into channel %s",
                member,
                personal_channel.id,
            )

            # If moving failed, don't leave an orphaned channel.
            if len(personal_channel.members) == 0:
                await self._delete_if_empty(personal_channel)

            return None

        return personal_channel

    async def _delete_if_empty(
        self,
        channel: discord.VoiceChannel,
    ) -> None:
        if channel.members:
            return

        guild = channel.guild

        hub_channel_id = await self.bot.database.get_hub_channel_id(
            guild_id=guild.id,
        )

        # Never delete the actual hub.
        if channel.id == hub_channel_id:
            return

        owner_id = await self.bot.database.get_hub_channel_owner_id(
            guild_id=guild.id,
            channel_id=channel.id,
        )

        # Not one of our temporary channels.
        if owner_id is None:
            return

        try:
            await self.bot.database.remove_hub_channel_owner_id(
                guild_id=guild.id,
                channel_id=channel.id,
            )

            await channel.delete(
                reason=(f"Join-to-create channel became empty (owner ID: {owner_id})"),
            )

        except discord.NotFound:
            # Channel was already deleted.
            await self.bot.database.remove_hub_channel_owner_id(
                guild_id=guild.id,
                channel_id=channel.id,
            )

        except discord.Forbidden:
            _log.exception(
                "Bot cannot delete temporary channel %s in guild %s",
                channel.id,
                guild.id,
            )

        except discord.HTTPException:
            _log.exception(
                "Failed to delete temporary channel %s in guild %s",
                channel.id,
                guild.id,
            )


async def setup(bot: Parrot) -> None:
    """Load the Hub cog."""
    await bot.add_cog(Hub(bot))
