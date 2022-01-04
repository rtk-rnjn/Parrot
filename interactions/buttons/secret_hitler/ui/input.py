from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from ..game import UserInputGameState

if TYPE_CHECKING:
    from .game import GameUI


class InputUI(discord.ui.View):
    def __init__(self, game: GameUI):
        self.game: GameUI = game
        super().__init__(timeout=None)

    @property
    def tooltip(self) -> str:
        if not isinstance(self.game.game.state, UserInputGameState):
            raise AssertionError
        return self.game.game.state.tooltip
