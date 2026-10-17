from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal, Protocol

import discord

from ..trigger import TriggerType
from .configs import (
    AlertConfig,
    BanConfig,
    DeleteMessagesConfig,
    MessageConfig,
    MuteConfig,
    NicknameConfig,
    RoleConfig,
    SendMessageConfig,
    SlowmodeConfig,
    TimeoutConfig,
    ViolationConfig,
)
from .enum import EffectType as E

if TYPE_CHECKING:
    from core import Bot

    from .effect import Effect

log = logging.getLogger(__name__)

DEFAULT_VIOLATION = "default"
MAX_TIMEOUT = timedelta(days=28) - timedelta(minutes=1)
BULK_MAX_AGE = timedelta(days=14) - timedelta(minutes=5)
MAX_BULK = 100
SCAN_LIMIT = 300
MAX_SLOWMODE = 21600
MAX_BAN_DAYS = 7
LAST = frozenset({E.KICK_USER, E.BAN_USER})


class EffectStore(Protocol):
    async def add_violation(self, guild_id: int, user_id: int, name: str, *, rule_name: str, at: datetime) -> None: ...

    async def reset_violations(self, guild_id: int, user_id: int, name: str | None) -> int: ...

    async def mute_member(self, member: discord.Member, *, duration: timedelta | None, reason: str) -> None: ...


class Status(StrEnum):
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class EffectOutcome:
    type: E
    status: Status
    detail: str = ""


class Skip(Exception):
    pass


@dataclass(frozen=True, slots=True)
class EffectContext:
    bot: Bot
    store: EffectStore
    guild: discord.Guild
    member: discord.Member
    rule_name: str
    trigger_type: TriggerType
    message: discord.Message | None = None
    now: datetime = field(default_factory=discord.utils.utcnow)

    @property
    def channel(self) -> Any:
        return None if self.message is None else self.message.channel


type Handler = Callable[[Any, EffectContext], Awaitable[str | None]]

HANDLERS: dict[E, Handler] = {}


def handles(*kinds: E) -> Callable[[Handler], Handler]:
    def register(handler: Handler) -> Handler:
        for kind in kinds:
            HANDLERS[kind] = handler
        return handler

    return register


def audit_reason(ctx: EffectContext) -> str:
    return f"Automod rule: {ctx.rule_name}"[:512]


def require_member(ctx: EffectContext) -> discord.Member:
    if not isinstance(ctx.member, discord.Member):
        msg = "the target is not a server member"
        raise Skip(msg)
    return ctx.member


def require_message(ctx: EffectContext) -> discord.Message:
    if ctx.message is None:
        msg = "this event has no message"
        raise Skip(msg)
    return ctx.message


def require_channel(ctx: EffectContext) -> Any:
    if ctx.message is None:
        msg = "this event has no channel"
        raise Skip(msg)
    return ctx.message.channel


def permissions_in(ctx: EffectContext, channel: Any) -> discord.Permissions | None:
    permissions_for = getattr(channel, "permissions_for", None)
    return None if permissions_for is None else permissions_for(ctx.guild.me)


def require_permissions(permissions: discord.Permissions | None, *names: str) -> None:
    if permissions is None:
        return
    missing = [name.replace("_", " ") for name in names if not getattr(permissions, name)]
    if missing:
        msg = "the bot is missing: " + ", ".join(missing)
        raise Skip(msg)


def require_hierarchy(ctx: EffectContext, member: discord.Member) -> None:
    me = ctx.guild.me
    if member.id == me.id:
        msg = "the target is the bot itself"
        raise Skip(msg)
    if member.id == ctx.guild.owner_id:
        msg = "the target is the server owner"
        raise Skip(msg)
    if member.top_role >= me.top_role:
        msg = "the target's top role is not below the bot's top role"
        raise Skip(msg)


