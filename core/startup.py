from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StartupCheck:
    name: str
    status: str
    detail: str
    repair: str


@dataclass(frozen=True, slots=True)
class StartupAudit:
    checks: tuple[StartupCheck, ...]
    report_path: Path

    @property
    def has_fatal_failure(self) -> bool:
        return any(check.status == "FAIL" for check in self.checks if check.name in {"Discord runtime", "Discord bot token"})

    @property
    def capabilities(self) -> dict[str, bool]:
        return {check.name: check.status == "OK" for check in self.checks}


def _package_check(name: str, import_name: str, repair: str, *, optional: bool = True) -> StartupCheck:
    available = importlib.util.find_spec(import_name) is not None
    if available:
        return StartupCheck(name, "OK", f"{import_name} is installed", "")

    return StartupCheck(
        name,
        "SKIP" if optional else "FAIL",
        f"{import_name} is not installed",
        repair,
    )


def _environment_check(name: str, variable: str, repair: str, *, required: bool = False) -> StartupCheck:
    configured = bool(os.environ.get(variable, "").strip())
    if configured:
        return StartupCheck(name, "OK", f"{variable} is configured", "")

    return StartupCheck(
        name,
        "FAIL" if required else "SKIP",
        f"{variable} is not configured",
        repair,
    )


def audit_startup(report_path: Path) -> StartupAudit:
    checks = (
        _package_check(
            "Discord runtime",
            "discord",
            "Run: python -m pip install discord.py",
            optional=False,
        ),
        _environment_check(
            "Discord bot token",
            "DISCORD_BOT_TOKEN",
            "Set DISCORD_BOT_TOKEN in .env or your process environment",
            required=True,
        ),
        _package_check(
            "MongoDB support",
            "pymongo",
            "Install PyMongo if database-backed features are needed: python -m pip install pymongo",
        ),
        _package_check(
            "Redis support",
            "redis",
            "Install Redis support if caching is needed: python -m pip install redis",
        ),
        _package_check(
            "Lavalink support",
            "pomice",
            "Install Pomice and run Lavalink if music features are needed",
        ),
        _package_check(
            "Jishaku",
            "jishaku",
            "Install Jishaku for developer commands: python -m pip install jishaku",
        ),
        _environment_check("Supercell Clash Royale", "SUPERCELL_ROYALE_API", "Set SUPERCELL_ROYALE_API in .env"),
        _environment_check("Supercell Clash of Clans", "SUPERCELL_COC_API", "Set SUPERCELL_COC_API in .env"),
        _environment_check("Supercell Brawl Stars", "SUPERCELL_BRAWL_STARS_API", "Set SUPERCELL_BRAWL_STARS_API in .env"),
        _environment_check("News API", "NEWS_API_KEY", "Set NEWS_API_KEY in .env"),
        _environment_check("NASA API", "NASA_API_KEY", "Set NASA_API_KEY in .env"),
        _environment_check("OpenWeather API", "OPEN_WEATHER_API_KEY", "Set OPEN_WEATHER_API_KEY in .env"),
        _environment_check("Imgflip API", "IMAGE_FLIP_KEY", "Set IMAGE_FLIP_KEY in .env"),
    )
    audit = StartupAudit(tuple(checks), report_path)

    for check in audit.checks:
        if check.status == "OK":
            _log.info("Startup check passed: %s (%s)", check.name, check.detail)
        elif check.status == "FAIL":
            _log.error("Startup check failed: %s. %s. Repair: %s", check.name, check.detail, check.repair)
        else:
            _log.warning("Startup capability unavailable: %s. %s. Repair: %s", check.name, check.detail, check.repair)

    write_startup_report(audit)
    return audit


async def probe_database_services(database: Any) -> tuple[StartupCheck, ...]:
    if database is None:
        return (
            StartupCheck("MongoDB service", "SKIP", "MongoDB support is unavailable", "Install PyMongo and configure MONGO_URI"),
            StartupCheck("Redis service", "SKIP", "Redis support is unavailable", "Install Redis and start the configured Redis server"),
        )

    async def probe(name: str, operation, repair: str) -> StartupCheck:
        try:
            result = await asyncio.wait_for(operation(), timeout=5)
        except Exception as error:  # pylint: disable=broad-exception-caught
            _log.warning("Startup service check failed for %s: %s", name, error)
            return StartupCheck(name, "SKIP", "Service did not respond successfully", repair)
        return StartupCheck(name, "OK" if result else "SKIP", "Service responded" if result else "Service returned an unsuccessful response", repair)

    return (
        await probe("MongoDB service", database.ping_mongo_server, "Start MongoDB and verify MONGO_URI"),
        await probe("Redis service", database.ping_redis_server, "Start Redis and verify REDIS_HOST/REDIS_PORT"),
    )


