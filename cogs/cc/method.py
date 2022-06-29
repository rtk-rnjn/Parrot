from __future__ import annotations
from contextlib import suppress
from operator import attrgetter
import traceback

import discord
from core import Parrot
from typing import Any, Callable, Dict, NoReturn, Optional, Union, List

import re
import time
import random
import datetime
import asyncio
import textwrap
import io

from async_timeout import timeout  # type: ignore

from discord import (
    File,
    Embed,
    Colour,
    Guild,
    Member,
    Permissions,
    PermissionOverwrite,
    Object,
    Role,
    User,
)


# Example
"""
async def function(message: Message):
    if message.content == "!ping":
        return await message_send(message.channel.id, "Pong!")
"""
"""
async def function(message: Message):
    if message.author.id == 123456789:
        return await message_add_reaction("\N{THINKING FACE}")
"""

ERROR_MESSAGE = """```ini
[Failed executing the custom command template in {} at: {}]
``````py
{}```"""

BASE_FUNCTIONS = {
    "MESSAGE": """
async def function(message):
{}
""",
    "REACTION": """
async def function(reaction, user):
{}
""",
    "MEMBER": """
async def function(member):
{}
""",
}


def indent(code: str, base_function: str) -> str:
    code = textwrap.indent(code.replace("\t", "    "), "    ")
    return BASE_FUNCTIONS[base_function.upper()].format(code)


env = {
    "__import__": None,
    "__builtins__": None,
    "__name__": "__custom_command__",
    "globals": None,
    "locals": None,
    "__doc__": None,
    "__package__": None,
    "__loader__": None,
    "__spec__": None,
    "__annotations__": None,
    "__all__": None,
    "__file__": None,
    "__cached__": None,
    "__docformat__": None,
    "Re": re,
    "Random": random.randint,
    "Datetime": datetime.datetime,
    "Time": time.time,
    "Sleep": asyncio.sleep,
    "Object": Object,
    "File": File,
    "Embed": Embed,
    "Colour": Colour,
    "Permissions": Permissions,
    "PermissionOverwrite": PermissionOverwrite,
    "BytesIO": io.BytesIO,
}


class CustomBase:
    def __repr__(self) -> None:
        return f"<Object {self.__class__.__name__}>"


class CustomMessage(CustomBase):
    def __init__(self, message: discord.Message):
        self.id = message.id
        self.author = CustomMember(message.author)
        self.channel = CustomTextChannel(message.channel)
        self.content = message.content
        self.embeds = message.embeds
        self.created_at = message.created_at
        self.guild = CustomGuild(message.guild)
        self.jump_url = message.jump_url
        self.mentions = message.mentions
        self.pinned = message.pinned
        self.edited_at = message.edited_at
        self.tts = message.tts
        self.type = message.type
        self.reactions = [
            CustomReactionPassive(reaction) for reaction in message.reactions
        ]


class CustomReactionPassive:
    def __init__(self, reaction: discord.Reaction):
        self.count = reaction.count
        self.emoji = CustomEmoji(reaction.emoji)


class CustomReaction:
    def __init__(self, reaction: discord.Reaction):
        self.count = reaction.count
        self.emoji = CustomEmoji(reaction.emoji)
        self.message = CustomMessage(reaction.message)


class CustomEmoji:
    def __init__(self, emoji: Union[discord.Emoji, discord.PartialEmoji, str]):
        if isinstance(emoji, (discord.PartialEmoji, discord.Emoji)):
            self.id = emoji.id
            self.name = emoji.name
            self.animated = emoji.animated
            self.url = emoji.url
        else:
            self.__str__ = emoji


class CustomMember(CustomBase):
    def __init__(self, member: Member):
        self.id = member.id
        self.name = member.name
        self.nick = member.nick
        self.display_name = member.display_name
        self.discriminator = member.discriminator
        self.bot = member.bot
        self.guild_permissions = member.guild_permissions
        self.top_role = member.top_role.id
        self.roles = [role.id for role in member.roles]
        self.created_at = member.created_at
        self.joined_at = member.joined_at


class CustomRole(CustomBase):
    def __init__(self, role: Role):
        self.id = role.id
        self.name = role.name
        self.color = role.color
        self.is_default = role.is_default
        self.hoist = role.hoist
        self.managed = role.managed
        self.position = role.position
        self.permissions = role.permissions
        self.created_at = role.created_at


