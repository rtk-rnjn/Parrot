from __future__ import annotations

import abc
import asyncio
import contextlib
import itertools
import logging
import platform
import time
from collections import Counter
from collections.abc import Awaitable, Sequence
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

import aiohttp
import discord
import pomice
import psutil
from discord.ext import commands

from core.bot import LOADABLE_COGS
from core.utils import BaseLayoutView, CallbackButton, CallbackStringSelect, format_friendly_duration, plural, truncate

if TYPE_CHECKING:
    from core import Bot

__all__ = ("OwnerPanel",)

_log = logging.getLogger(__name__)

type Interaction = discord.Interaction[Bot]

TIMEOUT_SECONDS = 10 * 60
OPERATION_TIMEOUT = 10
SELECT_LIMIT = 25
MAX_BODY = 3400
MAX_TASK_LINES = 40
BYTES_PER_UNIT = 1024
LAVALINK_LIST_URL = "https://lavalink-list.ajieblogs.eu.org/NonSSL"

OK = "\N{WHITE HEAVY CHECK MARK}"
WARN = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"
ERR = "\N{CROSS MARK}"
ONLINE = "\N{LARGE GREEN CIRCLE}"
OFFLINE = "\N{LARGE RED CIRCLE}"


def format_bytes(value: float) -> str:
    value = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < BYTES_PER_UNIT:
            return f"{value:.2f} {unit}"
        value /= BYTES_PER_UNIT
    return f"{value:.2f} EB"


def kv(rows: Sequence[tuple[str, object]]) -> str:
    return "\n".join(f"**{label}:** {value}" for label, value in rows)


def section(title: str, body: str) -> str:
    return f"### {title}\n{body}"


def code(value: object) -> str:
    return f"`{value}`"


def number(value: object) -> str:
    return f"`{value:,}`" if isinstance(value, int | float) else code(value)


class LavalinkProvider(NamedTuple):
    identifier: str
    host: str
    port: int
    password: str


class Tab(abc.ABC):
    """One tab of the owner panel: loads its data, renders markdown blocks and offers controls."""

    key: ClassVar[str]
    label: ClassVar[str]
    emoji: ClassVar[str]
    accent: ClassVar[discord.Colour]
    subtitle: ClassVar[str]
    views: ClassVar[tuple[tuple[str, str], ...]] = ()

    def __init__(self, panel: OwnerPanel) -> None:
        self.panel = panel
        self.view_key = self.views[0][0] if self.views else ""
        self.error: str | None = None

    @property
    def bot(self) -> Bot:
        return self.panel.bot

    async def load(self) -> None:  # noqa: B027
        """Refresh the data behind the tab. Failures land in ``self.error`` instead of raising."""

    @abc.abstractmethod
    def blocks(self) -> list[str]:
        """Markdown blocks for the current sub-view."""

    def controls(self) -> list[discord.ui.ActionRow]:
        return []

    async def guarded(self, label: str, operation: Awaitable[Any]) -> Any:
        """Await ``operation`` with a timeout, recording a readable error on failure."""
        try:
            return await asyncio.wait_for(operation, OPERATION_TIMEOUT)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.error = f"{label}: {type(exc).__name__}: {truncate(str(exc), 200)}"
            return None

    def view_select(self) -> discord.ui.ActionRow | None:
        if not self.views:
            return None
        options = [discord.SelectOption(label=label, value=key, default=key == self.view_key) for key, label in self.views]
        return discord.ui.ActionRow(CallbackStringSelect(self.pick_view, placeholder="View", options=options))

    async def pick_view(self, interaction: Interaction, values: list[str]) -> None:
        self.view_key = values[0]
        await self.panel.commit(interaction)

    def button(
        self,
        label: str,
        handler: Any,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        emoji: str | None = None,
        disabled: bool = False,
    ) -> CallbackButton:
        return CallbackButton(handler, label=label, style=style, emoji=emoji, disabled=disabled)


