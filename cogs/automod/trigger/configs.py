from __future__ import annotations

from dataclasses import dataclass


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
