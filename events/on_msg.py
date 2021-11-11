from __future__ import annotations

from core import Parrot, Cog

from discord.ext import commands

import aiohttp, re, asyncio, json
from discord import Webhook
from utilities.database import parrot_db
from utilities.regex import LINKS_NO_PROTOCOLS

collection = parrot_db['global_chat']

with open('extra/profanity.json') as f:
    bad_dict = json.load(f)

class OnMsg(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.channel)
        self.collection = None

    def refrain_message(self, msg: str):
        if 'chod' in msg:
            return False
        for bad_word in bad_dict:
            if bad_word.lower() in msg:
                return False
        return True

    async def is_banned(self, user) -> bool:
        if self.collection is None:
            db = await self.bot.db('parrot_db')
            self.collection = db['banned_users']
        if data := await self.collection.find_one({'_id': user.id}):
            if data['chat'] or data['global']:
                return True
        else:
            return False

    @Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        
        channel = await collection.find_one({
            '_id': message.guild.id,
            'channel_id': message.channel.id
        })

        if not channel: return

        bucket = self.cd_mapping.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            return await message.channel.send(
                f"{message.author.mention} Chill out | You reached the limit | Continous spam may leads to ban from global-chat | **Send message after {round(retry_after, 3)}s**", delete_after=10)

        guild = await collection.find_one({'_id': message.guild.id})
        # data = await collection.find({})

        role = message.guild.get_role(guild['ignore-role'])
        if role:
            if role in message.author.roles:
                return

        if message.content.startswith(("$", "!", "%", "^", "&", "*", "-", ">", "/")):
            return

        urls = LINKS_NO_PROTOCOLS.search(message.content)
        if urls:
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | URLs aren't allowed.",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | URLs aren't allowed.",
                    delete_after=5)

        if "discord.gg" in message.content.lower():
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | Advertisements aren't allowed.",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | Advertisements aren't allowed.",
                    delete_after=5)
        if len(message.content.split('\n')) > 4:
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                    delete_after=5)

        if "discord.com" in message.content.lower():
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | Advertisements aren't allowed.",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | Advertisements aren't allowed.",
                    delete_after=5)

        to_send = self.refrain_message(message.content.lower())
        if to_send:
            pass
        elif not to_send:
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | Sending Bad Word not allowed",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | Sending Bad Word not allowed",
                    delete_after=5)
        is_user_banned = await self.is_banned(message.author)
        if is_user_banned:
            return
        try:
            await asyncio.sleep(0.1)
            await message.delete()
        except:
            return await message.channel.send(
                "Bot requires **Manage Messages** permission(s) to function properly."
            )

        async for webhook in collection.find({}):
            hook = webhook['webhook']
            if hook:
                try:                
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(f"{hook}", session=session)
                        await webhook.send(
                                content=message.clean_content,
                                username=f"{message.author}",
                                avatar_url=message.author.display_avatar.url)
                except discord.NotFound:
                    await collection.delete_one({'webhook': hook})
                    continue

    @Cog.listener()
    async def on_message_delete(self, message):
        pass

    @Cog.listener()
    async def on_bulk_message_delete(self, messages):
        pass

    @Cog.listener()
    async def on_raw_message_delete(self, payload):
        # guild_id = payload.guild_id
        # collection = parrot_db['ticket']
        # if data := await collection.find_one({'_id': guild_id}):
        #     if data['message_id'] == payload.message_id:
        #         await collection.update_one({'_id': channel.guild.id}, {'$set': {'message_id': None, 'channel_id': None}})
        pass

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        pass

    @Cog.listener()
    async def on_message_edit(self, before, after):
        pass

    @Cog.listener()
    async def on_raw_message_edit(self, payload):
        pass


def setup(bot):
    bot.add_cog(OnMsg(bot))
