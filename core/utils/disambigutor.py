from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot


class DisambiguatorView[T](discord.ui.View):
    message: discord.Message
    selected: T

    def __init__(self, ctx: commands.Context[Parrot], data: list[T], entry: Callable[[T], str] = str):
        super().__init__()
        self.ctx = ctx
        self.data: list[T] = data

        options = []
        for i, x in enumerate(data):
            option = entry(x)
            if not isinstance(option, discord.SelectOption):
                option = discord.SelectOption(label=str(option))
            option.value = str(i)
            options.append(option)

        select = discord.ui.Select(options=options)

        select.callback = self.on_select_submit
        self.select = select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
            return False
        return True

    async def on_select_submit(self, interaction: discord.Interaction):
        index = int(self.select.values[0])
        self.selected = self.data[index]
        await interaction.response.defer()

        if not self.message.flags.ephemeral:
            await self.message.delete()

        self.stop()
