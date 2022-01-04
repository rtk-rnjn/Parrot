from __future__ import annotations

from typing import ClassVar

import discord

from .peek import *

__all__ = (
    "DiscardButton",
    "DiscardUI",
)


class DiscardButton(PeekButton):
    disabled: ClassVar[bool] = False


class DiscardUI(PeekUI):
    button_type: ClassVar[type[DiscardButton]] = DiscardButton

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.is_finished():
            await interaction.response.send_message(
                "You have already chosen a policy to discard", ephemeral=True
            )
            return False
        return True
