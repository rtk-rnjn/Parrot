from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

import discord


if TYPE_CHECKING:
    from core import Parrot
    from core.utils.database.models import GuildConfiguration


__all__ = ("GiveawayEditButton",)


class GiveawayConfigModal(discord.ui.Modal, title="Edit Giveaway Configuration"):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__()

        self.giveaway_channel_id = kwargs["giveaway_config"]["giveaway_channel_id"]
        self.giveaway_role_id = kwargs["giveaway_config"]["giveaway_role_id"]

        self._giveaway_channel_input = discord.ui.ChannelSelect(
            placeholder="Select a channel for giveaways...",
            channel_types=[discord.ChannelType.text],
            default_values=[discord.Object(id=self.giveaway_channel_id)] if self.giveaway_channel_id is not None else [],
            min_values=0,
            max_values=1,
        )
        self.giveaway_channel_input = discord.ui.Label(
            text="Giveaway Channel",
            component=self._giveaway_channel_input,
            description="This channel will be used to host giveaways in the server.",
        )
        self._giveaway_role_input = discord.ui.RoleSelect(
            placeholder="Select a role to mention for giveaways...",
            default_values=[discord.Object(id=self.giveaway_role_id)] if self.giveaway_role_id is not None else [],
            min_values=0,
            max_values=1,
        )
        self.giveaway_role_input = discord.ui.Label(
            text="Giveaway Role",
            component=self._giveaway_role_input,
            description="This role will be mentioned when a giveaway is started in the server.",
        )

        self.add_item(self.giveaway_channel_input)
        self.add_item(self.giveaway_role_input)

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        # Update the configuration in the database
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        guild_id = interaction.guild.id
        new_config = {
            "giveaway_channel_id": self._giveaway_channel_input.values[0].id if self._giveaway_channel_input.values else None,
            "giveaway_role_id": self._giveaway_role_input.values[0].id if self._giveaway_role_input.values else None,
        }
        await interaction.client.database.edit_giveaway_config(
            guild_id=guild_id,
            enabled=True,
            **new_config,
        )

        await interaction.response.send_message("Updated giveaway configuration.", ephemeral=True)


class GiveawayEditButton(discord.ui.Button):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__(emoji="\N{PENCIL}", style=discord.ButtonStyle.secondary)
        self.enabled = False
        self.kwargs = kwargs

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        self.kwargs: GuildConfiguration = await interaction.client.database.get_guild_configuration(interaction.guild.id)  # type: ignore
        modal = GiveawayConfigModal(**self.kwargs)

        await interaction.response.send_modal(modal)
        await modal.wait()
