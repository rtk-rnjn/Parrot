from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

import discord

from core.utils import PaginationView

if TYPE_CHECKING:
    from core import Parrot
    from core.utils.database.models import GuildConfiguration


class LevelingChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, channel_id: int | None) -> None:
        super().__init__(
            placeholder="Select a leveling channel...",
            min_values=0,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            default_values=[discord.Object(id=channel_id)] if channel_id is not None else [],
        )
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        selected_channel = self.values[0] if self.values else None

        if selected_channel is not None:
            new_channel_id = selected_channel.id

            await interaction.client.database.edit_leveling_config(guild_id=interaction.guild.id, enabled=True, channel_id=new_channel_id)
            await interaction.followup.send(f"Leveling channel updated to {selected_channel.mention}.", ephemeral=True)

        else:
            await interaction.client.database.edit_leveling_config(guild_id=interaction.guild.id, enabled=True, channel_id=None)
            await interaction.followup.send("Leveling channel has been removed.", ephemeral=True)


class LevelingRoleAddModal(discord.ui.Modal, title="Add Leveling Role"):
    def __init__(self) -> None:
        super().__init__()

        self.level_input = discord.ui.TextInput(
            label="Level",
            placeholder="Enter the level for this role...",
            style=discord.TextStyle.short,
            required=True,
        )

        self._role_input = discord.ui.RoleSelect(
            placeholder="Select a role to assign at this level...",
            min_values=1,
            max_values=1,
        )
        self.role_input = discord.ui.Label(
            text="Role",
            component=self._role_input,
            description="This role will be assigned to members when they reach the specified level.",
        )

        self.add_item(self.level_input)
        self.add_item(self.role_input)


class LevelingRoleRemoveModal(discord.ui.Modal, title="Select Roles to remove"):
    def __init__(self, level_role_mapping: dict[int, str]) -> None:
        super().__init__()

        self._input = discord.ui.CheckboxGroup(
            options=[
                discord.CheckboxGroupOption(label=f"Level {level}", value=str(level), description=f"Role: @{role_name}")
                for level, role_name in level_role_mapping.items()
            ],
        )
        self.input = discord.ui.Label(
            text="Select Levels",
            component=self._input,
            description="Select the levels for which you want to remove the associated roles.",
        )
        self.add_item(self.input)


class LevelingRolesConfig(PaginationView):
    def __init__(self, author: discord.Member | discord.User, **kwargs: Unpack[GuildConfiguration]) -> None:
        self.kwargs = kwargs

        self.data_chunks = list(discord.utils.as_chunks(self.kwargs["leveling_config"]["level_roles"].items(), 10))

        pages: list[discord.Embed] = []

        for chunk_index, chunk in enumerate(self.data_chunks):
            content = ""
            for index, (level, role_id) in enumerate(chunk):
                content += f"{(chunk_index * 10) + (index + 1)}. Level {level} - <@&{role_id}>\n"

            embed = discord.Embed(
                title="Leveling Roles Configuration",
                description=content if content else "No leveling roles configured.",
            )

            pages.append(embed)

        if not pages:
            embed = discord.Embed(
                title="Leveling Roles Configuration",
                description="No leveling roles configured.",
            )
            pages.append(embed)

        super().__init__(author=author, items=pages, hide_skip_button=True, hide_quit_button=True)

        self.reload_button = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}")
        self.reload_button.callback = self.on_reload_button_click

        self.add_level_role_button = discord.ui.Button(style=discord.ButtonStyle.green, emoji="\N{HEAVY PLUS SIGN}")
        self.remove_level_role_button = discord.ui.Button(style=discord.ButtonStyle.red, emoji="\N{HEAVY MINUS SIGN}")

        self.add_level_role_button.callback = self.on_add_level_role_button_click
        self.remove_level_role_button.callback = self.on_remove_level_role_button_click

        self.add_item(self.reload_button)
        self.add_item(self.add_level_role_button)
        self.add_item(self.remove_level_role_button)

    async def on_add_level_role_button_click(self, interaction: discord.Interaction[Parrot]) -> None:
        modal = LevelingRoleAddModal()
        modal.on_submit = self.on_add_level_role_modal_submit(modal)
        await interaction.response.send_modal(modal)

    async def on_remove_level_role_button_click(self, interaction: discord.Interaction[Parrot]) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        guild = interaction.guild
        level_role_mapping: dict[int, str] = {}

        current_chunk = self.data_chunks[self.current_index] if self.current_index < len(self.data_chunks) else []
        for level, role_id in current_chunk:
            role = guild.get_role(role_id)
            if role is not None:
                level_role_mapping[int(level)] = role.name

        modal = LevelingRoleRemoveModal(level_role_mapping)
        modal.on_submit = self.on_remove_level_role_modal_submit(modal)
        await interaction.response.send_modal(modal)

    def on_add_level_role_modal_submit(self, modal: LevelingRoleAddModal):
        async def callback(interaction: discord.Interaction[Parrot]) -> None:
            level = int(modal.level_input.value)
            role_id = int(modal._role_input.values[0].id)

            if interaction.guild is None:
                await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
                return

            await interaction.client.database.set_level_role(guild_id=interaction.guild.id, level=level, role_id=role_id)

            await interaction.response.send_message(f"Added leveling role: Level {level} - <@&{role_id}>", ephemeral=True)

        return callback

    def on_remove_level_role_modal_submit(self, modal: LevelingRoleRemoveModal):
        async def callback(interaction: discord.Interaction[Parrot]) -> None:
            selected_levels = [int(value) for value in modal._input.values]
            if interaction.guild is None:
                await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
                return

            for level in selected_levels:
                await interaction.client.database.remove_level_role(guild_id=interaction.guild.id, level=level)

            if interaction.guild is None:
                await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
                return

            await interaction.response.send_message(f"Removed leveling roles for levels: {', '.join(map(str, selected_levels))}", ephemeral=True)

        return callback

    async def on_reload_button_click(self, interaction: discord.Interaction[Parrot]) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        self.kwargs: GuildConfiguration = await interaction.client.database.get_guild_configuration(interaction.guild.id)  # type: ignore
        self.data_chunks = list(discord.utils.as_chunks(self.kwargs["leveling_config"]["level_roles"].items(), 10))

        pages: list[discord.Embed] = []

        for chunk_index, chunk in enumerate(self.data_chunks):
            content = ""
            for index, (level, role_id) in enumerate(chunk):
                content += f"{(chunk_index * 10) + (index + 1)}. Level {level} - <@&{role_id}>\n"

            embed = discord.Embed(
                title="Leveling Roles Configuration",
                description=content if content else "No leveling roles configured.",
            )

            pages.append(embed)

        if not pages:
            embed = discord.Embed(
                title="Leveling Roles Configuration",
                description="No leveling roles configured.",
            )
            pages.append(embed)

        self.items = pages
        self.current_index = 0
        await self.update_page(interaction)


class LevelingRewardRolesEditButton(discord.ui.Button):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__(emoji="\N{PENCIL}", style=discord.ButtonStyle.secondary)
        self.enabled = False
        self.kwargs = kwargs

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        self.kwargs: GuildConfiguration = await interaction.client.database.get_guild_configuration(interaction.guild.id)  # type: ignore

        view = LevelingRolesConfig(interaction.user, **self.kwargs)
        await interaction.response.send_message(embed=view.items[0], view=view, ephemeral=True)
