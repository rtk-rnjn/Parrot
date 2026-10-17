from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .condition import Condition
from .effect import Effect
from .trigger import Trigger

if TYPE_CHECKING:
    from core.utils.database.models import RuleDict


@dataclass(frozen=True, slots=True)
class Rule:
    """Represents a rule in the automod system."""

    name: str
    """The name of the rule."""

    trigger: Trigger
    """The triggers that activate this rule."""

    conditions: list[Condition]
    """The conditions that must be met for this rule to apply."""

    effects: list[Effect]
    """The effects that occur when this rule is triggered."""

    enabled: bool = True
    """Whether the rule is enabled or not."""

    priority: int = 0
    """The priority of the rule. Higher priority rules are evaluated first."""

    @classmethod
    def parse(cls, data: RuleDict) -> Rule:
        """Parses a rule from a dictionary."""
        return cls(
            name=data["name"],
            trigger=Trigger.parse(data["trigger"]),
            conditions=[Condition.parse(c) for c in data.get("conditions", [])],
            effects=[Effect.parse(e) for e in data.get("effects", [])],
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
        )