class RedisTab(Tab):
    key = "redis"
    label = "Redis"
    emoji = "\N{ELECTRIC PLUG}"
    accent = discord.Colour.red()
    subtitle = "Cache server health from `INFO`. Use the `redis-repl` command for ad-hoc commands."
    views = (
        ("overview", "Overview"),
        ("memory", "Memory"),
        ("clients", "Clients"),
        ("stats", "Statistics"),
        ("keyspace", "Keyspace"),
        ("persistence", "Persistence"),
        ("replication", "Replication"),
    )

    def __init__(self, panel: OwnerPanel) -> None:
        super().__init__(panel)
        self.info: dict[str, Any] = {}
        self.latency_ms: float | None = None
        self.config_result: tuple[str, dict[str, Any]] | None = None

    async def load(self) -> None:
        self.error = None
        redis = self.bot.database.redis_client
        started = time.perf_counter()
        if await self.guarded("PING", redis.ping()) is not None:
            self.latency_ms = (time.perf_counter() - started) * 1000
        info = await self.guarded("INFO", redis.info())
        self.info = info if isinstance(info, dict) else {}

    def blocks(self) -> list[str]:
        info = self.info
        if not info:
            return ["Redis did not answer `INFO`."]
        match self.view_key:
            case "memory":
                blocks = self._memory()
            case "clients":
                blocks = self._clients()
            case "stats":
                blocks = self._stats()
            case "keyspace":
                blocks = self._keyspace()
            case "persistence":
                blocks = self._persistence()
            case "replication":
                blocks = self._replication()
            case _:
                blocks = self._overview()
        if self.config_result is not None:
            parameter, values = self.config_result
            blocks.append(section(f"Config `{parameter}`", kv([(key, code(value)) for key, value in values.items()]) or "No matching parameter."))
        return blocks

    def _overview(self) -> list[str]:
        info = self.info
        latency = f"`{self.latency_ms:.1f} ms`" if self.latency_ms is not None else "`unknown`"
        return [
            section(
                "Server",
                kv(
                    [
                        ("Version", code(info.get("redis_version", "unknown"))),
                        ("Mode", code(info.get("redis_mode", "unknown"))),
                        ("OS", code(info.get("os", "unknown"))),
                        ("Uptime", code(format_friendly_duration(info.get("uptime_in_seconds", 0)))),
                    ]
                ),
            ),
            section(
                "Live",
                kv(
                    [
                        ("Ping", latency),
                        ("Clients", number(info.get("connected_clients", 0))),
                        ("Memory", code(format_bytes(info.get("used_memory", 0)))),
                        ("Peak memory", code(format_bytes(info.get("used_memory_peak", 0)))),
                        ("Commands", number(info.get("total_commands_processed", 0))),
                        ("Ops/sec", number(info.get("instantaneous_ops_per_sec", 0))),
                    ]
                ),
            ),
        ]

    def _memory(self) -> list[str]:
        info = self.info
        usage = [
            (label, code(format_bytes(info[key])))
            for label, key in (
                ("Used", "used_memory"),
                ("Peak", "used_memory_peak"),
                ("RSS", "used_memory_rss"),
                ("Lua", "used_memory_lua"),
                ("Functions", "used_memory_functions"),
                ("Dataset", "used_memory_dataset"),
                ("Overhead", "used_memory_overhead"),
            )
            if key in info
        ]
        limits: list[tuple[str, object]] = []
        if "maxmemory" in info:
            limits.append(("Max memory", code(format_bytes(info["maxmemory"]) if info["maxmemory"] else "unlimited")))
        if "mem_fragmentation_ratio" in info:
            limits.append(("Fragmentation", f"`{info['mem_fragmentation_ratio']:.2f}`"))
        blocks = [section("Usage", kv(usage) or "No memory figures reported.")]
        if limits:
            blocks.append(section("Limits", kv(limits)))
        return blocks

    def _clients(self) -> list[str]:
        info = self.info
        rows: list[tuple[str, object]] = []
        for label, key in (
            ("Connected", "connected_clients"),
            ("Blocked", "blocked_clients"),
            ("Tracking", "tracking_clients"),
            ("Watching", "watched_clients"),
            ("Max input buffer", "client_recent_max_input_buffer"),
            ("Max output buffer", "client_recent_max_output_buffer"),
        ):
            if key in info:
                rows.append((label, code(format_bytes(info[key])) if "buffer" in label else number(info[key])))
        return [kv(rows) or "No client figures reported."]

    def _stats(self) -> list[str]:
        info = self.info
        rows: list[tuple[str, object]] = [
            (label, number(info[key]))
            for label, key in (
                ("Commands processed", "total_commands_processed"),
                ("Ops/sec", "instantaneous_ops_per_sec"),
                ("Connections received", "total_connections_received"),
                ("Rejected connections", "rejected_connections"),
                ("Expired keys", "expired_keys"),
                ("Evicted keys", "evicted_keys"),
                ("Keyspace hits", "keyspace_hits"),
                ("Keyspace misses", "keyspace_misses"),
                ("Pub/Sub channels", "pubsub_channels"),
                ("Pub/Sub patterns", "pubsub_patterns"),
            )
            if key in info
        ]
        hits, misses = info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)
        if hits + misses:
            rows.append(("Cache hit rate", f"`{hits / (hits + misses) * 100:.2f}%`"))
        return [kv(rows) or "No statistics reported."]

    def _keyspace(self) -> list[str]:
        databases = {key: value for key, value in self.info.items() if key.startswith("db") and isinstance(value, dict)}
        if not databases:
            return ["No database currently holds keys."]
        return [
            section(
                name,
                kv(
                    [
                        ("Keys", number(data.get("keys", 0))),
                        ("With expiry", number(data.get("expires", 0))),
                        ("Average TTL", f"`{data.get('avg_ttl', 0):,} ms`"),
                    ]
                ),
            )
            for name, data in sorted(databases.items())
        ]

    def _persistence(self) -> list[str]:
        info = self.info
        last_save = info.get("rdb_last_save_time")
        return [
            section(
                "RDB",
                kv(
                    [
                        ("Last save", f"<t:{last_save}:R>" if last_save else "`never`"),
                        ("Changes since save", number(info.get("rdb_changes_since_last_save", 0))),
                        ("Last save status", code(info.get("rdb_last_bgsave_status", "unknown"))),
                        ("Save in progress", code(bool(info.get("rdb_bgsave_in_progress", 0)))),
                    ]
                ),
            ),
            section(
                "AOF",
                kv(
                    [
                        ("Enabled", code(bool(info.get("aof_enabled", 0)))),
                        ("Rewrite in progress", code(bool(info.get("aof_rewrite_in_progress", 0)))),
                        ("Rewrite scheduled", code(bool(info.get("aof_rewrite_scheduled", 0)))),
                    ]
                ),
            ),
        ]

    def _replication(self) -> list[str]:
        info = self.info
        role = info.get("role", "unknown")
        replicas = info.get("connected_slaves", 0)
        blocks = [section("Replication", kv([("Role", code(role)), ("Connected replicas", number(replicas))]))]
        if role == "master":
            entries = []
            for index in range(replicas):
                replica = info.get(f"slave{index}")
                if isinstance(replica, dict):
                    entries.append(
                        f"**Replica {index}**\n"
                        + kv(
                            [
                                ("Host", code(replica.get("ip", "unknown"))),
                                ("Port", code(replica.get("port", "unknown"))),
                                ("State", code(replica.get("state", "unknown"))),
                                ("Offset", number(replica.get("offset", 0))),
                            ]
                        )
                    )
            blocks.append(section("Replicas", "\n\n".join(entries) or "No replica is connected."))
        else:
            blocks.append(
                section(
                    "Master",
                    kv(
                        [
                            ("Host", code(info.get("master_host", "unknown"))),
                            ("Port", code(info.get("master_port", "unknown"))),
                            ("Link", code(info.get("master_link_status", "unknown"))),
                        ]
                    ),
                )
            )
        return blocks

    def controls(self) -> list[discord.ui.ActionRow]:
        return [
            discord.ui.ActionRow(
                self.button("Ping", self.ping, emoji="\N{TABLE TENNIS PADDLE AND BALL}"),
                self.button("Config\N{HORIZONTAL ELLIPSIS}", self.open_config, emoji="\N{GEAR}\N{VARIATION SELECTOR-16}"),
            )
        ]

    async def ping(self, interaction: Interaction) -> None:
        await self.panel.acknowledge(interaction)
        started = time.perf_counter()
        result = await self.guarded("PING", self.bot.database.redis_client.ping())
        if result is None:
            await self.panel.commit(interaction, f"{ERR} Redis did not answer: {self.error}")
            return
        await self.panel.commit(interaction, f"{OK} Redis answered `PING` in {(time.perf_counter() - started) * 1000:.1f} ms.")

    async def open_config(self, interaction: Interaction) -> None:
        await interaction.response.send_modal(RedisConfigModal(self))


