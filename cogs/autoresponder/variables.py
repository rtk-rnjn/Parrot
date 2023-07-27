from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core import Parrot

import discord


class Variables:
    __class__ = None  # type: ignore

    def __init__(self, *, message: discord.Message, bot: Parrot) -> None:
        self.__message = message
        self.__bot = bot

    def build_base(self) -> dict:
        self.get_role_name = self._get_role_name
        self.get_channel_name = self._get_channel_name
        self.get_member_name = self._get_member_name
        self.create_channel = self._create_channel
        self.create_role = self._create_role
        self.delete_message = self._delete_message
        self.delete_trigger = self._delete_trigger
        self.get_db = self._get_db
        self.set_db = self._set_db
        self.delete_db = self._delete_db
        self.update_db = self._update_db

        return {
            "message_id": self.message_id,
            "message_content": self.message_content,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "message_author_id": self.message_author_id,
            "message_author_name": self.message_author_name,
            "message_author": self.message_author,
            "get_role_name": self.get_role_name,
            "get_channel_name": self.get_channel_name,
            "get_member_name": self.get_member_name,
            "create_channel": self.create_channel,
            "create_role": self.create_role,
            "delete_message": self.delete_message,
            "delete_trigger": self.delete_trigger,
            "get_db": self.get_db,
            "set_db": self.set_db,
            "delete_db": self.delete_db,
            "update_db": self.update_db,
            "multiply": self.multiply,
        }

    @property
    def message_id(self):
        """Get message id."""
        return self.__message.id

    @property
    def message_content(self):
        """Get message content."""
        return self.__message.content

    @property
    def channel_id(self):
        """Get channel id."""
        return self.__message.channel.id

    @property
    def channel_name(self):
        """Get channel name."""
        return self.__message.channel.name  # type: ignore

    @property
    def message_author_id(self):
        """Get message author id."""
        return self.__message.author.id

    @property
    def message_author_name(self):
        """Get message author name."""
        return self.__message.author.name

    @property
    def message_author(self):
        """Get message author."""
        return str(self.__message.author)

    async def _send_message_after(self, channel: int, message: str, delay: int = 0):
        """Send a message after a delay."""
        delay = max(0, delay)
        if delay > 15 * 60:
            return
        if chn := self.__message.guild.get_channel(channel):  # type: ignore
            await chn.send(message[:1990], delete_after=delay or None)  # type: ignore

    async def _reply_message_after(self, message: str, delay: int = 0):
        """Reply to a message after a delay."""
        delay = max(0, delay)
        if delay > 15 * 60:
            return
        await self.__message.reply(message[:1990], delete_after=delay or None)  # type: ignore

    def _get_role_name(self, role_id: int):
        """Get role name from role id."""
        r = self.__message.guild.get_role(role_id)  # type: ignore
        return r.name if r else None

    def _get_channel_name(self, channel_id: int):
        """Get channel name from channel id."""
        c = self.__message.guild.get_channel(channel_id)  # type: ignore
        return c.name if c else None

    def _get_member_name(self, member_id: int):
        """Get member name from member id."""
        m = self.__message.guild.get_member(member_id)  # type: ignore
        return m.name if m else None

    async def _create_channel(self, name: str, position: int = None, category: int = None):
        """Create a channel in the same category as the message channel."""
        cat: discord.CategoryChannel = (
            self.__message.guild.get_channel(category) if category else None  # type: ignore
        )
        chn = await self.__message.guild.create_text_channel(  # type: ignore
            name,
            position=position or discord.utils.MISSING,
            category=cat,
        )
        return chn.id

    async def _create_role(self, name: str, permission: int = None, color: int = None):
        """Create a role in the same guild as the message."""
        if permission:
            perms = discord.Permissions(permission)
        else:
            perms = discord.Permissions.none()

        clr = discord.Color.from_str(str(color)) if color else discord.Color.default()
        role = await self.__message.guild.create_role(name=name, color=clr, permissions=perms)  # type: ignore
        return role.id

    async def _delete_message(self, channel: int, message: int):
        """Delete a message from a channel."""
        msg: discord.PartialMessage = self.__bot.get_or_fetch_message(channel, message, partial=True)  # type: ignore
        if msg and (msg.guild.id != self.__message.guild.id):  # type: ignore
            return
        await msg.delete(delay=0)

    async def _delete_trigger(self):
        await self.__message.delete(delay=0)

    async def _get_db(self, key: str):
        """Get the database."""
        data = await self.__bot.auto_responders.find_one({"_id": self.__message.guild.id, key: {"$exists": True}})  # type: ignore
        return data[key] if data else None

    async def _set_db(self, key: str, value: Any):
        """Set the database."""
        await self.__bot.auto_responders.update_one({"_id": self.__message.guild.id}, {"$set": {key: value}}, upsert=True)  # type: ignore

    async def _delete_db(self, key: str):
        """Delete the database."""
        await self.__bot.auto_responders.update_one({"_id": self.__message.guild.id}, {"$unset": {key: ""}})  # type: ignore

    async def _update_db(self, key: str, value: Any):
        """Update the database."""
        await self.__bot.auto_responders.update_one({"_id": self.__message.guild.id}, {"$set": {key: value}})  # type: ignore

    def multiply(self, a: int, b: int):
        if max(a, b) > 100000:
            msg = "The number is too big"
            raise ValueError(msg)
        return a * b
