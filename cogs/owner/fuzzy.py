from __future__ import annotations

import heapq
import re
from collections.abc import Callable, Iterator
from difflib import SequenceMatcher
from typing import TypeVar

KT = TypeVar("KT")
VT = TypeVar("VT")


def ratio(a: str, b: str) -> int:
    m = SequenceMatcher(None, a, b)
    return int(round(100 * m.ratio()))


def quick_ratio(a: str, b: str) -> int:
    m = SequenceMatcher(None, a, b)
    return int(round(100 * m.quick_ratio()))


def partial_ratio(a: str, b: str) -> int:
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    m = SequenceMatcher(None, short, long)

    blocks = m.get_matching_blocks()

    scores = []
    for i, j, _ in blocks:
        start = max(j - i, 0)
        end = start + len(short)
        o = SequenceMatcher(None, short, long[start:end])
        r = o.ratio()

        if r > 99 / 100:
            return 100
        scores.append(r)

    return int(round(100 * max(scores)))


_word_regex = re.compile(r"\W", re.IGNORECASE)


def _sort_tokens(a: str) -> str:
    a = _word_regex.sub(" ", a).lower().strip()
    return " ".join(sorted(a.split()))


def token_sort_ratio(a: str, b: str) -> int:
    a = _sort_tokens(a)
    b = _sort_tokens(b)
    return ratio(a, b)


def quick_token_sort_ratio(a: str, b: str) -> int:
    a = _sort_tokens(a)
    b = _sort_tokens(b)
    return quick_ratio(a, b)


def partial_token_sort_ratio(a: str, b: str) -> int:
    a = _sort_tokens(a)
    b = _sort_tokens(b)
    return partial_ratio(a, b)


def _extraction_generator(
    query: str,
    choices: dict[KT, VT] | list[str],
    scorer: Callable[[str, str], int] = quick_ratio,
    score_cutoff: int = 0,
) -> Iterator[tuple[KT, int, VT] | tuple[str, int]]:
    if isinstance(choices, dict):
        for key, value in choices.items():
            score = scorer(query, key)
            if score >= score_cutoff:
                yield (key, score, value)
    else:
        for choice in choices:
            score = scorer(query, choice)
            if score >= score_cutoff:
                yield (choice, score)


def extract(
    query: str,
    choices: dict[KT, VT] | list,
    *,
    scorer: Callable[[str, str], int] = quick_ratio,
    score_cutoff: int = 0,
    limit: int | None = 10,
) -> list[tuple[KT, int, VT] | tuple[str, int]]:
    it = _extraction_generator(query, choices, scorer, score_cutoff)

    def key(t):
        return t[1]

    if limit is not None:
        return heapq.nlargest(limit, it, key=key)
    return sorted(it, key=key, reverse=True)


def extract_one(
    query: str,
    choices: dict[KT, VT] | list,
    *,
    scorer: Callable[[str, str], int] = quick_ratio,
    score_cutoff: int = 0,
) -> tuple[KT, int, VT] | tuple[str, int] | None:
    it = _extraction_generator(query, choices, scorer, score_cutoff)

    def key(t):
        return t[1]

    try:
        return max(it, key=key)
    except Exception:
        # iterator could return nothing
        return None


def extract_or_exact(
    query: str,
    choices: dict | list,
    *,
    limit: int | None = None,
    scorer: Callable[[str, str], int] = quick_ratio,
    score_cutoff: int = 0,
):
    matches = extract(query, choices, scorer=scorer, score_cutoff=score_cutoff, limit=limit)
    if len(matches) == 0:
        return []

    if len(matches) == 1:
        return matches

    top = matches[0][1]
    second = matches[1][1]

    # check if the top one is exact or more than 30% more correct than the top
    return [matches[0]] if top == 100 or top > (second + 30) else matches


def extract_matches(query, choices, *, scorer=quick_ratio, score_cutoff=0):
    matches = extract(query, choices, scorer=scorer, score_cutoff=score_cutoff, limit=None)
    if len(matches) == 0:
        return []

    top_score = matches[0][1]
    to_return = []
    index = 0
    while True:
        try:
            match = matches[index]
        except IndexError:
            break
        else:
            index += 1

        if match[1] != top_score:
            break

        to_return.append(match)
    return to_return


def finder(
    text: str,
    collection: list[str],
    *,
    key: Callable[..., str] = None,
    lazy: bool = True,
) -> list[str] | tuple[str, ...] | Iterator[str]:
    suggestions = []
    text = str(text)
    pat = ".*?".join(map(re.escape, text))
    regex = re.compile(pat, flags=re.IGNORECASE)
    for item in collection:
        to_search = key(item) if key else item
        r = regex.search(to_search)
        if r:
            suggestions.append((len(r.group()), r.start(), item))

    def sort_key(tup: list):
        return (tup[0], tup[1], key(tup[2])) if key else tup

    if lazy:
        return (z for _, _, z in sorted(suggestions, key=sort_key))
    return [z for _, _, z in sorted(suggestions, key=sort_key)]


def find(text, collection, *, key=None):
    try:
        _r = finder(text, collection, key=key, lazy=False)
        return _r[0]
    except IndexError:
        return None
