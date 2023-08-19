from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Parrot

import discord


class JinjaBase:
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class JinjaEmbed(JinjaBase, discord.Embed):
    pass


class JinjaPermissions(JinjaBase, discord.Permissions):
    pass


class JinjaColour(JinjaBase, discord.Colour):
    pass


class JinjaPermissionOverwrite(JinjaBase, discord.PermissionOverwrite):
    pass


class JinjaAllowedMentions(JinjaBase, discord.AllowedMentions):
    pass


class utils:  # pylint: disable=invalid-name
    MISSING = discord.utils.MISSING
    sleep_until = discord.utils.sleep_until
    get = discord.utils.get
    find = discord.utils.find


class _discord:
    Embed = JinjaEmbed
    Permisisons = JinjaPermissions
    Colour = JinjaColour
    PermissionOverwrite = JinjaPermissionOverwrite
    AllowedMentions = JinjaAllowedMentions
    Object = discord.Object
    utils = utils()


class http:  # pylint: disable=invalid-name
    route = None
    token = "what is love?"
    session = None


class bot:  # pylint: disable=invalid-name
    def __init__(self, bot: Parrot) -> None:
        self.__bot = bot

    http = http()
    token = "what is love?"
    user = "love is something that you can't explain"
    guilds = []
    emojis = []
    users = []
    channels = []
    voice_clients = []

    def run(self) -> None:
        pass

    async def start(self, *args, **kwargs) -> None:
        pass

    async def get_db(self, key: str):
        """Get the database."""
        data = await self.__bot.auto_responders.find_one({"_id": self.__message.guild.id, key: {"$exists": True}})  # type: ignore
        return data[key] if data else None

    async def set_db(self, key: str, value: str | int):
        """Set the database."""
        await self.__bot.auto_responders.update_one({"_id": self.__message.guild.id}, {"$set": {key: value}}, upsert=True)  # type: ignore

    async def delete_db(self, key: str):
        """Delete the database."""
        await self.__bot.auto_responders.update_one({"_id": self.__message.guild.id}, {"$unset": {key: ""}})  # type: ignore

    async def update_db(self, key: str, value: str | int):
        """Update the database."""
        await self.__bot.auto_responders.update_one({"_id": self.__message.guild.id}, {"$set": {key: value}})  # type: ignore


class Variables:
    __class__ = None  # type: ignore

    def __init__(self, *, message: discord.Message, bot: Parrot) -> None:
        self.__message = message
        self.__bot = bot

    def build_base(self) -> dict:
        from .channel import JinjaChannel
        from .guild import JinjaGuild
        from .member import JinjaMember
        from .message import JinjaMessage

        return {
            "channel": JinjaChannel(channel=self.__message.channel),  # type: ignore
            "guild": JinjaGuild(guild=self.__message.guild),  # type: ignore
            "member": JinjaMember(member=self.__message.author),
            "message": JinjaMessage(message=self.__message),
            "discord": _discord(),
            "bot": bot(bot=self.__bot),
        }

    def multiply(self, a: int, b: int):
        if max(a, b) > 100000:
            msg = "The number is too big"
            raise ValueError(msg)
        return a * b
