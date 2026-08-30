from __future__ import annotations
from dataclasses import dataclass

from .condition import Condition
from .trigger import Trigger
from .effect import Effect

from enum import StrEnum


class MatchMode(StrEnum):
    ANY = "any"
    ALL = "all"

@dataclass
class Rule:
    """Represents a rule in the automod system."""

    name: str
    """The name of the rule."""

    triggers: Trigger
    """The triggers that activate this rule."""

    conditions: list[Condition]
    """The conditions that must be met for this rule to apply."""

    effects: list[Effect]
    """The effects that occur when this rule is triggered."""

    enabled: bool = True
    """Whether the rule is enabled or not."""

    priority: int = 0
    """The priority of the rule. Higher priority rules are evaluated first."""

    condition_match_mode: MatchMode = MatchMode.ALL
    """The mode for evaluating conditions. Can be 'any' or 'all'."""
