from __future__ import annotations

import datetime
from collections.abc import Container, Iterable
from typing import Callable, Dict, List, Optional, TypeAlias, Union

from core import Context, Parrot
import discord
from discord.ext import commands
from discord.ext.commands import (  # type: ignore
    BucketType,
    Cog,
    Command,
    CommandOnCooldown,
    Cooldown,
    CooldownMapping,
)

from utilities import exceptions as ex
from utilities.config import SUPER_USER
from pymongo.collection import Collection

MongoCollection: TypeAlias = Collection
__all__ = (
    "_can_run",
    "cooldown_with_role_bypass",
    "guild_premium",
    "guild_premium",
    "has_verified_role_ticket",
    "in_support_server",
    "in_temp_channel",
    "in_voice",
    "in_whitelist_check",
    "is_dj",
    "is_guild_owner",
    "is_me",
    "is_mod",
    "same_voice",
    "voter_only",
    "with_role_check",
    "without_role_check",
)


def in_support_server() -> Callable:
    def predicate(ctx: Context) -> bool:
        """Returns True if the guild is support server itself (SECTOR 17-29)."""
        if ctx.guild.id == getattr(ctx.bot.server, "id"):
            return True
        raise ex.NotInSupportServer()

    return commands.check(predicate)


def voter_only() -> Callable:
    async def predicate(ctx: Context) -> Optional[bool]:
        """Returns True if the user is a voter."""
        if is_voter := await ctx.is_voter():
            return is_voter

        raise ex.NotVoter()

    return commands.check(predicate)


def is_guild_owner() -> Callable:
    async def predicate(ctx: Context) -> Optional[bool]:
        if ctx.guild is not None and ctx.guild.owner_id == ctx.author.id:
            return True
        raise ex.NotGuildOwner()

    return commands.check(predicate)


def is_me() -> Callable:
    async def predicate(ctx: Context) -> Optional[bool]:
        if ctx.message.author.id == SUPER_USER:  # `!! Ritik Ranjan [*.*]#9230`
            return True
        raise ex.NotMe()

    return commands.check(predicate)


def has_verified_role_ticket() -> Callable:
    async def predicate(ctx: Context) -> Optional[bool]:
        data = await ctx.bot.mongo.parrot_db.ticket.find_one({"_id": ctx.guild.id})
        if not data:
            raise ex.NoVerifiedRoleTicket()
        data = await ctx.bot.mongo.parrot_db.ticket.find_one({"_id": ctx.guild.id})
        roles = data["verified_roles"]
        if not roles:
            raise ex.NoVerifiedRoleTicket()

        if any(ctx.author._roles.has(role) for role in roles):
            return True

        raise ex.NoVerifiedRoleTicket()

    return commands.check(predicate)


def is_mod() -> Callable:  # sourcery skip: use-contextlib-suppress
    async def predicate(ctx: Context) -> Optional[bool]:
        bot: Parrot = ctx.bot
        try:
            role = (
                bot.server_config[ctx.guild.id]["mod_role"] or 0
            )  # role could be `None`
            if true := ctx.author._roles.has(role):
                return true
            raise ex.NoModRole()
        except KeyError:
            pass

        if data := await ctx.bot.mongo.parrot_db.server_config.find_one(
            {"_id": ctx.guild.id}
        ):
            role = ctx.guild.get_role(data["mod_role"])
            if role and role in ctx.author.roles:
                return True
        raise ex.NoModRole()

    return commands.check(predicate)


def in_temp_channel() -> Callable:
    async def predicate(ctx: Context) -> Optional[bool]:
        data = await ctx.bot.mongo.parrot_db.server_config.find_one(
            {"_id": ctx.guild.id}
        )
        if not data:
            raise ex.InHubVoice()

        if not ctx.author.voice:
            raise ex.InHubVoice()

        if data := await ctx.bot.mongo.parrot_db.server_config.find_one(
            {
                "_id": ctx.guild.id,
                "temp_channels.channel_id": ctx.author.voice.channel.id,
                "temp_channels.author": ctx.author.id,
            }
        ):
            return True

        raise ex.InHubVoice()

    return commands.check(predicate)


async def set_command_run_cache(context: Context):
    for guild in context.bot.guilds:
        context.bot.__disabled_commands[guild.id] = await _get_server_command_cache(
            guild=guild, bot=context.bot
        )


