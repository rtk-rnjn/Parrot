from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import discord
from discord import Member as User

from ..game import Player
from .select import *

if TYPE_CHECKING:
    from .game import GameUI

__all__ = (
    "PlayerButton",
    "PlayerUI",
)


class PlayerButton(SelectButton[Player[User], "PlayerUI"]):
    def __init__(self, item: Player[User], disabled: bool):
        super().__init__(
            item,
            style=discord.ButtonStyle.secondary,
            label=item.identifier.display_name,
            disabled=disabled,
        )


class PlayerUI(SelectUI):
    button_type: ClassVar[type[PlayerButton]] = PlayerButton

    def __init__(self, game: GameUI, target: Player, options: list[Player[User]]):
        super().__init__(game, target, options)

        for player in self.game.game.players:
            self.add_item(self.button_type(player, player not in self.options))
