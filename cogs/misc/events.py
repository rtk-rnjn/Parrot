from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from discord.ext.commands import Cog, Context

if TYPE_CHECKING:
    from core import Parrot

_log = logging.getLogger("bot.cogs.misc.events")


class SnipeMessageListener(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.snipes: dict[int, deque[discord.Message]] = {}
        self.edit_snipes: dict[int, deque[tuple[discord.Message, discord.Message]]] = {}

        _log.info("Cog loaded: %s", self.__class__.__name__)

    @Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        ctx: Context = await self.bot.get_context(message, cls=Context)
        if ctx.valid:
            return

        if message.channel.id not in self.snipes:
            self.snipes[message.channel.id] = deque(maxlen=2**5)

        self.snipes[message.channel.id].appendleft(message)

    @Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        for msg in messages:
            await self.on_message_delete(msg)

    def get_snipe(self, channel: discord.abc.MessageableChannel, *, index: int) -> discord.Message:
        if channel.id not in self.snipes:
            msg = "No messages have been sniped in this channel"
            raise commands.BadArgument(msg)

        index -= 1
        if index < 0:
            msg = "Index must be positive"
            raise commands.BadArgument(msg)
        if index > len(self.snipes[channel.id]):
            msg = f"Index must be less than {len(self.snipes[channel.id])}"
            raise commands.BadArgument(msg)
        try:
            return self.snipes[channel.id][index]
        except Exception:
            err = "Message not found"
            raise commands.MessageNotFound(err) from None

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        if not before.guild:
            return

        if before.content == after.content:
            return

        if before.channel.id not in self.edit_snipes:
            self.edit_snipes[before.channel.id] = deque(maxlen=2**5)

        self.edit_snipes[before.channel.id].appendleft((before, after))

    def get_edit_snipe(self, channel: discord.abc.MessageableChannel, *, index: int) -> tuple[discord.Message, discord.Message]:
        if channel.id not in self.edit_snipes:
            msg = "No messages have been edited in this channel"
            raise commands.BadArgument(msg)

        index -= 1
        if index < 0:
            msg = "Index must be positive"
            raise commands.BadArgument(msg)
        if index > len(self.edit_snipes[channel.id]):
            msg = f"Index must be less than {len(self.edit_snipes[channel.id])}"
            raise commands.BadArgument(msg)
        try:
            return self.edit_snipes[channel.id][index]
        except Exception as e:
            err = "Message not found"
            raise commands.BadArgument(err) from e

    def delete_snipe(self, channel: discord.abc.MessageableChannel, *, index: int) -> None:
        try:
            self.snipes[channel.id].remove(self.snipes[channel.id][index - 1])
        except Exception:
            pass

    def delete_edit_snipe(self, channel: discord.abc.MessageableChannel, *, index: int) -> None:
        try:
            self.edit_snipes[channel.id].remove(self.edit_snipes[channel.id][index - 1])
        except Exception:
            pass


class PingMessageListner(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.ghost_pings: dict[int, deque[discord.Message]] = {}
        self.pings: dict[int, deque[discord.Message]] = {}

        _log.info("Cog loaded: %s", self.__class__.__name__)

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        assert isinstance(message.author, discord.Member)

        if message.author.id not in self.pings:
            self.pings[message.author.id] = deque(maxlen=2**5)

        if (
            message.author in message.mentions
            or any(role in message.role_mentions for role in message.author.roles)
            or "@everyone" in message.content
            or "@here" in message.content
        ):
            self.pings[message.author.id].append(message)

    @Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        assert isinstance(message.author, discord.Member)

        if message.author.id not in self.ghost_pings:
            self.ghost_pings[message.author.id] = deque(maxlen=2**5)

        if (
            message.author in message.mentions
            or any(role in message.role_mentions for role in message.author.roles)
            or "@everyone" in message.content
            or "@here" in message.content
        ):
            self.ghost_pings[message.author.id].append(message)

    @Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        for msg in messages:
            await self.on_message_delete(msg)

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.guild is None:
            return

        await self.on_message_delete(before)

    def get_pings(self, user_id: int) -> list[discord.Message]:
        return [] if user_id not in self.pings else list(self.pings[user_id])

    def get_ghost_pings(self, user_id: int) -> list[discord.Message]:
        return list(self.ghost_pings[user_id]) if user_id in self.ghost_pings else []
