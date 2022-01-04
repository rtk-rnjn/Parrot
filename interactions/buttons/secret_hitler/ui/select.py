from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import discord

from ..game import Player, SelectGameState
from .input import InputUI

if TYPE_CHECKING:
    from .game import GameUI

__all__ = (
    "SelectButton",
    "SelectUI",
)

T = TypeVar("T")
V = TypeVar("V", bound="SelectUI", covariant=True)


class SelectButton(discord.ui.Button[V], Generic[T, V]):
    def __init__(self, item: T, *args: Any, **kwargs: Any):
        self.item: T = item
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        await self.view.disable(interaction)

        if isinstance(self.view.game.game.state, SelectGameState):
            self.view.game.game.state.item = self.item
            self.view.game.waiting.set()


class SelectUI(InputUI, Generic[T], metaclass=ABCMeta):
    children: list[SelectButton]

    def __init__(self, game: GameUI, target: Player, options: list[T]):
        self.target = target
        self.options = options
        super().__init__(game)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        player = self.game.game.get_player(interaction.user)
        if player is not self.target:
            await interaction.response.send_message(
                "You cannot make a selection.", ephemeral=True
            )
            return False
        return True

    async def disable(self, interaction: discord.Interaction) -> None:
        # for button in self.children:
        #     button.disabled = True
        # await interaction.response.edit_message(view=self)
        player = self.game.game.get_player(interaction.user)
        self.game.interactions[player.identifier] = interaction
        self.stop()

    @property
    @classmethod
    @abstractmethod
    def button_type(cls) -> type[SelectButton]:
        raise NotImplementedError
