from __future__ import annotations

from collections import deque

import discord
from core import Cog, Parrot
from discord.ext import commands


class SnipeMessageListener(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.snipes: dict[int, deque[discord.Message]] = {}
        self.edit_snipes: dict[int, deque[tuple[discord.Message, discord.Message]]] = {}

    @Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        if message.channel.id not in self.snipes:
            self.snipes[message.channel.id] = deque(maxlen=2**5)

        self.snipes[message.channel.id].appendleft(message)

    def get_snipe(self, channel: discord.TextChannel, *, index: int) -> discord.Message:
        if channel.id not in self.snipes:
            msg = "No messages have been sniped in this channel"
            raise commands.BadArgument(msg)

        index -= 1
        if index < 0:
            msg = "Index must be positive"
            raise commands.BadArgument(msg)
        if index > len(self.snipes[channel.id]):
            msg = f"Index must be less than {len(self.snipes[channel.id])}"
            raise commands.BadArgument(msg)
        return self.snipes[channel.id][index]

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        if not before.guild:
            return

        if before.content == after.content:
            return

        if before.channel.id not in self.edit_snipes:
            self.edit_snipes[before.channel.id] = deque(maxlen=2**5)

        self.edit_snipes[before.channel.id].appendleft((before, after))

    def get_edit_snipe(self, channel: discord.TextChannel, *, index: int) -> tuple[discord.Message, discord.Message]:
        if channel.id not in self.edit_snipes:
            msg = "No messages have been edited in this channel"
            raise commands.BadArgument(msg)

        index -= 1
        if index < 0:
            msg = "Index must be positive"
            raise commands.BadArgument(msg)
        if index > len(self.edit_snipes[channel.id]):
            msg = f"Index must be less than {len(self.edit_snipes[channel.id])}"
            raise commands.BadArgument(msg)
        return self.edit_snipes[channel.id][index]

    def delete_snipe(self, channel: discord.TextChannel, *, index: int) -> None:
        try:
            self.snipes[channel.id].remove(self.snipes[channel.id][index])
        except Exception:
            pass

    def delete_edit_snipe(self, channel: discord.TextChannel, *, index: int) -> None:
        try:
            self.edit_snipes[channel.id].remove(self.edit_snipes[channel.id][index])
        except Exception:
            pass
