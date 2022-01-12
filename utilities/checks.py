from __future__ import annotations

from discord.ext import commands
from discord.ext.commands import (
    BucketType,
    CheckFailure,
    Cog,
    Command,
    CommandOnCooldown,
    Context,
    Cooldown,
    CooldownMapping,
)
from utilities import exceptions as ex
from utilities.config import SUPER_USER
from typing import Callable, Optional
from collections.abc import Container, Iterable
import datetime
from utilities.database import parrot_db, enable_disable

collection = parrot_db["server_config"]
c = parrot_db["ticket"]


def is_guild_owner():
    async def predicate(ctx):
        if ctx.guild is not None and ctx.guild.owner_id == ctx.author.id:
            return True
        raise ex.NotGuildOwner()

    return commands.check(predicate)


def is_me():
    async def predicate(ctx):
        if ctx.message.author.id == SUPER_USER:  # !! Ritik Ranjan [*.*]#9230
            return True
        raise ex.NotMe()

    return commands.check(predicate)


def has_verified_role_ticket():
    async def predicate(ctx):
        data = await c.find_one({"_id": ctx.guild.id})
        if not data:
            return False
        data = await c.find_one({"_id": ctx.guild.id})
        roles = data["verified_roles"]
        if not roles:
            return False
        for role in roles:
            if ctx.guild.get_role(role) in ctx.author.roles:
                return True

        raise ex.NoVerifiedRoleTicket()

    return commands.check(predicate)


def is_mod():
    async def predicate(ctx):
        data = await collection.find_one({"_id": ctx.guild.id})
        if not data:
            return False
        role = ctx.guild.get_role(data["mod_role"])
        if not role:
            return False
        if role in ctx.author.roles:
            return True
        raise ex.NoModRole()

    return commands.check(predicate)


def can_run():
    async def predicate(ctx):
        data = await collection.find_one({"_id": ctx.author.id})
        if not data:
            return True
        if data["cmd"]:
            return False
        if data["global"]:
            return False

    return commands.check(predicate)


async def _can_run(ctx):
    """Return True is the command is whitelisted in specific channel, also with specific role"""
    if ctx.guild is not None:
        roles = set(ctx.author.roles)
        collection = enable_disable[f"{ctx.guild.id}"]
        if ctx.command:
            if data := await collection.find_one({"_id": ctx.command.qualified_name}):
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
        if ctx.command.cog:
            # Incase I made a command from jsk and its might be obv that cog is None
            if data := await collection.find_one(
                {"_id": ctx.command.cog.qualified_name}
            ):
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
        if data := await collection.find_one({"_id": "all"}):
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
        return True
    return False


def cooldown_with_role_bypass(
    rate: int,
    per: float,
    type: BucketType = BucketType.default,
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
    buckets = CooldownMapping(Cooldown(rate, per, type))

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
    if not ctx.guild:  # Return False in a DM
        return False

    author_roles = [role.id for role in ctx.author.roles]
    check = all(role not in author_roles for role in role_ids)
    return check


def with_role_check(ctx: Context, *role_ids: int) -> bool:
    """Returns True if the user has any one of the roles in role_ids."""
    if not ctx.guild:  # Return False in a DM
        return False

    for role in ctx.author.roles:
        if role.id in role_ids:
            return True

    return False


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


class InWhitelistCheckFailure(CheckFailure):
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
