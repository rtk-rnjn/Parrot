from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core import Parrot


class WelcomeConfigModal(discord.ui.Modal, title="Edit Welcome Configuration"):
    def __init__(
        self,
        *,
        on_member_join_message: str | None,
        on_member_join_channel_id: int | None,
        on_member_join_role_id: int | None,
        on_member_leave_message: str | None,
        on_member_leave_channel_id: int | None,
    ) -> None:
        super().__init__()

        self.on_member_join_message = on_member_join_message
        self.on_member_join_channel_id = on_member_join_channel_id
        self.on_member_join_role_id = on_member_join_role_id
        self.on_member_leave_message = on_member_leave_message
        self.on_member_leave_channel_id = on_member_leave_channel_id

        self.join_message_input = discord.ui.TextInput(
            label="Join Message",
            placeholder="Enter the message to send when a member joins...",
            default=self.on_member_join_message or "",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=2000,
        )
        self.add_item(self.join_message_input)


class WelcomeEditButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            emoji="\N{PENCIL}",
            style=discord.ButtonStyle.secondary,
        )
        self.enabled = False

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        new_enabled_state = not self.enabled

        if new_enabled_state:
            await interaction.client.database.edit_welcome_config(guild_id=interaction.guild.id, enabled=True)
            await interaction.followup.send("Welcome messages have been enabled.", ephemeral=True)
        else:
            await interaction.client.database.edit_welcome_config(guild_id=interaction.guild.id, enabled=False)
            await interaction.followup.send("Welcome messages have been disabled.", ephemeral=True)

        self.enabled = new_enabled_state
        self.label = "On" if self.enabled else "Off"


# class MemberJoinChannelSelect(discord.ui.ChannelSelect):
#     def __init__(self, welcome_channel_id: int | None) -> None:
#         super().__init__(
#             placeholder="Select a welcome channel...",
#             min_values=0,
#             max_values=1,
#             channel_types=[discord.ChannelType.text],
#             default_values=[discord.Object(id=welcome_channel_id)] if welcome_channel_id is not None else [],
#         )
#         self.welcome_channel_id = welcome_channel_id

#     async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
#         assert self.view is not None
#         await interaction.response.defer(ephemeral=True)

#         if interaction.guild is None:
#             await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
#             return

#         selected_channel = self.values[0] if self.values else None

#         if selected_channel is not None:
#             new_welcome_channel_id = selected_channel.id

#             await interaction.client.database.edit_welcome_config(guild_id=interaction.guild.id, on_member_leave_channel_id=new_welcome_channel_id)
#             await interaction.followup.send(f"Welcome channel updated to {selected_channel.mention}.", ephemeral=True)

#         else:
#             await interaction.client.database.edit_welcome_config(guild_id=interaction.guild.id, on_member_leave_channel_id=None)
#             await interaction.followup.send("Welcome channel has been removed.", ephemeral=True)


# class MemberLeaveChannelSelect(discord.ui.ChannelSelect):
#     def __init__(self, leave_channel_id: int | None) -> None:
#         super().__init__(
#             placeholder="Select a leave channel...",
#             min_values=0,
#             max_values=1,
#             channel_types=[discord.ChannelType.text],
#             default_values=[discord.Object(id=leave_channel_id)] if leave_channel_id is not None else [],
#         )
#         self.leave_channel_id = leave_channel_id

#     async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
#         assert self.view is not None
#         await interaction.response.defer(ephemeral=True)

#         if interaction.guild is None:
#             await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
#             return

#         selected_channel = self.values[0] if self.values else None

#         if selected_channel is not None:
#             new_leave_channel_id = selected_channel.id

#             await interaction.client.database.edit_welcome_config(guild_id=interaction.guild.id, on_member_leave_channel_id=new_leave_channel_id)
#             await interaction.followup.send(f"Leave channel updated to {selected_channel.mention}.", ephemeral=True)

#         else:
#             await interaction.client.database.edit_welcome_config(guild_id=interaction.guild.id, on_member_leave_channel_id=None)
#             await interaction.followup.send("Leave channel has been removed.", ephemeral=True)
