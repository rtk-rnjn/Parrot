from __future__ import annotations

import datetime
from collections.abc import Callable, Container, Iterable
from typing import TYPE_CHECKING, TypeAlias

from discord.ext.commands import BucketType, Cog, Command, CommandOnCooldown, Cooldown, CooldownMapping
from pymongo.collection import Collection

import discord
from core import Context, Parrot
from discord.ext import commands
from utilities import exceptions as ex
from utilities.config import SUPER_USER

if TYPE_CHECKING:
    from discord.ext.commands._types import Check

    from cogs.nsfw import NSFW


MongoCollection: TypeAlias = Collection
__all__ = (
    "can_run",
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


def in_server(guild_id: int) -> Check[Context]:
    def predicate(ctx: Context) -> bool:
        guild = ctx.bot.get_guild(guild_id)
        if not guild:
            return False

        if ctx.guild.id == guild.id:
            return True

        msg = f"You must be in server: `{guild.name}`, to use the command"
        raise ex.CustomError(msg)

    return commands.check(predicate)


def in_support_server() -> Check[Context]:
    def predicate(ctx: Context) -> bool:
        """Returns True if the guild is support server itself (SECTOR 17-29)."""

        if ctx.guild.id == ctx.bot.server.id:
            return True
        raise ex.NotInSupportServer()

    return commands.check(predicate)


def voter_only() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        """Returns True if the user is a voter."""
        if is_voter := await ctx.is_voter():
            return is_voter

        raise ex.NotVoter()

    return commands.check(predicate)


def is_guild_owner() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        if ctx.guild is not None and ctx.guild.owner_id == ctx.author.id:
            return True
        raise ex.NotGuildOwner()

    return commands.check(predicate)


def is_me() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        if ctx.message.author.id == SUPER_USER:  # `!! Ritik Ranjan [*.*]#9230`
            return True
        raise ex.NotMe()

    return commands.check(predicate)


def is_adult() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        cog: NSFW = ctx.bot.get_cog("NSFW")
        if cog is None:
            return True
        is_adult = await cog.check_user_age(ctx)
        if not is_adult:
            raise ex.NotAdult()
        return is_adult

    return commands.check(predicate)


def has_verified_role_ticket() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        data = ctx.bot.guild_configurations_cache[ctx.guild.id]
        data = data["ticket_config"]
        roles = data["verified_roles"]
        if not roles:
            raise ex.NoVerifiedRoleTicket()

        if any(ctx.author.get_role(role) for role in roles):
            return True

        raise ex.NoVerifiedRoleTicket()

    return commands.check(predicate)


def is_mod() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        bot: Parrot = ctx.bot
        try:
            role = bot.guild_configurations_cache[ctx.guild.id]["mod_role"] or 0  # role could be `None`
            if ctx.author.get_role(role):
                return True
            raise ex.NoModRole()
        except KeyError:
            pass

        data = ctx.bot.guild_configurations_cache[ctx.guild.id]
        role = ctx.guild.get_role(data["mod_role"])
        if role and role in ctx.author.roles:
            return True
        raise ex.NoModRole()

    return commands.check(predicate)


def in_temp_channel() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        if not ctx.author.voice:
            raise ex.InHubVoice()

        if _ := await ctx.bot.guild_configurations.find_one(
            {
                "_id": ctx.guild.id,
                "hub_temp_channels.channel_id": getattr(ctx.author.voice.channel, "id", 0),
                "hub_temp_channels.author": ctx.author.id,
            },
        ):
            return True

        raise ex.InHubVoice()

    return commands.check(predicate)


def can_run(ctx: Context) -> bool | None:
    """Return True is the command is whitelisted in specific channel, also with specific role."""
    try:
        if ctx.bot.banned_users[ctx.author.id]["command"] is True:
            return False
    except KeyError:
        pass

    cmd = ctx.command.qualified_name.replace(" ", "_")
    cog = getattr(ctx.cog, "qualified_name", "").replace(" ", "_")

    cmd_config = ctx.bot.guild_configurations_cache[ctx.guild.id].get("cmd_config", {})

    for cmd_cog in (cmd, cog):
        return _can_run(cmd_cog, cmd_config, cmd, ctx)


def _can_run(cmd_cog: str, cmd_config: dict, cmd: str, ctx: Context) -> bool | None:
    # fmt: off
    global_check          = f"CMD_GLOBAL_ENABLE_{cmd_cog}".upper()  # noqa
    role_check_disable    = f"CMD_ROLE_DISABLE_{cmd_cog}".upper()  # noqa
    channel_check_disable = f"CMD_CHANNEL_DISABLE_{cmd_cog}".upper()  # noqa
    # fmt: on

    if any(r.id in cmd_config.get(role_check_disable, []) for r in ctx.author.roles):
        return False

    if ctx.channel.id in cmd_config.get(channel_check_disable, []):
        return False

    return cmd_config.get(global_check)


def guild_premium() -> Check[Context]:
    def predicate(ctx: Context) -> bool | None:
        """Returns True if the guild is premium."""
        if ctx.guild is not None and ctx.bot.guild_configurations_cache[ctx.guild.id].get("premium", False):
            return True

        raise ex.NotPremiumServer()

    return commands.check(predicate)


def is_dj() -> Check[Context]:
    async def predicate(ctx: Context) -> bool | None:
        """Returns True if the user is a DJ."""
        assert isinstance(ctx.author, discord.Member)
        if role := await ctx.dj_role():
            return role in ctx.author.roles

        raise ex.NoDJRole()

    return commands.check(predicate)


def in_voice() -> Check[Context]:
    def predicate(ctx: Context) -> bool | None:
        assert isinstance(ctx.author, discord.Member)
        if ctx.author.voice is None:
            raise ex.NotInVoice()
        return True

    return commands.check(predicate)


def same_voice() -> Check[Context]:
    async def predicate(ctx: Context) -> bool | None:
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
    bypass_roles: Iterable[int | str],
) -> Callable:
    """Applies a cooldown to a command, but allows members with certain roles to be ignored.
    NOTE: this replaces the `Command.before_invoke` callback, which *might* introduce problems in the future.
    """
    # Make it a set so lookup is hash based.
    bypass = set(bypass_roles)

    # This handles the actual cooldown logic.
    buckets = CooldownMapping(Cooldown(rate, per), _type)

    # Will be called after the command has been parse but before it has been invoked, ensures that
    # the cooldown won't be updated if the user screws up their input to the command.
    async def predicate(cog: Cog, ctx: Context) -> None:
        nonlocal bypass, buckets
        assert isinstance(ctx.author, discord.Member)
        if any((role.id in bypass or role.name in bypass) for role in ctx.author.roles):
            return

        # Cooldown logic, taken from discord.py internals.
        current = ctx.message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
        bucket = buckets.get_bucket(ctx.message)
        if bucket is None:
            return

        retry_after = bucket.update_rate_limit(current)
        if retry_after:
            raise CommandOnCooldown(bucket, retry_after, _type)

    def wrapper(command: Command) -> Command:
        # NOTE: this could be changed if a subclass of Command were to be used. I didn't see the need for it
        # so I just made it raise an error when the decorator is applied before the actual command object exists.
        #
        # If the `before_invoke` detail is ever a problem then I can quickly just swap over.
        if not isinstance(command, Command):
            msg = "Decorator `cooldown_with_role_bypass` must be applied after the command decorator. This means it has to be above the command decorator in the code."
            raise TypeError(
                msg,
            )

        command._before_invoke = predicate

        return command

    return wrapper


