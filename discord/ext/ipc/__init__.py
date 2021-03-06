import collections

from discord.ext.ipc.client import Client
from discord.ext.ipc.errors import (
    IPCError,
    JSONEncodeError,
    NoEndpointFoundError,
    NotConnected,
    ServerConnectionRefusedError,
)
from discord.ext.ipc.server import Server

_VersionInfo = collections.namedtuple(
    "_VersionInfo", "major minor micro release serial"
)

__all__ = (
    "Client",
    "Server",
    "IPCError",
    "NoEndpointFoundError",
    "ServerConnectionRefusedError",
    "JSONEncodeError",
    "NotConnected",
)

version = "2.1.1"
version_info = _VersionInfo(2, 1, 1, "final", 0)
