from __future__ import annotations

import datetime
from time import time
from typing import TYPE_CHECKING, Any, List, Literal, Optional, Union

import pymongo

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

    async def _factory_reactor(self, payload: discord.RawReactionActionEvent, *, tp: Literal["add", "remove"]) -> None:
        log.debug("Reaction %sing sequence started, %s", tp, payload)
        if not payload.guild_id:
            return

        CURRENT_TIME = time()
        DATETIME: datetime.datetime = discord.utils.snowflake_time(payload.message_id)
        if payload.channel_id in self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"]["ignore_channel"]:
            log.debug("Channel ignored %s", payload.channel_id)
            return

        max_duration = self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"]["max_duration"] or TWO_WEEK

        if (CURRENT_TIME - DATETIME.timestamp()) > max_duration:
            log.debug("Message too old %s", DATETIME)
            return

        self_star = self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"].get("can_self_star", False)

        try:
            locked: bool = self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"]["is_locked"]
        except KeyError:
            return

        log.debug(
            "Configurations loaded, CURRENT_TIME=%s MAX_DURATION=%s SELF_STAR=%s LOCKED=%s",
            CURRENT_TIME,
            max_duration,
            self_star,
            locked,
        )

        if locked:
            log.debug("Starboard locked")
            return

        msg: Optional[discord.Message] = await self.bot.get_or_fetch_message(payload.channel_id, payload.message_id)
        if not msg:
            log.debug("Message not found %s-%s", payload.channel_id, payload.message_id)
            return  # rare case

        if payload.user_id == msg.author.id and not self_star:
            log.debug("Self star not allowed %s", payload.user_id)
            return

        func = getattr(self, f"_on_star_reaction_{tp}")
        await func(payload, author_message=msg)
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

    async def get_star_count(self, message: Optional[discord.Message] = None, *, from_db: bool = True) -> int:
        stars = 0
        if message is None:
            return stars

        if data := await self.bot.starboards.find_one(
            {
                "$or": [
                    {"message_id.bot": message.id},
                    {"message_id.author": message.id},
                ]
            }
        ):
            stars = len(data["starrer"])

        count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == "\N{WHITE MEDIUM STAR}":
                count = reaction.count
                break

        return max(stars, count)

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

    async def star_post(self, *, starboard_channel: discord.TextChannel, message: discord.Message):
        count = await self.get_star_count(message)

        embed: discord.Embed = discord.Embed(timestamp=message.created_at, color=self.star_gradient_colour(count))
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
        await self.bot.starboards.insert_one(post)

    async def edit_starbord_post(self, payload: discord.RawReactionActionEvent, **data: Any):
        ch: discord.TextChannel = await self.bot.getch(
            self.bot.get_channel,
            self.bot.fetch_channel,
            data["channel_id"],
        )
        if ch is None:
            log.debug("Channel not found %s", data["channel_id"])
            return

        try:
            starboard_channel: int = (
                self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"]["channel"] or 0
            )
        except KeyError:
            return
        else:
            starchannel: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, starboard_channel
            )

        msg: discord.Message = await self.bot.get_or_fetch_message(starchannel, data["message_id"]["bot"])  # type: ignore
        main_message: discord.Message = await self.bot.get_or_fetch_message(ch, data["message_id"]["author"])  # type: ignore
        if msg and not msg.embeds:
            log.debug("Message has no embeds")
            return

        embed: discord.Embed = msg.embeds[0]

        count = await self.get_star_count(msg, from_db=True)

        if not count:
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

    async def _on_star_reaction_remove(
        self,
        payload: discord.RawReactionActionEvent,
        *,
        author_message: discord.Message,
    ):
        if not payload.guild_id:
            return False

        msg = author_message
        try:
            limit = self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"]["limit"] or 0
        except KeyError:
            return False

        count = await self.get_star_count(msg, from_db=True)

        collection: Collection = self.bot.starboards
        if limit > count:
            await self._delete_starboard_post(payload)
        else:
            data: DocumentType = await collection.find_one_and_update(
                {
                    "$or": [
                        {"message_id.bot": msg.id},
                        {"message_id.author": msg.id},
                    ]
                },
                {
                    "$pull": {"starrer": payload.user_id},
                    "$inc": {"number_of_stars": -1},
                },
                return_document=pymongo.ReturnDocument.AFTER,
            )
            if not data:
                return False
            if not data["starrer"]:
                await self._delete_starboard_post(payload)

            await self.edit_starbord_post(payload, **data)
        return False

    async def _delete_starboard_post(self, payload: discord.RawReactionActionEvent) -> bool:
        collection: Collection = self.bot.starboards
        ch = await self.bot.getch(self.bot.get_channel, self.bot.fetch_channel, payload.channel_id)
        msg: Optional[discord.Message] = await self.bot.get_or_fetch_message(ch, payload.message_id)
        data: DocumentType = await collection.find_one_and_delete(
            {"$or": [{"message_id.bot": msg.id}, {"message_id.author": msg.id}]},
        )
        if not data:
            return False
        try:
            channel: int = self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"]["channel"] or 0
        except KeyError:
            return False

        starboard_channel: discord.TextChannel = await self.bot.getch(self.bot.get_channel, self.bot.fetch_channel, channel)

        bot_msg: Optional[discord.Message] = await self.bot.get_or_fetch_message(  # type: ignore
            starboard_channel, data["message_id"]["bot"]
        )

        if bot_msg:
            await bot_msg.delete(delay=0)
        return True

    async def _on_star_reaction_add(
        self,
        payload: discord.RawReactionActionEvent,
        *,
        author_message: discord.Message,
    ):
        if not payload.guild_id:
            return

        msg = author_message

        if data := await self.bot.starboards.find_one_and_update(
            {"$or": [{"message_id.bot": msg.id}, {"message_id.author": msg.id}]},
            {
                "$addToSet": {"starrer": payload.user_id},
                "$inc": {"number_of_stars": 1},
            }
        ):
            await self.edit_starbord_post(payload, **data)
            return

        count = await self.get_star_count(msg)

        try:
            limit = self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"]["limit"] or 0
        except KeyError:
            return

        try:
            channel: int = self.bot.guild_configurations_cache[payload.guild_id]["starboard_config"]["channel"] or 0
        except KeyError:
            return
        else:
            starboard_channel: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, channel
            )
        if not limit:
            return

        if count >= limit and msg:
            await self.star_post(starboard_channel=starboard_channel, message=msg)
            return

    @Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]):
        if isinstance(user, discord.User):
            return
        if (
            str(reaction.emoji)
            in {
                "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                "\N{FACE WITH PLEADING EYES}",
            }
            and user.id in self.bot.owner_ids
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
            await self._factory_reactor(payload, tp="add")

    @Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]):
        if isinstance(user, discord.User):
            return
        if (
            str(reaction.emoji)
            in {
                "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                "\N{FACE WITH PLEADING EYES}",
            }
            and user.id in self.bot.owner_ids
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
            await self._factory_reactor(payload, tp="remove")

    @Cog.listener()
    async def on_reaction_clear(self, message: discord.Message, reactions: List[discord.Reaction]):
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
    async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionClearEmojiEvent):
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(OnReaction(bot))
