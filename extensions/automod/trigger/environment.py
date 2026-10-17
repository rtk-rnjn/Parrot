from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable, Hashable, Sequence
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .configs import TimeWindowConfig
from .enum import TriggerType as T
from .utils import RATE_LIMITS, Metric, Scope, link_hosts, mentioned_ids, normalize

if TYPE_CHECKING:
    from core import Bot

BUCKETS = {Scope.USER: commands.BucketType.user, Scope.CHANNEL: commands.BucketType.channel}


def units(metric: Metric, message: discord.Message) -> int:
    match metric:
        case Metric.MESSAGES:
            return 1
        case Metric.LINKS:
            return len(link_hosts(message.content))
        case Metric.ATTACHMENTS:
            return len(message.attachments)
        case Metric.MENTIONS:
            return len(mentioned_ids(message))


class RateLimiter:
    def __init__(self, *, clock: Callable[[], float] | None = None) -> None:
        self.clock = clock or time.time
        self.max_tracked_senders = 5000

        self.mappings: dict[tuple[int, Hashable, T, TimeWindowConfig], commands.CooldownMapping[discord.Message]] = {}
        self.last_seen: OrderedDict[tuple[tuple[int, Hashable, T, TimeWindowConfig], int], str] = OrderedDict()

    def mapping_for(
        self,
        guild_id: int,
        key: Hashable,
        kind: T,
        config: TimeWindowConfig,
    ) -> tuple[tuple[int, Hashable, T, TimeWindowConfig], commands.CooldownMapping[discord.Message]]:
        mapping_key: tuple[int, Hashable, T, TimeWindowConfig] = (guild_id, key, kind, config)
        mapping = self.mappings.get(mapping_key)
        if mapping is None:
            bucket = BUCKETS[RATE_LIMITS[kind][0]] if kind in RATE_LIMITS else commands.BucketType.user
            mapping = self.mappings[mapping_key] = config.cooldown(bucket)
        return mapping_key, mapping

    async def rate_hit(self, key: Hashable, kind: T, config: TimeWindowConfig, message: discord.Message) -> bool:
        if message.guild is None or message.author.bot:
            return False

        now = self.clock()
        mapping_key, mapping = self.mapping_for(message.guild.id, key, kind, config)

        if kind is T.X_CONSECUTIVE_IDENTICAL_MESSAGES:
            fingerprint = " ".join(normalize(message.content).split())
            if not fingerprint:
                return False
            sender: tuple[tuple[int, Hashable, T, TimeWindowConfig], int] = (mapping_key, message.author.id)
            if self.last_seen.get(sender) != fingerprint:
                mapping.get_bucket(message, now).reset()
            self.last_seen[sender] = fingerprint
            self.last_seen.move_to_end(sender)
            while len(self.last_seen) > self.max_tracked_senders:
                self.last_seen.popitem(last=False)
            amount = 1
        else:
            amount = units(RATE_LIMITS[kind][1], message)

        if amount == 0:
            return False
        return mapping.update_rate_limit(message, now, tokens=amount) is not None

    def forget_rule(self, guild_id: int, key: Hashable) -> None:
        for mapping_key in [k for k in self.mappings if k[0] == guild_id and k[1] == key]:
            del self.mappings[mapping_key]
        for sender in [s for s in self.last_seen if s[0][0] == guild_id and s[0][1] == key]:
            del self.last_seen[sender]


class AutomodEnvironment:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_list(self, guild_id: int, name: str) -> Sequence[str] | None:
        built_in = await self.bot.database.get_automod_list(guild_id=guild_id, list_name=name)  # pyright: ignore[reportArgumentType]
        if built_in is not None:
            return built_in

        return await self.bot.database.get_automod_custom_list(guild_id=guild_id, list_name=name)

    async def is_flagged_domain(self, host: str) -> bool:
        return await self.bot.database.is_scam_link(host)

    async def discord_automod_flagged(self, entry: discord.AuditLogEntry) -> bool:
        automod_actions = (
            discord.AuditLogAction.automod_block_message,
            discord.AuditLogAction.automod_flag_message,
            discord.AuditLogAction.automod_quarantine_user,
            discord.AuditLogAction.automod_timeout_member,
        )
        return entry.action in automod_actions and entry.target is not None

    async def violation_count(
        self,
        *,
        guild_id: int,
        user_id: int,
        name: str = "default",
        within: timedelta,
    ) -> int:
        return await self.bot.database.get_violation_count(
            guild_id=guild_id,
            user_id=user_id,
            violation_name=name,
            within=within,
        )


class Environment(AutomodEnvironment, RateLimiter):
    def __init__(self, bot: Bot):
        super().__init__(bot)
