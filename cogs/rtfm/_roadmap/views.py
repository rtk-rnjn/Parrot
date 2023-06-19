from __future__ import annotations

from typing import List

import aiofiles
import yaml

import discord
from core import Context
from discord.ext import commands

from .endpoints import FIRST_HALF_ENDPOINTS, SECOND_HALF_ENDPOINTS

ROOT_DIR = "./extra/tutorials/roadmaps"


def parse_content(content: str) -> dict:
    return yaml.safe_load(content)


def roadmap_pdf(self, endpoint: str) -> discord.File:
    with open(f"{ROOT_DIR}-pdf/{endpoint}.pdf", "rb") as f:
        return discord.File(f, filename=f"{endpoint}.pdf")


def get_roadmap_select_view(ls: List[str]) -> discord.ui.Select:
    class DropdownFirstHalf(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=name, description=f"Roadmap for {name}")
                for name in ls
            ]

            super().__init__(
                placeholder="Choose Roadmap...",
                min_values=1,
                max_values=1,
                options=options,
            )

        async def callback(self, interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            async with aiofiles.open(
                f"{ROOT_DIR}/{self.values[0]}/{self.values[0]}.md",
            ) as f:
                content = await f.read()
            data = parse_content(content)
            embed = discord.Embed(
                title=data["title"],
                description=data["description"],
                color=discord.Color.random(),
            ).set_footer(
                text=f"Related topics: `{'`, `'.join(data['relatedRoadmaps'])}`",
                icon_url=interaction.user.display_avatar.url,
            )
            if data.get("keywords"):
                keywords = data["keywords"][:5]
                embed.add_field(
                    name="Keywords",
                    value="`" + "`, `".join(keywords) + "`",
                )
            file = roadmap_pdf(self, self.values[0])
            await interaction.followup.send(
                embed=embed,
                file=file,
            )

    return DropdownFirstHalf()


class DropdownView(discord.ui.View):
    message: discord.Message

    def __init__(self, ctx: Context):
        super().__init__(timeout=30)

        self.ctx = ctx

        self.add_item(get_roadmap_select_view(FIRST_HALF_ENDPOINTS))
        self.add_item(get_roadmap_select_view(SECOND_HALF_ENDPOINTS))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Select, discord.ui.Button)):
                item.disabled = True
                if isinstance(item, discord.ui.Button):
                    item.style = discord.ButtonStyle.gray

        await self.message.edit(view=self)
