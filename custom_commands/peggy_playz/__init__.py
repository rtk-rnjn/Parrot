from __future__ import annotations

import asyncio

import discord
from core import Cog, Parrot

UPLOAD_CHANNEL_ID = 1021553838135713944
RULES_CHANNEL_ID = 1021457186997682308
PEGGY_PLAYZ = 971797000246923334
PINGCORD = 282286160494067712


class PeggyPlayZ(Cog):
    """Command Events for the server Peggy PlayZ."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.ON_TESTING = False

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        if message.channel.id == UPLOAD_CHANNEL_ID and message.author.id == PINGCORD:
            if message.channel.permissions_for(message.guild.me).manage_messages:  # type: ignore
                await message.publish()
            if message.channel.permissions_for(message.guild.me).add_reactions:  # type: ignore
                await message.add_reaction("\N{EYES}")

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id == PEGGY_PLAYZ:
            channel = self.bot.get_channel(RULES_CHANNEL_ID)
            if channel is not None:
                if not channel.permissions_for(member.guild.me).send_messages:  # type: ignore
                    return
                await channel.send(member.mention, delete_after=1)  # type: ignore

    @Cog.listener("on_message")
    async def on_announcement_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)
        if (
            message.guild is not None
            and message.guild.id == PEGGY_PLAYZ
            and (isinstance(message.channel, discord.TextChannel) and message.channel.is_news())
            and message.channel.id != UPLOAD_CHANNEL_ID
            and message.channel.permissions_for(message.guild.me).manage_messages
        ):
            await message.publish()
