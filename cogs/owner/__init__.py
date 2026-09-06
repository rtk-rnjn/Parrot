from __future__ import annotations

import logging
import traceback
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import TYPE_CHECKING

import discord
import matplotlib
from colorama import Fore
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from jishaku.functools import executor_function

matplotlib.use("agg")
from matplotlib import pyplot as plt  # noqa: E402

if TYPE_CHECKING:
    from core.bot import Parrot


_log = logging.getLogger("bot.cogs.owner")


@executor_function
def render_stats_report(records: list[dict], title: str) -> discord.File:  # noqa: C901, PLR0915
    daily_messages: defaultdict[str, float] = defaultdict(float)
    daily_commands: defaultdict[str, float] = defaultdict(float)
    daily_joins: defaultdict[str, float] = defaultdict(float)
    daily_leaves: defaultdict[str, float] = defaultdict(float)
    presence_seconds: defaultdict[str, float] = defaultdict(float)
    voice_seconds: defaultdict[str, float] = defaultdict(float)
    channel_messages: defaultdict[int, float] = defaultdict(float)
    interval_messages: list[float] = []

    for record in records:
        day = record["interval_start"].astimezone(UTC).strftime("%m-%d")
        values = record.get("values", {})
        kind = record.get("kind")
        kind = getattr(kind, "value", kind)
        event = record.get("event")
        event = getattr(event, "value", event)
        if kind == "message":
            messages = float(values.get("messages", 0))
            daily_messages[day] += messages
            channel_id = record.get("channel_id")
            if channel_id is not None:
                channel_messages[channel_id] += messages
            interval_messages.append(messages)
        elif kind == "command":
            daily_commands[day] += float(values.get("commands", 0))
        elif kind == "presence":
            status = record.get("status")
            presence_seconds[str(getattr(status, "value", status))] += float(values.get("seconds", 0))
        elif kind == "voice":
            state = record.get("voice_state")
            voice_seconds[str(getattr(state, "value", state))] += float(values.get("seconds", 0))
        elif event == "member_join":
            daily_joins[day] += float(values.get("events", 0))
        elif event == "member_leave":
            daily_leaves[day] += float(values.get("events", 0))

    days = sorted(set(daily_messages) | set(daily_commands) | set(daily_joins) | set(daily_leaves))
    if not days:
        days = [datetime.now(UTC).strftime("%m-%d")]

    figure, axes = plt.subplots(3, 2, figsize=(15, 12), layout="constrained")
    figure.suptitle(title, fontsize=18, fontweight="bold")

    axes[0, 0].plot(days, [daily_messages[day] for day in days], marker="o", label="Messages")
    axes[0, 0].plot(days, [daily_commands[day] for day in days], marker="o", label="Commands")
    axes[0, 0].set_title("Daily activity")
    axes[0, 0].legend()

    width = 0.38
    positions = list(range(len(days)))
    axes[0, 1].bar([position - width / 2 for position in positions], [daily_joins[day] for day in days], width, label="Joins")
    axes[0, 1].bar([position + width / 2 for position in positions], [daily_leaves[day] for day in days], width, label="Leaves")
    axes[0, 1].set_xticks(positions, days)
    axes[0, 1].set_title("Member joins vs. leaves")
    axes[0, 1].legend()

    presence_labels = list(presence_seconds) or ["No data"]
    presence_values = list(presence_seconds.values()) or [1]
    axes[1, 0].pie(presence_values, labels=presence_labels, autopct="%1.0f%%")
    axes[1, 0].set_title("Presence time")

    voice_labels = list(voice_seconds) or ["No data"]
    voice_values = list(voice_seconds.values()) or [1]
    axes[1, 1].pie(voice_values, labels=voice_labels, autopct="%1.0f%%")
    axes[1, 1].set_title("Voice time by state")

    top_channels = sorted(channel_messages.items(), key=lambda item: item[1], reverse=True)[:10]
    if top_channels:
        labels = [str(channel_id) for channel_id, _ in top_channels][::-1]
        values = [value for _, value in top_channels][::-1]
        axes[2, 0].barh(labels, values, color="#4c78a8")
        axes[2, 0].set_title("Top message channels")
        axes[2, 0].set_xlabel("Messages")
    else:
        axes[2, 0].text(0.5, 0.5, "No message data", ha="center", va="center")
        axes[2, 0].set_axis_off()

    axes[2, 1].hist(interval_messages or [0], bins=min(12, max(1, len(interval_messages))), color="#f58518")
    axes[2, 1].set_title("Messages per 30-minute bucket")
    axes[2, 1].set_xlabel("Messages")
    axes[2, 1].set_ylabel("Buckets")

    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=140)
    plt.close(figure)
    buffer.seek(0)
    return discord.File(buffer, filename="stats-report.png")


class Owner(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        _log.info("Cog loaded: %s", self.__class__.__name__)

    def _format_traceback(self, error: Exception) -> str:
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = "".join(tb)
        return f"```ansi\n{Fore.RED}{tb_str}{Fore.RESET}\n```"

    @commands.command(name="stats", aliases=("stats-report", "trends"))
    @commands.is_owner()
    async def stats_report(self, ctx: commands.Context[Parrot], guild: discord.Guild | None = None) -> None:
        """Render the last 30 days of bot statistics."""
        since = datetime.now(UTC) - timedelta(days=30)
        records = await self.bot.database_manager.get_stats_since(since, guild_id=guild.id if guild else None)
        scope = guild.name if guild else "all guilds"
        if not records:
            await ctx.reply(f"No statistics retained for {scope}.")
            return

        file = await render_stats_report(records, f"Parrot statistics: {scope} | last 30 days")
        await ctx.reply(file=file)

    @commands.command(name="redis-repl", aliases=["redis-cli", "redis"])
    @commands.is_owner()
    async def redis_repl(self, ctx: commands.Context[Parrot]) -> None:
        """Start a Redis REPL session."""
        await ctx.send("Starting Redis REPL session. Type `exit` to quit.")

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        while True:
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
                result = await self.bot.database_manager.redis_client.execute_command(codeblock.content)
                if len(str(result)) > 1980:
                    await msg.reply("Result is too long to display.")
                else:
                    await msg.reply(f"```py\n{result}```")
            except Exception as e:
                tb_fmt = self._format_traceback(e)
                await msg.reply(tb_fmt)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Owner(bot))