def without_role_check(ctx: Context, *role_ids: int) -> bool:
    """Returns True if the user does not have any of the roles in role_ids."""
    assert isinstance(ctx.guild, discord.Guild) and isinstance(ctx.author, discord.Member)
    author_roles = [role.id for role in ctx.author.roles]
    return all(role not in author_roles for role in role_ids)


def with_role_check(ctx: Context, *role_ids: int) -> bool:
    """Returns True if the user has any one of the roles in role_ids."""
    assert isinstance(ctx.guild, discord.Guild) and isinstance(ctx.author, discord.Member)

    return any(role.id in role_ids for role in ctx.author.roles) if ctx.guild else False


def in_whitelist_check(
    ctx: Context,
    channels: Container[int] = (),
    categories: Container[int] = (),
    roles: Container[int] = (),
    redirect: int | None = None,
    fail_silently: bool = False,
) -> bool:
    """Check if a command was issued in a whitelisted context.
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
    if categories and hasattr(ctx.channel, "category_id") and ctx.channel.category_id in categories:
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

    def __init__(self, redirect_channel: int | None) -> None:
        self.redirect_channel = redirect_channel

        if redirect_channel:
            redirect_message = f" here. Please use the <#{redirect_channel}> channel instead"
        else:
            redirect_message = ""

        error_message = f"You are not allowed to use that command{redirect_message}."

        super().__init__(error_message)
