from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from cogs.config.utils.ticket import TicketCreateView


if TYPE_CHECKING:
    from core import Parrot


class Ticket(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        async for message_id in self.bot.database.get_all_ticket_config_message_id():
            self.bot.add_view(TicketCreateView(), message_id=message_id)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Ticket(bot))
