from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

import discord

if TYPE_CHECKING:
    from core import Parrot
    from core.utils.database.models import GuildConfiguration


__all__ = ("WelcomeEditButton",)


class WelcomeConfigModal(discord.ui.Modal, title="Edit Welcome Configuration"):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__()

        self.on_member_join_channel_id = kwargs["welcome_config"]["on_member_join_channel_id"]
        self.on_member_join_message = kwargs["welcome_config"]["on_member_join_message"]

        self.on_member_join_role_id = kwargs["welcome_config"]["on_member_join_role_id"]

        self.on_member_leave_channel_id = kwargs["welcome_config"]["on_member_leave_channel_id"]
        self.on_member_leave_message = kwargs["welcome_config"]["on_member_leave_message"]

        self._join_channel_input = discord.ui.ChannelSelect(
            placeholder="Select a channel for join messages...",
            channel_types=[discord.ChannelType.text],
            default_values=[discord.Object(id=self.on_member_join_channel_id)] if self.on_member_join_channel_id is not None else [],
            min_values=0,
            max_values=1,
        )
        self.join_channel_input = discord.ui.Label(
            text="Join Channel",
            component=self._join_channel_input,
            description="This channel will be used to send welcome messages when a new member joins the server.",
        )
        self.join_message_input = discord.ui.TextInput(
            label="Join Message",
            placeholder="Enter a message to send when a member joins...",
            default=self.on_member_join_message if self.on_member_join_message is not None else "",
            style=discord.TextStyle.paragraph,
            max_length=800,
        )

        self._join_role_input = discord.ui.RoleSelect(
            placeholder="Select a role to assign to new members...",
            default_values=[discord.Object(id=self.on_member_join_role_id)] if self.on_member_join_role_id is not None else [],
            min_values=0,
            max_values=1,
        )
        self.join_role_input = discord.ui.Label(
            text="Join Role",
            component=self._join_role_input,
            description="This role will be assigned to new members when they join the server.",
        )

        self._leave_channel_input = discord.ui.ChannelSelect(
            placeholder="Select a channel for leave messages...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            default_values=[discord.Object(id=self.on_member_leave_channel_id)] if self.on_member_leave_channel_id is not None else [],
        )
        self.leave_channel_input = discord.ui.Label(
            text="Leave Channel",
            component=self._leave_channel_input,
            description="This channel will be used to send goodbye messages when a member leaves the server.",
        )
        self.leave_message_input = discord.ui.TextInput(
            label="Leave Message",
            placeholder="Enter a message to send when a member leaves...",
            default=self.on_member_leave_message if self.on_member_leave_message is not None else "",
            style=discord.TextStyle.paragraph,
            max_length=800,
        )

        self.add_item(self.join_channel_input)
        self.add_item(self.join_message_input)
        self.add_item(self.join_role_input)
        self.add_item(self.leave_channel_input)
        self.add_item(self.leave_message_input)

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        # Update the configuration in the database
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        guild_id = interaction.guild.id
        new_config = {
            "on_member_join_channel_id": self._join_channel_input.values[0].id if self._join_channel_input.values else None,
            "on_member_join_message": self.join_message_input.value,
            "on_member_join_role_id": self._join_role_input.values[0].id if self._join_role_input.values else None,
            "on_member_leave_channel_id": self._leave_channel_input.values[0].id if self._leave_channel_input.values else None,
            "on_member_leave_message": self.leave_message_input.value,
        }
        await interaction.client.database.edit_welcome_config(
            guild_id=guild_id,
            **new_config,
        )

        await interaction.response.send_message("Updated welcome configuration.", ephemeral=True)


class WelcomeEditButton(discord.ui.Button):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__(emoji="\N{PENCIL}", style=discord.ButtonStyle.secondary)
        self.enabled = False
        self.kwargs = kwargs

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        self.kwargs: GuildConfiguration = await interaction.client.database.get_guild_configuration(interaction.guild.id)  # type: ignore
        modal = WelcomeConfigModal(**self.kwargs)

        await interaction.response.send_modal(modal)
        await modal.wait()
