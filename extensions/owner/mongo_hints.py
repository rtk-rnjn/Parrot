from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypedDict


class Connections(TypedDict, total=False):
    current: int
    available: int
    totalCreated: int
    rejected: int
    active: int
    threaded: int
    exhaustIsMaster: int
    exhaustHello: int
    awaitingTopologyChanges: int
    loadBalanced: int
    queuedForEstablishment: int

    establishmentRateLimit: EstablishmentRateLimit


class EstablishmentRateLimit(TypedDict, total=False):
    rejected: int
    exempted: int
    interruptedDueToClientDisconnect: int


class Opcounters(TypedDict, total=False):
    insert: int
    query: int
    update: int
    delete: int
    getmore: int
    command: int


class Network(TypedDict, total=False):
    bytesIn: int
    bytesOut: int
    physicalBytesIn: int
    physicalBytesOut: int
    numRequests: int


class Memory(TypedDict, total=False):
    bits: int
    resident: float
    virtual: float
    supported: bool
    mapped: int
    mappedWithJournal: int


class Asserts(TypedDict, total=False):
    regular: int
    warning: int
    msg: int
    user: int
    rollovers: int


class ServerStatus(TypedDict, total=False):
    # Command response
    ok: float

    # Instance information
    host: str
    version: str
    process: Literal["mongod", "mongos"]
    service: Literal["router", "shard"]
    pid: int
    uptime: float
    uptimeMillis: int
    uptimeEstimate: int
    localTime: datetime
    advisoryHostFQDNs: list[str]

    # Connections
    connections: Connections

    # Operations
    opcounters: Opcounters

    # Network
    network: Network

    # Memory
    mem: Memory

    # Assertions
    asserts: Asserts

    # Large/version-dependent sections
    metrics: dict[str, Any]
    repl: dict[str, Any]
    wiredTiger: dict[str, Any]
    storageEngine: dict[str, Any]
    locks: dict[str, Any]
    extra_info: dict[str, Any]
    extraInfo: dict[str, Any]
    tcmalloc: dict[str, Any]
    indexCounters: dict[str, Any]
    opcountersRepl: dict[str, Any]
    electionMetrics: dict[str, Any]
    flowControl: dict[str, Any]
    sharding: dict[str, Any]
    writeBacksQueued: int