class RedisConfigModal(discord.ui.Modal, title="Redis configuration"):
    def __init__(self, tab: RedisTab) -> None:
        super().__init__(timeout=300)
        self.tab = tab
        self.parameter = discord.ui.TextInput(placeholder="maxmemory, save, appendonly, max*", min_length=1, max_length=64)
        self.add_item(discord.ui.Label(text="Parameter", description="A name or glob passed to CONFIG GET.", component=self.parameter))

    async def on_submit(self, interaction: Interaction) -> None:
        parameter = self.parameter.value.strip()
        await self.tab.panel.acknowledge(interaction)
        result = await self.tab.guarded("CONFIG GET", self.tab.bot.database.redis_client.config_get(parameter))
        if result is None:
            await self.tab.panel.commit(interaction, f"{ERR} {self.tab.error}")
            return
        self.tab.config_result = (parameter, dict(result))
        await self.tab.panel.commit(
            interaction, f"{OK} Fetched {plural(len(result)):value} for `{parameter}`." if result else f"{WARN} No parameter matches `{parameter}`."
        )


class MongoTab(Tab):
    key = "mongo"
    label = "MongoDB"
    emoji = "\N{LEAF FLUTTERING IN WIND}"
    accent = discord.Colour.green()
    subtitle = "Server status, databases and storage."
    views = (
        ("overview", "Overview"),
        ("connections", "Connections"),
        ("operations", "Operations"),
        ("network", "Network"),
        ("memory", "Memory"),
        ("databases", "Databases"),
        ("collections", "Collections"),
        ("storage", "Storage"),
    )

    def __init__(self, panel: OwnerPanel) -> None:
        super().__init__(panel)
        self.status: dict[str, Any] = {}
        self.databases: list[dict[str, Any]] = []
        self.database_name: str = panel.bot.database.mongo_db.name
        self.collections: list[str] = []
        self.storage: dict[str, Any] = {}

    async def load(self) -> None:
        self.error = None
        client = self.bot.database.mongo_client
        status = await self.guarded("serverStatus", client.admin.command("serverStatus"))
        self.status = status if isinstance(status, dict) else {}
        cursor = await self.guarded("listDatabases", client.list_databases())
        self.databases = [database async for database in cursor] if cursor is not None else []
        if self.view_key == "collections":
            names = await self.guarded("listCollections", client[self.database_name].list_collection_names())
            self.collections = sorted(names) if names else []
        if self.view_key == "storage":
            stats = await self.guarded("dbStats", client[self.database_name].command("dbStats"))
            self.storage = stats if isinstance(stats, dict) else {}

    def blocks(self) -> list[str]:
        renderers = {
            "connections": self._connections,
            "operations": self._operations,
            "network": self._network,
            "memory": self._memory,
            "databases": self._databases,
            "collections": self._collections,
            "storage": self._storage,
        }
        return renderers.get(self.view_key, self._overview)()

    def _connections(self) -> list[str]:
        connections = self.status.get("connections", {})
        return [
            kv(
                [
                    (label, number(connections.get(key, 0)))
                    for label, key in (
                        ("Current", "current"),
                        ("Available", "available"),
                        ("Total created", "totalCreated"),
                        ("Active", "active"),
                        ("Rejected", "rejected"),
                    )
                ]
            )
        ]

    def _operations(self) -> list[str]:
        operations = self.status.get("opcounters", {})
        return [kv([(name.capitalize(), number(operations.get(name, 0))) for name in ("insert", "query", "update", "delete", "getmore", "command")])]

    def _network(self) -> list[str]:
        network = self.status.get("network", {})
        return [
            kv(
                [
                    ("Bytes in", code(format_bytes(network.get("bytesIn", 0)))),
                    ("Bytes out", code(format_bytes(network.get("bytesOut", 0)))),
                    ("Requests", number(network.get("numRequests", 0))),
                ]
            )
        ]

    def _memory(self) -> list[str]:
        memory = self.status.get("mem", {})
        return [
            kv(
                [
                    ("Resident", f"`{memory.get('resident', 0):,} MB`"),
                    ("Virtual", f"`{memory.get('virtual', 0):,} MB`"),
                    ("Mapped", f"`{memory.get('mapped', 0):,} MB`"),
                ]
            )
        ]

    def _databases(self) -> list[str]:
        lines = [
            f"{'\N{BLACK RIGHT-POINTING TRIANGLE}' if database['name'] == self.database_name else '\N{BULLET}'} `{database['name']}` - {format_bytes(database.get('sizeOnDisk', 0))}"
            for database in self.databases
        ]
        return ["\n".join(lines) or "No databases found."]

    def _collections(self) -> list[str]:
        return [
            section(
                f"Collections in `{self.database_name}`", "\n".join(f"\N{BULLET} `{name}`" for name in self.collections) or "No collections found."
            )
        ]

    def _storage(self) -> list[str]:
        stats = self.storage
        return [
            section(
                f"Storage of `{self.database_name}`",
                kv(
                    [
                        ("Data size", code(format_bytes(stats.get("dataSize", 0)))),
                        ("Storage size", code(format_bytes(stats.get("storageSize", 0)))),
                        ("Indexes", number(stats.get("indexes", 0))),
                        ("Index size", code(format_bytes(stats.get("indexSize", 0)))),
                        ("Collections", number(stats.get("collections", 0))),
                        ("Objects", number(stats.get("objects", 0))),
                    ]
                ),
            )
        ]

    def _overview(self) -> list[str]:
        status = self.status
        if not status:
            return ["MongoDB did not answer `serverStatus`."]
        connections, memory, operations = status.get("connections", {}), status.get("mem", {}), status.get("opcounters", {})
        return [
            section(
                "Instance",
                kv(
                    [
                        ("Host", code(status.get("host", "unknown"))),
                        ("Version", code(status.get("version", "unknown"))),
                        ("Process", code(status.get("process", "unknown"))),
                        ("Uptime", code(format_friendly_duration(status.get("uptime", 0)))),
                    ]
                ),
            ),
            section(
                "Live",
                kv(
                    [
                        (
                            "Connections",
                            f"{number(connections.get('current', 0))} of {number(connections.get('current', 0) + connections.get('available', 0))}",
                        ),
                        ("Resident memory", f"`{memory.get('resident', 0):,} MB`"),
                        ("Queries", number(operations.get("query", 0))),
                        ("Writes", number(operations.get("insert", 0) + operations.get("update", 0) + operations.get("delete", 0))),
                        ("Databases", number(len(self.databases))),
                    ]
                ),
            ),
        ]

    def controls(self) -> list[discord.ui.ActionRow]:
        rows = [discord.ui.ActionRow(self.button("Ping", self.ping, emoji="\N{TABLE TENNIS PADDLE AND BALL}"))]
        names = sorted({database["name"] for database in self.databases} | {self.database_name})[:SELECT_LIMIT]
        if len(names) > 1:
            options = [discord.SelectOption(label=name[:100], value=name, default=name == self.database_name) for name in names]
            rows.append(
                discord.ui.ActionRow(CallbackStringSelect(self.pick_database, placeholder="Database for collections and storage", options=options))
            )
        return rows

    async def pick_database(self, interaction: Interaction, values: list[str]) -> None:
        self.database_name = values[0]
        if self.view_key not in ("collections", "storage"):
            self.view_key = "collections"
        await self.panel.commit(interaction, f"{OK} Inspecting `{self.database_name}`.")

    async def ping(self, interaction: Interaction) -> None:
        await self.panel.acknowledge(interaction)
        started = time.perf_counter()
        result = await self.guarded("ping", self.bot.database.mongo_client.admin.command("ping"))
        if not result:
            await self.panel.commit(interaction, f"{ERR} MongoDB did not answer: {self.error}")
            return
        await self.panel.commit(interaction, f"{OK} MongoDB answered `ping` in {(time.perf_counter() - started) * 1000:.1f} ms.")


