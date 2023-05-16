from __future__ import annotations

import io
import json
from contextlib import suppress
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import discord
from core import Cog, Parrot


class GuildChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    def _overwrite_to_json(
        self,
        overwrites: Dict[
            Union[discord.Role, discord.User], discord.PermissionOverwrite
        ],
    ) -> str:
        try:
            over = {
                f"{str(target.name)} ({'Role' if isinstance(target, discord.Role) else 'Member'})": overwrite._values
                for target, overwrite in overwrites.items()
            }
            return json.dumps(over, indent=4)
        except TypeError:
            return "{}"

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
            if role_id := self.bot.guild_configurations_cache[channel.guild.id][
                "mute_role"
            ]:
                if role := channel.guild.get_role(role_id):
                    await channel.set_permissions(
                        role, send_messages=False, add_reactions=False
                    )
            elif role := discord.utils.get(channel.guild.roles, name="Muted"):
                await channel.set_permissions(
                    role, send_messages=False, add_reactions=False
                )

    @Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        pass

    @Cog.listener()
    async def on_guild_channel_pins_update(
        self,
        channel: Union[discord.abc.GuildChannel, discord.Thread],
        last_pin: Optional[datetime],
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
    async def on_raw_integration_delete(
        self, payload: discord.RawIntegrationDeleteEvent
    ):
        pass


async def setup(bot):
    await bot.add_cog(GuildChannel(bot))
