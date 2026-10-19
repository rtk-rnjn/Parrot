from __future__ import annotations

import asyncio
import logging
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import aiohttp
from discord.ext import commands

if TYPE_CHECKING:
    from collections.abc import Iterable

    from core import Bot

__all__ = (
    "LANGUAGES",
    "MAP_LAYERS",
    "UNITS",
    "LocationNotFound",
    "Place",
    "PlanRequired",
    "Unavailable",
    "Units",
    "WeatherClient",
    "WeatherError",
    "build_fallback_overview",
    "from_day_summary",
    "from_standard",
    "icon_url",
    "lunar_phase",
)

_log = logging.getLogger(__name__)

BASE = "https://api.openweathermap.org"
TILE_BASE = "https://tile.openweathermap.org/map"
ICON_BASE = "https://openweathermap.org/img/wn"
TIMEOUT = aiohttp.ClientTimeout(total=15)
STALE_TTL = 86_400
ONECALL_BLOCK_TTL = 86_400

_SYNODIC_MONTH = 29.530588853 * 86_400
_NEW_MOON_EPOCH = 947_182_440  # 2000-01-06 18:14 UTC

_COORD_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$")
_ZIP_RE = re.compile(r"^\s*(\d{4,10}|[A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d|[A-Za-z]{1,2}\d[A-Za-z\d]?)(?:\s*,\s*([A-Za-z]{2}))?\s*$")

LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "kr": "Korean",
    "zh_cn": "Chinese (Simplified)",
    "ar": "Arabic",
    "tr": "Turkish",
    "nl": "Dutch",
    "pl": "Polish",
    "se": "Swedish",
    "ua": "Ukrainian",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "cz": "Czech",
    "el": "Greek",
    "he": "Hebrew",
    "ro": "Romanian",
    "hu": "Hungarian",
}

MAP_LAYERS: dict[str, tuple[str, str, tuple[tuple[int, int, int], ...]]] = {
    "precipitation_new": (
        "Precipitation",
        "0 mm|140 mm",
        ((110, 180, 255), (60, 120, 240), (80, 220, 140), (250, 210, 60), (255, 90, 60)),
    ),
    "temp_new": (
        "Temperature",
        "-40 \N{DEGREE SIGN}C|+40 \N{DEGREE SIGN}C",
        ((160, 130, 255), (90, 170, 255), (80, 215, 200), (130, 225, 120), (250, 215, 70), (255, 130, 50), (255, 70, 70)),
    ),
    "wind_new": (
        "Wind speed",
        "0 m/s|60 m/s",
        ((200, 230, 255), (100, 190, 255), (100, 230, 160), (250, 200, 70), (255, 90, 90), (200, 90, 230)),
    ),
    "clouds_new": (
        "Cloud cover",
        "0%|100%",
        ((40, 50, 70), (110, 125, 150), (185, 195, 210), (245, 248, 255)),
    ),
    "pressure_new": (
        "Sea-level pressure",
        "950 hPa|1050 hPa",
        ((90, 130, 255), (90, 215, 200), (140, 225, 120), (250, 210, 70), (255, 100, 70)),
    ),
}


class WeatherError(commands.CommandError):
    """A failure whose message is safe to show to the user."""


class LocationNotFound(WeatherError):
    pass


class PlanRequired(WeatherError):
    pass


class Unavailable(WeatherError):
    pass


def icon_url(code: str) -> str:
    return f"{ICON_BASE}/{code}@4x.png"


def lunar_phase(ts: float) -> float:
    """Compute astronomical moon phase in ``[0.0, 1.0)`` for any Unix timestamp (0 = New, 0.5 = Full)."""
    return ((ts - _NEW_MOON_EPOCH) % _SYNODIC_MONTH) / _SYNODIC_MONTH


