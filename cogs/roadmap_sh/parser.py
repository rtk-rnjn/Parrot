from __future__ import annotations

import os
import re

import aiofiles
from jishaku.paginators import PaginatorEmbedInterface

import discord
from core import Context
from discord.ext import commands

folders = {
    "roadmaps": r"extra/tutorials/roadmaps",
    "best": r"extra/tutorials/best-practices",
    "links": r"extra/tutorials/link-groups",
    "videos": r"extra/tutorials/videos",
}


class ParentView(discord.ui.View):
    message: discord.Message
    ctx: Context

    def __init__(self, timeout: float) -> None:
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Roadmap", style=discord.ButtonStyle.blurple)
    async def roadmap(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(label="Best Practices", style=discord.ButtonStyle.blurple)
    async def best_practices(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(label="Link Groups", style=discord.ButtonStyle.blurple)
    async def link_groups(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(label="Videos", style=discord.ButtonStyle.blurple)
    async def videos(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    async def start(self, ctx: Context) -> None:
        self.ctx = ctx
        self.message = await ctx.send(
            embed=discord.Embed(
                title="Developer Roadmaps",
                description="[roadmap.sh](https://roadmap.sh) is a community effort to create roadmaps, guides and other educational content to help guide developers in picking up a path and guide their learnings.",
                url="https://roadmap.sh/",
            ),
            view=self,
        )


class ContentView(discord.ui.Select):
    view: ParentView

    def __init__(self, *, folders: list[str]) -> None:
        super().__init__(placeholder="Select a folder...", min_values=1, max_values=1)

        for folder in folders:
            self.add_option(label=folder, value=folder)
    
    def remove_img_links(self, text: str) -> str:
        """Remove all ![]() links from text"""
        return re.sub(r"!\[.*\]\(.*\)", "", text)

    def replace_partial_links(self, text: str) -> str:
        def f(m: re.Match) -> str:
            title,link = m.groups()
            if link.startswith("/"):
                link = f"https://roadmap.sh{link}"
            return f"{title}({link})"
        
        return re.sub(r"(\[.*?\])\((.*?)\)", f, text)

    async def prepare_file_embed(self, path: str):
        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            content = await f.read()

        page = commands.Paginator(prefix="", suffix="")
        _ADD_LINE = True
        main = []
        for line in content.splitlines():
            if line.startswith("---"):
                _ADD_LINE = not _ADD_LINE
                continue
            if _ADD_LINE:
                line = self.remove_img_links(line)
                line = self.replace_partial_links(line)
                page.add_line(line)

        interference = PaginatorEmbedInterface(self.view.ctx, page, owner=self.view.ctx.author)
        await interference.send_to(self.view.ctx.channel)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        folder = self.values[0]
        if os.path.isdir(folder):
            await self.view.message.edit(
                embed=discord.Embed(
                    title="Developer Roadmaps",
                    description=f"**{folder}**",
                    url="https://roadmap.sh/",
                )
            )
            await self.prepare_file_embed(os.path.join(folder, "README.md"))