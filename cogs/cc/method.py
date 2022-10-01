from __future__ import annotations

import asyncio
import datetime
import io
import random
import re
import textwrap
import time
import traceback
from contextlib import suppress
from operator import attrgetter
from typing import Any, Callable, Coroutine, Dict, Iterable, List, Optional, Union

from async_timeout import timeout  # type: ignore

import discord
from core import Parrot
from discord import (
    Colour,
    Guild,
    Member,
    PermissionOverwrite,
    Permissions,
    Role,
    User,
)

# Example

# async def function(message: Message):
#     if message.content == "!ping":
#         return await message_send(message.channel.id, "Pong!")


# async def function(message: Message):
#     if message.author.id == 123456789:
#         return await message_add_reaction("\N{THINKING FACE}")


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


class BuiltInMethods:
    __class__ = None

    def __init__(self) -> None:
        self.Color: discord.Color = Colour
        self.Colour: discord.Color = Colour
        self.Permissions: discord.Permissions = Permissions

    @staticmethod
    def PermissionOverwrite(**kwargs: Any) -> discord.PermissionOverwrite:
        return PermissionOverwrite(**kwargs)

    @staticmethod
    def try_except(func: Callable, *args: Any, default: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception:
            return default

    @staticmethod
    def ToInt(value: Any) -> int:
        return BuiltInMethods.try_except(int, value, default=0)

    @staticmethod
    def ToStr(value: Any) -> str:
        return BuiltInMethods.try_except(str, value, default="")

    @staticmethod
    def ToFloat(value: Any) -> float:
        return BuiltInMethods.try_except(float, value, default=0.0)

    @staticmethod
    def ToBool(value: Any) -> bool:
        return BuiltInMethods.try_except(bool, value, default=False)

    @staticmethod
    def Len(value: Any) -> int:
        return BuiltInMethods.try_except(len, value, default=0)

    @staticmethod
    def Abs(value: Any) -> int:
        return BuiltInMethods.try_except(abs, value, default=0)

    @staticmethod
    def Min(
        *args,
    ) -> int:
        return BuiltInMethods.try_except(min, *args, default=0)

    @staticmethod
    def Max(
        *args,
    ) -> int:
        return BuiltInMethods.try_except(max, *args, default=0)

    @staticmethod
    def Sum(iterable: Iterable, start: int = 0) -> int:
        return BuiltInMethods.try_except(sum, iterable, start, default=0)

    @staticmethod
    def Round(value: Any, ndigits: int = 0) -> int:
        return BuiltInMethods.try_except(round, value, ndigits, default=0)

    @staticmethod
    def Ord(value: Any) -> int:
        return BuiltInMethods.try_except(ord, value, default=0)

    @staticmethod
    def Chr(value: Any) -> str:
        return BuiltInMethods.try_except(chr, value, default="")

    @staticmethod
    def Hex(value: int) -> str:
        return BuiltInMethods.try_except(hex, value, default="")

    @staticmethod
    def Oct(value: int) -> str:
        return BuiltInMethods.try_except(oct, value, default="")

    @staticmethod
    def Bin(value: int) -> str:
        return BuiltInMethods.try_except(bin, value, default="")

    @staticmethod
    def Divmod(a: int, b: int) -> tuple:
        return BuiltInMethods.try_except(divmod, a, b, default=(0, 0))

    @staticmethod
    def Pow(*args) -> int:
        return BuiltInMethods.try_except(pow, *args, default=0)

    @staticmethod
    def Range(*args) -> list:
        return BuiltInMethods.try_except(list, range(*args), default=[])

    @staticmethod
    def Zip(*args) -> list:
        return BuiltInMethods.try_except(list, zip(*args), default=[])

    @staticmethod
    def Filter(function: Callable, iterable: Iterable) -> list:
        return BuiltInMethods.try_except(list, filter(function, iterable), default=[])

    @staticmethod
    def Map(function: Callable, iterable: Iterable) -> list:
        return BuiltInMethods.try_except(list, map(function, iterable), default=[])

    @staticmethod
    def Sorted(iterable: Iterable, key: Callable = None, reverse: bool = False) -> list:
        return BuiltInMethods.try_except(
            list, sorted(iterable, key=key, reverse=reverse), default=[]
        )

    @staticmethod
    def Reversed(iterable: Iterable) -> list:
        return BuiltInMethods.try_except(list, reversed(iterable), default=[])

    @staticmethod
    def Enumerate(iterable: Iterable) -> list:
        return BuiltInMethods.try_except(list, enumerate(iterable), default=[])

    @staticmethod
    def Any(iterable: Iterable) -> bool:
        return BuiltInMethods.try_except(any, iterable, default=False)

    @staticmethod
    def All(iterable: Iterable) -> bool:
        return BuiltInMethods.try_except(all, iterable, default=False)

    @staticmethod
    def ReFindAll(pattern: str, string: str) -> list:
        return BuiltInMethods.try_except(re.findall, pattern, string, default=[])

    @staticmethod
    def ReSearch(pattern: str, string: str) -> re.Match:
        return BuiltInMethods.try_except(re.search, pattern, string, default=None)

    @staticmethod
    def ReMatch(pattern: str, string: str) -> re.Match:
        return BuiltInMethods.try_except(re.match, pattern, string, default=None)

    @staticmethod
    def ReSplit(pattern: str, string: str) -> list:
        return BuiltInMethods.try_except(re.split, pattern, string, default=[])

    @staticmethod
    def ReSub(pattern: str, repl: str, string: str) -> str:
        return BuiltInMethods.try_except(re.sub, pattern, repl, string, default="")

    @staticmethod
    def RandomRandint(a: int, b: int) -> int:
        return random.randint(a, b)

    @staticmethod
    def RandomChoice(iterable: Iterable) -> Any:
        return random.choice(iterable)

    @staticmethod
    def RandomSample(iterable: Iterable, k: int) -> list:
        return random.sample(iterable, k)

    @staticmethod
    def RandomShuffle(iterable: Iterable) -> list:
        return random.shuffle(iterable)

    @staticmethod
    def DateTimeNow() -> datetime.datetime:
        return datetime.datetime.now()

    @staticmethod
    def Time() -> float:
        return time.time()

    @staticmethod
    async def Sleep(seconds: float) -> None:
        return await asyncio.sleep(seconds)

    @staticmethod
    def Object(_id: int) -> discord.Object:
        return discord.Object(id=_id)

    @staticmethod
    def File(buffer: io.BytesIO, filename: str, *, kwargs: Any) -> discord.File:
        return discord.File(buffer, filename, **kwargs)

    @staticmethod
    def Embed(**kwargs: Any) -> discord.Embed:
        return discord.Embed(**kwargs)

    @staticmethod
    def BytesIO(bytes: BytesIO) -> io.BytesIO:
        return io.BytesIO(bytes)

    @staticmethod
    def EncodeBytes(string: str) -> bytes:
        return string.encode()

    @staticmethod
    def DecodeBytes(bytes: bytes) -> str:
        return bytes.decode()


env = {
    "__import__": None,
    "__builtins__": None,
    "__name__": "__custom_command__",
    "globals": None,
    "locals": None,
    "int": BuiltInMethods.ToInt,
    "str": BuiltInMethods.ToStr,
    "float": BuiltInMethods.ToFloat,
    "bool": BuiltInMethods.ToBool,
    "range": BuiltInMethods.Range,
    "len": BuiltInMethods.Len,
    "abs": BuiltInMethods.Abs,
    "min": BuiltInMethods.Min,
    "max": BuiltInMethods.Max,
    "sum": BuiltInMethods.Sum,
    "round": BuiltInMethods.Round,
    "ord": BuiltInMethods.Ord,
    "chr": BuiltInMethods.Chr,
    "hex": BuiltInMethods.Hex,
    "oct": BuiltInMethods.Oct,
    "bin": BuiltInMethods.Bin,
    "divmod": BuiltInMethods.Divmod,
    "pow": BuiltInMethods.Pow,
    "zip": BuiltInMethods.Zip,
    "filter": BuiltInMethods.Filter,
    "map": BuiltInMethods.Map,
    "sorted": BuiltInMethods.Sorted,
    "reversed": BuiltInMethods.Reversed,
    "enumerate": BuiltInMethods.Enumerate,
    "any": BuiltInMethods.Any,
    "all": BuiltInMethods.All,
    "Re": BuiltInMethods.ReFindAll,
    "Random": BuiltInMethods.RandomRandint,
    "Datetime": BuiltInMethods.DateTimeNow,
    "Time": BuiltInMethods.Time,
    "Sleep": asyncio.sleep,
    "Object": BuiltInMethods.Object,
    "File": BuiltInMethods.File,
    "Embed": BuiltInMethods.Embed,
    "Colour": BuiltInMethods.Colour,
    "Permissions": BuiltInMethods.Permissions,
    "PermissionOverwrite": BuiltInMethods.PermissionOverwrite,
    "BytesIO": BuiltInMethods.BytesIO,
}


class CustomBase:
    def __repr__(self) -> str:
        return f"<Object {self.__class__.__name__}>"


class CustomMessage(CustomBase):
    __slots__ = (
        "id",
        "author",
        "channel",
        "content",
        "embeds",
        "created_at",
        "guild",
        "jump_url",
        # "mentions",
        "pinned",
        "edited_at",
        "tts",
        # "type",
        "reactions",
        "delete",
    )

    def __init__(self, message: discord.Message):
        self.id: int = message.id
        self.author: CustomMember = (
            CustomMember(message.author)
            if isinstance(message.author, discord.Member)
            else None
        )
        self.channel: CustomTextChannel = (
            CustomTextChannel(message.channel)
            if isinstance(message.channel, discord.TextChannel)
            else None
        )
        self.content: str = message.content
        self.embeds: List[discord.Embed] = message.embeds
        self.created_at: datetime.datetime = message.created_at
        self.guild: "CustomGuild" = (
            CustomGuild(message.guild) if message.guild is not None else None
        )
        self.jump_url: str = message.jump_url
        # self.mentions: List["CustomMember"] = [CustomMember(u) for u in message.mentions]
        self.pinned: bool = message.pinned
        self.edited_at: Optional[datetime.datetime] = message.edited_at
        self.tts: bool = message.tts
        # self.type = message.type
        self.reactions: List[CustomReactionPassive] = [
            CustomReactionPassive(reaction) for reaction in message.reactions
        ]
        self.delete: Callable[..., Coroutine[Any, Any, None]] = message.delete


class CustomReactionPassive:
    __slots__ = (
        "emoji",
        "count",
    )

    def __init__(self, reaction: discord.Reaction):
        self.count = reaction.count
        self.emoji = CustomEmoji(reaction.emoji)


class CustomReaction:
    __slots__ = (
        "count",
        "emoji",
        "message",
    )

    def __init__(self, reaction: discord.Reaction):
        self.count = reaction.count
        self.emoji = CustomEmoji(reaction.emoji)
        self.message = CustomMessage(reaction.message)


class CustomEmoji:
    __slots__ = (
        "id",
        "name",
        "animated",
        "url",
    )

    def __init__(self, emoji: Union[discord.Emoji, discord.PartialEmoji, str]):
        if isinstance(emoji, (discord.PartialEmoji, discord.Emoji)):
            self.id = emoji.id
            self.name = emoji.name
            self.animated = emoji.animated
            self.url = emoji.url
        else:
            self.id = None
            self.name = emoji
            self.animated = False
            self.url = None


class CustomMember(CustomBase):
    __slots__ = (
        "id",
        "name",
        "nick",
        "display_name",
        "discriminator",
        "guild_permissions",
        "top_role",
        "roles",
        "joined_at",
        "created_at",
        "avatar_url",
    )

    def __init__(self, member: Member):
        self.id: int = member.id
        self.name: str = member.name
        self.nick: Optional[str] = member.nick
        self.display_name: str = member.display_name
        self.discriminator: str = member.discriminator
        self.bot: bool = member.bot
        self.guild_permissions: discord.Permissions = member.guild_permissions
        self.top_role: int = member.top_role.id
        self.roles: List[int] = [role.id for role in member.roles]
        self.created_at: datetime.datetime = member.created_at
        self.joined_at: datetime.datetime = member.joined_at
        self.avatar_url: str = member.display_avatar.url


class CustomRole(CustomBase):
    __slots__ = (
        "id",
        "name",
        "color",
        "position",
        "permissions",
        "mentionable",
        "hoist",
        "created_at",
    )

    def __init__(self, role: Role):
        self.id: int = role.id
        self.name: str = role.name
        self.color: discord.Color = role.color
        self.is_default: bool = role.is_default()
        self.hoist: bool = role.hoist
        self.managed: bool = role.managed
        self.position: int = role.position
        self.permissions: discord.Permissions = role.permissions
        self.created_at: datetime.datetime = role.created_at


class CustomGuild(CustomBase):
    __slots__ = (
        "id",
        "name",
        "created_at",
        "member_count",
        "roles",
        "description",
    )

    def __init__(self, guild: Guild):
        self.id: int = guild.id
        self.name: str = guild.name
        self.created_at: datetime.datetime = guild.created_at
        self.member_count: Optional[int] = guild.member_count
        self.roles: List[int] = [role.id for role in guild.roles]
        self.description: str = guild.description


class CustomTextChannel(CustomBase):
    __slots__ = (
        "id",
        "name",
        "created_at",
        "topic",
        "is_nsfw",
        "is_news",
        "created_at",
        "members",
    )

    def __init__(self, channel: discord.TextChannel):
        self.id: int = channel.id
        self.name: str = channel.name
        self.topic: Optional[str] = channel.topic
        self.position: int = channel.position
        self.is_news: bool = channel.is_news()
        self.is_nsfw: bool = channel.is_nsfw()
        self.created_at: datetime.datetime = channel.created_at
        self.members: List[int] = [member.id for member in channel.members]


class CustomVoiceChannel(CustomBase):
    __slots__ = (
        "id",
        "name",
        "created_at",
        "position",
        "bitrate",
        "user_limit",
        "members",
    )

    def __init__(self, channel: discord.VoiceChannel):
        self.id: int = channel.id
        self.name: str = channel.name
        self.position: int = channel.position
        self.bitrate: int = channel.bitrate
        self.user_limit: int = channel.user_limit
        self.created_at: datetime.datetime = channel.created_at
        self.members: List[int] = [member.id for member in channel.members]


class CustomCategoryChannel(CustomBase):
    __slots__ = (
        "id",
        "name",
        "created_at",
        "position",
        "channels",
    )

    def __init__(self, channel: discord.CategoryChannel):
        self.id: int = channel.id
        self.name: str = channel.name
        self.position: str = channel.position
        self.created_at: datetime.datetime = channel.created_at
        self.channels: List[int] = [channel.id for channel in channel.channels]


class BaseCustomCommand:
    __class__ = None

    def __init__(self, bot: Parrot, *, guild: Guild, **kwargs: Any) -> None:
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

    async def prefix(
        self,
    ) -> str:
        return self.__bot.get_guild_prefixes(self.__guild)

    async def wait_for_message(
        self, timeout: float, **kwargs: Any
    ) -> Optional[CustomMessage]:
        def check_outer(**kwargs) -> Callable:
            def __suppress_attr_error(
                func: Callable, *args: Any, **kwargs: Any
            ) -> bool:
                """Suppress attribute error for the function."""
                try:
                    func(*args, **kwargs)
                    return True
                except AttributeError:
                    return False

            def check(message) -> bool:
                converted_pred = [
                    (attrgetter(k.replace("__", ".")), v) for k, v in kwargs.items()
                ]
                return all(
                    pred(message) == value
                    for pred, value in converted_pred
                    if __suppress_attr_error(pred, message)
                )

            return check

        with suppress(asyncio.TimeoutError):
            msg = await self.__bot.wait_for(
                "message", check=check_outer(**kwargs), timeout=min(timeout, 10)
            )

        return None if msg.guild != self.__guild else CustomMessage(msg)

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
        channel: discord.TextChannel = self.__guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            msg = await channel.send(
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
        self, channel_type: str, name: str, **kwargs: Any
    ) -> Union[CustomTextChannel, CustomVoiceChannel, None]:
        if channel_type.upper() == "TEXT":
            text_channel = await self.__guild.create_text_channel(name, **kwargs)
            return CustomTextChannel(text_channel)
        if channel_type.upper() == "VOICE":
            voice_channel = await self.__guild.create_voice_channel(name, **kwargs)
            return CustomVoiceChannel(voice_channel)
        return None

    async def channel_edit(self, channel_id: int, **kwargs: Any) -> None:
        channel = self.__guild.get_channel(channel_id)
        if channel is not None:
            await channel.edit(**kwargs)
        return

    async def channel_delete(self, channel_id: int) -> None:
        channel = self.__guild.get_channel(channel_id)
        if channel is not None:
            await channel.delete()
        return

    # roles

    async def role_create(self, name: str, **kwargs: Any) -> CustomRole:
        role = await self.__guild.create_role(name, **kwargs)
        return CustomRole(role)

    async def role_edit(self, role_id: int, **kwargs: Any) -> None:
        await self.__guild.get_role(role_id).edit(**kwargs)
        return

    async def role_delete(
        self,
        role_id: int,
    ) -> None:
        await self.__guild.get_role(role_id).delete()
        return

    # mod actions

    async def kick_member(self, member_id: int, reason: str) -> None:
        member = self.__guild.get_member(member_id)
        if member is not None:
            await member.kick(reason=reason)
        return

    async def ban_member(self, member_id: int, reason: str) -> None:
        member = self.__guild.get_member(member_id)
        if member is not None:
            await member.ban(reason=reason)
        return

    async def edit_member(self, member_id: int, **kwargs: Any) -> None:
        member = self.__guild.get_member(member_id)
        if member is not None:
            await member.edit(**kwargs)
        return

    async def member_add_roles(
        self, member_id: int, *args: int, reason: Optional[str] = None
    ) -> None:
        member = self.__guild.get_member(member_id)
        if member is not None:
            for role_id in args:
                role = self.__guild.get_role(role_id)
                if role is not None:
                    await member.add_roles(role, reason=reason)
        return

    async def member_remove_roles(
        self, member_id: int, *args: int, reason: Optional[str] = None
    ) -> None:
        member = self.__guild.get_member(member_id)
        if member is not None:
            for role_id in args:
                role = self.__guild.get_role(role_id)
                if role is not None:
                    await member.remove_roles(role, reason=reason)
        return

    # utils

    async def get_member(self, member_id: int) -> Optional[CustomMember]:
        member = self.__guild.get_member(member_id)
        return CustomMember(member) if member is not None else None

    async def get_role(self, role_id: int) -> Optional[CustomRole]:
        role = self.__guild.get_role(role_id)
        return CustomRole(role) if role is not None else None

    async def get_channel(
        self, channel_id: int
    ) -> Union[CustomTextChannel, CustomVoiceChannel, CustomCategoryChannel, None]:
        channel = self.__guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return CustomTextChannel(channel)
        if isinstance(channel, discord.VoiceChannel):
            return CustomVoiceChannel(channel)
        if isinstance(channel, discord.CategoryChannel):
            return CustomCategoryChannel(channel)
        return None

    async def get_channel_type(self, channel_id: int) -> Optional[str]:
        channel = self.__guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return "TEXT"
        if isinstance(channel, discord.VoiceChannel):
            return "VOICE"
        if isinstance(channel, discord.CategoryChannel):
            return "CATEGORY"
        if isinstance(channel, discord.Thread):
            return "THREAD"
        return "STAGE" if isinstance(channel, discord.StageChannel) else None

    def __get_role_or_user(
        self, obj: Union[CustomMember, CustomRole, int], need_user: bool = False
    ) -> Union[Member, User, Role, None]:
        if isinstance(obj, (discord.Member, CustomMember)):
            return self.__guild.get_member(obj.id)
        elif isinstance(obj, (discord.Role, CustomRole)):
            return self.__guild.get_role(obj.id)

        elif isinstance(obj, int):
            obj = self.__guild.get_member(obj)
            if obj is None:
                return self.__guild.get_role(obj)

        return None

    async def get_permissions_for(
        self, channel: int, _for: Union[CustomMember, CustomRole, int]
    ) -> Optional[Permissions]:
        obj = self.__get_role_or_user(
            _for,
        )

        if obj is None:
            return None

        if chn := self.__guild.get_channel(channel):
            return chn.permissions_for(obj)
        return None

    async def get_overwrites_for(
        self, channel: int, _for: Union[CustomMember, CustomRole, int]
    ) -> Optional[PermissionOverwrite]:
        obj = self.__get_role_or_user(_for, need_user=True)

        if obj is None:
            return None

        if chn := self.__guild.get_channel(channel):
            return chn.overwrites_for(obj)
        return None

    # DB

    async def get_db(self, *, projection: dict = {}, **kwargs: Any) -> Dict[str, Any]:
        # sourcery skip: default-mutable-arg
        return await self.__bot.mongo.cc.storage.find_one(
            {"_id": self.__guild.id, **kwargs}, projection
        )

    async def edit_db(self, *, upsert: bool = True, update: dict) -> None:
        await self.__bot.mongo.cc.storage.update_one(
            {"_id": self.__guild.id}, update, upsert=upsert
        )
        return

    async def del_db(
        self,
    ) -> None:
        await self.__bot.mongo.cc.storage.delete_one(
            {
                "_id": self.__guild.id,
            }
        )
        return None


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

    async def message_pin(self) -> None:
        await self.__message.pin()
        return None

    async def message_unpin(self) -> None:
        await self.__message.unpin()
        return None

    async def message_publish(self) -> None:
        await self.__message.publish()
        return None

    async def message_create_thread(self) -> None:
        await self.__message.create_thread()
        return None

    async def message_add_reaction(self, emoji: str) -> None:
        await self.__message.add_reaction(emoji)
        return None

    async def message_remove_reaction(self, emoji: str, member: CustomMember) -> None:
        await self.__message.remove_reaction(emoji, discord.Object(id=member.id))
        return None

    async def message_clear_reactions(self) -> None:
        await self.__message.clear_reactions()
        return None

    async def reactions_users(self, emoji: Any) -> List[CustomMember]:
        # sourcery skip: use-next
        for reaction in self.__message.reactions:
            if str(reaction.emoji) == str(emoji):
                return [CustomMember(user) async for user in reaction.users()]
        return []


class CustomCommandsExecutionOnMsg(BaseCustomCommandOnMsg):
    __class__ = None

    def __init__(self, bot: Parrot, message: discord.Message, **kwargs: Any):
        super().__init__(bot, guild=message.guild, message=message, **kwargs)
        self.__message = message

    async def execute(
        self,
        code: str,
    ) -> None:
        try:
            async with timeout(10):
                exec(compile(code, "<string>", "exec"), self.env)

                try:
                    function: Callable = self.env["function"]
                except KeyError:
                    return

                await function(CustomMessage(self.__message))
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

    def __init__(self, bot: Parrot, member: discord.Member, **kwargs: Any):
        super().__init__(bot, guild=member.guild, **kwargs)
        self.__member = member
        self.env["guild"] = CustomGuild(self.__member.guild)

    async def execute(
        self,
        code: str,
    ) -> None:
        try:
            async with timeout(10):
                exec(compile(code, "<string>", "exec"), self.env)

                try:
                    function: Callable = self.env["function"]
                except KeyError:
                    return

                await function(CustomMember(self.__member))
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
        **kwargs: Any,
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
    ) -> None:
        try:
            async with timeout(10):
                exec(compile(code, "<string>", "exec"), self.env)

                try:
                    function: Callable = self.env["function"]
                except KeyError:
                    return

                await function(
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
