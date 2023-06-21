from __future__ import annotations

import datetime
from time import time
from typing import TYPE_CHECKING, Any, List, Optional, Union

import discord
from core import Cog

if TYPE_CHECKING:
    from pymongo.collection import Collection
    from pymongo.typings import _DocumentType
    from typing_extensions import TypeAlias

    from core import Parrot

    DocumentType: TypeAlias = _DocumentType

import logging

log = logging.getLogger("events.on_rexn")
TWO_WEEK = 1209600
# 60 * 60 * 24 * 7 * 2


class OnReaction(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    async def _add_reactor(self, payload: discord.RawReactionActionEvent) -> None:
        log.info("Reaction adding sequence started, %s", payload)
        if not payload.guild_id:
            return

        CURRENT_TIME = time()
        DATETIME: datetime.datetime = discord.utils.snowflake_time(payload.message_id)
        if (
            payload.channel_id
            in self.bot.guild_configurations_cache[payload.guild_id][
                "starboard_config"
            ]["ignore_channel"]
        ):
            log.info("Channel ignored %s", payload.channel_id)
            return

        max_duration = (
            self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"][
                "max_duration"
            ]
            or TWO_WEEK
        )

        if (CURRENT_TIME - DATETIME.timestamp()) > max_duration:
            log.info("Message too old %s", DATETIME)
            return

        self_star = self.bot.guild_configurations_cache[payload.guild_id][
            "starboard_config"
        ].get("can_self_star", False)

        log.info(
            "Configurations loaded, CURRENT_TIME=%s MAX_DURATION=%s SELF_STAR=%s",
            CURRENT_TIME,
            max_duration,
            self_star,
        )

        msg: Optional[discord.Message] = await self.bot.get_or_fetch_message(  # type: ignore
            payload.channel_id, payload.message_id
        )
        if not msg:
            log.info("Message not found %s-%s", payload.channel_id, payload.message_id)
            return  # rare case

        if payload.user_id == msg.author.id and not self_star:
            log.info("Self star not allowed %s", payload.user_id)
            return

        collection: Collection = self.bot.starboards
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
            log.info("Starboard post found %s", data)
            await self.edit_starbord_post(payload, **data)
            return

        await self.__on_star_reaction_add(payload)
        return

    async def _remove_reactor(self, payload: discord.RawReactionActionEvent) -> None:
        if not payload.guild_id:
            return

        CURRENT_TIME = time()
        DATETIME: datetime.datetime = discord.utils.snowflake_time(payload.message_id)
        if (
            payload.channel_id
            in self.bot.guild_configurations_cache[payload.guild_id][
                "starboard_config"
            ]["ignore_channel"]
        ):
            return
        max_duration = (
            self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"][
                "max_duration"
            ]
            or TWO_WEEK
        )
        if (CURRENT_TIME - DATETIME.utcnow().timestamp()) > max_duration:
            return

        self_star = self.bot.guild_configurations_cache[payload.guild_id][
            "starboard_config"
        ].get("can_self_star", False)

        msg: Optional[discord.Message] = await self.bot.get_or_fetch_message(  # type: ignore
            payload.channel_id, payload.message_id
        )
        if not msg:
            return  # rare case

        if payload.user_id == msg.author.id and not self_star:
            log.info("Self star not allowed %s", payload.user_id)
            return

        collection: Collection = self.bot.starboards
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
            if (
                message.attachments[0]
                .url.lower()
                .endswith(("png", "jpeg", "jpg", "gif", "webp"))
            ):
                post["picture"] = message.attachments[0].url
            else:
                post["attachment"] = message.attachments[0].url

        return post

    async def get_star_count(
        self, message: Optional[discord.Message] = None, *, from_db: bool = True
    ) -> int:
        if message is None:
            return 0

        if from_db:
            if data := await self.bot.starboards.find_one(
                {
                    "$or": [
                        {"message_id.bot": message.id},
                        {"message_id.author": message.id},
                    ]
                }
            ):
                return len(data["starrer"])

        return next(
            (
                reaction.count
                for reaction in message.reactions
                if str(reaction.emoji) == "\N{WHITE MEDIUM STAR}"
            ),
            0,
        )

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
        return "\N{DIZZY SYMBOL}" if 25 > stars >= 10 else "\N{SPARKLES}"

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
            if (
                message.attachments[0]
                .url.lower()
                .endswith(("png", "jpeg", "jpg", "gif", "webp"))
            ):
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
        await self.bot.starboards.insert_one(post)

    async def edit_starbord_post(
        self, payload: discord.RawReactionActionEvent, **data: Any
    ) -> bool:
        ch: discord.TextChannel = await self.bot.getch(
            self.bot.get_channel,
            self.bot.fetch_channel,
            data["channel_id"],
        )
        if ch is None:
            log.info("Channel not found %s", data["channel_id"])
            return False

        try:
            starboard_channel: int = (
                self.bot.guild_configurations_cache[payload.guild_id][
                    "starboard_config"
                ]["channel"]
                or 0
            )
        except KeyError:
            return False
        else:
            starchannel: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, starboard_channel
            )

        msg: discord.Message = await self.bot.get_or_fetch_message(  # type: ignore
            starchannel, data["message_id"]["bot"]
        )
        main_message: discord.Message = await self.bot.get_or_fetch_message(  # type: ignore
            ch, data["message_id"]["author"]
        )
        if not msg.embeds:
            log.info("Message has no embeds")
            return False

        embed: discord.Embed = msg.embeds[0]

        count = await self.get_star_count(msg, from_db=True)

        if count == 0:
            await self.bot.starboards.delete_one({"message_id.bot": msg.id})
            log.info("Deleted starboard post %s", msg.id)
            await msg.delete(delay=0)
            return False

        embed.color = self.star_gradient_colour(count)

        await msg.edit(
            embed=embed,
            content=(
                f"{self.star_emoji(count)} {count} | In: {main_message.channel.mention} | Message ID: {main_message.id}\n"
                f"> {main_message.jump_url}"
            ),
        )
        return True

    async def __on_star_reaction_remove(
        self, payload: discord.RawReactionActionEvent
    ) -> bool:
        if not payload.guild_id:
            return False

        server_config = self.bot.guild_configurations_cache
        ch: discord.TextChannel = await self.bot.getch(
            self.bot.get_channel, self.bot.fetch_channel, payload.channel_id
        )

        if not ch:
            return False

        msg: Optional[discord.Message] = await self.bot.get_or_fetch_message(  # type: ignore
            ch, payload.message_id
        )
        try:
            limit = server_config[payload.guild_id]["starboard_config"]["limit"] or 0
        except KeyError:
            return False
        count = await self.get_star_count(msg, from_db=True)
        if limit > count:
            collection: Collection = self.bot.starboards
            data: DocumentType = await collection.find_one_and_delete(
                {"$or": [{"message_id.bot": msg.id}, {"message_id.author": msg.id}]},
            )
            if not data:
                return False
            try:
                channel: int = (
                    server_config[payload.guild_id]["starboard_config"]["channel"] or 0
                )
            except KeyError:
                return False

            starboard_channel: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, channel
            )
            bot_msg: Optional[discord.Message] = await self.bot.get_or_fetch_message(  # type: ignore
                starboard_channel, data["message_id"]["bot"], partial=True
            )
            if bot_msg:
                await bot_msg.delete(delay=0)
            return True
        return False

    async def __on_star_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> bool:
        if not payload.guild_id:
            return False

        data = self.bot.guild_configurations_cache

        try:
            locked: bool = data[payload.guild_id]["starboard_config"]["is_locked"]
        except KeyError:
            return False

        try:
            channel: int = data[payload.guild_id]["starboard_config"]["channel"]  # type: ignore
        except KeyError:
            return False
        
        channel: discord.TextChannel = await self.bot.getch(
            self.bot.get_channel, self.bot.fetch_channel, channel
        )

        if not locked:
            try:
                limit: int = data[payload.guild_id]["starboard_config"]["limit"] or 0
            except KeyError:
                return False

            ch: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, payload.channel_id
            )
            msg: Optional[discord.Message] = await self.bot.get_or_fetch_message(  # type: ignore
                ch, payload.message_id
            )
            if msg and msg.author.bot:
                return False

            count = await self.get_star_count(msg)

            if not limit:
                return False

            if count >= limit and msg:
                await self.star_post(starboard_channel=channel, message=msg)
                return True
        return False

    @Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]
    ):
        if isinstance(user, discord.User):
            return
        if (
            str(reaction.emoji)
            in {
                "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                "\N{FACE WITH PLEADING EYES}",
            }
            and user.id in self.bot.owner_ids  # type: ignore
        ):
            await self.bot.update_server_config_cache.start(user.guild.id)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        if guild := self.bot.get_guild(payload.guild_id):
            member = await self.bot.get_or_fetch_member(guild, payload.user_id)
        else:
            member = None

        if member is not None and member.bot:
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
        if isinstance(user, discord.User):
            return
        if (
            str(reaction.emoji)
            in {
                "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                "\N{FACE WITH PLEADING EYES}",
            }
            and user.id in self.bot.owner_ids  # type: ignore
        ):
            await self.bot.update_server_config_cache.start(user.guild.id)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        if guild := self.bot.get_guild(payload.guild_id):
            member = await self.bot.get_or_fetch_member(guild, payload.user_id)
        else:
            member = None
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
    async def on_reaction_clear(
        self, message: discord.Message, reactions: List[discord.Reaction]
    ):
        pass

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        if not payload.guild_id:
            return

        await self.bot.starboards.delete_one(
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
    async def on_raw_reaction_clear_emoji(
        self, payload: discord.RawReactionClearEmojiEvent
    ):
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(OnReaction(bot))
