from __future__ import annotations

import re
from typing import Any

import discord

from core import Parrot, Cog


class CodeSnippets(Cog):
    """
    Cog that parses and sends code snippets to Discord.
    Matches each message against a regex and prints the contents of all matched snippets.
    """

    def __init__(self, bot: Parrot):
        """Initializes the cog's bot."""
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Checks if the message has a snippet link, removes the embed, then sends the snippet contents."""
        if message.author.bot:
            return


def setup(bot: Parrot) -> None:
    """Load the CodeSnippets cog."""
    bot.add_cog(CodeSnippets(bot))