def substitute(text: str, ctx: EffectContext) -> str:
    replacements = {
        "{user}": ctx.member.mention,
        "{user.name}": ctx.member.name,
        "{user.id}": str(ctx.member.id),
        "{server}": ctx.guild.name,
        "{channel}": getattr(ctx.channel, "mention", ""),
        "{rule}": ctx.rule_name,
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


async def notify(ctx: EffectContext, member: discord.Member, text: str | None) -> bool:
    if not text:
        return False
    body = f"**{ctx.guild.name}**\n{substitute(text, ctx)}"[:2000]
    try:
        await member.send(body)
    except discord.HTTPException:
        return False
    return True


EVENT_NAME = Literal["automod_unban", "automod_role", "automod_slowmode"]


async def schedule(ctx: EffectContext, event_name: EVENT_NAME, after: timedelta, metadata: dict[str, object]) -> None:
    await ctx.bot.event_scheduler.create_timer(event_name=event_name, expires_at=ctx.now + after, metadata=metadata)


def target_channel(ctx: EffectContext, channel_id: int | None, *, embed: bool = False) -> Any:
    if channel_id is not None:
        channel = ctx.guild.get_channel_or_thread(channel_id)
        if channel is None:
            msg = "the configured channel no longer exists"
            raise Skip(msg)
    elif ctx.message is not None:
        channel = ctx.message.channel
    else:
        msg = "no channel to send to; pick one explicitly for this kind of event"
        raise Skip(msg)

    if not hasattr(channel, "send"):
        msg = "the configured channel cannot receive messages"
        raise Skip(msg)

    sending = "send_messages_in_threads" if isinstance(channel, discord.Thread) else "send_messages"
    names = ("view_channel", sending, *(("embed_links",) if embed else ()))
    require_permissions(permissions_in(ctx, channel), *names)
    return channel


def resolve_role(ctx: EffectContext, role_id: int | None) -> discord.Role:
    if role_id is None:
        msg = "no role is configured"
        raise Skip(msg)
    role = ctx.guild.get_role(role_id)
    if role is None:
        msg = "the configured role no longer exists"
        raise Skip(msg)
    if role.is_default() or role.managed:
        msg = "the role cannot be assigned manually"
        raise Skip(msg)
    if role >= ctx.guild.me.top_role:
        msg = "the role is not below the bot's top role"
        raise Skip(msg)
    return role


@handles(E.DELETE_MESSAGE)
async def delete_message(config: object, ctx: EffectContext) -> str | None:
    message = require_message(ctx)
    require_permissions(permissions_in(ctx, message.channel), "manage_messages")
    await message.delete()
    return None


@handles(E.ADD_VIOLATION)
async def add_violation(config: ViolationConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    name = config.name or DEFAULT_VIOLATION
    await ctx.store.add_violation(ctx.guild.id, member.id, name, rule_name=ctx.rule_name, at=ctx.now)
    ctx.bot.dispatch("automod_violation", member, name)
    return name


@handles(E.RESET_VIOLATIONS)
async def reset_violations(config: ViolationConfig, ctx: EffectContext) -> str | None:
    removed = await ctx.store.reset_violations(ctx.guild.id, ctx.member.id, config.name)
    return f"removed {removed}"


@handles(E.WARN_USER)
async def warn_user(config: MessageConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    text = config.message or "You have received a warning from this server's automod."
    if not await notify(ctx, member, text):
        msg = "the user's DMs are closed"
        raise Skip(msg)
    return None


@handles(E.KICK_USER)
async def kick_user(config: MessageConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    require_permissions(ctx.guild.me.guild_permissions, "kick_members")
    require_hierarchy(ctx, member)
    notified = await notify(ctx, member, config.message)
    await member.kick(reason=audit_reason(ctx))
    return "notified" if notified else None


@handles(E.BAN_USER)
async def ban_user(config: BanConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    require_permissions(ctx.guild.me.guild_permissions, "ban_members")
    require_hierarchy(ctx, member)
    notified = await notify(ctx, member, config.message)
    days = min(max(config.delete_days, 0), MAX_BAN_DAYS)
    await ctx.guild.ban(member, reason=audit_reason(ctx), delete_message_seconds=days * 86400)
    if config.duration_minutes > 0:
        await schedule(
            ctx,
            "automod_unban",
            timedelta(minutes=config.duration_minutes),
            {"guild_id": ctx.guild.id, "user_id": member.id},
        )
    return "notified" if notified else None


@handles(E.MUTE_USER)
async def mute_user(config: MuteConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    require_hierarchy(ctx, member)
    notified = await notify(ctx, member, config.message)
    duration = timedelta(minutes=config.duration_minutes) if config.duration_minutes > 0 else None
    await ctx.store.mute_member(member, duration=duration, reason=audit_reason(ctx))
    return "notified" if notified else None


@handles(E.TIMEOUT_USER)
async def timeout_user(config: TimeoutConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    if config.duration_minutes <= 0:
        msg = "a timeout needs a duration of at least one minute"
        raise Skip(msg)
    require_permissions(ctx.guild.me.guild_permissions, "moderate_members")
    require_hierarchy(ctx, member)
    if member.guild_permissions.administrator:
        msg = "administrators cannot be timed out"
        raise Skip(msg)

    duration = min(timedelta(minutes=config.duration_minutes), MAX_TIMEOUT)
    current = member.timed_out_until
    if current is not None and current > ctx.now + duration:
        msg = "the member is already timed out for longer"
        raise Skip(msg)

    notified = await notify(ctx, member, config.message)
    await member.timeout(duration, reason=audit_reason(ctx))
    return "notified" if notified else None


@handles(E.SET_NICKNAME)
async def set_nickname(config: NicknameConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    require_permissions(ctx.guild.me.guild_permissions, "manage_nicknames")
    require_hierarchy(ctx, member)
    if member.nick == config.nickname:
        msg = "the nickname is already set"
        raise Skip(msg)
    await member.edit(nick=config.nickname, reason=audit_reason(ctx))
    return None


@handles(E.GIVE_ROLE)
async def give_role(config: RoleConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    require_permissions(ctx.guild.me.guild_permissions, "manage_roles")
    role = resolve_role(ctx, config.role_id)
    if role in member.roles:
        msg = "the member already has the role"
        raise Skip(msg)
    await member.add_roles(role, reason=audit_reason(ctx))
    if config.duration_seconds > 0:
        await schedule(
            ctx,
            "automod_role",
            timedelta(seconds=config.duration_seconds),
            {"guild_id": ctx.guild.id, "user_id": member.id, "role_id": role.id, "action": "remove"},
        )
    return None


@handles(E.REMOVE_ROLE)
async def remove_role(config: RoleConfig, ctx: EffectContext) -> str | None:
    member = require_member(ctx)
    require_permissions(ctx.guild.me.guild_permissions, "manage_roles")
    role = resolve_role(ctx, config.role_id)
    if role not in member.roles:
        msg = "the member does not have the role"
        raise Skip(msg)
    await member.remove_roles(role, reason=audit_reason(ctx))
    if config.duration_seconds > 0:
        await schedule(
            ctx,
            "automod_role",
            timedelta(seconds=config.duration_seconds),
            {"guild_id": ctx.guild.id, "user_id": member.id, "role_id": role.id, "action": "add"},
        )
    return None


@handles(E.ENABLE_SLOWMODE)
async def enable_slowmode(config: SlowmodeConfig, ctx: EffectContext) -> str | None:
    channel = require_channel(ctx)
    current = getattr(channel, "slowmode_delay", None)
    if current is None:
        msg = "this channel does not support slowmode"
        raise Skip(msg)

    rate = min(config.ratelimit_seconds, MAX_SLOWMODE)
    if rate <= 0:
        msg = "the slowmode delay must be at least one second"
        raise Skip(msg)
    if current >= rate:
        msg = "slowmode is already at least that strict"
        raise Skip(msg)

    needed = "manage_threads" if isinstance(channel, discord.Thread) else "manage_channels"
    require_permissions(permissions_in(ctx, channel), needed)
    await channel.edit(slowmode_delay=rate, reason=audit_reason(ctx))
    if config.duration_seconds > 0:
        await schedule(
            ctx,
            "automod_slowmode",
            timedelta(seconds=config.duration_seconds),
            {"guild_id": ctx.guild.id, "channel_id": channel.id, "restore": current, "applied": rate},
        )
    return None


@handles(E.DELETE_MULTIPLE_MESSAGES)
async def delete_multiple_messages(config: DeleteMessagesConfig, ctx: EffectContext) -> str | None:
    channel = require_channel(ctx)
    if not hasattr(channel, "purge"):
        msg = "this channel cannot delete messages in bulk"
        raise Skip(msg)
    require_permissions(permissions_in(ctx, channel), "manage_messages", "read_message_history")

    cutoff = max(ctx.now - timedelta(seconds=config.max_age_seconds), ctx.now - BULK_MAX_AGE)
    remaining = min(max(config.count, 1), MAX_BULK)
    author_id = ctx.member.id

    def check(found: discord.Message) -> bool:
        nonlocal remaining
        if remaining > 0 and found.author.id == author_id:
            remaining -= 1
            return True
        return False

    deleted = await channel.purge(
        limit=SCAN_LIMIT,
        check=check,
        after=cutoff,
        oldest_first=False,
        bulk=True,
        reason=audit_reason(ctx),
    )
    if not deleted:
        msg = "no recent messages to delete"
        raise Skip(msg)
    return f"deleted {len(deleted)}"


@handles(E.SEND_MESSAGE)
async def send_message(config: SendMessageConfig, ctx: EffectContext) -> str | None:
    if not config.message.strip():
        msg = "the message is empty"
        raise Skip(msg)

    channel = target_channel(ctx, config.channel_id)
    text = substitute(config.message, ctx)
    content = f"{ctx.member.mention} {text}" if config.ping_user else text
    allowed = discord.AllowedMentions(
        users=[ctx.member] if config.ping_user else False,
        roles=False,
        everyone=False,
        replied_user=False,
    )
    await channel.send(
        content[:2000],
        allowed_mentions=allowed,
        delete_after=config.delete_after_seconds or None,
    )
    return None


@handles(E.SEND_ALERT)
async def send_alert(config: AlertConfig, ctx: EffectContext) -> str | None:
    if not config.message.strip():
        msg = "the message is empty"
        raise Skip(msg)

    channel = target_channel(ctx, config.channel_id, embed=True)
    embed = (
        discord.Embed(
            title="Automod alert",
            description=substitute(config.message, ctx)[:4000],
            colour=discord.Colour.orange(),
            timestamp=ctx.now,
        )
        .add_field(name="User", value=f"{ctx.member.mention} (`{ctx.member.id}`)")
        .add_field(name="Rule", value=discord.utils.escape_markdown(ctx.rule_name)[:1024])
        .add_field(name="Trigger", value=f"`{ctx.trigger_type.value}`")
    )

    if ctx.message is not None:
        embed.add_field(name="Channel", value=getattr(ctx.message.channel, "mention", "unknown"))
        excerpt = discord.utils.escape_markdown(ctx.message.content[:500]) or "*no text*"
        embed.add_field(name="Message", value=f"{excerpt}\n[Jump to message]({ctx.message.jump_url})", inline=False)

    await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    return None


async def run_one(effect_type: E, config: object, ctx: EffectContext) -> EffectOutcome:
    handler = HANDLERS.get(effect_type)
    if handler is None:
        msg = f"no executor is registered for {effect_type.value!r}"
        raise NotImplementedError(msg)

    try:
        detail = await handler(config, ctx)
    except Skip as skip:
        return EffectOutcome(effect_type, Status.SKIPPED, str(skip))
    except discord.NotFound:
        return EffectOutcome(effect_type, Status.SKIPPED, "the target no longer exists")
    except discord.Forbidden:
        return EffectOutcome(effect_type, Status.FAILED, "Discord refused: missing permissions or role hierarchy")
    except discord.HTTPException as error:
        return EffectOutcome(effect_type, Status.FAILED, f"HTTP {error.status}: {error.text}")
    except Exception as error:
        log.exception("automod effect %s crashed", effect_type.value)
        return EffectOutcome(effect_type, Status.FAILED, f"{type(error).__name__}: {error}")
    return EffectOutcome(effect_type, Status.DONE, detail or "")


async def run_effects(effects: Sequence[Effect], ctx: EffectContext) -> list[EffectOutcome]:
    ordered = sorted(effects, key=lambda effect: effect.type in LAST)
    return [await run_one(effect.type, effect.config, ctx) for effect in ordered]