async def _get_server_command_cache(
    *,
    guild: discord.Guild,
    bot: Parrot,
    force_update: bool = False,
    command: Optional[str] = None,
):
    _cache: List = []
    collection: MongoCollection = bot.mongo.enabled_disable[f"{guild.id}"]

    def __internal_appender(data: Dict):
        data: Dict[str, Union[int, bool]]
        if data["_id"] != "all":
            cmd: commands.Command = bot.get_command(data["_id"])
            data.pop("_id")
            if cmd is not None:
                _cache.append({cmd: data})
        else:
            for cmd in bot.walk_commands():
                data.pop("_id")
                _cache.append({cmd: data})

    if command:
        data = await collection.find_one({"_id": command})
        __internal_appender(data)
    else:
        async for data in collection.find():
            __internal_appender(data)

    if force_update:
        bot.__disabled_commands[guild.id] = _cache

    return _cache


async def _can_run(ctx: Context) -> Optional[bool]:
    # sourcery skip: assign-if-exp, boolean-if-exp-identity
    # sourcery skip: reintroduce-else, remove-redundant-if, remove-unnecessary-cast
    """Return True is the command is whitelisted in specific channel, also with specific role"""
    _cached_data: List[
        Dict[commands.Command, Dict[str, Union[List[int], bool]]]
    ] = ctx.bot.__disabled_commands.get(ctx.guild.id)

    for data in _cached_data:
        for cmd in data:
            if cmd.qualified_name == ctx.command.qualified_name:
                return __internal_cmd_checker_parser(ctx=ctx, data=data)

    if not hasattr(ctx, "channel"):
        return True

    if ctx.guild is not None and ctx.command:
        collection = ctx.bot.mongo.enable_disable[f"{ctx.guild.id}"]
        if data := await collection.find_one(
            {
                "$or": [
                    {"_id": ctx.command.qualified_name},
                    {"_id": getattr(ctx.command.cog, "qualified_name", None)},
                    {"_id": "all"},
                ]
            }
        ):
            return __internal_cmd_checker_parser(ctx=ctx, data=data)

    return True


def __internal_cmd_checker_parser(*, ctx: Context, data: Dict):
    # sourcery skip: assign-if-exp, boolean-if-exp-identity, reintroduce-else, remove-redundant-if, remove-unnecessary-cast
    roles = set(ctx.author.roles)
    if ctx.channel.id in data["channel_in"]:
        return True
    if any(role.id in data["role_in"] for role in roles):
        return True
    if any(role.id in data["role_out"] for role in roles):
        return False
    if ctx.channel.id in data["channel_out"]:
        return False
    if data["server"]:
        return False
    if not data["server"]:
        return True


def guild_premium() -> Callable:
    def predicate(ctx: Context) -> bool:
        """Returns True if the guild is premium."""
        if ctx.guild is not None and ctx.bot.server_config[ctx.guild.id].get(
            "premium", False
        ):
            return True

        raise ex.NotPremiumServer()

    return commands.check(predicate)


def is_dj() -> Callable:
    async def predicate(ctx: Context) -> bool:
        """Returns True if the user is a DJ."""
        if role := await ctx.dj_role():
            return role in ctx.author.roles

        raise ex.NoDJRole()

    return commands.check(predicate)


def in_voice() -> Callable:
    def predicate(ctx: Context) -> bool:
        if ctx.author.voice is None:
            raise ex.NotInVoice()
        return True

    return commands.check(predicate)


def same_voice() -> Callable:
    async def predicate(ctx: Context) -> bool:
        if ctx.me.voice is None:
            raise ex.NotBotInVoice()
        if ctx.author.voice is None:
            raise ex.NotInVoice()
        if ctx.me.voice.channel != ctx.author.voice.channel:
            raise ex.NotSameVoice()

        return True

    return commands.check(predicate)


