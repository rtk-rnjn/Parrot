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
    MISSING = discord.utils._MissingSentinel()  # pylint: disable=protected-access

    def __init__(self) -> None:
        self.get = discord.utils.get
        self.find = discord.utils.find

    def __repr__(self) -> str:
        return "<Module discord.utils>"


class _discord:  # pylint: disable=invalid-name
    def __init__(self) -> None:
        self.utils = utils()

        self.Embed = JinjaEmbed
        self.Permisisons = JinjaPermissions
        self.Colour = JinjaColour
        self.PermissionOverwrite = JinjaPermissionOverwrite
        self.AllowedMentions = JinjaAllowedMentions
        self.Object = discord.Object

    def __repr__(self) -> str:
        return "<Module discord>"


class http:  # pylint: disable=invalid-name
    route = None
    token = "what is love?"
    session = None


class bot:  # pylint: disable=invalid-name
    def __init__(self, bot: Parrot, message: discord.Message) -> None:
        self.__bot = bot
        self.__message = message

    http = http()
    token = "what is love?"
    user = "love is something that you can't explain"
    guilds = []
    emojis = []
    users = []
    channels = []
    voice_clients = []

    def __repr__(self) -> str:
        return "<Module commands.Bot>"

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

    def build_base(self, get: str | None = None) -> dict:
        from .channel import JinjaChannel
        from .guild import JinjaGuild
        from .member import JinjaMember
        from .message import JinjaMessage

        _channel = JinjaChannel(channel=self.__message.channel)  # type: ignore
        _guild = JinjaGuild(guild=self.__message.guild)  # type: ignore
        _member = JinjaMember(member=self.__message.author)
        _message = JinjaMessage(message=self.__message)
        _bot = bot(bot=self.__bot, message=self.__message)

        class ctx:
            prefix = ""
            command = None
            token = "what is love?"

            def __init__(self):
                self.channel = _channel
                self.guild = _guild
                self.author = _member
                self.message = _message

                self.bot = _bot

            def __repr__(self) -> str:
                return "<Module commands.Context>"

            async def send(self, *args, **kwargs) -> JinjaMessage | None:
                """Send message to channel."""
                return await _channel.send(*args, **kwargs)

        data = {
            "channel": _channel,
            "guild": _guild,
            "member": _member,
            "message": _message,
            "discord": _discord(),
            "ctx": ctx(),
            "bot": _bot,
        }
        return data[get] if get else data

    def multiply(self, a: int, b: int):
        if max(a, b) > 100000:
            msg = "The number is too big"
            raise ValueError(msg)
        return a * b
