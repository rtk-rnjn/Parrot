from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from .views import BaseLayoutView

if TYPE_CHECKING:
    from core import Bot

__all__ = ("ConfirmationLayout",)


class ConfirmationLayout(BaseLayoutView):
    """A confirm/cancel prompt that shows its outcome in place.

    ``value`` stays ``None`` until the owner answers; a timeout leaves it ``None`` and is shown on the message.
    A components v2 message cannot be edited back to plain ``content``, so every outcome is rendered as a layout.
    """

    def __init__(self, author: discord.User | discord.Member, prompt: str, *, timeout: float | None = 30) -> None:
        super().__init__(author, timeout=timeout)
        self.prompt = prompt
        self.value: bool | None = None

        self.confirm_button = discord.ui.Button[ConfirmationLayout](label="Confirm", style=discord.ButtonStyle.success)
        self.cancel_button = discord.ui.Button[ConfirmationLayout](label="Cancel", style=discord.ButtonStyle.secondary)
        self.confirm_button.callback = self.confirm
        self.cancel_button.callback = self.cancel

        self.container = discord.ui.Container(
            discord.ui.TextDisplay(prompt),
            discord.ui.Separator(),
            discord.ui.ActionRow(self.confirm_button, self.cancel_button),
        )
        self.add_item(self.container)

    def render_outcome(self, outcome: str, *, colour: discord.Colour) -> None:
        """Replace the buttons with a one-line outcome so the prompt stays readable after it is answered."""
        self.container.clear_items()
        self.container.add_item(discord.ui.TextDisplay(f"{self.prompt}\n-# {outcome}"))
        self.container.accent_colour = colour

    async def _settle(self, interaction: discord.Interaction[Bot], value: bool, outcome: str, colour: discord.Colour) -> None:
        if self.value is None:
            self.value = value

        self.render_outcome(outcome, colour=colour)
        self.stop()
        await interaction.response.edit_message(view=self)

    async def confirm(self, interaction: discord.Interaction[Bot]) -> None:
        await self._settle(interaction, True, "Confirmed.", discord.Colour.green())

    async def cancel(self, interaction: discord.Interaction[Bot]) -> None:
        await self._settle(interaction, False, "Cancelled.", discord.Colour.dark_grey())

    async def on_timeout(self) -> None:
        self.render_outcome("Confirmation timed out.", colour=discord.Colour.dark_grey())
        await self.update_message()
