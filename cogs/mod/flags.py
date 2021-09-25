from discord.ext import commands
import typing


class purgeFlag(commands.FlagConverter,
                case_insensitive=True,
                prefix="-",
                delimiter=' '):
    regex: typing.Optional[str]
    attachment: typing.Optional[bool]
    links: typing.Optional[bool]
    iregex: typing.Optional[str]
