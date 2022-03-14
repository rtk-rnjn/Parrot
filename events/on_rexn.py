from __future__ import annotations
from typing import Dict, List, Optional, Union

from core import Parrot, Cog
import discord


class OnReaction(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
    
    async def _add_reactor(self, payload: discord.RawReactionActionEvent) -> bool:
        collection = self.bot.mongo.parrot_db.starboard
        data = await collection.find_one_and_update(
            {"message_id": payload.message_id},
            {"$addToSet": {"starrer": payload.user_id}, "$inc": {"number_of_stars": 1}},
            return_document=True
        )
        if data:
            return await self.edit_starbord_post(payload, **data)
        else:
            return await self.__on_star_reaction_add(payload)

    async def _remove_reactor(self, payload: discord.RawReactionActionEvent) -> bool:
        collection = self.bot.mongo.parrot_db.starboard
        data = await collection.find_one_and_update(
            {"message_id": payload.message_id},
            {"$pull": {"starrer": payload.user_id}, "$inc": {"number_of_stars": -1}},
            return_document=True
        )
        if data:
            await self.edit_starbord_post(payload, **data)
        return await self.__on_star_reaction_remove(payload)

    async def __make_starboard_post(self,
        *,
        bot_message: discord.Message,
        message: discord.Message,
    ) -> Dict[str, Union[str, int, List[int], None]]:
        post = {
            "message_id": [bot_message.id, message.id],
            "channel_id": message.channel.id,
            "author_id": message.author.id,
            "guild_id": message.guild.id,
            "created_at": message.created_at.timestamp(),
            "content": message.content,
            "number_of_stars": await self.get_star_count(message, from_db=False),
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


    async def get_star_count(self, message: discord.Message, *, from_db: bool=True) -> Optional[int]:
        if from_db:
            if data := await self.bot.mongo.parrot_db.starboard.find_one({"message_id": message.id}):
                return data["number_of_stars"]

        for reaction in message.reactions:
            if str(reaction.emoji) == "\N{WHITE MEDIUM STAR}":
                return reaction.count
        return 0

    def star_gradient_colour(self, stars) -> int:
        p = stars / 13
        if p > 1.0:
            p = 1.0
        red = 255
        green = int((194 * p) + (253 * (1 - p)))
        blue = int((12 * p) + (247 * (1 - p)))
        return (red << 16) + (green << 8) + blue

    def star_emoji(self, stars) -> str:
        if 5 > stars >= 0:
            return '\N{WHITE MEDIUM STAR}'
        elif 10 > stars >= 5:
            return '\N{GLOWING STAR}'
        elif 25 > stars >= 10:
            return '\N{DIZZY SYMBOL}'
        else:
            return '\N{SPARKLES}'

    async def star_post(
        self, *, starboard_channel: discord.TextChannel, message: discord.Message
    ) -> None:
        embed = discord.Embed(timestamp=message.created_at)
        embed.set_footer(text=f"ID: {message.author.id}")
        
        count = await self.get_star_count(message, from_db=True)
        embed.color = self.star_gradient_colour(count)

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
        msg = await starboard_channel.send(
            f"{self.star_emoji(count)} {count} | In: {message.channel.mention} | Message ID: {message.id}\n> {message.jump_url}",
            embed=embed
        )

        self.bot.message_cache[msg.id] = msg
        self.bot.message_cache[message.id] = message

        post = await self.__make_starboard_post(bot_message=msg, message=message)
        await self.bot.mongo.parrot_db.starboard.insert_one(post)

    async def edit_starbord_post(self, payload: discord.RawReactionActionEvent, **data) -> bool:
        ch: discord.TextChannel = await self.bot.getch(self.bot.get_channel, self.bot.fetch_channel, data["channel_id"])
        if ch is None:
            return False

        if payload.user_id == self.bot.user.id:
            # message was reacted on bot's message
            bot_message_id = payload.message_id
        else:
            data["message_id"].remove(payload.message_id)
            bot_message_id = data["message_id"][0]

        msg: discord.Message = await self.bot.get_or_fetch_message(ch, bot_message_id)
        
        if not msg.embeds:
            # moderators removed the embeds
            return False

        embed: discord.Embed = msg.embeds[0]

        count = await self.get_star_count(msg, from_db=True)
        embed.color = self.star_gradient_colour(count)

        await msg.edit(
            embed=embed,
            content=f"{self.star_emoji(count)} {count} | In: {msg.channel.mention} | Message ID: {msg.id}\n> {msg.jump_url}",)
        return True

    async def __on_star_reaction_remove(self, payload) -> bool:
        server_config = self.bot.server_config
        ch = await self.bot.getch(
            self.bot.get_channel, self.bot.fetch_channel, payload.channel_id
        )
        msg = await self.bot.get_or_fetch_message(ch, payload.message_id)
        try:
            limit = server_config[payload.guild_id]["starboard"]["limit"]
        except KeyError:
            return False
        count = await self.get_star_count(msg, from_db=True)
        if limit > count:
            data = await self.bot.mongo.parrot_db.starboard.find_one_and_delete(
                {"message_id": msg.id}
            )
            if not data:
                return False
            try:
                channel = server_config[payload.guild_id]["starboard"]["channel"]
            except KeyError:
                return False
            msg_list = data["message_id"]
            msg_list.remove(msg.id)

            starboard_channel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, channel
            )
            bot_msg = await self.bot.get_or_fetch_message(
                starboard_channel, msg_list[0], partial=True
            )
            await bot_msg.delete(delay=0)
            return True
        return False

    async def __on_star_reaction_add(self, payload) -> bool:
        data = self.bot.server_config

        try:
            locked = data[payload.guild_id]["starboard"]["is_locked"]
        except KeyError:
            return False

        try:
            channel = data[payload.guild_id]["starboard"]["channel"]
        except KeyError:
            return False
        else:
            channel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, channel
            )

        if not locked:
            try:
                limit = data[payload.guild_id]["starboard"]["limit"]
            except KeyError:
                return False

            ch = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, payload.channel_id
            )
            msg: discord.Message = await self.bot.get_or_fetch_message(
                ch, payload.message_id
            )
            count = await self.get_star_count(msg)

            if count >= limit:
                await self.star_post(
                    starboard_channel=channel, message=msg
                )
                return True
        return False

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        pass

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):

        if not payload.guild_id:
            return

        if str(payload.emoji) == "\N{WHITE MEDIUM STAR}":
            await self._add_reactor(payload)

    @Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        pass

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id:
            return

        if str(payload.emoji) == "\N{WHITE MEDIUM STAR}":
            await self._remove_reactor(payload)

    @Cog.listener()
    async def on_reaction_clear(self, message, reactions):
        pass

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        pass

    @Cog.listener()
    async def on_reaction_clear_emoji(self, reaction):
        pass

    @Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload):
        pass


def setup(bot):
    bot.add_cog(OnReaction(bot))
