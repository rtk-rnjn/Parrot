from __future__ import annotations

import asyncio
import logging
import traceback
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import discord
from colorama import Fore
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter

if TYPE_CHECKING:
    from core import Parrot

    from .hints import ServerStatus


_log = logging.getLogger("bot.cogs.owner")

# Shared accent colors so every dashboard for a given backend looks the same.
_REDIS_COLOR = discord.Color.red()
_MONGO_COLOR = discord.Color.blurple()
_ONLINE_COLOR = discord.Color.green()
_OFFLINE_COLOR = discord.Color.red()


def create_dashboard_view(
    *,
    title: str,
    accent_color: discord.Color,
    blocks: Sequence[str],
    footer: str | None = None,
) -> discord.ui.LayoutView:
    """Build a small, read-only Components V2 "dashboard" message.

    This is the Components V2 replacement for the old ``discord.Embed`` +
    ``add_field`` pattern: ``title`` becomes the header text, each entry in
    ``blocks`` becomes its own markdown section separated by a divider, and
    ``footer`` (if given) is rendered as small text at the bottom, mirroring
    an embed's footer.
    """
    items: list[discord.ui.Item[Any]] = [discord.ui.TextDisplay(title)]

    for index, block in enumerate(blocks):
        spacing = discord.SeparatorSpacing.large if index == 0 else discord.SeparatorSpacing.small
        items.append(discord.ui.Separator(spacing=spacing))
        items.append(discord.ui.TextDisplay(block))

    if footer:
        items.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        items.append(discord.ui.TextDisplay(f"-# {footer}"))

    view = discord.ui.LayoutView()
    view.add_item(discord.ui.Container(*items, accent_color=accent_color))
    return view


def _error_dashboard(system: str, exc: Exception) -> discord.ui.LayoutView:
    """Build a small red dashboard for a caught exception."""
    return create_dashboard_view(
        title=f"## \N{CROSS MARK} {system} Error",
        accent_color=_OFFLINE_COLOR,
        blocks=[f"```py\n{type(exc).__name__}: {exc}\n```"],
    )


def _status_dashboard(*, online: bool, system: str, message: str) -> discord.ui.LayoutView:
    """Build a small pass/fail dashboard, e.g. for a ping check."""
    icon = "\N{LARGE GREEN CIRCLE}" if online else "\N{LARGE RED CIRCLE}"
    return create_dashboard_view(
        title=f"## {icon} {system}",
        accent_color=_ONLINE_COLOR if online else _OFFLINE_COLOR,
        blocks=[message],
    )


def _field(emoji: str, name: str, value: str) -> str:
    """Render a single markdown "field", the CV2 equivalent of an embed field."""
    return f"### {emoji} {name}\n{value}"


def _kv_lines(rows: Sequence[tuple[str | None, str]]) -> str:
    """Render (label, value) pairs as a compact bullet list."""
    return "\n".join(f"- **{label}:** {value}" for label, value in rows)


def create_footer(ctx: commands.Context) -> str:
    ts = int(discord.utils.utcnow().timestamp())
    return f"Requested by {ctx.author} \N{BULLET} <t:{ts}:R>"


