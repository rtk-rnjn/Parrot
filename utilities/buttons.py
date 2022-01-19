from __future__ import annotations

import discord
from typing import NamedTuple


class Confirm(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=30.0)
        self.user_id = user_id
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Sorry, you can't use this interaction as it is not started by you.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        self.stop()


class LinkButton(discord.ui.View):
    def __init__(self, links: list):
        super().__init__()

        for link in links:
            self.add_item(discord.ui.Button(label=link.name, url=link.url))


class LinkType(NamedTuple):
    name: str
    url: str


class Prompt(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=30.0)
        self.user_id = user_id
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Sorry, you can't use this interaction as it is not started by you.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="YES", style=discord.ButtonStyle.green)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = True
        self.stop()

    @discord.ui.button(label="NO", style=discord.ButtonStyle.danger)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        self.stop()

class Delete(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=30.0)
        self.user = user
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user.bot:
            return True
        if self.user.id != interaction.user.id:
            return False
        return True

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.message.delete()
        self.stop()
