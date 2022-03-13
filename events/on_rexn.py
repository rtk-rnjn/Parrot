from __future__ import annotations

from core import Parrot, Cog
from cogs.utils import star_method
import discord


class OnReaction(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    async def __on_star_reaction_remove(self, payload):
        data = self.bot.server_config
        ch = await self.bot.getch(
            self.bot.get_channel, self.bot.fetch_channel, payload.channel_id
        )
        msg = await self.bot.get_or_fetch_message(ch, payload.message_id)
        try:
            limit = data[payload.guild_id]["starboard"]["limit"]
        except KeyError:
            return
        if count := star_method.get_star_count(msg):
            if limit < count:
                data = await self.bot.mongo.parrot_db.starboard.find_one({"message_id": msg.id})
                if not data:
                    return
                try:
                    channel = data[payload.guild_id]["starboard"]["channel"]
                except KeyError:
                    return
                msg_list = data["message_id"]
                msg_list.remove(msg.id)

                starboard_channel = self.bot.getch(self.bot.get_channel, self.bot.fetch_channel, channel)
                bot_msg = await self.bot.get_or_fetch_message(starboard_channel, msg_list[0])
                await bot_msg.delete(delay=0)

        
    async def __on_star_reaction_add(self, payload):
        data = self.bot.server_config

        try:
            locked = data[payload.guild_id]["starboard"]["is_locked"]
        except KeyError:
            return
        
        try:
            channel = data[payload.guild_id]["starboard"]["channel"]
        except KeyError:
            return
        else:
            channel = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, channel
            )

        if not locked:
            try:
                limit = data[payload.guild_id]["starboard"]["limit"]
            except KeyError:
                return

            ch = await self.bot.getch(
                self.bot.get_channel, self.bot.fetch_channel, payload.channel_id
            )
            msg: discord.Message = await self.bot.get_or_fetch_message(ch, payload.message_id)
            count = star_method.get_star_count(msg)

            if count >= limit:
                await star_method.star_post(self.bot, starboard_channel=channel, message=msg)

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        pass

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):

        if not payload.guild_id:
            return

        if str(payload.emoji) == "\N{WHITE MEDIUM STAR}":
            await self.__on_star_reaction_add(payload)
        await star_method._add_reactor(self.bot, payload)

    @Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        pass

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id:
            return

        if str(payload.emoji) == "\N{WHITE MEDIUM STAR}":
            await self.__on_star_reaction_remove(payload)
        await star_method._remove_reactor(self.bot, payload)

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
