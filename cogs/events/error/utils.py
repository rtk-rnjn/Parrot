from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from functools import cache
from pathlib import Path
from typing import NamedTuple, Protocol

from rapidfuzz import fuzz, process

from core import human_join

QUOTES_PATH = Path("assets/random_quotes.txt")


class Named(Protocol):
    id: int
    name: str


class FuzzyMatch[T: Named](NamedTuple):
    obj: T
    name: str
    score: int


@cache
def _load_quotes() -> tuple[str, ...]:
    with QUOTES_PATH.open(encoding="utf-8") as f:
        return tuple(line.strip() for line in f if line.strip())


def random_quote() -> str | None:
    quotes = _load_quotes()
    return random.choice(quotes) if quotes else None


def format_permissions(permissions: Iterable[str]) -> str:
    names = [perm.replace("_", " ").replace("guild", "server").title() for perm in permissions]
    return human_join(names, delim="`, `", final="and")


def find_closest[T: Named](argument: str, objects: Sequence[T], *, cutoff: int = 90) -> FuzzyMatch[T] | None:
    """Fuzzy-match `argument` against the `name` of each object."""
    if not argument or not objects:
        return None

    found = process.extractOne(argument, [o.name for o in objects], scorer=fuzz.WRatio, score_cutoff=cutoff)
    if found is None:
        return None

    name, score, index = found
    return FuzzyMatch(objects[index], name, int(score))
