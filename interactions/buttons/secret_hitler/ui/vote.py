from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord import Member as User


def format_list(
    string: str,
    *list: Any,
    singular: str = "has",
    plural: str = "have",
    oxford_comma: bool = True
) -> str:
    if len(list) == 0:
        return string.format("no-one", singular)
    if len(list) == 1:
        return string.format(list[0], singular)

    *rest, last = list
    rest_str = ", ".join(str(item) for item in rest)
    return string.format(rest_str + "," * oxford_comma + " and " + str(last), plural)


from ..game import Player, VoteGameState
from .input import InputUI

if TYPE_CHECKING:
    from .game import GameUI

__all__ = ("VoteUI",)


class VoteUI(InputUI):
    def __init__(self, game: GameUI, voters: list[Player[User]]):
        self.voters = voters
        super().__init__(game)

    @property
    def content(self) -> str:
        if not isinstance(self.game.game.state, VoteGameState):
            raise AssertionError
        return format_list(
            self.game.game.state.tooltip + "\nCurrently: {0} {1} voted.", *self.votes
        )

    @property
    def votes(self) -> dict[Player[User], bool]:
        if isinstance(self.game.game.state, VoteGameState):
            return self.game.game.state.votes
        return {}

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        player = self.game.game.get_player(interaction.user)
        if player not in self.voters:
            await interaction.response.send_message(
                "You cannot participate in this vote.", ephemeral=True
            )
            return False
        if player in self.votes:
            await interaction.response.send_message(
                "You have already voted.", ephemeral=True
            )
            return False
        return True

    async def vote(self, interaction: discord.Interaction, vote: bool) -> None:
        await self.game.store_interaction(interaction)

        player = self.game.game.get_player(interaction.user)
        if player is None:
            raise RuntimeError("How?")
        self.votes[player] = vote

        if self.game.game.state.ready:
            self.game.waiting.set()

        await interaction.message.edit(content=self.content, view=self)

    @discord.ui.button(label="ja!", style=discord.ButtonStyle.danger)
    async def ja(
        self, item: discord.ui.Button, interation: discord.Interaction
    ) -> None:
        return await self.vote(interation, True)

    @discord.ui.button(label="nein!", style=discord.ButtonStyle.primary)
    async def nein(
        self, item: discord.ui.Button, interation: discord.Interaction
    ) -> None:
        return await self.vote(interation, False)
