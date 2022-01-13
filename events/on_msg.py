from __future__ import annotations

from core import Parrot, Cog

from discord.ext import commands

import aiohttp
import asyncio
import discord
import io
import json
from discord import Webhook


import typing as tp

from utilities.database import parrot_db, msg_increment
from utilities.regex import LINKS_NO_PROTOCOLS, INVITE_RE
from time import time

collection = parrot_db["global_chat"]

with open("extra/profanity.json") as f:
    bad_dict = json.load(f)

TRIGGER = (
    'ok google,',
    'ok google ',
    'hey google,',
    'hey google ',
)

class OnMsg(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.channel
        )
        self.collection = None
        self.log_collection = parrot_db["logging"]

    async def query_ddg(self, query: str) -> tp.Optional[str]:
        link = "https://api.duckduckgo.com/?q={}&format=json&pretty=1".format(query)
        # saying `ok google`, and querying from ddg LOL. 
        res = await self.bot.session.get(link)
        data = await res.json()
        if data.get('Abstract'):
            return data.get('Abstract')
        if data['RelatedTopics']:
            return data['RelatedTopics'][0]['Text']

    async def quick_answer(self, message: discord.Message):
        """This is good."""
        if message.content.lower().startswith(TRIGGER):
            if message.content.lower().startswith('ok'):
                query = message.content.lower()[10:]
                res = await self.query_ddg(query)
                if not res:
                    return
                try:
                    return await message.channel.send(res)
                except discord.Forbidden:
                    pass
            if message.content.lower().startswith('hey'):
                query = message.content.lower()[11:]
                res = await self.query_ddg(query)
                if not res:
                    return
                try:
                    return await message.channel.send(res)
                except discord.Forbidden:
                    pass

    def refrain_message(self, msg: str):
        if "chod" in msg.replace(",", "").split(" "):
            return False
        for bad_word in bad_dict:
            if bad_word.lower() in msg.replace(",", "").split(" "):
                return False
        return True

    async def is_banned(self, user) -> bool:
        if self.collection is None:
            db = await self.bot.db("parrot_db")
            self.collection = db["banned_users"]
        if data := await self.collection.find_one({"_id": user.id}):
            if data["chat"] or data["global"]:
                return True
        else:
            return False

    async def on_invite(self, message: discord.Message, invite_link: list):
        if data := await self.log_collection.find_one(
            {"_id": message.guild.id, "on_invite_post": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_invite_post"], session=self.bot.session
            )
            if webhook:
                content = f"""**Invite Link Posted**

`Author (ID):` **{message.author} [`{message.author.id}`]**
`Message ID :` **{message.id}**
`Jump URL   :` **{message.jump_url}**
`Invite Link:` **<{invite_link[0]}>**

`Content    :` **{message.content[:250:]}**
"""
                msg = message
                if content:
                    fp = io.BytesIO(
                        f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n".encode()
                    )
                else:
                    fp = io.BytesIO("NOTHING HERE".ecnode())
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )

    @Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return
        await msg_increment(message.guild.id, message.author.id)  # for gw only
        await self.quick_answer(message)
        channel = await collection.find_one(
            {"_id": message.guild.id, "channel_id": message.channel.id}
        )
        if links := INVITE_RE.findall(message.content):
            await self.on_invite(message, links)

        if channel:
            bucket = self.cd_mapping.get_bucket(message)
            retry_after = bucket.update_rate_limit()

            if retry_after:
                return await message.channel.send(
                    f"{message.author.mention} Chill out | You reached the limit | Continous spam may leads to ban from global-chat | **Send message after {round(retry_after, 3)}s**",
                    delete_after=10,
                )

            guild = await collection.find_one({"_id": message.guild.id})
            # data = await collection.find({})

            role = message.guild.get_role(guild["ignore-role"])
            if role:
                if role in message.author.roles:
                    return

            if message.content.startswith(
                ("$", "!", "%", "^", "&", "*", "-", ">", "/", "\\")
            ):  # bot commands or mention in starting
                return

            urls = LINKS_NO_PROTOCOLS.search(message.content)
            if urls:
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | URLs aren't allowed.",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | URLs aren't allowed.",
                        delete_after=5,
                    )

            if "discord.gg" in message.content.lower():
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | Advertisements aren't allowed.",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | Advertisements aren't allowed.",
                        delete_after=5,
                    )
            if len(message.content.split("\n")) > 4:
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                        delete_after=5,
                    )

            if "discord.com" in message.content.lower():
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | Advertisements aren't allowed.",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | Advertisements aren't allowed.",
                        delete_after=5,
                    )

            to_send = self.refrain_message(message.content.lower())
            if to_send:
                pass
            elif not to_send:
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | Sending Bad Word not allowed",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | Sending Bad Word not allowed",
                        delete_after=5,
                    )
            is_user_banned = await self.is_banned(message.author)
            if is_user_banned:
                return
            try:
                await asyncio.sleep(0.1)
                await message.delete()
            except Exception:
                return await message.channel.send(
                    "Bot requires **Manage Messages** permission(s) to function properly."
                )

            async for webhook in collection.find({}):
                hook = webhook["webhook"]
                if hook:
                    try:
                        async with aiohttp.ClientSession() as session:
                            webhook = Webhook.from_url(f"{hook}", session=session)
                            await webhook.send(
                                content=message.content,
                                username=f"{message.author}",
                                avatar_url=message.author.display_avatar.url,
                                allowed_mentions=discord.AllowedMentions.none(),
                            )
                    except Exception:
                        continue

    @Cog.listener()
    async def on_message_delete(self, message):
        pass

    @Cog.listener()
    async def on_bulk_message_delete(self, messages):
        pass

    @Cog.listener()
    async def on_raw_message_delete(self, payload):
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_message_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_message_delete"], session=self.bot.session
            )
            if webhook:
                if payload.cached_message:
                    msg = payload.cached_message
                    message_author = msg.author
                    if (message_author.id == self.bot.user.id) or message_author.bot:
                        return
                    content = msg.content
                else:
                    guild = self.bot.get_guild(payload.guild_id)
                    message_author = None
                    content = None

                main_content = f"""**Message Delete Event**

`ID      :` **{payload.message_id}**
`Channel :` **<#{payload.channel_id}>**
`Author  :` **{message_author}**
`Deleted at:` **<t:{int(time())}>**
"""
                if content:
                    fp = io.BytesIO(
                        f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n".encode()
                    )
                else:
                    fp = io.BytesIO("NOTHING HERE".ecnode())
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_bulk_message_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_bulk_message_delete"], session=self.bot.session
            )
            main = ""
            if webhook:
                if payload.cached_messages:
                    msgs = payload.cached_messages
                else:
                    msgs = []
                for msg in msgs:
                    if not msg.bot:
                        main += f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n"
                if msgs:
                    fp = io.BytesIO(main.encode())
                else:
                    fp = io.BytesIO("NOTHING HERE", filename="content.txt")
                main_content = f"""**Bulk Message Delete**

`Total Messages:` **{len(msgs)}**
`Channel       :` **<#{payload.channel_id}>**
"""
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )

    @Cog.listener()
    async def on_message_edit(self, before, after):
        pass

    @Cog.listener()
    async def on_raw_message_edit(self, payload):
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_message_edit": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_message_edit"], session=self.bot.session
            )
            if webhook:
                if payload.cached_message:
                    msg = payload.cached_message
                    message_author = msg.author
                    if message_author.bot:
                        return
                    content = msg.content
                else:
                    # guild = self.bot.get_guild(payload.guild_id)
                    message_author = None
                    content = None

                main_content = f"""**Message Edit Event**

`ID       :` **{payload.message_id}**
`Channel  :` **<#{payload.channel_id}>**
`Author   :` **{message_author}**
`Edited at:` **<t:{int(time())}>**
`Jump URL :` **<https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}>**
"""
                if content:
                    fp = io.BytesIO(
                        f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n".encode()
                    )
                else:
                    fp = io.BytesIO("NOTHING HERE".ecnode())
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )


def setup(bot):
    bot.add_cog(OnMsg(bot))