class LavalinkTab(Tab):
    key = "lavalink"
    label = "Lavalink"
    emoji = "\N{MUSICAL NOTE}"
    accent = discord.Colour.purple()
    subtitle = "Audio nodes known to the bot."

    @property
    def nodes(self) -> dict[str, pomice.Node]:
        return self.bot.lavalink_node_pool.nodes

    def blocks(self) -> list[str]:
        if not self.nodes:
            return ["No Lavalink node is connected. Connect one below or load the public list."]
        lines = []
        for identifier, node in self.nodes.items():
            status = ONLINE if node.is_connected else OFFLINE
            latency = getattr(node, "latency", None)
            extra = f" \N{MIDDLE DOT} `{latency:.0f} ms`" if isinstance(latency, int | float) else ""
            lines.append(f"{status} **{identifier}** `{node._host}:{node._port}` \N{MIDDLE DOT} {plural(node.player_count):player}{extra}")
        return ["\n".join(lines)]

    def controls(self) -> list[discord.ui.ActionRow]:
        rows = [
            discord.ui.ActionRow(
                self.button("Connect\N{HORIZONTAL ELLIPSIS}", self.open_connect, style=discord.ButtonStyle.primary, emoji="\N{ELECTRIC PLUG}"),
                self.button("Load public nodes", self.load_public, emoji="\N{GLOBE WITH MERIDIANS}"),
            )
        ]
        if self.nodes:
            options = [discord.SelectOption(label=identifier[:100], value=identifier) for identifier in list(self.nodes)[:SELECT_LIMIT]]
            rows.append(discord.ui.ActionRow(CallbackStringSelect(self.disconnect, placeholder="Disconnect a node", options=options)))
        return rows

    async def open_connect(self, interaction: Interaction) -> None:
        await interaction.response.send_modal(LavalinkConnectModal(self))

    async def connect(self, interaction: Interaction, provider: LavalinkProvider) -> None:
        await self.panel.acknowledge(interaction)
        try:
            if provider.host in {"localhost", "127.0.0.1"} and provider.identifier == "MAIN":
                await self.bot.connect_lavalink_node()
            else:
                await self.bot.lavalink_node_pool.create_node(
                    bot=self.bot,
                    host=provider.host,
                    port=provider.port,
                    loop=self.bot.loop,
                    session=self.bot.http_session,
                    password=provider.password,
                    identifier=provider.identifier,
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _log.warning("Could not connect to Lavalink node %s: %s", provider.identifier, exc)
            await self.panel.commit(interaction, f"{ERR} Could not connect `{provider.identifier}`: {truncate(str(exc), 150)}")
            return
        await self.panel.commit(interaction, f"{OK} Connected `{provider.identifier}` at `{provider.host}:{provider.port}`.")

    async def disconnect(self, interaction: Interaction, values: list[str]) -> None:
        node = self.nodes.get(values[0])
        if node is None:
            await self.panel.commit(interaction, f"{WARN} Node `{values[0]}` is already gone.")
            return
        await self.panel.acknowledge(interaction)
        with contextlib.suppress(Exception):
            await node.disconnect()
        await self.panel.commit(interaction, f"{OK} Disconnected `{values[0]}`.")

    async def fetch_providers(self) -> list[LavalinkProvider]:
        async with self.bot.http_session.get(LAVALINK_LIST_URL) as response:
            response.raise_for_status()
            data: list[dict[str, object]] = await response.json()

        providers: list[LavalinkProvider] = []
        for entry in data:
            if entry.get("version") != "v4":
                continue
            identifier, host, port, password = (entry.get(key) for key in ("identifier", "host", "port", "password"))
            if not (identifier and host and port and password):
                continue
            try:
                providers.append(LavalinkProvider(str(identifier), str(host), int(str(port)), str(password)))
            except ValueError:
                _log.debug("Skipping Lavalink provider %s with invalid port %r", identifier, port)
        return providers

    async def load_public(self, interaction: Interaction) -> None:
        await self.panel.acknowledge(interaction)
        try:
            providers = await self.fetch_providers()
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            await self.panel.commit(interaction, f"{ERR} Could not fetch the public node list: {truncate(str(exc), 150)}")
            return
        if not providers:
            await self.panel.commit(interaction, f"{WARN} The public list has no usable v4 nodes.")
            return

        failures = 0
        for index, provider in enumerate(providers, start=1):
            try:
                await self.bot.lavalink_node_pool.create_node(
                    bot=self.bot,
                    host=provider.host,
                    port=provider.port,
                    loop=self.bot.loop,
                    session=self.bot.http_session,
                    password=provider.password,
                    identifier=provider.identifier,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                _log.warning("Could not connect to Lavalink node %s: %s", provider.identifier, exc)
                failures += 1
            await self.panel.commit(interaction, f"\N{HOURGLASS WITH FLOWING SAND} Connecting public nodes: {index}/{len(providers)}", reload=False)

        connected = len(providers) - failures
        icon = OK if not failures else WARN
        await self.panel.commit(interaction, f"{icon} Connected {connected} of {len(providers)} public nodes.")


class LavalinkConnectModal(discord.ui.Modal, title="Connect a Lavalink node"):
    def __init__(self, tab: LavalinkTab) -> None:
        super().__init__(timeout=300)
        self.tab = tab
        self.host = discord.ui.TextInput(default="localhost", max_length=255)
        self.port = discord.ui.TextInput(default="2333", min_length=1, max_length=5)
        self.password = discord.ui.TextInput(default="youshallnotpass", max_length=255)
        self.identifier = discord.ui.TextInput(default="MAIN", max_length=64)
        for text, component in (("Host", self.host), ("Port", self.port), ("Password", self.password), ("Identifier", self.identifier)):
            self.add_item(discord.ui.Label(text=text, component=component))

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            port = int(self.port.value.strip())
        except ValueError:
            await self.tab.panel.commit(interaction, f"{ERR} The port must be a number.")
            return
        provider = LavalinkProvider(self.identifier.value.strip() or "MAIN", self.host.value.strip() or "localhost", port, self.password.value)
        await self.tab.connect(interaction, provider)


class TasksTab(Tab):
    key = "tasks"
    label = "Tasks"
    emoji = "\N{SPIRAL CALENDAR PAD}\N{VARIATION SELECTOR-16}"
    accent = discord.Colour.blue()
    subtitle = "asyncio tasks on the event loop."

    def __init__(self, panel: OwnerPanel) -> None:
        super().__init__(panel)
        self.counts: Counter[str] = Counter()
        self.pending_cancel: str | None = None

    async def load(self) -> None:
        self.counts = Counter(task.get_name() for task in asyncio.all_tasks())

    def blocks(self) -> list[str]:
        total = sum(self.counts.values())
        lines = [f"**{total:,}** tasks, {len(self.counts):,} distinct names."]
        for name, count in self.counts.most_common(MAX_TASK_LINES):
            lines.append(f"\N{BULLET} `{truncate(name, 80)}`" + (f" \N{MULTIPLICATION SIGN}{count}" if count > 1 else ""))
        if len(self.counts) > MAX_TASK_LINES:
            lines.append(f"-# and {len(self.counts) - MAX_TASK_LINES} more")
        return ["\n".join(lines)]

    def _cancellable(self) -> list[str]:
        return [name for name in sorted(self.counts) if not name.startswith(("discord-ui-", "Task-"))][:SELECT_LIMIT]

    def controls(self) -> list[discord.ui.ActionRow]:
        if self.pending_cancel is not None:
            return [
                discord.ui.ActionRow(
                    self.button(f"Cancel `{truncate(self.pending_cancel, 60)}`", self.confirm_cancel, style=discord.ButtonStyle.danger),
                    self.button("Keep it", self.keep, style=discord.ButtonStyle.secondary),
                )
            ]
        names = self._cancellable()
        if not names:
            return []
        options = [discord.SelectOption(label=truncate(name, 100), value=name[:100]) for name in names]
        return [discord.ui.ActionRow(CallbackStringSelect(self.pick_cancel, placeholder="Cancel a task", options=options))]

    async def pick_cancel(self, interaction: Interaction, values: list[str]) -> None:
        self.pending_cancel = values[0]
        await self.panel.commit(interaction, f"{WARN} Cancelling a task cannot be undone. Confirm below.", reload=False)

    async def keep(self, interaction: Interaction) -> None:
        self.pending_cancel = None
        await self.panel.commit(interaction, reload=False)

    async def confirm_cancel(self, interaction: Interaction) -> None:
        name = self.pending_cancel
        self.pending_cancel = None
        cancelled = 0
        for task in asyncio.all_tasks():
            if task.get_name() == name:
                task.cancel()
                cancelled += 1
        await self.panel.commit(
            interaction,
            f"{OK} Cancelled {plural(cancelled):task} named `{name}`." if cancelled else f"{WARN} No task named `{name}` is running any more.",
        )


class BotTab(Tab):
    key = "bot"
    label = "Bot"
    emoji = "\N{ROBOT FACE}"
    accent = discord.Colour.blurple()
    subtitle = "Process, gateway and extension state."

    def __init__(self, panel: OwnerPanel) -> None:
        super().__init__(panel)
        self.process = psutil.Process()
        self.memory_rss = 0
        self.cpu_percent = 0.0
        self.threads = 0

    async def load(self) -> None:
        with self.process.oneshot():
            self.memory_rss = self.process.memory_info().rss
            self.cpu_percent = self.process.cpu_percent(interval=None)
            self.threads = self.process.num_threads()

    def blocks(self) -> list[str]:
        bot = self.bot
        started = getattr(bot, "_started_at", None)
        members = sum(guild.member_count or 0 for guild in bot.guilds)
        loaded = len(bot.extensions)
        return [
            section(
                "Runtime",
                kv(
                    [
                        ("Online since", discord.utils.format_dt(started, "R") if started else "`not ready`"),
                        ("Gateway latency", f"`{bot.latency * 1000:.0f} ms`"),
                        ("Process memory", code(format_bytes(self.memory_rss))),
                        ("CPU", f"`{self.cpu_percent:.1f}%`"),
                        ("Threads", number(self.threads)),
                        (
                            "Versions",
                            f"Python `{platform.python_version()}` \N{MIDDLE DOT} discord.py `{discord.__version__}` \N{MIDDLE DOT} pomice `{pomice.__version__}`",
                        ),
                    ]
                ),
            ),
            section(
                "Discord",
                kv(
                    [
                        ("Servers", number(len(bot.guilds))),
                        ("Members", number(members)),
                        ("Shards", number(bot.shard_count or 1)),
                        ("Cached messages", number(len(bot.cached_messages))),
                        ("Commands", number(len(list(bot.walk_commands())))),
                    ]
                ),
            ),
            section(
                "Extensions",
                kv(
                    [
                        ("Loaded", f"{number(loaded)} of {number(len(LOADABLE_COGS))}"),
                        ("Autoreload", code(bot._cog_autoreload_task is not None and not bot._cog_autoreload_task.done())),
                    ]
                ),
            ),
        ]

    def controls(self) -> list[discord.ui.ActionRow]:
        rows = [
            discord.ui.ActionRow(self.button("Sync app commands", self.sync_tree, emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"))
        ]
        for chunk in itertools.batched(LOADABLE_COGS, SELECT_LIMIT, strict=False):
            options = [
                discord.SelectOption(label=name.removeprefix("extensions."), value=name, emoji=ONLINE if name in self.bot.extensions else OFFLINE)
                for name in chunk
            ]
            rows.append(
                discord.ui.ActionRow(
                    CallbackStringSelect(
                        self.reload_extension,
                        placeholder=f"Reload an extension ({chunk[0].removeprefix('extensions.')[0]}\N{EN DASH}{chunk[-1].removeprefix('extensions.')[0]})",
                        options=options,
                    )
                )
            )
        return rows

    async def sync_tree(self, interaction: Interaction) -> None:
        await self.panel.acknowledge(interaction)
        synced = await self.guarded("sync", self.bot.tree.sync())
        if synced is None:
            await self.panel.commit(interaction, f"{ERR} {self.error}")
            return
        await self.panel.commit(interaction, f"{OK} Synced {plural(len(synced)):global application command}.")

    async def reload_extension(self, interaction: Interaction, values: list[str]) -> None:
        name = values[0]
        await self.panel.acknowledge(interaction)
        try:
            if name in self.bot.extensions:
                await self.bot.reload_extension(name)
                verb = "Reloaded"
            else:
                await self.bot.load_extension(name)
                verb = "Loaded"
        except commands.ExtensionError as exc:
            _log.exception("Could not reload %s", name)
            await self.panel.commit(interaction, f"{ERR} {type(exc).__name__}: {truncate(str(exc.__cause__ or exc), 180)}")
            return
        await self.panel.commit(interaction, f"{OK} {verb} `{name}`.")


class OwnerPanel(BaseLayoutView):
    """Tabbed diagnostics for the bot owner: Redis, MongoDB, Lavalink, asyncio tasks and the bot process."""

    def __init__(self, author: discord.Member | discord.User, *, bot: Bot) -> None:
        super().__init__(author, timeout=TIMEOUT_SECONDS)
        self.bot = bot
        self.tabs: dict[str, Tab] = {tab.key: tab for tab in (BotTab(self), RedisTab(self), MongoTab(self), LavalinkTab(self), TasksTab(self))}
        self.current = "bot"
        self.notice: str | None = None
        self._last_interaction: Interaction | None = None

        self.tab_row = discord.ui.ActionRow()
        self.container = discord.ui.Container()
        self.add_item(self.tab_row)
        self.add_item(self.container)
        self.add_item(
            discord.ui.ActionRow(
                CallbackButton(self.refresh_pressed, label="Refresh", emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"),
                CallbackButton(self.close_pressed, label="Close", emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}"),
            )
        )

    @property
    def tab(self) -> Tab:
        return self.tabs[self.current]

    def render(self) -> None:
        tab = self.tab
        self.tab_row.clear_items()
        for key, other in self.tabs.items():
            style = discord.ButtonStyle.primary if key == self.current else discord.ButtonStyle.secondary
            self.tab_row.add_item(CallbackButton(self._switcher(key), label=other.label, emoji=other.emoji, style=style))

        self.container.clear_items()
        self.container.accent_colour = discord.Colour.red() if tab.error else tab.accent
        self.container.add_item(discord.ui.TextDisplay(f"## {tab.emoji} {tab.label}\n-# {tab.subtitle}"))
        selector = tab.view_select()
        if selector is not None:
            self.container.add_item(selector)
        self.container.add_item(discord.ui.Separator())

        body = "\n".join(tab.blocks())
        self.container.add_item(discord.ui.TextDisplay(truncate(body, MAX_BODY)))
        if tab.error:
            self.container.add_item(discord.ui.TextDisplay(f"{ERR} {tab.error}"))
        for row in tab.controls():
            self.container.add_item(row)
        if self.notice:
            self.container.add_item(discord.ui.Separator())
            self.container.add_item(discord.ui.TextDisplay(f"-# {self.notice}"))

    def _switcher(self, key: str):
        async def switch(interaction: Interaction) -> None:
            await self.acknowledge(interaction)
            self.current = key
            self.notice = None
            await self.tab.load()
            self.render()
            await self.respond(interaction)

        return switch

    async def start(self, ctx: commands.Context[Bot]) -> discord.Message:
        await self.tab.load()
        self.render()
        self.message = await ctx.reply(view=self)
        return self.message

    @staticmethod
    async def acknowledge(interaction: Interaction) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer()

    async def respond(self, interaction: Interaction) -> None:
        self._last_interaction = interaction
        if interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        else:
            await interaction.response.edit_message(view=self)

    async def commit(self, interaction: Interaction, notice: str | None = None, *, reload: bool = True) -> None:
        await self.acknowledge(interaction)
        if reload:
            await self.tab.load()
        self.notice = notice
        self.render()
        await self.respond(interaction)

    async def refresh_pressed(self, interaction: Interaction) -> None:
        await self.commit(interaction, f"{OK} Refreshed.")

    async def close_pressed(self, interaction: Interaction) -> None:
        self.stop()
        await interaction.response.defer()
        with contextlib.suppress(discord.HTTPException):
            await interaction.delete_original_response()

    async def on_timeout(self) -> None:
        self.notice = "This panel timed out. Run the command again to keep going."
        self.render()
        self.disable_all_items()
        if self._last_interaction is not None:
            with contextlib.suppress(discord.HTTPException):
                await self._last_interaction.edit_original_response(view=self)
                return
        await self.update_message()