class CustomGuild(CustomBase):
    def __init__(self, guild: Guild):
        self.id = guild.id
        self.name = guild.name

        if guild.afk_channel:
            self.afk_channel = guild.afk_channel.id
            self.afk_timeout = guild.afk_timeout
        else:
            self.afk_channel = None
            self.afk_timeout = None

        self.created_at = guild.created_at
        self.verification_level = guild.verification_level
        self.default_notifications = guild.default_notifications
        self.explicit_content_filter = guild.explicit_content_filter
        self.mfa_level = guild.mfa_level
        self.large = guild.large
        self.member_count = guild.member_count
        self.roles = [role.id for role in guild.roles]
        self.features = guild.features
        self.approximate_member_count = guild.approximate_member_count
        self.premium_tier = guild.premium_tier
        self.premium_subscription_count = guild.premium_subscription_count
        self.preferred_locale = guild.preferred_locale
        self.description = guild.description
        self.public_updates_channel = guild.public_updates_channel
        self.max_video_channel_users = guild.max_video_channel_users


class CustomTextChannel(CustomBase):
    def __init__(self, channel: discord.TextChannel):
        self.id = channel.id
        self.name = channel.name
        self.topic = channel.topic
        self.position = channel.position
        self.is_news = channel.is_news()
        self.is_nsfw = channel.is_nsfw
        self.created_at = channel.created_at
        self.members = [member.id for member in channel.members]


class CustomVoiceChannel(CustomBase):
    def __init__(self, channel: discord.VoiceChannel):
        self.id = channel.id
        self.name = channel.name
        self.position = channel.position
        self.bitrate = channel.bitrate
        self.user_limit = channel.user_limit
        self.created_at = channel.created_at
        self.members = [member.id for member in channel.members]


class CustomCategoryChannel(CustomBase):
    def __init__(self, channel: discord.CategoryChannel):
        self.id = channel.id
        self.name = channel.name
        self.position = channel.position
        self.created_at = channel.created_at
        self.channels = [channel.id for channel in channel.channels]


