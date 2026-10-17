from __future__ import annotations

from collections.abc import Awaitable, Callable, Hashable
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from functools import lru_cache
from typing import Any

import discord
import re2

from core.constants import INVITE_RE

from .configs import AllCapsConfig, CountConfig, LengthConfig, ListConfig, RegexConfig, TimeWindowConfig, ViolationConfig
from .enum import TriggerType as T
from .environment import Environment as TriggerEnv
from .utils import RATE_LIMITS, count_letters, covered, link_hosts, mentioned_ids, words_of

NEGATED = {T.MESSAGE_NOT_REGEX, T.NICKNAME_NOT_REGEX, T.JOIN_USERNAME_NOT_REGEX}
ALLOWLISTS = {T.WORD_ALLOWLIST, T.NICKNAME_WORD_ALLOWLIST, T.JOIN_USERNAME_WORD_ALLOWLIST}


class TriggerEnvError(RuntimeError):
    pass


class TriggerEvent(StrEnum):
    MESSAGE = "message"
    MEMBER_JOIN = "member_join"
    NICKNAME_CHANGE = "nickname_change"
    VIOLATION = "violation"
    DISCORD_AUTOMOD = "discord_automod"


@lru_cache(maxsize=512)
def compile_pattern(pattern: str):
    try:
        return re2.compile(pattern)
    except re2.error:
        return None


def window(minutes: int) -> timedelta:
    return timedelta(minutes=minutes)


@dataclass(frozen=True, slots=True)
class Subject:
    kind: T
    event: TriggerEvent
    guild_id: int
    env: TriggerEnv | None = None
    message: discord.Message | None = None
    member: discord.Member | None = None
    audit_log_entry: discord.AuditLogEntry | None = None
    key: Hashable | None = None

    def require_key(self) -> Hashable:
        if self.key is None:
            msg = f"{self.kind.value!r} needs a rule key"
            raise TriggerEnvError(msg)
        return self.key

    @property
    def msg(self) -> discord.Message:
        assert self.message is not None
        return self.message

    @property
    def who(self) -> discord.Member:
        assert self.member is not None
        return self.member

    @property
    def text(self) -> str | None:
        match self.event:
            case TriggerEvent.MESSAGE:
                return self.msg.content
            case TriggerEvent.NICKNAME_CHANGE:
                return self.who.nick
            case TriggerEvent.MEMBER_JOIN:
                return self.who.name
            case _:
                return None

    def require_env(self) -> TriggerEnv:
        if self.env is None:
            msg = f"{self.kind.value!r} needs a TriggerEnv"
            raise TriggerEnvError(msg)
        return self.env


type Handler = Callable[[Any, Subject], Awaitable[bool]]


@dataclass(frozen=True, slots=True)
class Spec:
    handler: Handler
    event: TriggerEvent


HANDLERS: dict[T, Spec] = {}


def handles(*kinds: T, event: TriggerEvent) -> Callable[[Handler], Handler]:
    def register(handler: Handler) -> Handler:
        for kind in kinds:
            HANDLERS[kind] = Spec(handler, event)
        return handler

    return register


E = TriggerEvent


@handles(T.NEW_MEMBER, event=E.MEMBER_JOIN)
async def new_member(config: object, subject: Subject) -> bool:
    return True


@handles(T.ALL_CAPS, event=E.MESSAGE)
async def all_caps(config: AllCapsConfig, subject: Subject) -> bool:
    upper, total = count_letters(subject.msg.content)
    return total > 0 and total >= config.min_count and upper * 100 >= config.percentage * total


@handles(T.MESSAGE_MENTIONS, event=E.MESSAGE)
async def message_mentions(config: CountConfig, subject: Subject) -> bool:
    return len(mentioned_ids(subject.msg)) >= config.count


@handles(T.MESSAGE_LENGTH_GT, event=E.MESSAGE)
async def length_gt(config: LengthConfig, subject: Subject) -> bool:
    return len(subject.msg.content) > config.length


@handles(T.MESSAGE_LENGTH_LT, event=E.MESSAGE)
async def length_lt(config: LengthConfig, subject: Subject) -> bool:
    return len(subject.msg.content) < config.length


@handles(T.MESSAGE_WITH_ATTACHMENTS, event=E.MESSAGE)
async def with_attachments(config: object, subject: Subject) -> bool:
    return bool(subject.msg.attachments)


@handles(T.MESSAGE_WITHOUT_ATTACHMENTS, event=E.MESSAGE)
async def without_attachments(config: object, subject: Subject) -> bool:
    return not subject.msg.attachments


@handles(T.ANY_LINK, event=E.MESSAGE)
async def any_link(config: object, subject: Subject) -> bool:
    return bool(link_hosts(subject.msg.content))


