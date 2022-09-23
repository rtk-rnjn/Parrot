from __future__ import annotations

import contextlib
import discord

from core import Parrot, Cog

UPLOAD_CHANNEL_ID = 1021553838135713944
RULES_CHANNEL_ID = 1021457186997682308
PEGGY_PLAYZ = 971797000246923334


class PeggyPlayZ(Cog):
    """Command Events for the server Peggy PlayZ"""
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.channel.id == UPLOAD_CHANNEL_ID:
            with contextlib.suppress(discord.HTTPException):
                await message.publish()
                await message.add_reaction("\N{EYES}")

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id == PEGGY_PLAYZ:
            channel = self.bot.get_channel(RULES_CHANNEL_ID)
            if channel is not None:
                await channel.send(member.mention, delete_after=1)
