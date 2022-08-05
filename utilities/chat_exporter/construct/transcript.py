from __future__ import annotations

import html
import traceback

from typing import List, Optional

import discord
from discord.ext import commands

from ..construct.message import Message
from ..construct.assets.component import Component

from ..ext.cache import clear_cache
from ..parse.mention import pass_bot
from ..ext.discord_utils import DiscordUtils
from ..ext.html_generator import fill_out, total, PARSE_MODE_NONE


class TranscriptDAO:
    html: str

    def __init__(
        self,
        channel: discord.TextChannel,
        limit: Optional[int],
        messages: Optional[List[discord.Message]],
        pytz_timezone,
        military_time: bool,
        bot: Optional[commands.Bot],
    ):
        self.channel = channel
        self.messages = messages
        self.limit = int(limit) if limit else None
        self.military_time = military_time
        self.pytz_timezone = pytz_timezone

        if bot:
            pass_bot(bot)

    async def build_transcript(self):
        message_html = await Message(
            self.messages,
            self.channel.guild,
            self.pytz_timezone,
            self.military_time,
        ).gather()
        await self.export_transcript(message_html)
        clear_cache()
        Component.menu_div_id = 0
        return self

    async def export_transcript(self, message_html: str):
        guild_icon = self.channel.guild.icon if (
                self.channel.guild.icon and len(self.channel.guild.icon) > 2
        ) else DiscordUtils.default_avatar

        guild_name = html.escape(self.channel.guild.name)

        self.html = await fill_out(self.channel.guild, total, [
            ("SERVER_NAME", f"Guild: {guild_name}"),
            ("SERVER_AVATAR_URL", str(guild_icon), PARSE_MODE_NONE),
            ("CHANNEL_NAME", f"Channel: {self.channel.name}"),
            ("MESSAGE_COUNT", str(len(self.messages))),
            ("MESSAGES", message_html, PARSE_MODE_NONE),
            ("TIMEZONE", str(self.pytz_timezone)),
        ])


class Transcript(TranscriptDAO):
    async def export(self):
        if not self.messages:
            self.messages = [message async for message in self.channel.history(limit=self.limit)]
        self.messages.reverse()

        try:
            return await super().build_transcript()
        except Exception:
            traceback.print_exc()