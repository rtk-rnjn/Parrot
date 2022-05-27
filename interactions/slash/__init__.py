from __future__ import annotations

from core import Cog, Parrot

from discord.ext import commands
from discord import app_commands
import discord

class ContextMenu(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

        self.ctx_menu = app_commands.ContextMenu(
            name="Interpret as command",
            # description="Interpret the message as a command.",
            guild_ids=[guild.id for guild in bot.guilds],
            callback=self.ctx_menu
        )
        self.bot.tree.add_command(self.ctx_menu)
    
    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu)
    
    async def ctx_menu(self, interaction: discord.Interaction, message: discord.Message) -> None:
        await interaction.response.send_message('hello...')


async def setup(bot: Parrot) -> None:
    await bot.add_cog(ContextMenu(bot))