async def probe_http_services(session: Any) -> tuple[StartupCheck, ...]:
    async def probe(
        name: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        repair: str,
        valid_statuses: set[int] | None = None,
    ) -> StartupCheck:
        if valid_statuses is None:
            valid_statuses = {200}
        if not params and not headers:
            return StartupCheck(name, "SKIP", "API configuration is missing", repair)
        try:
            async with session.get(url, params=params, headers=headers, timeout=5) as response:
                status = response.status
                if status in valid_statuses:
                    return StartupCheck(name, "OK", "API responded successfully", "")
                detail = "API rejected the request" if status in {401, 403} else f"API returned HTTP {status}"
                return StartupCheck(name, "SKIP", detail, repair)
        except Exception as error:  # pylint: disable=broad-exception-caught
            _log.warning("Startup API check failed for %s: %s", name, error)
            return StartupCheck(name, "SKIP", "API did not respond", repair)

    checks: list[StartupCheck] = []
    keys = {
        "Supercell Clash Royale": ("SUPERCELL_ROYALE_API", "https://proxy.royaleapi.dev/v1/locations"),
        "Supercell Clash of Clans": ("SUPERCELL_COC_API", "https://cocproxy.royaleapi.dev/v1/locations"),
        "Supercell Brawl Stars": ("SUPERCELL_BRAWL_STARS_API", "https://bsproxy.royaleapi.dev/v1/locations"),
    }
    for name, (variable, url) in keys.items():
        token = os.environ.get(variable)
        checks.append(
            await probe(
                name,
                url,
                headers={"Authorization": f"Bearer {token}"} if token else None,
                repair=f"Set a valid {variable} in .env",
                valid_statuses={200},
            )
        )

    news_key = os.environ.get("NEWS_API_KEY")
    checks.append(
        await probe(
            "News API service",
            "https://newsapi.org/v2/top-headlines",
            params={"country": "us", "pageSize": "1", "apiKey": news_key} if news_key else None,
            repair="Set a valid NEWS_API_KEY in .env",
        )
    )
    nasa_key = os.environ.get("NASA_API_KEY")
    checks.append(
        await probe(
            "NASA API service",
            "https://api.nasa.gov/planetary/apod",
            params={"api_key": nasa_key} if nasa_key else None,
            repair="Set a valid NASA_API_KEY in .env",
        )
    )
    weather_key = os.environ.get("OPEN_WEATHER_API_KEY")
    checks.append(
        await probe(
            "OpenWeather API service",
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": "London", "appid": weather_key} if weather_key else None,
            repair="Set a valid OPEN_WEATHER_API_KEY in .env",
        )
    )
    return tuple(checks)


def extend_audit(audit: StartupAudit, checks: tuple[StartupCheck, ...]) -> StartupAudit:
    updated = StartupAudit(audit.checks + checks, audit.report_path)
    for check in checks:
        if check.status == "OK":
            _log.info("Startup service check passed: %s", check.name)
        else:
            _log.warning("Startup capability unavailable: %s. Repair: %s", check.name, check.repair)
    write_startup_report(updated)
    return updated


def write_startup_report(audit: StartupAudit) -> None:
    try:
        audit.report_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "Parrot startup capability report",
            f"Generated: {datetime.now(UTC).isoformat()}",
            "",
            "Values are intentionally not printed. Set secrets in .env or the process environment.",
            "",
        ]
        for check in audit.checks:
            lines.append(f"[{check.status}] {check.name}: {check.detail}")
            if check.repair:
                lines.append(f"  Repair: {check.repair}")

        audit.report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _log.info("Wrote startup report to %s", audit.report_path)
    except OSError:
        _log.exception("Could not write startup report to %s", audit.report_path)
