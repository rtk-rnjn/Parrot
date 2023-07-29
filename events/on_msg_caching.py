from __future__ import annotations

import discord
from core import Cog, Context, Parrot
from discord.ext import commands


class OnMsgCaching(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.__stop_caching = True

    def get_raw_message(self, message: discord.Message) -> dict:
        return {
            "id": message.id,
            "content": message.content,
            "author": message.author.id,
            "channel": message.channel.id,
            "guild": getattr(message.guild, "id", None),
            "timestamp": message.created_at.timestamp(),
            "reference": getattr(message.reference, "message_id", None),
            "bot": message.author.bot,
            "attachments": [attachment.proxy_url for attachment in message.attachments],
            "embeds": [embed.to_dict() for embed in message.embeds],
            "reactions": [
                {
                    "emoji": str(reaction.emoji),
                    "count": reaction.count,
                    "me": reaction.me,
                }
                for reaction in message.reactions
            ],
            "jump_url": message.jump_url,
            "type": str(message.type),
        }

    @Cog.listener("on_message")
    async def on_message_updater(self, message: discord.Message) -> None:
        if message.author.id in self.bot.message_cache:
            self.bot.message_cache[message.author.id] = message

        if self.__stop_caching:
            return

        query = {
            "_id": message.author.id,
        }
        update = {
            "$inc": {
                "messageCount": 1,
            },
            "$set": {
                "lastMessage": {
                    "content": message.content,
                    "channel": message.channel.id,
                    "guild": getattr(message.guild, "id", None),
                    "timestamp": message.created_at.timestamp(),
                },
            },
            "$addToSet": {
                "messageCollection": self.get_raw_message(message),
            },
        }
        self.bot.add_global_write_data(col="messageCollections", query=query, update=update, cls="UpdateOne")
        self.bot.add_global_write_data(
            col="messageCollections",
            query={},
            update={"$pull": {"messageCollection": {"timestamp": {"$lt": message.created_at.timestamp() - 604800}}}},
            cls="UpdateMany",
        )

    @Cog.listener("on_message_delete")
    async def on_message_delete_updater(self, message: discord.Message) -> None:
        if message.author.id in self.bot.message_cache:
            del self.bot.message_cache[message.author.id]

        if self.__stop_caching:
            return

        query = {}
        update = {
            "$pull": {
                "messageCollection": {
                    "id": message.id,
                },
            },
        }
        self.bot.add_global_write_data(col="messageCollections", query=query, update=update, cls="UpdateOne")

    @Cog.listener("on_message_edit")
    async def on_message_edit_updater(self, before: discord.Message, after: discord.Message) -> None:
        if before.author.id in self.bot.message_cache:
            self.bot.message_cache[before.author.id] = after

        if self.__stop_caching:
            return

        message = after
        query = {
            "_id": message.author.id,
        }
        update = {
            "$addToSet": {
                "messageCollection": self.get_raw_message(message),
            },
        }
        self.bot.add_global_write_data(col="messageCollections", query=query, update=update, cls="UpdateOne")

    @Cog.listener("on_reaction_add")
    async def on_reaction_add_updater(self, reaction: discord.Reaction, _: discord.User) -> None:
        if reaction.message.id in self.bot.message_cache:
            self.bot.message_cache[reaction.message.id] = reaction.message

    @Cog.listener("on_reaction_remove")
    async def on_reaction_remove_updater(self, reaction: discord.Reaction, _: discord.User) -> None:
        if reaction.message.id in self.bot.message_cache:
            self.bot.message_cache[reaction.message.id] = reaction.message

    @Cog.listener("on_reaction_clear")
    async def on_reaction_clear_updater(self, message: discord.Message, _: list[discord.Reaction]) -> None:
        if message.id in self.bot.message_cache:
            self.bot.message_cache[message.id] = message

    @Cog.listener("on_reaction_clear_emoji")
    async def on_reaction_clear_emoji_updater(self, reaction: discord.Reaction) -> None:
        if reaction.message.id in self.bot.message_cache:
            self.bot.message_cache[reaction.message.id] = reaction.message

    @commands.group(name="message", aliases=["msg"], invoke_without_command=True)
    @commands.is_owner()
    async def message_group(self, ctx: Context) -> None:
        """Message caching commands.

        ```py
        cog = bot.get_cog("OnMsgCaching")
        cog._OnMsgCaching__stop_caching = ...
        ```
        """
        await ctx.send_help(ctx.command)

    @message_group.command(name="start")
    @commands.is_owner()
    async def message_start(self, ctx: Context) -> None:
        """Start message caching.

        ```py
        cog = bot.get_cog("OnMsgCaching")
        cog._OnMsgCaching__stop_caching = True
        ```
        """
        self.__stop_caching = False
        await ctx.tick()

    @message_group.command(name="stop")
    @commands.is_owner()
    async def message_stop(self, ctx: Context) -> None:
        """Stop message caching.

        ```py
        cog = bot.get_cog("OnMsgCaching")
        cog._OnMsgCaching__stop_caching = True
        ```
        """
        self.__stop_caching = True
        await ctx.tick()

    @message_group.command(name="toggle")
    @commands.is_owner()
    async def message_toggle(self, ctx: Context) -> None:
        """Toggle message caching.

        ```py
        cog = bot.get_cog("OnMsgCaching")
        cog._OnMsgCaching__stop_caching = not cog._OnMsgCaching__stop_caching
        ```
        """
        self.__stop_caching = not self.__stop_caching
        await ctx.tick()

    @message_group.command(name="clear")
    @commands.is_owner()
    async def message_clear(self, ctx: Context) -> None:
        """Clear message cache.

        ```py
        cog = bot.get_cog("OnMsgCaching")
        confirm = await ctx.prompt("Are you sure you want to clear the message cache?")
        if confirm is None:
            return
        cog.bot.message_cache.clear()
        ```
        """
        confirm = await ctx.prompt("Are you sure you want to clear the message cache?")
        if confirm is None:
            return

        if confirm:
            self.bot.message_cache.clear()
            await ctx.tick()
        else:
            await ctx.send("Cancelled.")
