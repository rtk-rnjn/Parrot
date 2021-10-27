from __future__ import annotations

from discord.ext import commands
import discord

import re

from core import Parrot, Cog


class EmojiCapsProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.data = {}
        self.update_data.start()

    async def get_emoji_count(self, message_content: str) -> int:
        str_count = len(re.findall(r'[\U0001f600-\U0001f650]', message_content))
        dis_count = len(re.findall(r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', message_content))
        return int(str_count + dis_count)
    
    async def get_caps_count(self, message_content: str) -> int:
        caps_count = len(re.findall(r'[A-Z]', message_content))
        return int(caps_count)
    
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        