@dataclass(frozen=True, slots=True)
class Units:
    key: str

    @property
    def symbol(self) -> str:
        return {"metric": "\N{DEGREE SIGN}C", "imperial": "\N{DEGREE SIGN}F", "standard": "K"}[self.key]

    @property
    def label(self) -> str:
        return {
            "metric": "Metric (\N{DEGREE SIGN}C, km/h)",
            "imperial": "Imperial (\N{DEGREE SIGN}F, mph)",
            "standard": "Standard (K, m/s)",
        }[self.key]

    def temp(self, value: float) -> str:
        return f"{value:.0f} K" if self.key == "standard" else f"{value:.0f}{self.symbol}"

    def deg(self, value: float) -> str:
        return f"{value:.0f}" if self.key == "standard" else f"{value:.0f}\N{DEGREE SIGN}"

    def speed(self, value: float) -> str:
        if self.key == "metric":
            return f"{value * 3.6:.0f} km/h"
        return f"{value:.0f} mph" if self.key == "imperial" else f"{value:.1f} m/s"

    def distance(self, metres: float) -> str:
        return f"{metres / 1609.34:.1f} mi" if self.key == "imperial" else f"{metres / 1000:.1f} km"

    def pressure(self, hpa: float) -> str:
        return f"{hpa * 0.02953:.2f} inHg" if self.key == "imperial" else f"{hpa:.0f} hPa"

    def precip(self, mm: float) -> str:
        return f"{mm / 25.4:.2f} in" if self.key == "imperial" else f"{mm:.1f} mm"

    def to_celsius(self, value: float) -> float:
        if self.key == "imperial":
            return (value - 32) * 5 / 9
        return value - 273.15 if self.key == "standard" else value

    def from_celsius(self, value: float) -> float:
        if self.key == "imperial":
            return value * 9 / 5 + 32
        return value + 273.15 if self.key == "standard" else value


UNITS = {key: Units(key) for key in ("metric", "imperial", "standard")}


@dataclass(frozen=True, slots=True)
class Place:
    name: str
    lat: float
    lon: float
    country: str = ""
    state: str = ""

    @property
    def title(self) -> str:
        return ", ".join(part for part in (self.name, self.state, self.country) if part)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "lat": self.lat, "lon": self.lon, "country": self.country, "state": self.state}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Place:
        return cls(data["name"], float(data["lat"]), float(data["lon"]), data.get("country", ""), data.get("state", ""))

    @classmethod
    def from_geo(cls, data: dict[str, Any], lang: str = "en") -> Place:
        name = (data.get("local_names") or {}).get(lang) or data.get("name") or "Unknown"
        return cls(name, float(data["lat"]), float(data["lon"]), data.get("country", ""), data.get("state", ""))


def _dew_point(temp: float, humidity: float, units: Units) -> float:
    celsius = units.to_celsius(temp)
    gamma = math.log(max(humidity, 1) / 100) + 17.62 * celsius / (243.12 + celsius)
    return units.from_celsius(243.12 * gamma / (17.62 - gamma))


def _hour(entry: dict[str, Any], units: Units) -> dict[str, Any]:
    main, wind = entry["main"], entry.get("wind", {})
    rain, snow = (entry.get("rain") or {}).get("3h"), (entry.get("snow") or {}).get("3h")
    return {
        "dt": entry["dt"],
        "temp": main["temp"],
        "feels_like": main["feels_like"],
        "pressure": main["pressure"],
        "humidity": main["humidity"],
        "dew_point": _dew_point(main["temp"], main["humidity"], units),
        "clouds": entry.get("clouds", {}).get("all", 0),
        "visibility": entry.get("visibility"),
        "wind_speed": wind.get("speed", 0),
        "wind_deg": wind.get("deg"),
        "wind_gust": wind.get("gust"),
        "pop": entry.get("pop", 0),
        "weather": entry["weather"],
        "rain": {"1h": rain / 3} if rain else None,
        "snow": {"1h": snow / 3} if snow else None,
    }