@handles(T.SERVER_INVITES, event=E.MESSAGE)
@handles(T.JOIN_USERNAME_INVITE, event=E.MEMBER_JOIN)
async def invite(config: object, subject: Subject) -> bool:
    return INVITE_RE.search(subject.text or "") is not None


@handles(T.MESSAGE_REGEX, T.MESSAGE_NOT_REGEX, event=E.MESSAGE)
@handles(T.NICKNAME_REGEX, T.NICKNAME_NOT_REGEX, event=E.NICKNAME_CHANGE)
@handles(T.JOIN_USERNAME_REGEX, T.JOIN_USERNAME_NOT_REGEX, event=E.MEMBER_JOIN)
async def regex(config: RegexConfig, subject: Subject) -> bool:
    text = subject.text
    compiled = compile_pattern(config.regex)
    if text is None or compiled is None:
        return False
    return (compiled.search(text) is not None) != (subject.kind in NEGATED)


@handles(T.WORD_DENYLIST, T.WORD_ALLOWLIST, event=E.MESSAGE)
@handles(T.NICKNAME_WORD_DENYLIST, T.NICKNAME_WORD_ALLOWLIST, event=E.NICKNAME_CHANGE)
@handles(T.JOIN_USERNAME_WORD_DENYLIST, T.JOIN_USERNAME_WORD_ALLOWLIST, event=E.MEMBER_JOIN)
async def word_list(config: ListConfig, subject: Subject) -> bool:
    text = subject.text
    if config.list_name is None or text is None:
        return False

    entries = await subject.require_env().get_list(subject.guild_id, config.list_name)
    if entries is None:
        return False

    words = words_of(text)
    if subject.kind in ALLOWLISTS:
        return any(word not in entries for word in words)
    return any(word in entries for word in words)


@handles(T.WEBSITE_DENYLIST, T.WEBSITE_ALLOWLIST, event=E.MESSAGE)
async def website_list(config: ListConfig, subject: Subject) -> bool:
    hosts = link_hosts(subject.msg.content)
    if config.list_name is None or not hosts:
        return False

    domains = await subject.require_env().get_list(subject.guild_id, config.list_name)
    if domains is None:
        return False

    if subject.kind is T.WEBSITE_ALLOWLIST:
        return any(not covered(host, domains) for host in hosts)
    return any(covered(host, domains) for host in hosts)


@handles(T.FLAGGED_SCAM_LINKS, event=E.MESSAGE)
async def scam_links(config: object, subject: Subject) -> bool:
    hosts = dict.fromkeys(link_hosts(subject.msg.content))
    if not hosts:
        return False

    env = subject.require_env()
    for host in hosts:
        if await env.is_flagged_domain(host):
            return True
    return False


@handles(T.DISCORD_AUTOMOD, event=E.DISCORD_AUTOMOD)
async def discord_automod(config: object, subject: Subject) -> bool:
    if subject.audit_log_entry is None:
        return False
    return await subject.require_env().discord_automod_flagged(subject.audit_log_entry)


@handles(*RATE_LIMITS, T.X_CONSECUTIVE_IDENTICAL_MESSAGES, event=E.MESSAGE)
async def rate_limit(config: TimeWindowConfig, subject: Subject) -> bool:
    return await subject.require_env().rate_hit(subject.require_key(), subject.kind, config, subject.msg)


@handles(T.VIOLATIONS, event=E.VIOLATION)
async def named_violations(config: ViolationConfig, subject: Subject) -> bool:
    total = await subject.require_env().violation_count(
        guild_id=subject.guild_id,
        user_id=subject.who.id,
        name=config.violation_name,
        within=window(config.within_minutes),
    )
    return total >= config.number_of_violations


@handles(T.X_VIOLATION_IN_Y_MINUTES, event=E.VIOLATION)
async def any_violations(config: TimeWindowConfig, subject: Subject) -> bool:
    total = await subject.require_env().violation_count(
        guild_id=subject.guild_id,
        user_id=subject.who.id,
        within=window(config.within_minutes),
    )
    return total >= config.count


async def evaluate(
    kind: T,
    config: object,
    *,
    message: discord.Message | None,
    member: discord.Member | None,
    env: TriggerEnv | None,
    key: Hashable | None = None,
) -> bool:
    spec = HANDLERS.get(kind)
    if spec is None:
        msg = f"no check is registered for {kind.value!r}"
        raise NotImplementedError(msg)

    if spec.event is TriggerEvent.MESSAGE:
        if message is None or message.guild is None:
            return False
        subject = Subject(kind, spec.event, message.guild.id, env, message=message, key=key)
    else:
        if member is None:
            return False
        subject = Subject(kind, spec.event, member.guild.id, env, member=member, key=key)

    return await spec.handler(config, subject)
