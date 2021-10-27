from __future__ import annotations

from core import Parrot, Cog

from discord.ext import commands
import discord, random

from utilities.database import parrot_db

with open('extra/duke_nekum.txt') as f:
    quotes = f.read().split('\n')


class SpamProt(Cog):
    def __init__(self, bot: Parrot):
        print('loaded')
        self.bot = bot
        self.collection = parrot_db['server_config']
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.member)
        
    async def delete(self, message: discord.Message, *, reason: str=None) -> None:
        def check(m: discord.Message):
            return m.author.id == message.author.id
        try:
            await message.channel.purge(5, check=check, reason=reason)
        except Exception:
            pass
    
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        print(1)
        if message.author.guild_permissions.administrator:
            if message.author.id == 741614468546560092:
                print(2)
                pass
            else:
                print(3)
                return
        bucket = self.cd_mapping.get_bucket(message)
        print(4)
        retry_after = bucket.update_rate_limit()
        print(5, retry_after)
        if retry_after:
            print(6)
            if data := await self.collection.find_one({'_id': message.guild.id, 'automod.spam.enable': {'$exists': True}}):
                print(7)
                if not data['automod']['spam']['enable']:
                    print(8)
                    return
                try:
                    ignore = data['automod']['spam']['channel']
                except KeyError:
                    ignore = []
                
                if message.channel.id in ignore:
                    return
                await self.delete(message)
                await message.channel.send(f"{message.author.mention} *{random.choice(quotes)}* **[Spam Protection] [Warning]**", delete_after=10)