class BaseCustomCommand:
    __class__ = None

    def __init__(self, bot: Parrot, *, guild: Guild, **kwargs: Dict[str, Any]) -> None:
        self.__bot = bot
        self.__guild = guild
        self.env = env
        self.env["get_db"] = self.get_db
        self.env["edit_db"] = self.edit_db
        self.env["del_db"] = self.del_db
        self.env["channel_create"] = self.channel_create
        self.env["channel_delete"] = self.channel_delete
        self.env["channel_edit"] = self.channel_edit

        self.env["role_create"] = self.role_create
        self.env["role_delete"] = self.role_delete
        self.env["role_edit"] = self.role_edit

        self.env["kick_member"] = self.kick_member
        self.env["ban_member"] = self.ban_member
        self.env["edit_member"] = self.edit_member

        self.env["get_member"] = self.get_member
        self.env["get_channel"] = self.get_channel
        self.env["get_role"] = self.get_role
        self.env["get_channel_type"] = self.get_channel_type
        self.env["get_permissions_for"] = self.get_permissions_for
        self.env["get_overwrites_for"] = self.get_overwrites_for

        self.env["wait_for_message"] = self.wait_for_message
        self.env["message_send"] = self.message_send

        [setattr(self, k, v) for k, v in kwargs.items()]  # type: ignore

    async def wait_for_message(
        self, timeout: float, **kwargs: Dict[str, Any]
    ) -> Optional[CustomMessage]:
        def check_outer(**kwargs) -> Callable:
            def check(message) -> bool:
                converted_pred = [
                    (attrgetter(k.replace("__", ".")), v) for k, v in kwargs.items()
                ]
                return all(pred(message) == value for pred, value in converted_pred)

            return check

        with suppress(asyncio.TimeoutError):
            msg = await self.__bot.wait_for(
                "message",
                check=check_outer(**kwargs),
                timeout=10 if timeout > 10 else timeout,
            )

        if msg.guild != self.__guild:
            return None
        return CustomMessage(msg)

    async def message_send(
        self,
        channel_id: int,
        content: str = None,
        *,
        embed: discord.Embed = None,
        embeds: List[discord.Embed] = None,
        file: discord.File = None,
        files: List[discord.File] = None,
        delete_after: float = None,
    ) -> Optional[CustomMessage]:
        allowed_mentions = discord.AllowedMentions.none()
        msg = await self.__guild.get_channel(channel_id).send(
            content,
            embed=embed,
            embeds=embeds,
            file=file,
            files=files,
            delete_after=delete_after,
            allowed_mentions=allowed_mentions,
        )
        return CustomMessage(msg)

    async def channel_create(
        self, channel_type: str, name: str, **kwargs: Dict[str, Any]
    ) -> Union[CustomTextChannel, CustomVoiceChannel]:
        if channel_type.upper() == "TEXT":
            channel = await self.__guild.create_text_channel(name, **kwargs)
            return CustomTextChannel(channel)
        if channel_type.upper() == "VOICE":
            channel = await self.__guild.create_voice_channel(name, **kwargs)
            return CustomVoiceChannel(channel)

    async def channel_edit(self, channel_id: int, **kwargs: Dict[str, Any]) -> NoReturn:
        await self.__guild.get_channel(channel_id).edit(**kwargs)
        return

    async def channel_delete(self, channel_id: int) -> NoReturn:
        await self.__guild.get_channel(channel_id).delete()
        return

    # roles

    async def role_create(self, name: str, **kwargs: Dict[str, Any]) -> CustomRole:
        role = await self.__guild.create_role(name, **kwargs)
        return CustomRole(role)

    async def role_edit(self, role_id: int, **kwargs: Dict[str, Any]) -> NoReturn:
        await self.__guild.get_role(role_id).edit(**kwargs)
        return

    async def role_delete(
        self,
        role_id: int,
    ) -> NoReturn:
        await self.__guild.get_role(role_id).delete()
        return

    # mod actions

    async def kick_member(self, member_id: int, reason: str) -> NoReturn:
        await self.__guild.get_member(member_id).kick(reason)
        return

    async def ban_member(self, member_id: int, reason: str) -> NoReturn:
        await self.__guild.get_member(member_id).ban(reason)
        return

    async def edit_member(self, member_id: int, **kwargs: Dict[str, Any]) -> NoReturn:
        await self.__guild.get_member(member_id).edit(**kwargs)
        return

    # utils

    async def get_member(self, member_id: int) -> CustomMember:
        return CustomMember(self.__guild.get_member(member_id))

    async def get_role(self, role_id: int) -> CustomRole:
        return CustomRole(self.__guild.get_role(role_id))

    async def get_channel(
        self, channel_id: int
    ) -> Union[CustomTextChannel, CustomVoiceChannel, CustomCategoryChannel]:
        channel = self.__guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return CustomTextChannel(channel)
        if isinstance(channel, discord.VoiceChannel):
            return CustomVoiceChannel(channel)
        if isinstance(channel, discord.CategoryChannel):
            return CustomCategoryChannel(channel)

    async def get_channel_type(self, channel: int) -> Optional[str]:
        channel = self.__guild.get_channel(channel)
        if isinstance(channel, discord.TextChannel):
            return "TEXT"
        if isinstance(channel, discord.VoiceChannel):
            return "VOICE"
        if isinstance(channel, discord.CategoryChannel):
            return "CATEGORY"
        if isinstance(channel, discord.Thread):
            return "THREAD"
        if isinstance(channel, discord.StageChannel):
            return "STAGE"
        return None

    def __get_role_or_user(
        self, obj: Union[CustomMember, CustomRole, int], need_user: bool = False
    ) -> Union[Member, User, Role, None]:
        obj = None
        if isinstance(obj, CustomMember):
            obj = self.__guild.get_member(obj.id)
        elif isinstance(obj, CustomRole):
            obj = self.__guild.get_role(obj.id)

        elif isinstance(obj, int):
            obj = self.__guild.get_member(obj)
            if obj is None:
                obj = self.__guild.get_role(obj)

            if obj is None and need_user:
                obj = self.__bot.get_user(obj)

        return obj

    async def get_permissions_for(
        self, channel: int, _for: Union[CustomMember, CustomRole, int]
    ) -> Optional[Permissions]:
        obj = self.__get_role_or_user(
            _for,
        )

        if obj is None:
            return None

        chn = self.__guild.get_channel(channel)
        if chn:
            return chn.permissions_for(obj)
        return None

    async def get_overwrites_for(
        self, channel: int, _for: Union[CustomMember, CustomRole, int]
    ) -> Optional[PermissionOverwrite]:
        obj = self.__get_role_or_user(_for, need_user=True)

        if obj is None:
            return None

        chn = self.__guild.get_channel(channel)
        if chn:
            return chn.overwrites_for(obj)
        return None

    # DB

    async def get_db(self, **kwargs: Dict[str, Any]) -> Dict[str, Any]:
        project = kwargs.pop("projection", {})
        return await self.__bot.mongo.cc.storage.find_one(
            {"_id": self.__guild.id, **kwargs}, project
        )

    async def edit_db(self, **kwargs: Dict[str, Any]) -> NoReturn:
        upsert = kwargs.pop("upsert", False)
        await self.__bot.mongo.cc.storage.update_one(
            {"_id": self.__guild.id}, kwargs, upsert=upsert
        )
        return

    async def del_db(
        self,
    ) -> NoReturn:
        await self.__bot.mongo.cc.storage.delete_one(
            {
                "_id": self.__guild.id,
            }
        )
        return


