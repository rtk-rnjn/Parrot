from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import discord

from .configs import CategoriesConfig, ChannelsConfig, DurationConfig, RolesConfig
from .enum import ConditionType as C

type Handler = Callable[[Any, Subject], bool]

HANDLERS: dict[C, Handler] = {}


def handles(*kinds: C) -> Callable[[Handler], Handler]:
    def register(handler: Handler) -> Handler:
        for kind in kinds:
            HANDLERS[kind] = handler
        return handler

    return register


@dataclass(frozen=True, slots=True)
class Subject:
    now: datetime
    user: discord.Member
    message: discord.Message | None = None
    edited: bool | None = None

    @property
    def role_ids(self) -> frozenset[int]:
        if isinstance(self.user, discord.Member):
            return frozenset(role.id for role in self.user.roles)
        return frozenset()

    @property
    def channel_ids(self) -> frozenset[int]:
        if self.message is None:
            return frozenset()
        channel = self.message.channel
        ids = {channel.id}
        if isinstance(channel, discord.Thread) and channel.parent_id is not None:
            ids.add(channel.parent_id)
        return frozenset(ids)

    @property
    def category_ids(self) -> frozenset[int]:
        if self.message is None:
            return frozenset()
        category_id = getattr(self.message.channel, "category_id", None)
        return frozenset() if category_id is None else frozenset({category_id})

    @property
    def in_thread(self) -> bool:
        return self.message is not None and isinstance(self.message.channel, discord.Thread)

    @property
    def is_forward(self) -> bool:
        return self.message is not None and bool(self.message.message_snapshots)

    @property
    def account_age(self) -> timedelta:
        return self.now - self.user.created_at

    @property
    def member_age(self) -> timedelta | None:
        joined = getattr(self.user, "joined_at", None)
        return None if joined is None else self.now - joined


def minutes(config: DurationConfig) -> timedelta:
    return timedelta(minutes=config.minutes)


@handles(C.IGNORED_ROLES)
def ignored_roles(config: RolesConfig, subject: Subject) -> bool:
    return subject.role_ids.isdisjoint(config.roles)


@handles(C.REQUIRED_ROLES)
def required_roles(config: RolesConfig, subject: Subject) -> bool:
    wanted = frozenset(config.roles)
    if not wanted:
        return False
    return wanted <= subject.role_ids if config.require_all else not wanted.isdisjoint(subject.role_ids)


@handles(C.IGNORED_CHANNELS)
def ignored_channels(config: ChannelsConfig, subject: Subject) -> bool:
    return subject.channel_ids.isdisjoint(config.channels)


@handles(C.ACTIVE_CHANNELS)
def active_channels(config: ChannelsConfig, subject: Subject) -> bool:
    return not subject.channel_ids.isdisjoint(config.channels)


@handles(C.IGNORED_CATEGORIES)
def ignored_categories(config: CategoriesConfig, subject: Subject) -> bool:
    return subject.category_ids.isdisjoint(config.categories)


@handles(C.ACTIVE_CATEGORIES)
def active_categories(config: CategoriesConfig, subject: Subject) -> bool:
    return not subject.category_ids.isdisjoint(config.categories)


@handles(C.ACCOUNT_AGE_ABOVE)
def account_age_above(config: DurationConfig, subject: Subject) -> bool:
    return subject.account_age > minutes(config)


@handles(C.ACCOUNT_AGE_BELOW)
def account_age_below(config: DurationConfig, subject: Subject) -> bool:
    return subject.account_age < minutes(config)


@handles(C.MEMBER_DURATION_ABOVE)
def member_duration_above(config: DurationConfig, subject: Subject) -> bool:
    age = subject.member_age
    return age is not None and age > minutes(config)


@handles(C.MEMBER_DURATION_BELOW)
def member_duration_below(config: DurationConfig, subject: Subject) -> bool:
    age = subject.member_age
    return age is not None and age < minutes(config)


@handles(C.IGNORE_BOTS)
def ignore_bots(config: object, subject: Subject) -> bool:
    return not subject.user.bot


@handles(C.ONLY_BOTS)
def only_bots(config: object, subject: Subject) -> bool:
    return subject.user.bot


@handles(C.NEW_MESSAGE)
def new_message(config: object, subject: Subject) -> bool:
    return subject.edited is False


@handles(C.EDITED_MESSAGE)
def edited_message(config: object, subject: Subject) -> bool:
    return subject.edited is True


@handles(C.ACTIVE_IN_THREADS)
def active_in_threads(config: object, subject: Subject) -> bool:
    return subject.in_thread


@handles(C.IGNORE_THREADS)
def ignore_threads(config: object, subject: Subject) -> bool:
    return not subject.in_thread


@handles(C.IGNORE_FORWARDS)
def ignore_forwards(config: object, subject: Subject) -> bool:
    return not subject.is_forward


@handles(C.ONLY_FORWARDS)
def only_forwards(config: object, subject: Subject) -> bool:
    return subject.is_forward


def evaluate(
    kind: C,
    config: object,
    *,
    message: discord.Message | None,
    member: discord.Member | None,
    edited: bool | None,
    now: datetime | None,
) -> bool:
    handler = HANDLERS.get(kind)
    if handler is None:
        msg = f"no check is registered for {kind.value!r}"
        raise NotImplementedError(msg)

    user = member if member is not None else message.author
    if edited is None and message is not None:
        edited = message.edited_at is not None

    subject = Subject(now=now or discord.utils.utcnow(), user=user, message=message, edited=edited)
    return handler(config, subject)
