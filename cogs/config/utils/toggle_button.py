from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import discord

if TYPE_CHECKING:
    from core import Parrot

__all__ = ("ToggleButton",)


class ToggleButtonCallback(Protocol):
    async def __call__(self, *, guild_id: int, enabled: bool): ...


class ToggleButton(discord.ui.Button):
    def __init__(
        self,
        *,
        enabled: bool,
        enable_callback: ToggleButtonCallback,
        disable_callback: ToggleButtonCallback,
    ) -> None:
        super().__init__(
            label="On" if enabled else "Off",
            style=discord.ButtonStyle.secondary,
        )
        self.enable_callback = enable_callback
        self.disable_callback = disable_callback

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        assert self.view is not None
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        new_enabled_state = not self.enabled

        CHECKMARK = "\N{WHITE HEAVY CHECK MARK}"

        if new_enabled_state:
            await self.enable_callback(guild_id=interaction.guild.id, enabled=True)
            await interaction.followup.send(f"{CHECKMARK} Enabled", ephemeral=True)
        else:
            await self.disable_callback(guild_id=interaction.guild.id, enabled=False)
            await interaction.followup.send(f"{CHECKMARK} Disabled", ephemeral=True)

        self.enabled = new_enabled_state
        self.label = "On" if self.enabled else "Off"