def _synthesize_minutely(now: dict[str, Any], hourly: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Interpolate a 60-minute precipitation series from free 2.5 current + forecast data."""
    base_dt = int(now["dt"])
    now_rain = float((now.get("rain") or {}).get("1h") or (now.get("rain") or {}).get("3h", 0) / 3 or 0.0)
    now_snow = float((now.get("snow") or {}).get("1h") or (now.get("snow") or {}).get("3h", 0) / 3 or 0.0)
    rate_0 = now_rain + now_snow

    next_rate = 0.0
    next_pop = 0.0
    if hourly:
        first = hourly[0]
        r1 = float((first.get("rain") or {}).get("1h") or 0.0)
        s1 = float((first.get("snow") or {}).get("1h") or 0.0)
        next_rate = r1 + s1
        next_pop = float(first.get("pop") or 0.0)
        if next_rate == 0.0 and next_pop >= 0.35:
            next_rate = round(next_pop * 2.2, 2)

    if rate_0 == 0.0 and next_rate == 0.0:
        return [{"dt": base_dt + i * 60, "precipitation": 0.0} for i in range(60)]

    points: list[dict[str, Any]] = []
    for i in range(60):
        t = i / 59
        smooth_t = (1 - math.cos(math.pi * t)) / 2
        val = rate_0 * (1 - smooth_t) + next_rate * smooth_t
        if rate_0 == 0.0 and next_pop >= 0.35 and i < 15:
            val = 0.0
        points.append({"dt": base_dt + i * 60, "precipitation": max(0.0, round(val, 2))})
    return points


def _aggregate(hourly: list[dict[str, Any]], offset: int, current: dict[str, Any], units: Units) -> list[dict[str, Any]]:
    days: dict[Any, list[dict[str, Any]]] = {}
    for entry in hourly:
        days.setdefault(datetime.fromtimestamp(entry["dt"] + offset, UTC).date(), []).append(entry)

    today = datetime.fromtimestamp(current["dt"] + offset, UTC).date()
    result: list[dict[str, Any]] = []

    for day, items in days.items():

        def near(hour: int, items: list[dict[str, Any]] = items) -> dict[str, Any]:
            return min(items, key=lambda weather_item: abs(datetime.fromtimestamp(weather_item["dt"] + offset, UTC).hour - hour))

        temps = [h["temp"] for h in items]
        shift = (day - today).days * 86_400
        midday = int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp()) - offset + 43_200
        rain = sum((h.get("rain") or {}).get("1h", 0) * 3 for h in items)
        snow = sum((h.get("snow") or {}).get("1h", 0) * 3 for h in items)
        mean_humidity = sum(h["humidity"] for h in items) / len(items)
        mean_temp = sum(temps) / len(temps)
        min_t, max_t = min(temps), max(temps)
        max_pop = max(h["pop"] for h in items)
        mean_wind = sum(h["wind_speed"] for h in items) / len(items)
        rep_weather = near(13)["weather"]
        desc = rep_weather[0]["description"].capitalize()

        summary_parts = [
            f"{desc} with a high of {units.temp(max_t)} and low of {units.temp(min_t)}.",
            f"Average humidity {mean_humidity:.0f}% and winds around {units.speed(mean_wind)}.",
        ]
        if max_pop >= 0.15:
            summary_parts.append(f"Up to {max_pop * 100:.0f}% chance of precipitation.")

        result.append(
            {
                "dt": midday,
                "sunrise": current["sunrise"] + shift if current.get("sunrise") else None,
                "sunset": current["sunset"] + shift if current.get("sunset") else None,
                "moonrise": None,
                "moonset": None,
                "moon_phase": lunar_phase(midday),
                "summary": " ".join(summary_parts),
                "temp": {
                    "day": near(14)["temp"],
                    "min": min_t,
                    "max": max_t,
                    "night": near(2)["temp"],
                    "eve": near(19)["temp"],
                    "morn": near(8)["temp"],
                },
                "feels_like": {
                    "day": near(14)["feels_like"],
                    "night": near(2)["feels_like"],
                    "eve": near(19)["feels_like"],
                    "morn": near(8)["feels_like"],
                },
                "pressure": sum(h["pressure"] for h in items) / len(items),
                "humidity": mean_humidity,
                "dew_point": _dew_point(mean_temp, mean_humidity, units),
                "wind_speed": mean_wind,
                "wind_deg": near(13)["wind_deg"],
                "wind_gust": max((h["wind_gust"] or 0) for h in items) or None,
                "weather": rep_weather,
                "clouds": sum(h["clouds"] for h in items) / len(items),
                "pop": max_pop,
                "rain": rain or None,
                "snow": snow or None,
                "uvi": None,
            }
        )
    return result


def from_standard(current: dict[str, Any], forecast: dict[str, Any], units: Units) -> dict[str, Any]:
    """Reshape the free 2.5 ``weather`` + ``forecast`` payloads into the One Call 3.0 layout."""
    offset = current.get("timezone", 0)
    main, wind = current["main"], current.get("wind", {})
    rain_raw = current.get("rain")
    snow_raw = current.get("snow")
    rain = (
        {"1h": rain_raw["1h"]}
        if isinstance(rain_raw, dict) and "1h" in rain_raw
        else ({"1h": rain_raw["3h"] / 3} if isinstance(rain_raw, dict) and "3h" in rain_raw else None)
    )
    snow = (
        {"1h": snow_raw["1h"]}
        if isinstance(snow_raw, dict) and "1h" in snow_raw
        else ({"1h": snow_raw["3h"] / 3} if isinstance(snow_raw, dict) and "3h" in snow_raw else None)
    )

    now = {
        "dt": current["dt"],
        "sunrise": current["sys"].get("sunrise"),
        "sunset": current["sys"].get("sunset"),
        "temp": main["temp"],
        "feels_like": main["feels_like"],
        "pressure": main["pressure"],
        "humidity": main["humidity"],
        "dew_point": _dew_point(main["temp"], main["humidity"], units),
        "uvi": None,
        "clouds": current.get("clouds", {}).get("all", 0),
        "visibility": current.get("visibility"),
        "wind_speed": wind.get("speed", 0),
        "wind_deg": wind.get("deg"),
        "wind_gust": wind.get("gust"),
        "weather": current["weather"],
        "rain": rain,
        "snow": snow,
    }
    hourly = [_hour(entry, units) for entry in forecast["list"]]
    return {
        "lat": current["coord"]["lat"],
        "lon": current["coord"]["lon"],
        "timezone": f"UTC{offset / 3600:+g}",
        "timezone_offset": offset,
        "current": now,
        "minutely": _synthesize_minutely(now, hourly),
        "hourly": hourly,
        "daily": _aggregate(hourly, offset, now, units),
        "alerts": [],
        "_source": "standard",
    }


def build_fallback_overview(
    place: Place,
    data: dict[str, Any],
    units: Units,
    air: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize a comprehensive natural-language weather overview from 2.5 data when One Call 3.0 is unavailable."""
    current = data["current"]
    weather = current["weather"][0]
    offset = data.get("timezone_offset", 0)
    daily = data.get("daily") or []
    hourly = data.get("hourly") or []

    now_dt = datetime.fromtimestamp(current["dt"] + offset, UTC)
    desc = weather["description"].lower()
    temp_s = units.temp(current["temp"])
    feels_s = units.temp(current["feels_like"])
    wind_s = units.speed(current.get("wind_speed", 0))
    hum = current.get("humidity", 0)
    dew_s = units.temp(current["dew_point"]) if current.get("dew_point") is not None else "N/A"

    sentences: list[str] = [
        f"Currently in **{place.title}**, conditions are **{desc}** with a temperature of **{temp_s}** (feels like **{feels_s}**).",
        f"Humidity stands at **{hum}%** (dew point **{dew_s}**), with winds blowing at **{wind_s}** and atmospheric pressure at **{units.pressure(current['pressure'])}**.",
    ]

    if daily:
        today = daily[0]
        hi_s = units.temp(today["temp"]["max"])
        lo_s = units.temp(today["temp"]["min"])
        pop_pct = (today.get("pop") or 0) * 100
        sentences.append(
            f"Today's temperature is expected to range between **{lo_s}** and **{hi_s}** with a **{pop_pct:.0f}%** peak chance of precipitation."
        )

    if len(daily) > 1:
        upcoming = daily[1:5]
        hi_week = max(d["temp"]["max"] for d in upcoming)
        lo_week = min(d["temp"]["min"] for d in upcoming)
        wet_days = [datetime.fromtimestamp(d["dt"] + offset, UTC).strftime("%A") for d in upcoming if (d.get("pop") or 0) >= 0.35]
        rain_clause = f"notable rain chances on **{', '.join(wet_days)}**" if wet_days else "mostly dry conditions across the upcoming days"
        sentences.append(
            f"Looking ahead over the next {len(upcoming)} days, temperatures will span **{units.temp(lo_week)}** to **{units.temp(hi_week)}** with {rain_clause}."
        )

    if air and air.get("current"):
        aqi = air["current"]["main"]["aqi"]
        aqi_labels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
        pm25 = air["current"]["components"].get("pm2_5", 0.0)
        sentences.append(
            f"Air quality is currently **{aqi_labels.get(aqi, 'Unknown')} (AQI {aqi}/5)** with PM2.5 at **{pm25:.1f} \N{MICRO SIGN}g/m\N{SUPERSCRIPT THREE}**."
        )

    del hourly
    return {
        "lat": place.lat,
        "lon": place.lon,
        "date": now_dt.strftime("%Y-%m-%d"),
        "units": units.key,
        "weather_overview": " ".join(sentences),
        "_source": "standard",
    }


def from_day_summary(payload: dict[str, Any], units: Units, offset: int = 0) -> dict[str, Any]:
    """Convert a One Call 3.0 ``day_summary`` response into the ``day_card`` dict shape."""
    date_str = payload.get("date", "1970-01-01")
    dt_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    tz_str = payload.get("tz") or ""
    if tz_str and (len(tz_str) == 6 and tz_str[0] in "+-"):
        sign = -1 if tz_str[0] == "-" else 1
        offset = sign * (int(tz_str[1:3]) * 3600 + int(tz_str[4:6]) * 60)

    midday = int(dt_obj.timestamp()) - offset + 43_200
    temps = payload.get("temperature", {})
    humidity = float((payload.get("humidity") or {}).get("afternoon", 50))
    pressure = float((payload.get("pressure") or {}).get("afternoon", 1013))
    clouds = float((payload.get("cloud_cover") or {}).get("afternoon", 0))
    precip = float((payload.get("precipitation") or {}).get("total", 0))
    wind_max = (payload.get("wind") or {}).get("max", {})
    wind_speed = float(wind_max.get("speed", 0))
    wind_deg = wind_max.get("direction")

    day_temp = float(temps.get("afternoon", temps.get("max", 20)))
    min_temp = float(temps.get("min", day_temp))
    max_temp = float(temps.get("max", day_temp))
    morn_temp = float(temps.get("morning", min_temp))
    eve_temp = float(temps.get("evening", day_temp))
    night_temp = float(temps.get("night", min_temp))

    if precip >= 10:
        weather = [{"id": 502, "main": "Rain", "description": "heavy intensity rain", "icon": "10d"}]
    elif precip >= 0.5:
        weather = [{"id": 500, "main": "Rain", "description": "light rain", "icon": "10d"}]
    elif clouds >= 85:
        weather = [{"id": 804, "main": "Clouds", "description": "overcast clouds", "icon": "04d"}]
    elif clouds >= 50:
        weather = [{"id": 803, "main": "Clouds", "description": "broken clouds", "icon": "03d"}]
    elif clouds >= 20:
        weather = [{"id": 801, "main": "Clouds", "description": "few clouds", "icon": "02d"}]
    else:
        weather = [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}]

    return {
        "dt": midday,
        "sunrise": None,
        "sunset": None,
        "moonrise": None,
        "moonset": None,
        "moon_phase": lunar_phase(midday),
        "summary": f"Daily aggregated summary for {date_str} ({tz_str or 'UTC'}).",
        "temp": {
            "day": day_temp,
            "min": min_temp,
            "max": max_temp,
            "night": night_temp,
            "eve": eve_temp,
            "morn": morn_temp,
        },
        "feels_like": {
            "day": day_temp,
            "night": night_temp,
            "eve": eve_temp,
            "morn": morn_temp,
        },
        "pressure": pressure,
        "humidity": humidity,
        "dew_point": _dew_point(day_temp, humidity, units),
        "wind_speed": wind_speed,
        "wind_deg": wind_deg,
        "wind_gust": None,
        "weather": weather,
        "clouds": clouds,
        "pop": 1.0 if precip > 0 else 0.0,
        "rain": precip or None,
        "snow": None,
        "uvi": None,
        "_offset": offset,
    }


