from typing import Literal, NamedTuple

from .client import Client  # noqa: F401  # pylint: disable=unused-import
from .errors import *  # noqa: F401, F403  # pylint: disable=unused-wildcard-import
from .paste import File, Paste  # noqa: F401  # pylint: disable=unused-import


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


version_info: VersionInfo = VersionInfo(major=5, minor=1, micro=0, releaselevel="final", serial=0)
