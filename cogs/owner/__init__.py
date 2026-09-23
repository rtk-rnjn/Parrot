from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING

import discord
from colorama import Fore
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter

if TYPE_CHECKING:
    from core import Parrot

    from .hints import ServerStatus


_log = logging.getLogger("bot.cogs.owner")


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
        await ctx.reply("Starting Redis REPL session. Type `exit` to quit.")

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        while True + True == 2:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=300)
            except TimeoutError:
                await ctx.reply("Redis REPL session timed out.")
                break

            if msg.content.lower() == "exit":
                await msg.reply("Exiting Redis REPL session.")
                break

            codeblock = codeblock_converter(msg.content)
            try:
                result = await self.bot.database.redis_client.execute_command(codeblock.content)
                if len(str(result)) > 1980:
                    await msg.reply("Result is too long to display.")
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
        info = await self.bot.database.redis_client.info(section)

        # redis-py normally returns section dictionaries.
        # Flattening isn't necessary; this helper simply gives us a
        # predictable return type for the commands below.
        return info

    @redis.command(name="ping")
    async def redis_ping(self, ctx: commands.Context) -> None:
        """Check whether Redis is reachable."""
        try:
            result = await self.bot.database.redis_client.ping()
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        await ctx.reply(
            "Redis is online." if result else "Redis returned an unexpected response.",
        )

    @redis.command(name="status")
    async def redis_status(self, ctx: commands.Context) -> None:
        """Show Redis instance status."""
        redis = self.bot.database.redis_client

        try:
            info = await redis.info()
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        server = info.get("Server", {})
        clients = info.get("Clients", {})
        memory = info.get("Memory", {})
        stats = info.get("Stats", {})

        embed = discord.Embed(
            title="Redis Status",
            color=discord.Color.red(),
        )

        embed.add_field(
            name="Server",
            value=(
                f"Version: `{server.get('redis_version', 'unknown')}`\n"
                f"Mode: `{server.get('redis_mode', 'unknown')}`\n"
                f"OS: `{server.get('os', 'unknown')}`"
            ),
            inline=False,
        )

        embed.add_field(
            name="Uptime",
            value=(f"`{self._format_duration(server.get('uptime_in_seconds', 0))}`"),
        )

        embed.add_field(
            name="Clients",
            value=f"`{clients.get('connected_clients', 0):,}`",
        )

        embed.add_field(
            name="Memory",
            value=self._format_bytes(memory.get("used_memory", 0)),
        )

        embed.add_field(
            name="Peak Memory",
            value=self._format_bytes(memory.get("used_memory_peak", 0)),
        )

        embed.add_field(
            name="Commands",
            value=f"`{stats.get('total_commands_processed', 0):,}`",
        )

        embed.add_field(
            name="Ops/sec",
            value=f"`{stats.get('instantaneous_ops_per_sec', 0):,}`",
        )

        await ctx.reply(embed=embed)

    @redis.command(name="memory")
    async def redis_memory(self, ctx: commands.Context) -> None:
        """Show Redis memory statistics."""
        try:
            info = await self.bot.database.redis_client.info("memory")
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        memory = info.get("Memory", info)

        embed = discord.Embed(
            title="Redis Memory",
            color=discord.Color.red(),
        )

        fields = (
            ("Used", "used_memory"),
            ("Peak", "used_memory_peak"),
            ("RSS", "used_memory_rss"),
            ("Lua", "used_memory_lua"),
            ("Functions", "used_memory_functions"),
            ("Dataset", "used_memory_dataset"),
            ("Overhead", "used_memory_overhead"),
        )

        for name, key in fields:
            if key in memory:
                embed.add_field(
                    name=name,
                    value=self._format_bytes(memory[key]),
                    inline=True,
                )

        if "maxmemory" in memory:
            embed.add_field(
                name="Max Memory",
                value=self._format_bytes(memory["maxmemory"]),
                inline=True,
            )

        if "mem_fragmentation_ratio" in memory:
            embed.add_field(
                name="Fragmentation",
                value=f"`{memory['mem_fragmentation_ratio']:.2f}`",
                inline=True,
            )

        await ctx.reply(embed=embed)

    @redis.command(name="clients")
    async def redis_clients(self, ctx: commands.Context) -> None:
        """Show Redis client statistics."""
        try:
            info = await self.bot.database.redis_client.info("clients")
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        clients = info.get("Clients", info)

        embed = discord.Embed(
            title="Redis Clients",
            color=discord.Color.red(),
        )

        fields = (
            ("Connected", "connected_clients"),
            ("Blocked", "blocked_clients"),
            ("Tracking", "tracking_clients"),
            ("Watching", "watched_clients"),
            ("Max Input Buffer", "client_recent_max_input_buffer"),
            ("Max Output Buffer", "client_recent_max_output_buffer"),
        )

        for name, key in fields:
            value = clients.get(key)

            if value is not None:
                if "Buffer" in name:
                    value = self._format_bytes(value)

                embed.add_field(
                    name=name,
                    value=f"`{value}`",
                    inline=True,
                )

        await ctx.reply(embed=embed)

    @redis.command(name="stats")
    async def redis_stats(self, ctx: commands.Context) -> None:
        """Show Redis command and network statistics."""
        try:
            info = await self.bot.database.redis_client.info("stats")
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        stats = info.get("Stats", info)

        embed = discord.Embed(
            title="Redis Statistics",
            color=discord.Color.red(),
        )

        fields = (
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
        )

        for name, key in fields:
            if key in stats:
                embed.add_field(
                    name=name,
                    value=f"`{stats[key]:,}`",
                    inline=True,
                )

        hits = stats.get("keyspace_hits", 0)
        misses = stats.get("keyspace_misses", 0)
        total = hits + misses

        if total:
            hit_rate = hits / total * 100

            embed.add_field(
                name="Cache Hit Rate",
                value=f"`{hit_rate:.2f}%`",
                inline=True,
            )

        await ctx.reply(embed=embed)

    @redis.command(name="keyspace")
    async def redis_keyspace(self, ctx: commands.Context) -> None:
        """Show Redis keyspace statistics."""
        try:
            info = await self.bot.database.redis_client.info("keyspace")
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        keyspace = info.get("Keyspace", info)

        embed = discord.Embed(
            title="Redis Keyspace",
            color=discord.Color.red(),
        )

        if not keyspace:
            embed.description = "No databases contain keys."
            await ctx.reply(embed=embed)
            return

        for database, data in keyspace.items():
            if isinstance(data, dict):
                keys = data.get("keys", 0)
                expires = data.get("expires", 0)
                avg_ttl = data.get("avg_ttl", 0)

            else:
                # Compatibility with clients that expose the raw
                # `db0:keys=10,expires=2,avg_ttl=...` representation.
                keys = expires = avg_ttl = 0

            embed.add_field(
                name=database,
                value=(f"Keys: `{keys:,}`\nExpires: `{expires:,}`\nAvg TTL: `{avg_ttl:,} ms`"),
                inline=True,
            )

        await ctx.reply(embed=embed)

    @redis.command(name="persistence")
    async def redis_persistence(self, ctx: commands.Context) -> None:
        """Show Redis persistence status."""
        try:
            info = await self.bot.database.redis_client.info("persistence")
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        persistence = info.get("Persistence", info)

        embed = discord.Embed(
            title="Redis Persistence",
            color=discord.Color.red(),
        )

        rdb = (
            f"Last save: `{persistence.get('rdb_last_save_time', 0)}`\n"
            f"Changes since save: `{persistence.get('rdb_changes_since_last_save', 0):,}`\n"
            f"Last save status: `{persistence.get('rdb_last_bgsave_status', 'unknown')}`\n"
            f"Save in progress: `{bool(persistence.get('rdb_bgsave_in_progress', 0))}`"
        )

        aof = (
            f"Enabled: `{bool(persistence.get('aof_enabled', 0))}`\n"
            f"Rewrite in progress: "
            f"`{bool(persistence.get('aof_rewrite_in_progress', 0))}`\n"
            f"Pending rewrite: "
            f"`{bool(persistence.get('aof_rewrite_scheduled', 0))}`"
        )

        embed.add_field(name="RDB", value=rdb, inline=False)
        embed.add_field(name="AOF", value=aof, inline=False)

        await ctx.reply(embed=embed)

    @redis.command(name="replication")
    async def redis_replication(self, ctx: commands.Context) -> None:
        """Show Redis replication status."""
        try:
            info = await self.bot.database.redis_client.info("replication")
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        replication = info.get("Replication", info)

        role = replication.get("role", "unknown")
        connected_slaves = replication.get("connected_slaves", 0)

        embed = discord.Embed(
            title="Redis Replication",
            color=discord.Color.red(),
        )

        embed.add_field(
            name="Role",
            value=f"`{role}`",
        )

        embed.add_field(
            name="Connected Replicas",
            value=f"`{connected_slaves}`",
        )

        if role == "master":
            for index in range(connected_slaves):
                replica = replication.get(f"slave{index}")

                if replica:
                    embed.add_field(
                        name=f"Replica {index}",
                        value=(
                            f"Host: `{replica.get('ip', 'unknown')}`\n"
                            f"Port: `{replica.get('port', 'unknown')}`\n"
                            f"State: `{replica.get('state', 'unknown')}`\n"
                            f"Offset: `{replica.get('offset', 0):,}`"
                        ),
                        inline=False,
                    )

        else:
            master_host = replication.get("master_host", "unknown")
            master_port = replication.get("master_port", "unknown")
            master_link = replication.get("master_link_status", "unknown")

            embed.add_field(
                name="Master",
                value=(f"Host: `{master_host}`\nPort: `{master_port}`\nLink: `{master_link}`"),
                inline=False,
            )

        await ctx.reply(embed=embed)

    @redis.command(name="config")
    async def redis_config(
        self,
        ctx: commands.Context,
        parameter: str | None = None,
    ) -> None:
        """Show a Redis configuration value."""
        if not parameter:
            await ctx.reply(
                "Specify a configuration parameter, e.g. `redis config maxmemory`.",
            )
            return

        try:
            result = await self.bot.database.redis_client.config_get(
                parameter,
            )
        except Exception as exc:
            await ctx.reply(
                f"Redis error: `{type(exc).__name__}: {exc}`",
            )
            return

        if not result:
            await ctx.reply(f"No configuration value found for `{parameter}`.")
            return

        lines = [f"`{key}` = `{value}`" for key, value in result.items()]

        await ctx.reply("\n".join(lines))

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
            await ctx.reply(f"MongoDB error: `{type(exc).__name__}: {exc}`")
            return

        await ctx.reply(
            f"MongoDB is online. `ok={result.get('ok', 0)}`",
        )

    @mongodb.command(name="status")
    async def mongodb_status(self, ctx: commands.Context) -> None:
        """Show MongoDB server status."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # type: ignore

        connections = status.get("connections", {})
        memory = status.get("mem", {})
        network = status.get("network", {})
        operations = status.get("opcounters", {})

        embed = {
            "title": "MongoDB Server Status",
            "description": (
                f"**Host:** `{status.get('host', 'unknown')}`\n"
                f"**Version:** `{status.get('version', 'unknown')}`\n"
                f"**Process:** `{status.get('process', 'unknown')}`\n"
                f"**Uptime:** `{status.get('uptime', 0):,.0f}s`"
            ),
            "fields": [
                (
                    "Connections",
                    (f"Current: `{connections.get('current', 0):,}`\nAvailable: `{connections.get('available', 0):,}`"),
                ),
                (
                    "Memory",
                    (f"Resident: `{memory.get('resident', 0):,} MB`\nVirtual: `{memory.get('virtual', 0):,} MB`"),
                ),
                (
                    "Network",
                    (f"In: `{network.get('bytesIn', 0):,}` bytes\nOut: `{network.get('bytesOut', 0):,}` bytes"),
                ),
                (
                    "Operations",
                    (
                        f"Queries: `{operations.get('query', 0):,}`\n"
                        f"Inserts: `{operations.get('insert', 0):,}`\n"
                        f"Updates: `{operations.get('update', 0):,}`\n"
                        f"Deletes: `{operations.get('delete', 0):,}`"
                    ),
                ),
            ],
        }

        message = discord.Embed(
            title=embed["title"],
            description=embed["description"],
            color=discord.Color.blurple(),
        )

        for name, value in embed["fields"]:
            message.add_field(name=name, value=value)

        await ctx.reply(embed=message)

    @mongodb.command(name="connections")
    async def mongodb_connections(self, ctx: commands.Context) -> None:
        """Show MongoDB connection statistics."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # type: ignore

        connections = status.get("connections", {})

        embed = discord.Embed(
            title="MongoDB Connections",
            color=discord.Color.blurple(),
        )

        for name, key in (
            ("Current", "current"),
            ("Available", "available"),
            ("Total Created", "totalCreated"),
            ("Active", "active"),
            ("Rejected", "rejected"),
        ):
            embed.add_field(
                name=name,
                value=f"`{connections.get(key, 0):,}`",
                inline=True,
            )

        await ctx.reply(embed=embed)

    @mongodb.command(name="operations")
    async def mongodb_operations(self, ctx: commands.Context) -> None:
        """Show MongoDB operation counters."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # type: ignore

        operations = status.get("opcounters", {})

        embed = discord.Embed(
            title="MongoDB Operations",
            color=discord.Color.blurple(),
        )

        for name in (
            "insert",
            "query",
            "update",
            "delete",
            "getmore",
            "command",
        ):
            embed.add_field(
                name=name.capitalize(),
                value=f"`{operations.get(name, 0):,}`",
                inline=True,
            )

        await ctx.reply(embed=embed)

    @mongodb.command(name="network")
    async def mongodb_network(self, ctx: commands.Context) -> None:
        """Show MongoDB network statistics."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # type: ignore

        network = status.get("network", {})

        embed = discord.Embed(
            title="MongoDB Network",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="Bytes In",
            value=f"`{network.get('bytesIn', 0):,}`",
        )
        embed.add_field(
            name="Bytes Out",
            value=f"`{network.get('bytesOut', 0):,}`",
        )
        embed.add_field(
            name="Requests",
            value=f"`{network.get('numRequests', 0):,}`",
        )

        await ctx.reply(embed=embed)

    @mongodb.command(name="memory")
    async def mongodb_memory(self, ctx: commands.Context) -> None:
        """Show MongoDB memory usage."""
        status: ServerStatus = await self.bot.database.mongo_client.admin.command("serverStatus")  # type: ignore

        memory = status.get("mem", {})

        embed = discord.Embed(
            title="MongoDB Memory",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="Resident",
            value=f"`{memory.get('resident', 0):,} MB",
        )
        embed.add_field(
            name="Virtual",
            value=f"`{memory.get('virtual', 0):,} MB",
        )
        embed.add_field(
            name="Mapped",
            value=f"`{memory.get('mapped', 0):,} MB",
        )

        await ctx.reply(embed=embed)

    @mongodb.command(name="databases")
    async def mongodb_databases(self, ctx: commands.Context) -> None:
        """List MongoDB databases."""
        try:
            databases = await self.bot.database.mongo_client.list_databases()
            databases = [database async for database in databases]
        except Exception as exc:
            await ctx.reply(f"MongoDB error: `{type(exc).__name__}: {exc}`")
            return

        lines = []

        for database in databases:
            name = database["name"]
            size = database.get("sizeOnDisk", 0)

            lines.append(
                f"`{name}` — {self._format_bytes(size)}",
            )

        embed = discord.Embed(
            title="MongoDB Databases",
            description="\n".join(lines) or "No databases found.",
            color=discord.Color.blurple(),
        )

        await ctx.reply(embed=embed)

    @mongodb.command(name="collections")
    async def mongodb_collections(
        self,
        ctx: commands.Context,
        database: str | None = None,
    ) -> None:
        """List collections in a database."""
        database_name = database or self.bot.database.mongo_client.get_default_database().name

        try:
            names = await self.bot.database.mongo_client[database_name].list_collection_names()
        except Exception as exc:
            await ctx.reply(f"MongoDB error: `{type(exc).__name__}: {exc}`")
            return

        embed = discord.Embed(
            title=f"Collections — {database_name}",
            description="\n".join(f"`{name}`" for name in names) or "No collections found.",
            color=discord.Color.blurple(),
        )

        await ctx.reply(embed=embed)

    @mongodb.command(name="storage")
    async def mongodb_storage(
        self,
        ctx: commands.Context,
        database: str | None = None,
    ) -> None:
        """Show database storage statistics."""
        database_name = database or self.bot.database.mongo_client.get_default_database().name
        db = self.bot.database.mongo_client[database_name]

        try:
            stats = await db.command("dbStats")
        except Exception as exc:
            await ctx.reply(f"MongoDB error: `{type(exc).__name__}: {exc}`")
            return

        embed = (
            discord.Embed(
                title=f"MongoDB Storage — {database_name}",
                color=discord.Color.blurple(),
            )
            .add_field(
                name="Data Size",
                value=self._format_bytes(stats.get("dataSize", 0)),
            )
            .add_field(
                name="Storage Size",
                value=self._format_bytes(stats.get("storageSize", 0)),
            )
            .add_field(
                name="Indexes",
                value=f"`{stats.get('indexes', 0):,}`",
            )
            .add_field(
                name="Index Size",
                value=self._format_bytes(stats.get("indexSize", 0)),
            )
            .add_field(
                name="Collections",
                value=f"`{stats.get('collections', 0):,}`",
            )
            .add_field(
                name="Objects",
                value=f"`{stats.get('objects', 0):,}`",
            )
        )

        await ctx.reply(embed=embed)

    @staticmethod
    def _format_bytes(value: int | float) -> str:
        value = float(value)

        for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
            if value < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024

        return f"{value:.2f} EB"


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Owner(bot))
