from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, Unpack

import discord

if TYPE_CHECKING:
    from core import Parrot
    from core.utils.database.models import GuildConfiguration


__all__ = ("StarboardEditButton",)


def _parse_positive_int(value: str) -> int | None:
    try:
        parsed = int(value)
        if parsed < 0:
            return None
        return parsed
    except ValueError:
        return None


def _is_valid_emoji(emoji: str) -> bool:
    try:
        return unicodedata.name(emoji) is not None
    except ValueError:
        return False


class StarboardConfigModal(discord.ui.Modal, title="Edit Starboard Configuration"):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__()

        self.starboard_channel_id = kwargs["starboard_config"]["channel_id"]
        self.starboard_threshold = kwargs["starboard_config"]["threshold"]
        self.starboard_emoji = kwargs["starboard_config"]["emoji"]

        self._starboard_channel_input = discord.ui.ChannelSelect(
            placeholder="Select a channel for starboards...",
            channel_types=[discord.ChannelType.text],
            default_values=[discord.Object(id=self.starboard_channel_id)] if self.starboard_channel_id is not None else [],
            min_values=0,
            max_values=1,
        )
        self.starboard_channel_input = discord.ui.Label(
            text="Starboard Channel",
            component=self._starboard_channel_input,
            description="This channel will be used to host starboards in the server.",
        )
        self.starboard_threshold_input = discord.ui.TextInput(
            label="Starboard Threshold",
            placeholder="Enter the number of stars required to create a starboard...",
            default=str(self.starboard_threshold) if self.starboard_threshold is not None else None,
            required=False,
        )
        self.starboard_emoji_input = discord.ui.TextInput(
            label="Starboard Emoji",
            placeholder="Enter the emoji to be used for starboards...",
            default=self.starboard_emoji,
            required=False,
        )

        self.add_item(self.starboard_channel_input)
        self.add_item(self.starboard_threshold_input)
        self.add_item(self.starboard_emoji_input)

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        # Update the configuration in the database
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        guild_id = interaction.guild.id
        new_config = {
            "channel_id": self._starboard_channel_input.values[0].id if self._starboard_channel_input.values else None,
            "threshold": _parse_positive_int(self.starboard_threshold_input.value) if self.starboard_threshold_input.value else None,
            "emoji": self.starboard_emoji_input.value
            if self.starboard_emoji_input.value and _is_valid_emoji(self.starboard_emoji_input.value)
            else None,
        }
        await interaction.client.database.edit_starboard_config(
            guild_id=guild_id,
            enabled=True,
            **new_config,
        )

        await interaction.response.send_message("Updated starboard configuration.", ephemeral=True)


class StarboardEditButton(discord.ui.Button):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__(emoji="\N{PENCIL}", style=discord.ButtonStyle.secondary)
        self.enabled = False
        self.kwargs = kwargs

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        self.kwargs: GuildConfiguration = await interaction.client.database.get_guild_configuration(interaction.guild.id)  # type: ignore
        modal = StarboardConfigModal(**self.kwargs)

        await interaction.response.send_modal(modal)
        await modal.wait()
