from __future__ import annotations

from datetime import datetime

import discord
from core import Cog, Parrot


class GuildChannel(Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        pass

    @Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if (
            channel.permissions_for(channel.guild.me).manage_channels
            and channel.permissions_for(channel.guild.default_role).send_messages
            and channel.permissions_for(channel.guild.me).manage_roles
        ):
            if channel.guild.id not in self.bot.guild_configurations_cache:
                return

            if role_id := self.bot.guild_configurations_cache[channel.guild.id]["mute_role"]:
                if role := channel.guild.get_role(role_id):
                    await channel.set_permissions(
                        role,
                        send_messages=False,
                        add_reactions=False,
                        reason="Mute role override",
                    )
            elif role := discord.utils.get(channel.guild.roles, name="Muted"):
                await channel.set_permissions(
                    role,
                    send_messages=False,
                    add_reactions=False,
                    reason="Mute role override",
                )

    @Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        pass

    @Cog.listener()
    async def on_guild_channel_pins_update(
        self,
        channel: discord.abc.GuildChannel | discord.Thread,
        last_pin: datetime | None,
    ):
        pass

    @Cog.listener()
    async def on_guild_integrations_update(self, guild: discord.Guild):
        pass

    @Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        pass

    @Cog.listener()
    async def on_integration_create(self, integration: discord.Integration):
        pass

    @Cog.listener()
    async def on_integration_update(self, integration: discord.Integration):
        pass

    @Cog.listener()
    async def on_raw_integration_delete(self, payload: discord.RawIntegrationDeleteEvent):
        pass


async def setup(bot):
    await bot.add_cog(GuildChannel(bot))
