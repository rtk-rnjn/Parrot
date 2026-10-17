"""Competitive-programming contest listings, one module per site, all reduced to :class:`Contest`."""

from .atcoder import PLATFORM as ATCODER
from .base import Contest, Fetcher, Platform, Status
from .codeforces import PLATFORM as CODEFORCES
from .csacademy import PLATFORM as CSACADEMY
from .hackerearth import PLATFORM as HACKEREARTH
from .hackerrank import PLATFORM as HACKERRANK

PLATFORMS: tuple[Platform, ...] = (CODEFORCES, ATCODER, HACKERRANK, HACKEREARTH, CSACADEMY)

__all__ = ("PLATFORMS", "Contest", "Fetcher", "Platform", "Status")