def cooldown_with_role_bypass(
    rate: int,
    per: float,
    _type: BucketType = BucketType.default,
    *,
    bypass_roles: Iterable[int],
) -> Callable:
    """
    Applies a cooldown to a command, but allows members with certain roles to be ignored.
    NOTE: this replaces the `Command.before_invoke` callback, which *might* introduce problems in the future.
    """
    # Make it a set so lookup is hash based.
    bypass = set(bypass_roles)

    # This handles the actual cooldown logic.
    buckets = CooldownMapping(Cooldown(rate, per, _type))

    # Will be called after the command has been parse but before it has been invoked, ensures that
    # the cooldown won't be updated if the user screws up their input to the command.
    async def predicate(cog: Cog, ctx: Context) -> None:
        nonlocal bypass, buckets

        if any(role.id in bypass for role in ctx.author.roles):
            return

        # Cooldown logic, taken from discord.py internals.
        current = ctx.message.created_at.replace(
            tzinfo=datetime.timezone.utc
        ).timestamp()
        bucket = buckets.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit(current)
        if retry_after:
            raise CommandOnCooldown(bucket, retry_after)

    def wrapper(command: Command) -> Command:
        # NOTE: this could be changed if a subclass of Command were to be used. I didn't see the need for it
        # so I just made it raise an error when the decorator is applied before the actual command object exists.
        #
        # If the `before_invoke` detail is ever a problem then I can quickly just swap over.
        if not isinstance(command, Command):
            raise TypeError(
                "Decorator `cooldown_with_role_bypass` must be applied after the command decorator. "
                "This means it has to be above the command decorator in the code."
            )

        command._before_invoke = predicate

        return command

    return wrapper


def without_role_check(ctx: Context, *role_ids: int) -> bool:
    """Returns True if the user does not have any of the roles in role_ids."""
    if not ctx.guild:
        return False
    author_roles = [role.id for role in ctx.author.roles]
    return all(role not in author_roles for role in role_ids)


def with_role_check(ctx: Context, *role_ids: int) -> bool:
    """Returns True if the user has any one of the roles in role_ids."""
    return any(role.id in role_ids for role in ctx.author.roles) if ctx.guild else False


def in_whitelist_check(
    ctx: Context,
    channels: Container[int] = (),
    categories: Container[int] = (),
    roles: Container[int] = (),
    redirect: Optional[int] = None,
    fail_silently: bool = False,
) -> bool:
    """
    Check if a command was issued in a whitelisted context.
    The whitelists that can be provided are:
    - `channels`: a container with channel ids for whitelisted channels
    - `categories`: a container with category ids for whitelisted categories
    - `roles`: a container with with role ids for whitelisted roles
    If the command was invoked in a context that was not whitelisted, the member is either
    redirected to the `redirect` channel that was passed (default: #bot-commands) or simply
    told that they're not allowed to use this particular command (if `None` was passed).
    """
    if redirect and redirect not in channels:
        # It does not make sense for the channel whitelist to not contain the redirection
        # channel (if applicable). That's why we add the redirection channel to the `channels`
        # container if it's not already in it. As we allow any container type to be passed,
        # we first create a tuple in order to safely add the redirection channel.
        #
        # Note: It's possible for the redirect channel to be in a whitelisted category, but
        # there's no easy way to check that and as a channel can easily be moved in and out of
        # categories, it's probably not wise to rely on its category in any case.
        channels = tuple(channels) + (redirect,)

    if channels and ctx.channel.id in channels:
        return True

    # Only check the category id if we have a category whitelist and the channel has a `category_id`
    if (
        categories
        and hasattr(ctx.channel, "category_id")
        and ctx.channel.category_id in categories
    ):
        return True

    # category = getattr(ctx.channel, "category", None)
    # if category and category.name == "GAMES":
    #     return True

    # Only check the roles whitelist if we have one and ensure the author's roles attribute returns
    # an iterable to prevent breakage in DM channels (for if we ever decide to enable commands there).
    if roles and any(r.id in roles for r in getattr(ctx.author, "roles", ())):
        return True

    # Some commands are secret, and should produce no feedback at all.
    if not fail_silently:
        raise InWhitelistCheckFailure(redirect)
    return False


class InWhitelistCheckFailure(ex.ParrotCheckFailure):
    """Raised when the `in_whitelist` check fails."""

    def __init__(self, redirect_channel: Optional[int]):
        self.redirect_channel = redirect_channel

        if redirect_channel:
            redirect_message = (
                f" here. Please use the <#{redirect_channel}> channel instead"
            )
        else:
            redirect_message = ""

        error_message = f"You are not allowed to use that command{redirect_message}."

        super().__init__(error_message)
