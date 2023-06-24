from typing import Literal, NamedTuple

from .client import Client as Client
from .errors import *  # noqa: F401, F403  # pylint: disable=unused-wildcard-import
from .paste import File as File, Paste as Paste


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


version_info: VersionInfo = VersionInfo(major=5, minor=1, micro=0, releaselevel="final", serial=0)