class Owner(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        _log.info("Cog loaded: %s", self.__class__.__name__)

    async def cog_check(self, ctx: commands.Context[Parrot]) -> bool:
        if await self.bot.is_owner(ctx.author):
            return True

        raise commands.NotOwner()

    def _format_traceback(self, error: Exception) -> str:
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = "".join(tb)
        return f"```ansi\n{Fore.RED}{tb_str}{Fore.RESET}\n```"

    @commands.command(name="redis-repl", aliases=["redis-cli"])
    @commands.is_owner()
    async def redis_repl(self, ctx: commands.Context[Parrot]) -> None:
        """Start a Redis REPL session."""
        await ctx.reply("\N{VIDEO GAME} Starting Redis REPL session. Type `exit` to quit.")

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        while True + True == 2:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=300)
            except TimeoutError:
                await ctx.reply("\N{ALARM CLOCK} Redis REPL session timed out.")
                break

            if msg.content.lower() == "exit":
                await msg.reply("\N{WAVING HAND SIGN} Exiting Redis REPL session.")
                break

            codeblock = codeblock_converter(msg.content)
            try:
                result = await self.bot.database.redis_client.execute_command(codeblock.content)
                if len(str(result)) > 1980:
                    await msg.reply("\N{WARNING SIGN} Result is too long to display.")
                else:
                    await msg.reply(f"```py\n{result}```")
            except Exception as e:
                tb_fmt = self._format_traceback(e)
                await msg.reply(tb_fmt)

    @commands.group(name="redis", invoke_without_command=True)
    async def redis(self, ctx: commands.Context) -> None:
        """Redis monitoring commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    async def _info(self, section: str | None = None) -> dict[str, str]:
        """Get parsed Redis INFO output."""
        return await self.bot.database.redis_client.info(section)

        # redis-py normally returns section dictionaries.
        # Flattening isn't necessary; this helper simply gives us a
        # predictable return type for the commands below.

    @redis.command(name="ping")
    async def redis_ping(self, ctx: commands.Context) -> None:
        """Check whether Redis is reachable."""
        try:
            result = await self.bot.database.redis_client.ping()
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        await ctx.reply(
            view=_status_dashboard(
                online=bool(result),
                system="Redis",
                message=("Redis is online and responding to `PING`." if result else "Redis responded, but not with the expected result."),
            )
        )

    @redis.command(name="status")
    async def redis_status(self, ctx: commands.Context) -> None:
        """Show Redis instance status."""
        redis = self.bot.database.redis_client

        try:
            info = await redis.info()
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        server = info.get("Server", {})
        clients = info.get("Clients", {})
        memory = info.get("Memory", {})
        stats = info.get("Stats", {})

        server_block = _field(
            "\N{DESKTOP COMPUTER}",
            "Server",
            _kv_lines(
                [
                    ("Version", f"`{server.get('redis_version', 'unknown')}`"),
                    ("Mode", f"`{server.get('redis_mode', 'unknown')}`"),
                    ("OS", f"`{server.get('os', 'unknown')}`"),
                ]
            ),
        )

        stats_block = _field(
            "\N{BAR CHART}",
            "Live Stats",
            _kv_lines(
                [
                    (
                        "Uptime",
                        f"`{self._format_duration(server.get('uptime_in_seconds', 0))}`",
                    ),
                    ("Clients", f"`{clients.get('connected_clients', 0):,}`"),
                    ("Memory", self._format_bytes(memory.get("used_memory", 0))),
                    (
                        "Peak Memory",
                        self._format_bytes(memory.get("used_memory_peak", 0)),
                    ),
                    ("Commands", f"`{stats.get('total_commands_processed', 0):,}`"),
                    ("Ops/sec", f"`{stats.get('instantaneous_ops_per_sec', 0):,}`"),
                ]
            ),
        )

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{ELECTRIC PLUG} Redis Status",
                accent_color=_REDIS_COLOR,
                blocks=[server_block, stats_block],
                footer=create_footer(ctx),
            )
        )

    @redis.command(name="memory")
    async def redis_memory(self, ctx: commands.Context) -> None:
        """Show Redis memory statistics."""
        try:
            info = await self.bot.database.redis_client.info("memory")
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        memory = info.get("Memory", info)

        usage_rows: list[tuple[str, str]] = []
        for name, key in (
            ("Used", "used_memory"),
            ("Peak", "used_memory_peak"),
            ("RSS", "used_memory_rss"),
            ("Lua", "used_memory_lua"),
            ("Functions", "used_memory_functions"),
            ("Dataset", "used_memory_dataset"),
            ("Overhead", "used_memory_overhead"),
        ):
            if key in memory:
                usage_rows.append((name, self._format_bytes(memory[key])))

        blocks = [_field("\N{FLOPPY DISK}", "Usage", _kv_lines(usage_rows))]

        limit_rows: list[tuple[str, str]] = []
        if "maxmemory" in memory:
            limit_rows.append(("Max Memory", self._format_bytes(memory["maxmemory"])))
        if "mem_fragmentation_ratio" in memory:
            limit_rows.append(("Fragmentation", f"`{memory['mem_fragmentation_ratio']:.2f}`"))

        if limit_rows:
            blocks.append(_field("\N{ROCKET}", "Limits", _kv_lines(limit_rows)))

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{FLOPPY DISK} Redis Memory",
                accent_color=_REDIS_COLOR,
                blocks=blocks,
                footer=create_footer(ctx),
            )
        )

    @redis.command(name="clients")
    async def redis_clients(self, ctx: commands.Context) -> None:
        """Show Redis client statistics."""
        try:
            info = await self.bot.database.redis_client.info("clients")
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        clients = info.get("Clients", info)

        rows: list[tuple[str, str]] = []
        for name, key in (
            ("Connected", "connected_clients"),
            ("Blocked", "blocked_clients"),
            ("Tracking", "tracking_clients"),
            ("Watching", "watched_clients"),
            ("Max Input Buffer", "client_recent_max_input_buffer"),
            ("Max Output Buffer", "client_recent_max_output_buffer"),
        ):
            value = clients.get(key)
            if value is None:
                continue
            value = self._format_bytes(value) if "Buffer" in name else f"`{value}`"
            rows.append((name, value))

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{BUSTS IN SILHOUETTE} Redis Clients",
                accent_color=_REDIS_COLOR,
                blocks=[_kv_lines(rows)],
                footer=create_footer(ctx),
            )
        )

    @redis.command(name="stats")
    async def redis_stats(self, ctx: commands.Context) -> None:
        """Show Redis command and network statistics."""
        try:
            info = await self.bot.database.redis_client.info("stats")
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        stats = info.get("Stats", info)

        rows: list[tuple[str, str]] = []
        for name, key in (
            ("Commands Processed", "total_commands_processed"),
            ("Ops/sec", "instantaneous_ops_per_sec"),
            ("Connections Received", "total_connections_received"),
            ("Rejected Connections", "rejected_connections"),
            ("Expired Keys", "expired_keys"),
            ("Evicted Keys", "evicted_keys"),
            ("Keyspace Hits", "keyspace_hits"),
            ("Keyspace Misses", "keyspace_misses"),
            ("Pub/Sub Channels", "pubsub_channels"),
            ("Pub/Sub Patterns", "pubsub_patterns"),
        ):
            if key in stats:
                rows.append((name, f"`{stats[key]:,}`"))

        hits = stats.get("keyspace_hits", 0)
        misses = stats.get("keyspace_misses", 0)
        total = hits + misses

        if total:
            hit_rate = hits / total * 100
            rows.append(("Cache Hit Rate", f"`{hit_rate:.2f}%`"))

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{BAR CHART} Redis Statistics",
                accent_color=_REDIS_COLOR,
                blocks=[_kv_lines(rows)],
                footer=create_footer(ctx),
            )
        )

    @redis.command(name="keyspace")
    async def redis_keyspace(self, ctx: commands.Context) -> None:
        """Show Redis keyspace statistics."""
        try:
            info = await self.bot.database.redis_client.info("keyspace")
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        keyspace = info.get("Keyspace", info)

        if not keyspace:
            blocks = ["No databases currently contain keys."]
        else:
            blocks = []
            for database, data in keyspace.items():
                if isinstance(data, dict):
                    keys = data.get("keys", 0)
                    expires = data.get("expires", 0)
                    avg_ttl = data.get("avg_ttl", 0)
                else:
                    # Compatibility with clients that expose the raw
                    # `db0:keys=10,expires=2,avg_ttl=...` representation.
                    keys = expires = avg_ttl = 0

                blocks.append(
                    _field(
                        "\N{FILE CABINET}",
                        database,
                        _kv_lines(
                            [
                                ("Keys", f"`{keys:,}`"),
                                ("Expires", f"`{expires:,}`"),
                                ("Avg TTL", f"`{avg_ttl:,} ms`"),
                            ]
                        ),
                    )
                )

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{OLD KEY} Redis Keyspace",
                accent_color=_REDIS_COLOR,
                blocks=blocks,
                footer=create_footer(ctx),
            )
        )

    @redis.command(name="persistence")
    async def redis_persistence(self, ctx: commands.Context) -> None:
        """Show Redis persistence status."""
        try:
            info = await self.bot.database.redis_client.info("persistence")
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        persistence = info.get("Persistence", info)

        rdb_block = _field(
            "\N{FLOPPY DISK}",
            "RDB",
            _kv_lines(
                [
                    ("Last save", f"`{persistence.get('rdb_last_save_time', 0)}`"),
                    (
                        "Changes since save",
                        f"`{persistence.get('rdb_changes_since_last_save', 0):,}`",
                    ),
                    (
                        "Last save status",
                        f"`{persistence.get('rdb_last_bgsave_status', 'unknown')}`",
                    ),
                    (
                        "Save in progress",
                        f"`{bool(persistence.get('rdb_bgsave_in_progress', 0))}`",
                    ),
                ]
            ),
        )

        aof_block = _field(
            "\N{SCROLL}",
            "AOF",
            _kv_lines(
                [
                    ("Enabled", f"`{bool(persistence.get('aof_enabled', 0))}`"),
                    (
                        "Rewrite in progress",
                        f"`{bool(persistence.get('aof_rewrite_in_progress', 0))}`",
                    ),
                    (
                        "Pending rewrite",
                        f"`{bool(persistence.get('aof_rewrite_scheduled', 0))}`",
                    ),
                ]
            ),
        )

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{PACKAGE} Redis Persistence",
                accent_color=_REDIS_COLOR,
                blocks=[rdb_block, aof_block],
                footer=create_footer(ctx),
            )
        )

    @redis.command(name="replication")
    async def redis_replication(self, ctx: commands.Context) -> None:
        """Show Redis replication status."""
        try:
            info = await self.bot.database.redis_client.info("replication")
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        replication = info.get("Replication", info)

        role = replication.get("role", "unknown")
        connected_slaves = replication.get("connected_slaves", 0)

        summary_block = _field(
            "\N{CROWN}" if role == "master" else "\N{LINK SYMBOL}",
            "Replication",
            _kv_lines([("Role", f"`{role}`"), ("Connected Replicas", f"`{connected_slaves}`")]),
        )
        blocks = [summary_block]

        if role == "master":
            replica_entries: list[str] = []
            for index in range(connected_slaves):
                replica = replication.get(f"slave{index}")

                if not replica:
                    continue

                replica_entries.append(
                    f"**Replica {index}**\n"
                    + _kv_lines(
                        [
                            ("Host", f"`{replica.get('ip', 'unknown')}`"),
                            ("Port", f"`{replica.get('port', 'unknown')}`"),
                            ("State", f"`{replica.get('state', 'unknown')}`"),
                            ("Offset", f"`{replica.get('offset', 0):,}`"),
                        ]
                    )
                )

            blocks.append(
                _field(
                    "\N{ANTENNA WITH BARS}",
                    "Replicas",
                    ("\n\n".join(replica_entries) if replica_entries else "No replicas currently connected."),
                )
            )
        else:
            blocks.append(
                _field(
                    "\N{LINK SYMBOL}",
                    "Master",
                    _kv_lines(
                        [
                            ("Host", f"`{replication.get('master_host', 'unknown')}`"),
                            ("Port", f"`{replication.get('master_port', 'unknown')}`"),
                            (
                                "Link",
                                f"`{replication.get('master_link_status', 'unknown')}`",
                            ),
                        ]
                    ),
                )
            )

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{TWISTED RIGHTWARDS ARROWS} Redis Replication",
                accent_color=_REDIS_COLOR,
                blocks=blocks,
                footer=create_footer(ctx),
            )
        )

    @redis.command(name="config")
    async def redis_config(self, ctx: commands.Context, parameter: str | None = None) -> None:
        """Show a Redis configuration value."""
        if not parameter:
            await ctx.reply("\N{INFORMATION SOURCE} Specify a configuration parameter, e.g. `redis config maxmemory`.")
            return

        try:
            result = await self.bot.database.redis_client.config_get(parameter)
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("Redis", exc))
            return

        if not result:
            await ctx.reply(f"\N{CROSS MARK} No configuration value found for `{parameter}`.")
            return

        rows = [(key, f"`{value}`") for key, value in result.items()]

        await ctx.reply(
            view=create_dashboard_view(
                title=f"## \N{GEAR} Redis Config \N{EM DASH} `{parameter}`",
                accent_color=_REDIS_COLOR,
                blocks=[_kv_lines(rows)],
                footer=create_footer(ctx),
            )
        )

    @staticmethod
    def _format_duration(seconds: int | float) -> str:
        seconds = int(seconds)

        days, seconds = divmod(seconds, 86_400)
        hours, seconds = divmod(seconds, 3_600)
        minutes, seconds = divmod(seconds, 60)

        parts = []

        if days:
            parts.append(f"{days}d")

        if hours:
            parts.append(f"{hours}h")

        if minutes:
            parts.append(f"{minutes}m")

        if seconds or not parts:
            parts.append(f"{seconds}s")

        return " ".join(parts)

    @commands.group(name="mongodb", invoke_without_command=True)
    async def mongodb(self, ctx: commands.Context) -> None:
        """MongoDB monitoring commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @mongodb.command(name="ping")
    async def mongodb_ping(self, ctx: commands.Context) -> None:
        """Check MongoDB connectivity."""
        try:
            result = await self.bot.database.mongo_client.admin.command("ping")
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("MongoDB", exc))
            return

        ok_value = result.get("ok", 0)
        await ctx.reply(
            view=_status_dashboard(
                online=bool(ok_value),
                system="MongoDB",
                message=f"MongoDB is online. `ok={ok_value}`",
            )
        )

    @mongodb.command(name="status")
    async def mongodb_status(self, ctx: commands.Context) -> None:
        """Show MongoDB server status."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # pyright: ignore[reportAssignmentType]

        connections = status.get("connections", {})
        memory = status.get("mem", {})
        network = status.get("network", {})
        operations = status.get("opcounters", {})

        instance_block = _field(
            "\N{DESKTOP COMPUTER}",
            "Instance",
            _kv_lines(
                [
                    ("Host", f"`{status.get('host', 'unknown')}`"),
                    ("Version", f"`{status.get('version', 'unknown')}`"),
                    ("Process", f"`{status.get('process', 'unknown')}`"),
                    ("Uptime", f"`{status.get('uptime', 0):,.0f}s`"),
                ]
            ),
        )

        connections_block = _field(
            "\N{ELECTRIC PLUG}",
            "Connections",
            _kv_lines(
                [
                    ("Current", f"`{connections.get('current', 0):,}`"),
                    ("Available", f"`{connections.get('available', 0):,}`"),
                ]
            ),
        )

        memory_block = _field(
            "\N{FLOPPY DISK}",
            "Memory",
            _kv_lines(
                [
                    ("Resident", f"`{memory.get('resident', 0):,} MB`"),
                    ("Virtual", f"`{memory.get('virtual', 0):,} MB`"),
                ]
            ),
        )

        network_block = _field(
            "\N{GLOBE WITH MERIDIANS}",
            "Network",
            _kv_lines(
                [
                    ("In", f"`{network.get('bytesIn', 0):,}` bytes"),
                    ("Out", f"`{network.get('bytesOut', 0):,}` bytes"),
                ]
            ),
        )

        operations_block = _field(
            "\N{GEAR}",
            "Operations",
            _kv_lines(
                [
                    ("Queries", f"`{operations.get('query', 0):,}`"),
                    ("Inserts", f"`{operations.get('insert', 0):,}`"),
                    ("Updates", f"`{operations.get('update', 0):,}`"),
                    ("Deletes", f"`{operations.get('delete', 0):,}`"),
                ]
            ),
        )

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{LEAF FLUTTERING IN WIND} MongoDB Server Status",
                accent_color=_MONGO_COLOR,
                blocks=[
                    instance_block,
                    connections_block,
                    memory_block,
                    network_block,
                    operations_block,
                ],
                footer=create_footer(ctx),
            )
        )

    @mongodb.command(name="connections")
    async def mongodb_connections(self, ctx: commands.Context) -> None:
        """Show MongoDB connection statistics."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # pyright: ignore[reportAssignmentType]

        connections = status.get("connections", {})

        rows = [
            (name, f"`{connections.get(key, 0):,}`")
            for name, key in (
                ("Current", "current"),
                ("Available", "available"),
                ("Total Created", "totalCreated"),
                ("Active", "active"),
                ("Rejected", "rejected"),
            )
        ]

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{ELECTRIC PLUG} MongoDB Connections",
                accent_color=_MONGO_COLOR,
                blocks=[_kv_lines(rows)],
                footer=create_footer(ctx),
            )
        )

    @mongodb.command(name="operations")
    async def mongodb_operations(self, ctx: commands.Context) -> None:
        """Show MongoDB operation counters."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # pyright: ignore[reportAssignmentType]

        operations = status.get("opcounters", {})

        rows = [(name.capitalize(), f"`{operations.get(name, 0):,}`") for name in ("insert", "query", "update", "delete", "getmore", "command")]

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{GEAR} MongoDB Operations",
                accent_color=_MONGO_COLOR,
                blocks=[_kv_lines(rows)],
                footer=create_footer(ctx),
            )
        )

    @mongodb.command(name="network")
    async def mongodb_network(self, ctx: commands.Context) -> None:
        """Show MongoDB network statistics."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # pyright: ignore[reportAssignmentType]

        network = status.get("network", {})

        rows = [
            ("Bytes In", f"`{network.get('bytesIn', 0):,}`"),
            ("Bytes Out", f"`{network.get('bytesOut', 0):,}`"),
            ("Requests", f"`{network.get('numRequests', 0):,}`"),
        ]

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{GLOBE WITH MERIDIANS} MongoDB Network",
                accent_color=_MONGO_COLOR,
                blocks=[_kv_lines(rows)],
                footer=create_footer(ctx),
            )
        )

    @mongodb.command(name="memory")
    async def mongodb_memory(self, ctx: commands.Context) -> None:
        """Show MongoDB memory usage."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # pyright: ignore[reportAssignmentType]

        memory = status.get("mem", {})

        rows = [
            ("Resident", f"`{memory.get('resident', 0):,} MB`"),
            ("Virtual", f"`{memory.get('virtual', 0):,} MB`"),
            ("Mapped", f"`{memory.get('mapped', 0):,} MB`"),
        ]

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{FLOPPY DISK} MongoDB Memory",
                accent_color=_MONGO_COLOR,
                blocks=[_kv_lines(rows)],
                footer=create_footer(ctx),
            )
        )

    @mongodb.command(name="databases")
    async def mongodb_databases(self, ctx: commands.Context) -> None:
        """List MongoDB databases."""
        try:
            databases = await self.bot.database.mongo_client.list_databases()
            databases = [database async for database in databases]
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("MongoDB", exc))
            return

        if not databases:
            block = "No databases found."
        else:
            block = "\n".join(f"- `{database['name']}` \N{EM DASH} {self._format_bytes(database.get('sizeOnDisk', 0))}" for database in databases)

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{FILE CABINET} MongoDB Databases",
                accent_color=_MONGO_COLOR,
                blocks=[block],
                footer=create_footer(ctx),
            )
        )

    @mongodb.command(name="collections")
    async def mongodb_collections(self, ctx: commands.Context, database: str | None = None) -> None:
        """List collections in a database."""
        database_name = database or self.bot.database.mongo_client.get_default_database().name

        try:
            names = await self.bot.database.mongo_client[database_name].list_collection_names()
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("MongoDB", exc))
            return

        block = "\n".join(f"- `{name}`" for name in names) or "No collections found."

        await ctx.reply(
            view=create_dashboard_view(
                title=f"## \N{OPEN FILE FOLDER} MongoDB Collections \N{EM DASH} `{database_name}`",
                accent_color=_MONGO_COLOR,
                blocks=[block],
                footer=create_footer(ctx),
            )
        )

    @mongodb.command(name="storage")
    async def mongodb_storage(self, ctx: commands.Context, database: str | None = None) -> None:
        """Show database storage statistics."""
        database_name = database or self.bot.database.mongo_client.get_default_database().name
        db = self.bot.database.mongo_client[database_name]

        try:
            stats = await db.command("dbStats")
        except Exception as exc:
            await ctx.reply(view=_error_dashboard("MongoDB", exc))
            return

        rows = [
            ("Data Size", self._format_bytes(stats.get("dataSize", 0))),
            ("Storage Size", self._format_bytes(stats.get("storageSize", 0))),
            ("Indexes", f"`{stats.get('indexes', 0):,}`"),
            ("Index Size", self._format_bytes(stats.get("indexSize", 0))),
            ("Collections", f"`{stats.get('collections', 0):,}`"),
            ("Objects", f"`{stats.get('objects', 0):,}`"),
        ]

        await ctx.reply(
            view=create_dashboard_view(
                title=f"## \N{PACKAGE} MongoDB Storage \N{EM DASH} `{database_name}`",
                accent_color=_MONGO_COLOR,
                blocks=[_kv_lines(rows)],
                footer=create_footer(ctx),
            )
        )

    @staticmethod
    def _format_bytes(value: int | float) -> str:
        value = float(value)

        for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
            if value < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024

        return f"{value:.2f} EB"

    @commands.Cog.listener()
    async def on_redis_message(self, channel: str, message: str) -> None:
        """Log Redis pub/sub messages to the console."""

    @commands.Cog.listener()
    async def on_mongodb_change(self, change) -> None:
        """Log MongoDB change events to the console."""

    @commands.group(name="asyncio", invoke_without_command=True, aliases=["async", "loop"])
    @commands.is_owner()
    async def asyncio_group(self, ctx: commands.Context) -> None:
        """Asyncio event loop monitoring commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @asyncio_group.command(name="tasks")
    @commands.is_owner()
    async def asyncio_tasks(self, ctx: commands.Context[Parrot]) -> None:
        """List all asyncio tasks in the event loop."""
        tasks = asyncio.all_tasks(loop=self.bot.loop)
        task_list = "\n".join(f"- {task.get_name()}" for task in tasks)

        await ctx.reply(
            view=create_dashboard_view(
                title="## \N{SPIRAL CALENDAR PAD} Asyncio Tasks",
                accent_color=discord.Color.blue(),
                blocks=[task_list or "No tasks found."],
                footer=create_footer(ctx),
            )
        )

    @asyncio_group.command(name="cancel")
    @commands.is_owner()
    async def asyncio_cancel(self, ctx: commands.Context[Parrot], task_name: str) -> None:
        """Cancel an asyncio task by name."""
        tasks = asyncio.all_tasks(loop=self.bot.loop)
        for task in tasks:
            if task.get_name() == task_name:
                task.cancel()
                await ctx.reply(f"\N{CROSS MARK} Task `{task_name}` has been cancelled.")
                return

        await ctx.reply(f"\N{WARNING SIGN} No task found with the name `{task_name}`.")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Owner(bot))
