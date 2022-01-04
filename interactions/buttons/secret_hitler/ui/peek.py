from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import discord

from ..game import Party, Player
from .select import *

if TYPE_CHECKING:
    from .game import GameUI

__all__ = (
    "PeekButton",
    "PeekUI",
)

POLICY_STYLE: dict[Party, discord.ButtonStyle] = {
    Party.Liberal: discord.ButtonStyle.primary,
    Party.Fascist: discord.ButtonStyle.danger,
}


class PeekButton(SelectButton[Party, "PeekUI"]):
    disabled: ClassVar[bool] = True

    def __init__(self, item: Party):
        super().__init__(
            item, style=POLICY_STYLE[item], label=item.name, disabled=self.disabled
        )


class PeekUI(SelectUI):
    button_type: ClassVar[type[SelectButton]] = PeekButton

    def __init__(self, game: GameUI, target: Player, options: list[Party]):
        super().__init__(game, target, options)

        for option in options:
            self.add_item(self.button_type(option))
