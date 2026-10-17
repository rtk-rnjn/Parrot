"""Fuzzy search over a documentation index, shared by every source."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from rapidfuzz import fuzz, process

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from .references import Entries, Entry

# A results message holds 4 + 3n components; Discord allows 40, so 12 would be the ceiling.
MAX_RESULTS = 10
CANDIDATES = 60  # big indexes have many equal fuzzy scores; re-rank a wide pool, not just the first few
SCORE_CUTOFF = 55

SEPARATORS = re.compile(r"[.:/\\\s()<>,\[\]_?!-]+")  # `try-with-resources` and `push_back` are three and two words


def tokens(name: str) -> str:
    """Lower-case words with every path separator unified, so `Array.prototype.map` and `Array map` compare alike."""
    return SEPARATORS.sub(" ", name).lower().strip()


def last_segment(name: str) -> str:
    parts = [part for part in SEPARATORS.split(name.strip()) if part]
    return parts[-1] if parts else name


class Index(Protocol):
    async def search_async(self, query: str, limit: int = MAX_RESULTS) -> list[tuple[str, Entry]]: ...

    def describe(self) -> str: ...


@dataclass(slots=True)
class SiteIndex:
    kind: str
    names: list[str]
    entries: list[Entry]
    lowered: list[str]

    @classmethod
    def build(cls, kind: str, entries: Entries) -> SiteIndex:
        names = list(entries)
        return cls(kind, names, [entries[n] for n in names], [tokens(n) for n in names])

    def search(self, query: str, limit: int = MAX_RESULTS) -> list[tuple[str, Entry]]:
        needle = tokens(query)
        hits = process.extract(needle, self.lowered, scorer=fuzz.WRatio, limit=CANDIDATES, score_cutoff=SCORE_CUTOFF)
        wanted = query.strip()
        wanted_tail = last_segment(wanted)
        wanted_words = set(needle.split())

        def rank(hit: tuple[str, float, int]) -> tuple[int, int, float, int]:
            """Names sharing more of the query's segments win, then an exact last segment, then the fuzzy score."""
            name = self.names[hit[2]]
            shared = len(wanted_words & set(self.lowered[hit[2]].split()))
            tail = last_segment(name)
            exact = 0 if tail == wanted_tail else 1 if tail.lower() == wanted_tail.lower() else 2
            return (-shared, exact, -hit[1], len(name))

        return [(self.names[idx], self.entries[idx]) for _choice, _score, idx in sorted(hits, key=rank)[:limit]]

    async def search_async(self, query: str, limit: int = MAX_RESULTS) -> list[tuple[str, Entry]]:
        return await asyncio.to_thread(self.search, query, limit)

    def describe(self) -> str:
        return f"{self.kind} index \N{MIDDLE DOT} {len(self):,} entries"

    def __len__(self) -> int:
        return len(self.names)


@dataclass(slots=True)
class LiveIndex:
    """A source that is queried on every search instead of being indexed up front."""

    kind: str
    searcher: Callable[[str, int], Awaitable[list[tuple[str, Entry]]]]

    async def search_async(self, query: str, limit: int = MAX_RESULTS) -> list[tuple[str, Entry]]:
        return await self.searcher(query, limit)

    def describe(self) -> str:
        return f"{self.kind} live search"
