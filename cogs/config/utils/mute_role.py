from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core import Parrot


class MuteRoleSelect(discord.ui.RoleSelect):
    def __init__(self, mute_role_id: int | None) -> None:
        super().__init__(
            placeholder="Select a mute role...",
            min_values=0,
            max_values=1,
            default_values=[discord.Object(id=mute_role_id)] if mute_role_id is not None else [],
        )
        self.mute_role_id = mute_role_id

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        selected_role = self.values[0] if self.values else None

        if selected_role is not None:
            new_mute_role_id = selected_role.id

            await interaction.client.database.set_guild_mute_role(guild_id=interaction.guild.id, mute_role_id=new_mute_role_id)
            await interaction.followup.send(f"Mute role updated to {selected_role.mention}.", ephemeral=True)

        else:
            await interaction.client.database.delete_mute_role(guild_id=interaction.guild.id)
            await interaction.followup.send("Mute role has been removed.", ephemeral=True)