class BaseCustomCommandOnMsg(BaseCustomCommand):
    __class__ = None

    def __init__(self, bot: Parrot, *, guild: Guild, message: discord.Message):
        super().__init__(bot, guild=guild)
        self.__message = message

        self.env["message_add_reaction"] = self.message_add_reaction
        self.env["message_remove_reaction"] = self.message_remove_reaction
        self.env["message_clear_reactions"] = self.message_clear_reactions
        self.env["message_pin"] = self.message_pin
        self.env["message_unpin"] = self.message_unpin
        self.env["message_publish"] = self.message_publish
        self.env["message_create_thread"] = self.message_create_thread
        self.env["reactions_users"] = self.reactions_users

    async def message_pin(self) -> NoReturn:
        await self.__message.pin()
        return

    async def message_unpin(self) -> NoReturn:
        await self.__message.unpin()
        return

    async def message_publish(self) -> NoReturn:
        await self.__message.publish()
        return

    async def message_create_thread(self) -> NoReturn:
        await self.__message.create_thread()
        return

    async def message_add_reaction(self, emoji: str) -> NoReturn:
        await self.__message.add_reaction(emoji)
        return

    async def message_remove_reaction(
        self, emoji: str, member: CustomMember
    ) -> NoReturn:
        await self.__message.remove_reaction(emoji, discord.Object(id=member.id))
        return

    async def message_clear_reactions(self) -> NoReturn:
        await self.__message.clear_reactions()
        return

    async def reactions_users(self, emoji: Any) -> List[CustomMember]:
        for reaction in self.__message.reactions:
            if str(reaction.emoji) == emoji:
                return [CustomMember(member) async for member in reaction.users()]


class CustomCommandsExecutionOnMsg(BaseCustomCommandOnMsg):
    __class__ = None

    def __init__(self, bot: Parrot, message: discord.Message, **kwargs: Dict[str, Any]):
        super().__init__(bot, guild=message.guild, message=message, **kwargs)
        self.__message = message

    async def execute(
        self,
        code: str,
    ) -> NoReturn:
        try:
            async with timeout(10):
                exec(compile(code, "<string>", "exec"), self.env)

                try:
                    self.env["function"]
                except KeyError:
                    return

                await self.env["function"](CustomMessage(self.__message))
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await self.__message.channel.send(
                ERROR_MESSAGE.format(
                    f"#{self.__message.channel.name}", self.__message.created_at, tbe
                )
            )
            return


class _CustomCommandsExecutionOnMember(BaseCustomCommand):
    __class__ = None

    def __init__(self, bot: Parrot, member: discord.member, **kwargs: Dict[str, Any]):
        super().__init__(bot, guild=member.guild, **kwargs)
        self.__member = member
        self.env["guild"] = CustomGuild(self.__member.guild)

    async def execute(
        self,
        code: str,
    ) -> NoReturn:
        try:
            async with timeout(10):
                exec(compile(code, "<string>", "exec"), self.env)

                try:
                    self.env["function"]
                except KeyError:
                    return

                await self.env["function"](CustomMember(self.__member))
                return
        except Exception as e:
            return


class CustomCommandsExecutionOnJoin(_CustomCommandsExecutionOnMember):
    __class__ = None
    ...


class CustomCommandsExecutionOnRemove(_CustomCommandsExecutionOnMember):
    __class__ = None
    ...


class CustomCommandsExecutionOnReaction(BaseCustomCommandOnMsg):
    __class__ = None

    def __init__(
        self,
        bot: Parrot,
        reaction: discord.Reaction,
        user: discord.User,
        **kwargs: Dict[str, Any],
    ):
        super().__init__(
            bot,
            guild=reaction.message.guild,
            message=reaction.message,
        )
        self.__reaction = reaction
        self.__user = user
        self.__message = reaction.message

        self.env["user"] = CustomMember(self.__user)
        [setattr(self, k, v) for k, v in kwargs.items()]  # type: ignore

    async def execute(
        self,
        code: str,
    ) -> NoReturn:
        try:
            async with timeout(10):
                exec(compile(code, "<string>", "exec"), self.env)

                try:
                    self.env["function"]
                except KeyError:
                    return

                await self.env["function"](
                    CustomReaction(self.__reaction), CustomMember(self.__user)
                )
                return
        except Exception as e:
            tb = traceback.format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            await self.__message.channel.send(
                ERROR_MESSAGE.format(
                    f"#{self.__message.channel.name}", self.__message.created_at, tbe
                )
            )
            return
