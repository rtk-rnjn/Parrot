from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:

    from core import Parrot

from pymongo.collection import ReturnDocument

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

    def __repr__(self) -> str:
        return "<Module discord.utils>"

    def get(self, *args, **kwargs) -> discord.Object:
        return discord.utils.get(*args, **kwargs)

    def find(self, *args, **kwargs) -> discord.Object:
        return discord.utils.find(*args, **kwargs)


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
    http = http()
    token = "what is love?"
    user = "love is something that you can't explain"
    guilds = []
    emojis = []
    users = []
    channels = []
    voice_clients = []

    def __init__(self, bot: Parrot, message: discord.Message) -> None:
        self.__bot = bot
        self.__message = message

        self.db = db(bot=self.__bot, guild=self.__message.guild)  # type: ignore

    async def init_db(self) -> None:
        await self.db.init_cache()

    def __repr__(self) -> str:
        return "<Module commands.Bot>"

    def run(self) -> None:
        pass

    async def start(self, *args, **kwargs) -> None:
        pass

    async def close(self) -> None:
        pass

    async def logout(self) -> None:
        pass

    async def get_context(self, *args, **kwargs) -> None:
        pass

    async def on_ready(self) -> None:
        pass

    async def set_db(self, *args, **kwargs):
        await self.db.set_db(*args, **kwargs)

    async def get_db(self, *args, **kwargs):
        return await self.db.get_db(*args, **kwargs)

    async def delete_db(self, *args, **kwargs):
        await self.db.delete_db(*args, **kwargs)


class db:  # pylint: disable=invalid-name
    def __init__(self, bot: Parrot, guild: discord.Guild) -> None:
        self.__bot = bot
        self.__guild = guild

        self.__cache: dict[int, dict[str | int, dict | list | str | int | float | bool | None]] = {}

    @property
    def cache(self) -> dict:
        return self.__cache[self.__guild.id]

    @property
    def bucket_exceeded(self) -> bool:
        return len(self.__cache[self.__guild.id]) >= 1000

    def __repr__(self) -> str:
        return "<Module commands.Bot.db>"

    def _raise_if_bucket_exceeded(self):
        if self.bucket_exceeded:
            msg = "Bucket exceeded"
            raise ValueError(msg)

    async def init_cache(self) -> None:
        """Initialize the cache."""
        data = await self.__bot.auto_responders.find_one({"_id": self.__guild.id})
        self.__cache[self.__guild.id] = data or {}

    async def get_db(self, key: str | int) -> dict | list | str | int | float | bool | None:
        """Get the database."""
        if val := self.__cache.get(self.__guild.id, {}).get(key, None):
            return val

        data = await self.__bot.auto_responders.find_one({"_id": self.__guild.id, key: {"$exists": True}})
        self.__cache[self.__guild.id] = data
        return data[key] if data else None

    async def set_db(self, key: str | int, value: dict | list | str | int | float | bool):
        """Set the database."""
        self._raise_if_bucket_exceeded()

        if key == "_id":
            msg = "Cannot set _id"
            raise ValueError(msg)

        if not isinstance(value, dict | list | str | int | float | bool):
            msg = "Value must be a dict, list, str, int, float, or bool"
            raise ValueError(msg)

        data = await self.__bot.auto_responders.find_one_and_update(
            {"_id": self.__guild.id},
            {"$set": {key: value}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        self.__cache[self.__guild.id] = data

    async def delete_db(self, key: str | int) -> None:
        """Delete the database."""
        if key == "_id":
            msg = "Cannot delete _id"
            raise ValueError(msg)

        data = await self.__bot.auto_responders.find_one_and_update(
            {"_id": self.__guild.id},
            {"$unset": {key: ""}},
            return_document=ReturnDocument.AFTER,
        )
        self.__cache[self.__guild.id] = data

    async def update_db(self, key: str | int, value: dict | list | str | int | float | bool) -> None:
        """Update the database."""
        if key == "_id":
            msg = "Cannot update _id"
            raise ValueError(msg)

        if not isinstance(value, dict | list | str | int | float | bool):
            msg = "Value must be a dict, list, str, int, float, or bool"
            raise ValueError(msg)

        data = await self.__bot.auto_responders.find_one_and_update(
            {"_id": self.__guild.id},
            {"$set": {key: value}},
            return_document=ReturnDocument.AFTER,
        )
        self.__cache[self.__guild.id] = data


class Variables:
    __class__ = None  # type: ignore

    def __init__(self, *, message: discord.Message, bot: Parrot) -> None:
        self.__message = message
        self.__bot = bot

    async def build_base(self, get: str | None = None) -> dict:
        from .channel import JinjaChannel
        from .guild import JinjaGuild
        from .member import JinjaMember
        from .message import JinjaMessage

        _channel = JinjaChannel(channel=self.__message.channel)  # type: ignore
        _guild = JinjaGuild(guild=self.__message.guild)  # type: ignore
        _member = JinjaMember(member=self.__message.author)
        _message = JinjaMessage(message=self.__message)
        _bot = bot(self.__bot, self.__message)
        await _bot.init_db()

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
