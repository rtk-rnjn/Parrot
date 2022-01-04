from __future__ import annotations

import asyncio

import discord
from discord.utils import MISSING
from discord import Member as User

from core import Context
from typing import Any

from .game import GameUI

__all__ = ("JoinUI",)


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


class JoinUI(discord.ui.View):
    message: discord.Message

    def __init__(self, host: User, games: dict[int, discord.ui.View]):
        super().__init__(timeout=60 * 15)
        self.host = host
        self.users: dict[User, discord.Interaction] = {host: MISSING}
        self.user_lock = asyncio.Lock()
        self.started: bool = False
        self.games = games

    async def on_timeout(self) -> None:
        self.join_leave.disabled = True
        self.start_game.disabled = True
        await self.message.edit(content="Timed-out waiting for players.", view=self)
        del self.games[self.message.channel.id]

    @discord.ui.button(label="Join/Leave", style=discord.ButtonStyle.primary)
    async def join_leave(
        self, item: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        async with self.user_lock:
            if self.started:
                return await interaction.response.send_message(
                    "This game has already started.", ephemeral=True
                )

            await interaction.response.defer(ephemeral=True)

            if interaction.user in self.users:
                del self.users[interaction.user]  # type: ignore
            else:
                self.users[interaction.user] = interaction  # type: ignore

        if len(self.users) >= 5:
            self.start_game.disabled = False
            self.start_game.style = discord.ButtonStyle.success
        else:
            self.start_game.disabled = True
            self.start_game.style = discord.ButtonStyle.danger

        await interaction.message.edit(content=self.content, view=self)

    @property
    def content(self) -> str:
        return format_list("Secret Hitler! Currently: {0} {1} joined.", *self.users)

    @discord.ui.button(
        label="Start Game", style=discord.ButtonStyle.danger, disabled=True
    )
    async def start_game(
        self, item: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if len(self.users) < 5:
            return await interaction.response.send_message(
                "There are not enough players to start the game.", ephemeral=True
            )

        if interaction.user != self.host:
            return await interaction.response.send_message(
                "Only the host can start the game.", ephemeral=True
            )

        async with self.user_lock:
            if self.started:
                return await interaction.response.send_message(
                    "This game has already started.", ephemeral=True
                )

            self.started = True
            self.users[self.host] = interaction
            await interaction.response.defer(ephemeral=True)
            self.stop()

            await GameUI.start(self.message, self.host, self.users, self.games)

    @classmethod
    async def start(
        cls, ctx: Context, games: dict[int, discord.ui.View]
    ) -> JoinUI:  # todo: TextGuildChannel
        games[ctx.channel.id] = self = cls(ctx.author, games)
        self.message = await ctx.channel.send(self.content, view=self)
        return self
