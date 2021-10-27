from __future__ import annotations

from core import Parrot, Cog

from discord.ext import commands
import discord

from utilities.database import parrot_db


class SpamProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['server_config']
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.Member)
        
    async def delete(self, message: discord.Message, *, reason: str=None) -> None:
        try:
            await message.delete(reason=reason)
        except Exception:
            pass
    
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        
        bucket = self.cd_mapping.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        