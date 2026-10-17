from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import discord
from discord.ext import commands


@dataclass(frozen=True, slots=True)
class NoConfig:
    """Trigger has no configuration."""


@dataclass(frozen=True, slots=True)
class CountConfig:
    count: int


@dataclass(frozen=True, slots=True)
class TimeWindowConfig:
    count: int
    within_minutes: int

    def cooldown(
        self,
        bucket: commands.BucketType | Callable[[discord.Message], Any],
    ) -> commands.CooldownMapping[discord.Message]:
        return commands.CooldownMapping.from_cooldown(max(self.count - 1, 0), self.within_minutes * 60, bucket)


@dataclass(frozen=True, slots=True)
class ListConfig:
    list_name: str | None = None


@dataclass(frozen=True, slots=True)
class RegexConfig:
    regex: str


@dataclass(frozen=True, slots=True)
class LengthConfig:
    length: int


@dataclass(frozen=True, slots=True)
class ViolationConfig:
    violation_name: str
    number_of_violations: int
    within_minutes: int


@dataclass(frozen=True, slots=True)
class AllCapsConfig:
    min_count: int = 3
    percentage: int = 100
