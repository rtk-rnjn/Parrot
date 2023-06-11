from typing import Literal, NamedTuple

from .client import Client as Client
from .errors import *
from .paste import File as File
from .paste import Paste as Paste


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


version_info: VersionInfo = VersionInfo(
    major=5, minor=1, micro=0, releaselevel="final", serial=0
)
