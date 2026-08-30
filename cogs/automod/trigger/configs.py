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
    within_seconds: int


@dataclass(frozen=True, slots=True)
class ListConfig:
    list_name: str | None = None
    match_similar: bool = False


@dataclass(frozen=True, slots=True)
class RegexConfig:
    regex: str
    match_similar: bool = False


@dataclass(frozen=True, slots=True)
class LengthConfig:
    length: int


@dataclass(frozen=True, slots=True)
class MentionConfig:
    mentions: int
    within_seconds: int
    count_duplicates: bool = False


@dataclass(frozen=True, slots=True)
class AttachmentConfig:
    attachments: int
    within_seconds: int
    count_multiple_per_message: bool = False


@dataclass(frozen=True, slots=True)
class ViolationConfig:
    violation_name: str
    number_of_violations: int
    within_minutes: int
    ignore_higher_trigger: bool = True


@dataclass(frozen=True, slots=True)
class AllCapsConfig:
    min_count: int = 3
    percentage: int = 100
    match_similar: bool = False


@dataclass(frozen=True, slots=True)
class DiscordAutomodConfig:
    rule_id: int | None = None
