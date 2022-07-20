from __future__ import annotations

import datetime
from time import time
from typing import Any, Dict, List, Optional, Union

import discord
from core import Cog, Parrot
from pymongo.collection import Collection
from pymongo.typings import _DocumentType as DocumentType

TWO_WEEK = 1209600
# 60 * 60 * 24 * 7 * 2


class OnReaction(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    async def _add_reactor(self, payload: discord.RawReactionActionEvent) -> None:
        CURRENT_TIME = time()
        DATETIME: datetime.datetime = discord.utils.snowflake_time(payload.message_id)
        try:
            if (
                payload.channel_id
                in self.bot.server_config[payload.guild_id]["starboard"]["ignore_channel"]
            ):
                return False
        except KeyError:
            pass

        try:
            max_duration = (
                self.bot.server_config[payload.guild_id]["starboard"]["max_duration"] or TWO_WEEK
            )
        except KeyError:
            if (CURRENT_TIME - DATETIME.timestamp()) > TWO_WEEK:
                return
        else:
            if (CURRENT_TIME - DATETIME.timestamp()) > max_duration:
                return

        collection: Collection = self.bot.mongo.parrot_db.starboard
        data = await collection.find_one_and_update(
            {
                "$or": [
                    {"message_id.bot": payload.message_id},
                    {"message_id.author": payload.message_id},
                ]
            },
            {"$addToSet": {"starrer": payload.user_id}, "$inc": {"number_of_stars": 1}},
            return_document=True,
        )
        if data:
            await self.edit_starbord_post(payload, **data)
            return

        await self.__on_star_reaction_add(payload)
        return

    async def _remove_reactor(self, payload: discord.RawReactionActionEvent) -> None:
        CURRENT_TIME = time()
        DATETIME: datetime.datetime = discord.utils.snowflake_time(payload.message_id)
        try:
            if (
                payload.channel_id
                in self.bot.server_config[payload.guild_id]["starboard"]["ignore_channel"]
            ):
                return
        except KeyError:
            pass

        try:
            max_duration = (
                self.bot.server_config[payload.guild_id]["starboard"]["max_duration"] or TWO_WEEK
            )
        except KeyError:
            if (CURRENT_TIME - DATETIME.utcnow().timestamp()) > TWO_WEEK:
                return
        else:
            if (CURRENT_TIME - DATETIME.utcnow().timestamp()) > max_duration:
                return

        collection: Collection = self.bot.mongo.parrot_db.starboard
        data = await collection.find_one_and_update(
            {
                "$or": [
                    {"message_id.bot": payload.message_id},
                    {"message_id.author": payload.message_id},
                ]
            },
            {"$pull": {"starrer": payload.user_id}, "$inc": {"number_of_stars": -1}},
            return_document=True,
        )
        if data:
            await self.edit_starbord_post(payload, **data)
            return

        await self.__on_star_reaction_remove(payload)
        return

    async def __make_starboard_post(
        self,
        *,
        bot_message: discord.Message,
        message: discord.Message,
    ) -> dict:
        post = {
            "message_id": {"bot": bot_message.id, "author": message.id},
            "channel_id": message.channel.id,
            "author_id": message.author.id,
            "guild_id": message.guild.id,
            "created_at": message.created_at.timestamp(),
            "content": message.content,
            "number_of_stars": await self.get_star_count(message, from_db=False),
            "starrer": [message.author.id],
        }

        if message.attachments:
            if message.attachments[0].url.lower().endswith(("png", "jpeg", "jpg", "gif", "webp")):
                post["picture"] = message.attachments[0].url
            else:
                post["attachment"] = message.attachments[0].url

        return post

    async def get_star_count(
        self, message: Optional[discord.Message] = None, *, from_db: bool = True
    ) -> int:
        if not message:
            return 0

        if from_db:
            if data := await self.bot.mongo.parrot_db.starboard.find_one(
                {
                    "$or": [
                        {"message_id.bot": message.id},
                        {"message_id.author": message.id},
                    ]
                }
            ):
                return len(data["starrer"])

        for reaction in message.reactions:
            if str(reaction.emoji) == "\N{WHITE MEDIUM STAR}":
                return reaction.count
        return 0

    def star_gradient_colour(self, stars: int) -> int:
        p = stars / 13
        p = min(p, 1.0)
        red = 255
        green = int((194 * p) + (253 * (1 - p)))
        blue = int((12 * p) + (247 * (1 - p)))
        return (red << 16) + (green << 8) + blue

    def star_emoji(self, stars: int) -> str:
        if 5 > stars >= 0:
            return "\N{WHITE MEDIUM STAR}"
        if 10 > stars >= 5:
            return "\N{GLOWING STAR}"
        if 25 > stars >= 10:
            return "\N{DIZZY SYMBOL}"
        return "\N{SPARKLES}"

    async def star_post(
        self, *, starboard_channel: discord.TextChannel, message: discord.Message
    ) -> None:
        count = await self.get_star_count(message, from_db=True)

        embed: discord.Embed = discord.Embed(
            timestamp=message.created_at, color=self.star_gradient_colour(count)
        )
        embed.set_footer(text=f"ID: {message.author.id}")

        embed.set_author(
            name=str(message.author),
            icon_url=message.author.display_avatar.url,
            url=message.jump_url,
        )
        if message.content:
            embed.description = message.content
        if message.attachments:
            if message.attachments[0].url.lower().endswith(("png", "jpeg", "jpg", "gif", "webp")):
                embed.set_image(url=message.attachments[0].url)
            else:
                embed.add_field(
                    name="Attachment",
                    value=f"[{message.attachments[0].filename}]({message.attachments[0].url})",
                )
        msg: discord.Message = await starboard_channel.send(
            f"{self.star_emoji(count)} {count} | In: {message.channel.mention} | Message ID: {message.id}\n> {message.jump_url}",
            embed=embed,
        )

        self.bot.message_cache[msg.id] = msg
        self.bot.message_cache[message.id] = message

        post = await self.__make_starboard_post(bot_message=msg, message=message)
        await self.bot.mongo.parrot_db.starboard.insert_one(post)

    async def edit_starbord_post(
        self, payload: discord.RawReactionActionEvent, **data: Any
    ) -> bool:
        ch: discord.TextChannel = await self.bot.getch(
            self.bot.get_channel,
            self.bot.fetch_channel,
            data["channel_id"],
        )
        if ch is None:
            return False

        bot_message_id = data["message_id"]["bot"]
        main_message = data["message_id"]["author"]
        try:
            starboard_channel: int = (
                self.bot.server_config[payload.guild_id]["starboard"]["channel"] or 0
            )
        except KeyError:
            return False
        else:
            starchannel: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, starboard_channel
            )

        msg: discord.Message = await self.bot.get_or_fetch_message(starchannel, bot_message_id)
        main_message: discord.Message = await self.bot.get_or_fetch_message(ch, main_message)
        if not msg.embeds:
            # moderators removed the embeds
            return False

        embed: discord.Embed = msg.embeds[0]

        count = await self.get_star_count(msg, from_db=True)
        embed.color = self.star_gradient_colour(count)

        await msg.edit(
            embed=embed,
            content=(
                f"{self.star_emoji(count)} {count} | In: {main_message.channel.mention} | Message ID: {main_message.id}\n"
                f"> {main_message.jump_url}"
            ),
        )
        return True

    async def __on_star_reaction_remove(self, payload: discord.RawReactionActionEvent) -> bool:
        server_config = self.bot.server_config
        ch: discord.TextChannel = await self.bot.getch(
            self.bot.get_channel, self.bot.fetch_channel, payload.channel_id
        )

        if not ch:
            return False

        msg = await self.bot.get_or_fetch_message(ch, payload.message_id)
        try:
            limit = server_config[payload.guild_id]["starboard"]["limit"] or 0
        except KeyError:
            return False
        count = await self.get_star_count(msg, from_db=True)
        if limit > count:
            collection: Collection = self.bot.mongo.parrot_db.starboard
            data: DocumentType = await collection.find_one_and_delete(
                {"$or": [{"message_id.bot": msg.id}, {"message_id.author": msg.id}]},
            )
            if not data:
                return False
            try:
                channel: int = server_config[payload.guild_id]["starboard"]["channel"] or 0
            except KeyError:
                return False

            starboard_channel: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, channel
            )
            bot_msg: discord.Message = await self.bot.get_or_fetch_message(
                starboard_channel, data["message_id"]["bot"], partial=True
            )
            await bot_msg.delete(delay=0)
            return True
        return False

    async def __on_star_reaction_add(self, payload: discord.RawReactionActionEvent) -> bool:
        data = self.bot.server_config

        try:
            locked: bool = data[payload.guild_id]["starboard"]["is_locked"]
        except KeyError:
            return False

        try:
            channel = data[payload.guild_id]["starboard"]["channel"]
        except KeyError:
            return False
        else:
            channel: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, channel
            )

        if not locked:
            try:
                limit: int = data[payload.guild_id]["starboard"]["limit"] or 0
            except KeyError:
                return False

            ch: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, payload.channel_id
            )
            msg: discord.Message = await self.bot.get_or_fetch_message(ch, payload.message_id)
            if msg.author.bot:
                return False

            count = await self.get_star_count(msg)

            if not limit:
                return False

            if count >= limit:
                await self.star_post(starboard_channel=channel, message=msg)
                return True
        return False

    @Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]
    ):
        if (
            str(reaction.emoji)
            in (
                "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                "\N{FACE WITH PLEADING EYES}",
            )
            and user.id in self.bot.owner_ids
        ):
            await self.bot.update_server_config_cache.start(user.guild.id)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = await self.bot.get_or_fetch_member(guild, payload.user_id)

        if member.bot:
            return

        try:
            self.bot.banned_users[payload.user_id]
        except KeyError:
            pass
        else:
            if self.bot.banned_users[payload.user_id].get("global"):
                return

        if str(payload.emoji) == "\N{WHITE MEDIUM STAR}":
            await self._add_reactor(payload)

    @Cog.listener()
    async def on_reaction_remove(
        self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]
    ):
        if (
            str(reaction.emoji)
            in (
                "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                "\N{FACE WITH PLEADING EYES}",
            )
            and user.id in self.bot.owner_ids
        ):
            await self.bot.update_server_config_cache.start(user.guild.id)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = await self.bot.get_or_fetch_member(guild, payload.user_id)

        if member is None:
            return

        if member.bot:
            return

        try:
            self.bot.banned_users[payload.user_id]
        except KeyError:
            pass
        else:
            if self.bot.banned_users[payload.user_id].get("global"):
                return

        if str(payload.emoji) == "\N{WHITE MEDIUM STAR}":
            await self._remove_reactor(payload)

    @Cog.listener()
    async def on_reaction_clear(self, message: discord.Message, reactions: List[discord.Reaction]):
        pass

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        if not payload.guild_id:
            return

        await self.bot.mongo.parrot_db.starboard.delete_one(
            {
                "$or": [
                    {"message_id.bot": payload.message_id},
                    {"message_id.author": payload.message_id},
                ]
            },
        )

    @Cog.listener()
    async def on_reaction_clear_emoji(self, reaction: discord.Reaction):
        pass

    @Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionClearEmojiEvent):
        pass

        # if not payload.guild_id:
        #     return

        # if str(payload.emoji) == "\N{WHITE MEDIUM STAR}":
        #     await self._remove_reactor(payload)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(OnReaction(bot))