class WeatherClient:
    """Cached, rate-limited access to the OpenWeather APIs with automatic Free Tier (2.5) fallback."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._gate = asyncio.Semaphore(6)

    @property
    def key(self) -> str | None:
        return os.environ.get("OPEN_WEATHER_API_KEY") or None

    @property
    def onecall_available(self) -> bool:
        return time.monotonic() >= self._onecall_blocked_until

    def _is_onecall_blocked(self) -> bool:
        return True

    def _mark_onecall_blocked(self) -> None:
        self._onecall_blocked_until = time.monotonic() + ONECALL_BLOCK_TTL

    async def get(self, path: str, params: dict[str, Any], *, ttl: int = 600, fresh: bool = False) -> Any:
        return await self._send(path, params)

    async def _send(self, path: str, params: dict[str, Any]) -> Any:
        token = self.key
        if token is None:
            message = "The OpenWeather API key (`OPEN_WEATHER_API_KEY`) is not configured."
            raise Unavailable(message)

        try:
            async with self._gate, self.bot.http_session.get(f"{BASE}{path}", params={**params, "appid": token}, timeout=TIMEOUT) as response:
                status = response.status
                payload = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as error:
            message = "OpenWeather did not respond. Try again shortly."
            raise Unavailable(message) from error

        if status == 200:
            return payload

        detail = payload.get("message", "") if isinstance(payload, dict) else ""

        match status:
            case 401 if path.startswith("/data/3.0"):
                _log.debug("OpenWeather 3.0 not subscribed (%s); falling back to 2.5 free tier.", path)
                message = "This API key uses the free OpenWeather 2.5 tier (One Call 3.0 is not enabled)."
                raise PlanRequired(message)
            case 401:
                _log.warning("OpenWeather GET %s -> %s %s", path, status, detail)
                message = "OpenWeather rejected the API key. New keys can take up to two hours to activate."
                raise WeatherError(message)
            case 404:
                message = "OpenWeather has no data for that."
                raise LocationNotFound(message)
            case 400:
                _log.warning("OpenWeather GET %s -> %s %s", path, status, detail)
                message = f"OpenWeather rejected the request: {detail or 'bad parameters'}."
                raise WeatherError(message)
            case 429:
                _log.warning("OpenWeather GET %s -> 429 rate limit", path)
                message = "The OpenWeather API limit was reached. Try again in a moment."
                raise Unavailable(message)
            case _:
                _log.warning("OpenWeather GET %s -> %s %s", path, status, detail)
                message = f"OpenWeather returned an unexpected error ({status})."
                raise Unavailable(message)

    async def _fetch_bytes(self, url: str, *, params: dict[str, Any] | None = None, ttl: int = 86_400) -> bytes | None:
        try:
            async with self._gate, self.bot.http_session.get(url, params=params, timeout=TIMEOUT) as response:
                if response.status != 200:
                    return None
                raw = await response.read()
        except TimeoutError, aiohttp.ClientError:
            return None

        return raw

    async def icon(self, code: str | None) -> bytes | None:
        if not code:
            return None
        return await self._fetch_bytes(icon_url(code), ttl=604_800)

    async def icons(self, codes: Iterable[str]) -> dict[str, bytes | None]:
        unique = sorted({c for c in codes if c})
        results = await asyncio.gather(*(self.icon(c) for c in unique))
        return dict(zip(unique, results, strict=True))

    async def geocode(self, query: str, lang: str = "en", limit: int = 5) -> list[Place]:
        data = await self.get("/geo/1.0/direct", {"q": query, "limit": limit}, ttl=604_800)
        places: list[Place] = []
        for item in data:
            place = Place.from_geo(item, lang)
            if all((place.title, round(place.lat, 2), round(place.lon, 2)) != (p.title, round(p.lat, 2), round(p.lon, 2)) for p in places):
                places.append(place)
        return places

    async def zip(self, query: str, lang: str = "en") -> Place:
        return Place.from_geo(await self.get("/geo/1.0/zip", {"zip": query}, ttl=604_800), lang)

    async def reverse(self, lat: float, lon: float, lang: str = "en") -> Place | None:
        data = await self.get("/geo/1.0/reverse", {"lat": lat, "lon": lon, "limit": 1}, ttl=604_800)
        return Place.from_geo(data[0], lang) if data else None

    async def resolve(self, query: str, lang: str = "en", limit: int = 5) -> list[Place]:
        """Resolve coordinates, postal/zip codes, or place names into up to ``limit`` :class:`Place` candidates."""
        cleaned = query.strip()
        if not cleaned:
            msg = "Please provide a location name, postal code, or `lat, lon` coordinates."
            raise LocationNotFound(msg)

        match = _COORD_RE.match(cleaned)
        if match:
            lat, lon = float(match.group(1)), float(match.group(2))
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                msg = "Coordinates must be between -90..90 latitude and -180..180 longitude."
                raise WeatherError(msg)
            try:
                place = await self.reverse(lat, lon, lang)
            except WeatherError:
                place = None
            return [place or Place(f"{lat:.3f}, {lon:.3f}", lat, lon)]

        if _ZIP_RE.match(cleaned):
            zip_query = cleaned.replace(" ", "") if "," in cleaned else cleaned
            try:
                return [await self.zip(zip_query, lang)]
            except WeatherError:
                pass

        places = await self.geocode(cleaned, lang, limit=limit)
        if places:
            return places

        try:
            return [await self.zip(cleaned, lang)]
        except WeatherError as err:
            msg = f"Couldn't find a location matching **{cleaned}**."
            raise LocationNotFound(msg) from err

    async def bundle(self, place: Place, units: Units, lang: str, *, fresh: bool = False) -> dict[str, Any]:
        """Everything for a place in One Call layout, falling back cleanly to the free 2.5 endpoints."""
        params = {"lat": place.lat, "lon": place.lon, "units": units.key, "lang": lang}

        if not self._is_onecall_blocked():
            try:
                data = await self.get("/data/3.0/onecall", params, ttl=600, fresh=fresh)
            except PlanRequired:
                pass
            else:
                for key in ("minutely", "hourly", "daily", "alerts"):
                    data.setdefault(key, [])
                data["_source"] = "onecall"
                return data

        current, forecast = await asyncio.gather(
            self.get("/data/2.5/weather", params, ttl=600, fresh=fresh),
            self.get("/data/2.5/forecast", params, ttl=1800, fresh=fresh),
        )
        return from_standard(current, forecast, units)

    async def air(self, place: Place, *, fresh: bool = False) -> dict[str, Any]:
        params = {"lat": place.lat, "lon": place.lon}
        current, forecast = await asyncio.gather(
            self.get("/data/2.5/air_pollution", params, ttl=1800, fresh=fresh),
            self.get("/data/2.5/air_pollution/forecast", params, ttl=3600, fresh=fresh),
        )

        end = int(time.time()) // 3600 * 3600
        try:
            history = (await self.get("/data/2.5/air_pollution/history", {**params, "start": end - 86_400, "end": end}, ttl=3600))["list"]
        except WeatherError:
            history = []

        return {"current": current["list"][0], "forecast": forecast["list"], "history": history}

    async def day_summary(self, place: Place, date: str, units: Units, lang: str) -> dict[str, Any]:
        if self._is_onecall_blocked():
            msg = "This API key uses the free OpenWeather 2.5 tier."
            raise PlanRequired(msg)
        params = {"lat": place.lat, "lon": place.lon, "date": date, "units": units.key, "lang": lang}
        return await self.get("/data/3.0/onecall/day_summary", params, ttl=3600)

    async def timemachine(self, place: Place, timestamp: int, units: Units, lang: str) -> dict[str, Any]:
        if self._is_onecall_blocked():
            msg = "This API key uses the free OpenWeather 2.5 tier."
            raise PlanRequired(msg)
        params = {"lat": place.lat, "lon": place.lon, "dt": timestamp, "units": units.key, "lang": lang}
        return await self.get("/data/3.0/onecall/timemachine", params, ttl=86_400)

    async def overview(
        self,
        place: Place,
        units: Units,
        *,
        bundle_data: dict[str, Any] | None = None,
        air_data: dict[str, Any] | None = None,
        lang: str = "en",
        fresh: bool = False,
    ) -> dict[str, Any]:
        """Fetch One Call 3.0 AI overview, or synthesize a rich 2.5 overview on the Free Tier."""
        if not self._is_onecall_blocked():
            params = {"lat": place.lat, "lon": place.lon, "units": units.key}
            try:
                data = await self.get("/data/3.0/onecall/overview", params, ttl=1800, fresh=fresh)
                data["_source"] = "onecall"
                return data
            except PlanRequired:
                pass

        if bundle_data is None:
            bundle_data = await self.bundle(place, units, lang, fresh=fresh)
        if air_data is None:
            try:
                air_data = await self.air(place, fresh=fresh)
            except WeatherError:
                air_data = None
        return build_fallback_overview(place, bundle_data, units, air_data)
