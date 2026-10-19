from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, date, datetime, timedelta
from datetime import time as dt_time
from io import BytesIO
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import ui
from discord.ext import commands

from . import render
from .api import LANGUAGES, MAP_LAYERS, UNITS, LocationNotFound, Place, Units, WeatherClient, WeatherError, from_day_summary, icon_url, lunar_phase

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from core import Bot
    from core.utils.database.models import WeatherSettings


PageKey = Literal["current", "hourly", "daily", "day", "minutely", "air", "alerts"]

PAGE_META: dict[str, tuple[str, str, str]] = {
    "current": ("Current conditions", "\N{WHITE SUN WITH SMALL CLOUD}", "Live temperature, wind, UV, sun arc & 9-tile metrics"),
    "hourly": ("Hourly forecast", "\N{CLOCK FACE THREE OCLOCK}", "Temperature curve, wind speeds & rain probability"),
    "daily": ("Daily forecast", "\N{SPIRAL CALENDAR PAD}", "Multi-day temperature range bars & daily breakdown"),
    "minutely": ("Next-hour precipitation", "\N{CLOUD WITH RAIN}", "Minute-by-minute precipitation radar for 60 minutes"),
    "air": ("Air quality", "\N{LEAF FLUTTERING IN WIND}", "AQI gauge, 8 pollutant concentrations & 5-day trend"),
    "alerts": ("Weather alerts", "\N{WARNING SIGN}", "Active government severe weather advisories"),
}

LAYER_EMOJIS: dict[str, str] = {
    "precipitation_new": "\N{CLOUD WITH RAIN}",
    "temp_new": "\N{THERMOMETER}",
    "wind_new": "\N{WIND BLOWING FACE}",
    "clouds_new": "\N{CLOUD}",
    "pressure_new": "\N{COMPASS}",
}

POPULAR_PLACES: tuple[tuple[str, str], ...] = (
    ("New York, NY, US", "New York, US"),
    ("London, GB", "London, GB"),
    ("Tokyo, JP", "Tokyo, JP"),
    ("Delhi, IN", "Delhi, IN"),
    ("Paris, FR", "Paris, FR"),
    ("Sydney, AU", "Sydney, AU"),
)


def rain_outlook(minutely: list[dict[str, Any]], now: int, units: Units) -> str:
    """Build a natural-language next-hour precipitation summary from ``minutely`` points."""
    points = [m for m in minutely if m.get("dt", 0) >= now - 60][:60]
    if not points:
        return "No precipitation expected over the next 60 minutes."

    wet = [i for i, m in enumerate(points) if (m.get("precipitation") or 0) > 0.01]
    if not wet:
        return "No precipitation expected over the next 60 minutes."

    peak = max(float(m.get("precipitation") or 0) for m in points)
    peak_str = f"{units.precip(peak)}/h"

    if wet[0] == 0:
        dry_after = next((i for i, m in enumerate(points) if (m.get("precipitation") or 0) <= 0.01), None)
        if dry_after is None or dry_after >= 55:
            return f"Precipitation continuing for the next hour (peak {peak_str})."
        return f"Precipitation ending in ~{dry_after} min (peak {peak_str})."

    start = wet[0]
    duration = len(wet)
    return f"Precipitation starting in ~{start} min for ~{duration} min (peak {peak_str})."


def _accent_colour(weather_id: int, night: bool) -> discord.Colour:
    r, g, b = render.theme_for(weather_id, night).accent
    return discord.Colour.from_rgb(r, g, b)


def clip_headline(text: str) -> str:
    return text if len(text) <= 58 else f"{text[:55]}\N{HORIZONTAL ELLIPSIS}"


def _parse_history_window(
    date_text: str,
    time_text: str | None,
    offset: int,
) -> tuple[date, int | None]:
    """Validate and parse a lookup date (and optional ``HH:MM`` local time)."""
    cleaned_date = date_text.strip()
    try:
        target_date = datetime.strptime(cleaned_date, "%Y-%m-%d").replace(tzinfo=UTC).date()
    except ValueError as err:
        msg = "Invalid date format. Please use `YYYY-MM-DD` (for example, `2026-10-17`)."
        raise WeatherError(msg) from err

    today = datetime.now(UTC).date()
    cleaned_time = (time_text or "").strip()

    if cleaned_time:
        try:
            parts = cleaned_time.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            local_t = dt_time(hour=hour, minute=minute)
        except (ValueError, IndexError) as err:
            msg = "Invalid time format. Please use 24-hour `HH:MM` (for example, `14:30`)."
            raise WeatherError(msg) from err

        if target_date < date(1979, 1, 1):
            msg = "OpenWeather archives begin on **1979-01-01**."
            raise WeatherError(msg)
        if target_date > today + timedelta(days=5):
            msg = "Timestamp lookups cannot be more than **5 days** in the future."
            raise WeatherError(msg)

        naive_dt = datetime.combine(target_date, local_t, tzinfo=UTC)
        utc_ts = int(naive_dt.timestamp()) - offset
        return target_date, utc_ts

    if target_date < date(1979, 1, 2):
        msg = "OpenWeather daily archives begin on **1979-01-02**."
        raise WeatherError(msg)
    if target_date > today + timedelta(days=547):
        msg = "Daily summary lookups cannot be more than **1.5 years** in the future."
        raise WeatherError(msg)

    return target_date, None


class CardLayoutView(ui.LayoutView):
    """Static Components V2 container view for one-off weather cards (Overview & History/Date Lookup)."""

    def __init__(
        self,
        *,
        heading: str,
        body: str,
        footer: str,
        colour: discord.Colour,
        thumbnail_url: str | None = None,
        filename: str | None = None,
    ) -> None:
        super().__init__(timeout=None)
        container = ui.Container(accent_colour=colour)

        if thumbnail_url:
            container.add_item(
                ui.Section(
                    ui.TextDisplay(heading),
                    ui.TextDisplay(body),
                    accessory=ui.Thumbnail(thumbnail_url),
                )
            )
        else:
            container.add_item(ui.TextDisplay(f"{heading}\n{body}"))

        if filename:
            container.add_item(ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{filename}")))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"-# {footer}"))
        self.add_item(container)


class LocationModal(ui.Modal, title="Change Weather Location"):
    """Shared modal for resolving a place from either the weather dashboard or user settings."""

    query = ui.TextInput(
        label="City, postal/zip code, or coordinates",
        placeholder="e.g. Tokyo, JP  \N{BULLET}  10001,US  \N{BULLET}  28.6139, 77.2090",
        min_length=2,
        max_length=100,
        required=True,
    )

    def __init__(
        self,
        client: WeatherClient,
        lang: str,
        callback: Callable[[discord.Interaction, list[Place]], Coroutine[Any, Any, None]],
        *,
        default: str = "",
    ) -> None:
        super().__init__(timeout=180)
        self.client = client
        self.lang = lang
        self._callback = callback
        if default:
            self.query.default = default[:100]

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            places = await self.client.resolve(self.query.value, lang=self.lang, limit=5)
        except WeatherError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        await self._callback(interaction, places)


class HistoryModal(ui.Modal, title="Date & Time Weather Lookup"):
    """Modal for querying a specific date/time (uses One Call 3.0 or free 5-day 2.5 forecast fallback)."""

    date_input = ui.TextInput(
        label="Date (YYYY-MM-DD)",
        placeholder="e.g. 2026-10-17 (up to 5 days ahead on Free Tier, or 1979+ on One Call)",
        min_length=10,
        max_length=10,
        required=True,
    )
    time_input = ui.TextInput(
        label="Local time (HH:MM, optional)",
        placeholder="Leave blank for full-day card, or e.g. 14:00 for a specific hour",
        min_length=0,
        max_length=5,
        required=False,
    )

    def __init__(self, dashboard: WeatherDashboard) -> None:
        super().__init__(timeout=180)
        self.dashboard = dashboard
        offset = dashboard.data.get("timezone_offset", 0)
        local_today = render.local(dashboard.data["current"]["dt"], offset).date()
        default_date = local_today + timedelta(days=1) if dashboard.data.get("_source") == "standard" else local_today - timedelta(days=1)
        self.date_input.default = default_date.isoformat()

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        offset = self.dashboard.data.get("timezone_offset", 0)
        try:
            target_date, timestamp = _parse_history_window(
                self.date_input.value,
                self.time_input.value,
                offset,
            )
            file, view = await self.dashboard.cog.build_history_view(
                place=self.dashboard.place,
                units=self.dashboard.units,
                lang=self.dashboard.lang,
                target_date=target_date,
                timestamp=timestamp,
                fallback_offset=offset,
            )
        except WeatherError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return

        await interaction.followup.send(view=view, file=file, ephemeral=True)


class _PageSelect(ui.Select["WeatherDashboard"]):
    def __init__(self, dashboard: WeatherDashboard) -> None:
        alerts = dashboard.data.get("alerts") or []
        options: list[discord.SelectOption] = []
        for key, (label, emoji, desc) in PAGE_META.items():
            if key == "alerts" and not alerts and dashboard.page != "alerts":
                continue
            item_label = f"{label} ({len(alerts)})" if key == "alerts" and alerts else label
            is_current = (dashboard.page == key) or (dashboard.page == "day" and key == "daily")
            options.append(
                discord.SelectOption(
                    label=item_label,
                    value=key,
                    emoji=emoji,
                    description=desc,
                    default=is_current,
                )
            )
        super().__init__(placeholder="Switch weather view\N{HORIZONTAL ELLIPSIS}", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        chosen = self.values[0]
        self.view.page = chosen  # type: ignore[assignment]
        if chosen != "day":
            self.view.day_index = None
        await self.view.refresh_message(interaction)


class _DaySelect(ui.Select["WeatherDashboard"]):
    def __init__(self, dashboard: WeatherDashboard) -> None:
        days = dashboard.data.get("daily") or []
        offset = dashboard.data.get("timezone_offset", 0)
        today_date = render.local(dashboard.data["current"]["dt"], offset).date()

        options: list[discord.SelectOption] = [
            discord.SelectOption(
                label=f"All {len(days)} days (overview)",
                value="all",
                emoji="\N{SPIRAL CALENDAR PAD}",
                description="View the multi-day temperature range bar chart",
                default=dashboard.page == "daily",
            )
        ]
        for idx, day in enumerate(days[:24]):
            dt_val = render.local(day["dt"], offset)
            name = "Today" if dt_val.date() == today_date else f"{dt_val:%a, %d %b}"
            weather = day["weather"][0]
            hi = dashboard.units.temp(day["temp"]["max"])
            lo = dashboard.units.temp(day["temp"]["min"])
            options.append(
                discord.SelectOption(
                    label=f"{name} \N{EM DASH} {hi} / {lo}",
                    value=str(idx),
                    description=weather["description"].title()[:100],
                    default=dashboard.page == "day" and dashboard.day_index == idx,
                )
            )
        super().__init__(placeholder="Inspect a specific day\N{HORIZONTAL ELLIPSIS}", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        choice = self.values[0]
        if choice == "all":
            self.view.page = "daily"
            self.view.day_index = None
        else:
            self.view.page = "day"
            self.view.day_index = int(choice)
        await self.view.refresh_message(interaction)


class _LayerSelect(ui.Select["WeatherDashboard"]):
    def __init__(self, dashboard: WeatherDashboard) -> None:
        options = [
            discord.SelectOption(
                label=title,
                value=key,
                emoji=LAYER_EMOJIS.get(key, "\N{WORLD MAP}"),
                description=f"Scale: {scale.replace('|', ' to ')}",
                default=key == dashboard.map_layer,
            )
            for key, (title, scale, _) in MAP_LAYERS.items()
        ]
        super().__init__(placeholder="Select map overlay layer\N{HORIZONTAL ELLIPSIS}", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        self.view.map_layer = self.values[0]
        await self.view.refresh_message(interaction)


class _AlertSelect(ui.Select["WeatherDashboard"]):
    def __init__(self, dashboard: WeatherDashboard) -> None:
        alerts = dashboard.data.get("alerts") or []
        options = [
            discord.SelectOption(
                label=f"{idx + 1}. {(alert.get('event') or 'Weather Alert')[:80]}",
                value=str(idx),
                emoji="\N{WARNING SIGN}",
                description=(alert.get("sender_name") or "Official advisory")[:100],
                default=idx == dashboard.alert_index,
            )
            for idx, alert in enumerate(alerts[:25])
        ]
        super().__init__(placeholder="Select weather alert\N{HORIZONTAL ELLIPSIS}", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        self.view.alert_index = int(self.values[0])
        await self.view.refresh_message(interaction)


class _PlaceSelect(ui.Select["WeatherDashboard"]):
    def __init__(self, dashboard: WeatherDashboard) -> None:
        options = [
            discord.SelectOption(
                label=place.title[:100],
                value=str(idx),
                emoji="\N{ROUND PUSHPIN}",
                description=f"{place.lat:.3f}, {place.lon:.3f}",
                default=(place.title == dashboard.place.title and abs(place.lat - dashboard.place.lat) < 0.01),
            )
            for idx, place in enumerate(dashboard.candidates[:25])
        ]
        super().__init__(placeholder="Multiple matching locations found\N{HORIZONTAL ELLIPSIS}", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        chosen = self.view.candidates[int(self.values[0])]
        self.view.candidates = []
        await self.view.switch_place(interaction, chosen)


class WeatherDashboard(ui.LayoutView):
    """Full interactive multi-page OpenWeather dashboard built with Discord Components V2 (``ui.LayoutView``)."""

    def __init__(
        self,
        cog: Weather,
        author_id: int,
        place: Place,
        units: Units,
        lang: str,
        data: dict[str, Any],
        *,
        page: PageKey = "current",
        day_index: int | None = None,
        map_layer: str = "precipitation_new",
        zoom: int = 5,
        animated: bool = False,
        candidates: list[Place] | None = None,
    ) -> None:
        super().__init__(timeout=600)
        self.cog = cog
        self.client = cog.client
        self.author_id = author_id
        self.place = place
        self.units = units
        self.lang = lang
        self.data = data
        self.page: PageKey = page
        self.day_index = day_index
        self.map_layer = map_layer if map_layer in MAP_LAYERS else "precipitation_new"
        self.zoom = max(2, min(10, zoom))
        self.animated = animated
        self.alert_index = 0
        self.candidates: list[Place] = candidates if candidates and len(candidates) > 1 else []

        self._air_data: dict[str, Any] | None = None
        self._card_cache: dict[tuple[Any, ...], bytes] = {}
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the user who opened this weather dashboard can control it. Run `/weather` to open your own!",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.walk_children():
            if isinstance(item, (ui.Button, ui.Select)):
                item.disabled = True
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)

    def _build_layout(  # noqa: PLR0915
        self,
        *,
        summary: str,
        filename: str | None,
        colour: discord.Colour,
        thumb_url: str,
        alert_body: str | None = None,
    ) -> None:
        self.clear_items()
        container = ui.Container(accent_colour=colour)

        header_title = f"### {self.place.title}\n-# {self.place.lat:.2f}\N{DEGREE SIGN}, {self.place.lon:.2f}\N{DEGREE SIGN}"
        container.add_item(
            ui.Section(
                ui.TextDisplay(header_title),
                ui.TextDisplay(summary),
                accessory=ui.Thumbnail(thumb_url),
            )
        )

        if alert_body:
            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(ui.TextDisplay(alert_body))

        if filename:
            container.add_item(ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{filename}")))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.ActionRow(_PageSelect(self)))

        if self.page in {"daily", "day"} and self.data.get("daily"):
            container.add_item(ui.ActionRow(_DaySelect(self)))
        elif self.page == "alerts" and len(self.data.get("alerts") or []) > 1:
            container.add_item(ui.ActionRow(_AlertSelect(self)))

        if self.candidates:
            container.add_item(ui.ActionRow(_PlaceSelect(self)))

        primary_row: ui.ActionRow[WeatherDashboard] = ui.ActionRow()

        refresh_btn = ui.Button(
            label="Refresh",
            emoji="\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}",
            style=discord.ButtonStyle.secondary,
        )
        refresh_btn.callback = self._on_refresh
        primary_row.add_item(refresh_btn)

        if self.page in {"current", "hourly", "day"}:
            anim_btn = ui.Button(
                label="Static" if self.animated else "Animate",
                emoji="\N{FRAME WITH PICTURE}" if self.animated else "\N{SPARKLES}",
                style=discord.ButtonStyle.primary if self.animated else discord.ButtonStyle.secondary,
            )
            anim_btn.callback = self._on_toggle_animate
            primary_row.add_item(anim_btn)

        loc_btn = ui.Button(
            label="Location",
            emoji="\N{ROUND PUSHPIN}",
            style=discord.ButtonStyle.secondary,
        )
        loc_btn.callback = self._on_location_modal
        primary_row.add_item(loc_btn)

        unit_cycle = {"metric": "imperial", "imperial": "standard", "standard": "metric"}[self.units.key]
        unit_btn = ui.Button(
            label=f"Units: {self.units.symbol}",
            style=discord.ButtonStyle.secondary,
        )

        async def _cycle_units(interaction: discord.Interaction, next_key: str = unit_cycle) -> None:
            await interaction.response.defer()
            self.units = UNITS[next_key]
            self._card_cache.clear()
            self.data = await self.client.bundle(self.place, self.units, self.lang)
            await self.refresh_message(interaction, deferred=True)

        unit_btn.callback = _cycle_units
        primary_row.add_item(unit_btn)
        container.add_item(primary_row)

        secondary_row: ui.ActionRow[WeatherDashboard] = ui.ActionRow()

        overview_btn = ui.Button(
            label="Overview",
            emoji="\N{MEMO}",
            style=discord.ButtonStyle.secondary,
        )
        overview_btn.callback = self._on_overview
        secondary_row.add_item(overview_btn)

        history_btn = ui.Button(
            label="Date Lookup" if self.data.get("_source") == "standard" else "History",
            emoji="\N{CALENDAR}",
            style=discord.ButtonStyle.secondary,
        )
        history_btn.callback = self._on_history
        secondary_row.add_item(history_btn)

        save_btn = ui.Button(
            label="Save Default",
            emoji="\N{WHITE MEDIUM STAR}",
            style=discord.ButtonStyle.success,
        )
        save_btn.callback = self._on_save_default
        secondary_row.add_item(save_btn)

        alerts = self.data.get("alerts") or []
        if alerts and self.page != "alerts":
            alert_btn = ui.Button(
                label=f"Alerts ({len(alerts)})",
                emoji="\N{WARNING SIGN}",
                style=discord.ButtonStyle.danger,
            )
            alert_btn.callback = self._on_jump_alerts
            secondary_row.add_item(alert_btn)

        container.add_item(secondary_row)

        source_note = "One Call 3.0" if self.data.get("_source") == "onecall" else "OpenWeather 2.5"
        page_label = PAGE_META.get(self.page, ("Day detail", "", ""))[0]
        container.add_item(ui.TextDisplay(f"-# {page_label} \N{BULLET} {self.units.label} \N{BULLET} {source_note}"))

        self.add_item(container)

    async def _on_refresh(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self._card_cache.clear()
        self.data = await self.client.bundle(self.place, self.units, self.lang, fresh=True)
        if self.page == "air" or self._air_data is not None:
            with contextlib.suppress(WeatherError):
                self._air_data = await self.client.air(self.place, fresh=True)
        await self.refresh_message(interaction, deferred=True)

    async def _on_toggle_animate(self, interaction: discord.Interaction) -> None:
        self.animated = not self.animated
        await self.refresh_message(interaction)

    async def _on_zoom_out(self, interaction: discord.Interaction) -> None:
        self.zoom = max(2, self.zoom - 1)
        await self.refresh_message(interaction)

    async def _on_zoom_in(self, interaction: discord.Interaction) -> None:
        self.zoom = min(10, self.zoom + 1)
        await self.refresh_message(interaction)

    async def _on_location_modal(self, interaction: discord.Interaction) -> None:
        modal = LocationModal(
            self.client,
            self.lang,
            self._handle_modal_places,
            default=self.place.title,
        )
        await interaction.response.send_modal(modal)

    async def _handle_modal_places(self, interaction: discord.Interaction, places: list[Place]) -> None:
        self.candidates = places if len(places) > 1 else []
        await self.switch_place(interaction, places[0], deferred=True)

    async def switch_place(self, interaction: discord.Interaction, place: Place, *, deferred: bool = False) -> None:
        if not deferred and not interaction.response.is_done():
            await interaction.response.defer()
        try:
            data = await self.client.bundle(place, self.units, self.lang)
        except WeatherError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        self.place = place
        self.data = data
        self._air_data = None
        self._card_cache.clear()
        self.alert_index = 0
        if self.page == "day":
            self.page = "daily"
            self.day_index = None
        await self.refresh_message(interaction, deferred=True)

    async def _on_overview(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            air = await self._ensure_air()
            payload = await self.client.overview(
                self.place,
                self.units,
                bundle_data=self.data,
                air_data=air,
                lang=self.lang,
            )
        except WeatherError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return

        weather = self.data["current"]["weather"][0]
        date_str = payload.get("date") or "Today"
        src = "OpenWeather AI Overview" if payload.get("_source") == "onecall" else "OpenWeather 2.5 Briefing"
        view = CardLayoutView(
            heading=f"### \N{MEMO} Weather Overview \N{EM DASH} {self.place.title}",
            body=payload.get("weather_overview") or "No overview text available.",
            footer=f"{src} \N{BULLET} {date_str} \N{BULLET} {self.units.label}",
            colour=_accent_colour(weather["id"], weather["icon"].endswith("n")),
            thumbnail_url=icon_url(weather["icon"]),
        )
        await interaction.followup.send(view=view, ephemeral=True)

    async def _on_history(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(HistoryModal(self))

    async def _on_save_default(self, interaction: discord.Interaction) -> None:
        await self.cog.bot.database.update_weather_settings(
            interaction.user.id,
            location=self.place.to_dict(),
            units=self.units.key,
            lang=self.lang,
        )
        await interaction.response.send_message(
            f"Saved **{self.place.title}** ({self.units.label}, {LANGUAGES.get(self.lang, self.lang)}) as your default weather settings.",
            ephemeral=True,
        )

    async def _on_jump_alerts(self, interaction: discord.Interaction) -> None:
        self.page = "alerts"
        await self.refresh_message(interaction)

    async def _ensure_air(self) -> dict[str, Any] | None:
        if self._air_data is None:
            try:
                self._air_data = await self.client.air(self.place)
            except WeatherError:
                return None
        return self._air_data

    async def render_active_page(self) -> discord.File | None:  # noqa: PLR0912, PLR0915
        current = self.data["current"]
        weather = current["weather"][0]
        offset = self.data.get("timezone_offset", 0)
        night = weather["icon"].endswith("n")
        colour = _accent_colour(weather["id"], night)
        thumb = icon_url(weather["icon"])
        alerts = self.data.get("alerts") or []

        if self.page == "alerts":
            if not alerts:
                note = (
                    f"No active government weather alerts for **{self.place.title}**."
                    if self.data.get("_source") == "onecall"
                    else f"No active weather alerts reported for **{self.place.title}** (government alert feeds require One Call 3.0)."
                )
                self._build_layout(
                    summary=note,
                    filename=None,
                    colour=colour,
                    thumb_url=thumb,
                )
                return None

            idx = min(self.alert_index, len(alerts) - 1)
            alert = alerts[idx]
            event = alert.get("event") or "Weather Advisory"
            sender = alert.get("sender_name") or "National Weather Service"
            start_ts = alert.get("start")
            end_ts = alert.get("end")
            desc = (alert.get("description") or "No additional details provided.").strip()
            tags = ", ".join(alert.get("tags") or [])

            meta_lines = [f"**\N{WARNING SIGN} {event} ({idx + 1}/{len(alerts)})**", f"**Issued by:** {sender}"]
            if start_ts and end_ts:
                meta_lines.append(f"**Window:** <t:{int(start_ts)}:f> \N{RIGHTWARDS ARROW} <t:{int(end_ts)}:f> (<t:{int(end_ts)}:R>)")
            if tags:
                meta_lines.append(f"**Tags:** {tags}")

            self._build_layout(
                summary="\n".join(meta_lines),
                filename=None,
                colour=discord.Colour.from_rgb(235, 85, 75),
                thumb_url=thumb,
                alert_body=desc[:3500],
            )
            return None

        cache_key = (
            self.page,
            self.place.title,
            round(self.place.lat, 3),
            round(self.place.lon, 3),
            self.units.key,
            self.day_index,
            self.map_layer,
            self.zoom,
            self.animated if self.page in {"current", "hourly", "day"} else False,
            current["dt"],
        )

        raw = self._card_cache.get(cache_key)
        ext = "gif" if (self.animated and self.page in {"current", "hourly", "day"}) else "png"
        summary = ""

        if self.page == "current":
            air = await self._ensure_air()
            aqi = air["current"]["main"]["aqi"] if air else None
            daily = self.data.get("daily") or []
            hi_lo = (daily[0]["temp"]["max"], daily[0]["temp"]["min"]) if daily else None
            hourly = self.data.get("hourly") or []
            pop = hourly[0].get("pop") if hourly else None
            moon_phase = (daily[0].get("moon_phase") if daily else None) or lunar_phase(current["dt"])
            banner = f"\N{WARNING SIGN} {len(alerts)} Alert{'s' if len(alerts) > 1 else ''}" if alerts else None

            if raw is None:
                icon_bytes = await self.client.icon(weather["icon"])
                card = await asyncio.to_thread(
                    render.current_card,
                    place=self.place.title,
                    current=current,
                    units=self.units,
                    offset=offset,
                    icon=icon_bytes,
                    hi_lo=hi_lo,
                    pop=pop,
                    aqi=aqi,
                    moon_phase=moon_phase,
                    banner=banner,
                )
                if self.animated:
                    card = await asyncio.to_thread(render.animate, card, weather["id"], night)
                self._card_cache[cache_key] = card
                raw = card

            summary_parts = [
                f"**{self.units.temp(current['temp'])}** ({weather['description'].title()}, feels like {self.units.temp(current['feels_like'])})",
            ]
            if self.data.get("minutely"):
                summary_parts.append(rain_outlook(self.data["minutely"], current["dt"], self.units))
            if alerts:
                top_event = alerts[0].get("event") or "Weather Alert"
                summary_parts.append(f"\N{WARNING SIGN} **{top_event}** active \N{EM DASH} switch to the **Alerts** view for details.")
            summary = "\n".join(summary_parts)

        elif self.page == "hourly":
            points = (self.data.get("hourly") or [])[:24]
            if not points:
                self._build_layout(
                    summary="Hourly forecast data is unavailable for this location.",
                    filename=None,
                    colour=colour,
                    thumb_url=thumb,
                )
                return None

            step = points[1]["dt"] - points[0]["dt"] if len(points) > 1 else 3600
            if raw is None:
                icons = await self.client.icons(p["weather"][0]["icon"] for p in points)
                card = await asyncio.to_thread(
                    render.hourly_card,
                    place=self.place.title,
                    points=points,
                    icons=icons,
                    units=self.units,
                    offset=offset,
                    step=step,
                )
                if self.animated:
                    card = await asyncio.to_thread(render.animate, card, weather["id"], night)
                self._card_cache[cache_key] = card
                raw = card

            temps = [p["temp"] for p in points]
            max_pop = max((p.get("pop") or 0) for p in points)
            max_wind = max((p.get("wind_speed") or 0) for p in points)
            summary = (
                f"Range **{self.units.temp(min(temps))} \N{RIGHTWARDS ARROW} {self.units.temp(max(temps))}**  \N{MIDDLE DOT}  "
                f"Peak rain chance **{max_pop * 100:.0f}%**  \N{MIDDLE DOT}  "
                f"Peak wind **{self.units.speed(max_wind)}**"
            )

        elif self.page == "daily":
            days = (self.data.get("daily") or [])[:8]
            if not days:
                self._build_layout(
                    summary="Daily forecast data is unavailable for this location.",
                    filename=None,
                    colour=colour,
                    thumb_url=thumb,
                )
                return None

            if raw is None:
                icons = await self.client.icons(d["weather"][0]["icon"] for d in days)
                raw = await asyncio.to_thread(
                    render.daily_card,
                    place=self.place.title,
                    days=days,
                    icons=icons,
                    units=self.units,
                    offset=offset,
                    today=current["dt"],
                )
                self._card_cache[cache_key] = raw

            week_lo = min(d["temp"]["min"] for d in days)
            week_hi = max(d["temp"]["max"] for d in days)
            wettest = max(days, key=lambda d: d.get("pop") or 0)
            wet_date = render.local(wettest["dt"], offset)
            summary = (
                f"{len(days)}-day range **{self.units.temp(week_lo)} \N{EM DASH} {self.units.temp(week_hi)}**  \N{MIDDLE DOT}  "
                f"Highest rain chance **{(wettest.get('pop') or 0) * 100:.0f}%** on **{wet_date:%a %d %b}**"
            )

        elif self.page == "day":
            days = self.data.get("daily") or []
            idx = min(self.day_index or 0, max(0, len(days) - 1))
            day = days[idx]
            day_weather = day["weather"][0]
            if raw is None:
                icon_bytes = await self.client.icon(day_weather["icon"])
                card = await asyncio.to_thread(
                    render.day_card,
                    place=self.place.title,
                    day=day,
                    icon=icon_bytes,
                    units=self.units,
                    offset=offset,
                )
                if self.animated:
                    card = await asyncio.to_thread(render.animate, card, day_weather["id"], False)
                self._card_cache[cache_key] = card
                raw = card

            dt_val = render.local(day["dt"], offset)
            day_summary = day.get("summary") or (
                f"{day_weather['description'].title()} with a high of {self.units.temp(day['temp']['max'])} "
                f"and low of {self.units.temp(day['temp']['min'])}."
            )
            summary = f"**{dt_val:%A, %d %B %Y}** \N{EM DASH} {day_summary}"

        elif self.page == "minutely":
            minutely = self.data.get("minutely") or []
            headline = rain_outlook(minutely, current["dt"], self.units)
            if not minutely:
                synthesized = [{"dt": current["dt"] + i * 60, "precipitation": float((current.get("rain") or {}).get("1h", 0))} for i in range(60)]
            else:
                synthesized = minutely

            if raw is None:
                raw = await asyncio.to_thread(
                    render.minutely_card,
                    place=self.place.title,
                    minutely=synthesized,
                    now=current["dt"],
                    weather=weather,
                    units=self.units,
                    headline=clip_headline(headline),
                )
                self._card_cache[cache_key] = raw

            summary = headline

        elif self.page == "air":
            air = await self._ensure_air()
            if air is None:
                self._build_layout(
                    summary="Air quality data is currently unavailable for this location.",
                    filename=None,
                    colour=colour,
                    thumb_url=thumb,
                )
                return None

            if raw is None:
                raw = await asyncio.to_thread(
                    render.air_card,
                    place=self.place.title,
                    air=air,
                    weather=weather,
                    offset=offset,
                )
                self._card_cache[cache_key] = raw

            aqi = air["current"]["main"]["aqi"]
            comp = air["current"]["components"]
            summary = (
                f"**AQI {aqi}/5 ({render.AQI_NAMES.get(aqi, 'Unknown')})**  \N{MIDDLE DOT}  "
                f"PM2.5 **{comp.get('pm2_5', 0):.1f} \N{MICRO SIGN}g/m\N{SUPERSCRIPT THREE}**  \N{MIDDLE DOT}  "
                f"PM10 **{comp.get('pm10', 0):.1f} \N{MICRO SIGN}g/m\N{SUPERSCRIPT THREE}**  \N{MIDDLE DOT}  "
                f"O\N{SUBSCRIPT THREE} **{comp.get('o3', 0):.1f} \N{MICRO SIGN}g/m\N{SUPERSCRIPT THREE}**"
            )

        filename = f"weather.{ext}"
        self._build_layout(
            summary=summary,
            filename=filename,
            colour=colour,
            thumb_url=thumb,
        )
        return discord.File(BytesIO(raw), filename=filename)  # pyright: ignore[reportArgumentType]

    async def refresh_message(self, interaction: discord.Interaction, *, deferred: bool = False) -> None:
        if not deferred and not interaction.response.is_done():
            await interaction.response.defer()
        try:
            file = await self.render_active_page()
        except WeatherError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return

        attachments = [file] if file is not None else []
        await interaction.edit_original_response(view=self, attachments=attachments)


class _UnitsSelect(ui.Select["SettingsView"]):
    def __init__(self, current_units: str) -> None:
        options = [
            discord.SelectOption(
                label=u.label,
                value=key,
                emoji="\N{THERMOMETER}",
                default=key == current_units,
            )
            for key, u in UNITS.items()
        ]
        super().__init__(placeholder="Preferred measurement units\N{HORIZONTAL ELLIPSIS}", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        chosen = self.values[0]
        self.view.settings["units"] = chosen
        await self.view.cog.bot.database.update_weather_settings(interaction.user.id, units=chosen)
        await self.view.refresh(interaction)


class _LanguageSelect(ui.Select["SettingsView"]):
    def __init__(self, current_lang: str) -> None:
        options = [
            discord.SelectOption(
                label=name,
                value=code,
                description=f"OpenWeather language code: {code}",
                default=code == current_lang,
            )
            for code, name in LANGUAGES.items()
        ]
        super().__init__(placeholder="Preferred weather language\N{HORIZONTAL ELLIPSIS}", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        chosen = self.values[0]
        self.view.settings["lang"] = chosen
        await self.view.cog.bot.database.update_weather_settings(interaction.user.id, lang=chosen)
        await self.view.refresh(interaction)


class _SettingsPlaceSelect(ui.Select["SettingsView"]):
    def __init__(self, candidates: list[Place]) -> None:
        options = [
            discord.SelectOption(
                label=place.title[:100],
                value=str(idx),
                emoji="\N{ROUND PUSHPIN}",
                description=f"{place.lat:.3f}, {place.lon:.3f}",
            )
            for idx, place in enumerate(candidates[:25])
        ]
        super().__init__(placeholder="Select which matching location to save\N{HORIZONTAL ELLIPSIS}", options=options)
        self.candidates = candidates

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        place = self.candidates[int(self.values[0])]
        self.view.candidates = []
        self.view.settings["location"] = place.to_dict()
        await self.view.cog.bot.database.update_weather_settings(interaction.user.id, location=place.to_dict())
        await self.view.refresh(interaction)


class SettingsView(ui.LayoutView):
    """Interactive Components V2 (``ui.LayoutView``) view for managing default weather location, units, and language."""

    def __init__(self, cog: Weather, user_id: int, settings: WeatherSettings) -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.settings = settings
        self.candidates: list[Place] = []
        self._rebuild()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("These weather settings belong to another user.", ephemeral=True)
            return False
        return True

    def _rebuild(self) -> None:
        self.clear_items()
        loc_dict = self.settings.get("location")
        place = Place.from_dict(loc_dict) if loc_dict else None
        units_key = self.settings.get("units", "metric")
        if units_key not in UNITS:
            units_key = "metric"
        units = UNITS[units_key]
        lang = self.settings.get("lang", "en")
        if lang not in LANGUAGES:
            lang = "en"

        container = ui.Container(accent_colour=discord.Colour.from_rgb(70, 150, 235))
        loc_text = f"**{place.title}** (`{place.lat:.3f}, {place.lon:.3f}`)" if place else "*Not set*"

        container.add_item(
            ui.TextDisplay(
                "### \N{GEAR} Weather Preferences\n"
                "Your defaults are used automatically whenever you run `/weather` without specifying a location.\n\n"
                f"\N{ROUND PUSHPIN} **Default Location:** {loc_text}\n"
                f"\N{THERMOMETER} **Units:** {units.label}\n"
                f"\N{GLOBE WITH MERIDIANS} **Language:** {LANGUAGES.get(lang, lang)} (`{lang}`)"
            )
        )
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.ActionRow(_UnitsSelect(units_key)))
        container.add_item(ui.ActionRow(_LanguageSelect(lang)))

        if self.candidates:
            container.add_item(ui.ActionRow(_SettingsPlaceSelect(self.candidates)))

        btn_row: ui.ActionRow[SettingsView] = ui.ActionRow()
        set_btn = ui.Button(
            label="Set Location",
            emoji="\N{ROUND PUSHPIN}",
            style=discord.ButtonStyle.primary,
        )
        set_btn.callback = self._on_set_location
        btn_row.add_item(set_btn)

        clear_btn = ui.Button(
            label="Clear Location",
            emoji="\N{WASTEBASKET}",
            style=discord.ButtonStyle.danger,
            disabled="location" not in self.settings,
        )
        clear_btn.callback = self._on_clear_location
        btn_row.add_item(clear_btn)

        container.add_item(btn_row)

        if self.candidates:
            container.add_item(ui.TextDisplay("-# Multiple locations matched your search \N{EM DASH} choose one from the dropdown above."))

        self.add_item(container)

    async def _on_set_location(self, interaction: discord.Interaction) -> None:
        current_loc = self.settings.get("location")
        default_text = Place.from_dict(current_loc).title if current_loc else ""
        lang = self.settings.get("lang", "en")
        await interaction.response.send_modal(LocationModal(self.cog.client, lang, self._handle_places, default=default_text))

    async def _handle_places(self, interaction: discord.Interaction, places: list[Place]) -> None:
        if len(places) == 1:
            self.candidates = []
            self.settings["location"] = places[0].to_dict()
            await self.cog.bot.database.update_weather_settings(interaction.user.id, location=places[0].to_dict())
        else:
            self.candidates = places
        await self.refresh(interaction, deferred=True)

    async def _on_clear_location(self, interaction: discord.Interaction) -> None:
        await self.cog.bot.database.remove_weather_location(interaction.user.id)
        self.settings.pop("location", None)
        self.candidates = []
        await self.refresh(interaction)

    async def refresh(self, interaction: discord.Interaction, *, deferred: bool = False) -> None:
        self._rebuild()
        if deferred or interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        else:
            await interaction.response.edit_message(view=self)


class Weather(commands.Cog, command_attrs={"hidden": True}):
    """Full-featured OpenWeather forecast, radar map, air quality, and historical weather suite."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.client = WeatherClient(bot)

    async def _user_context(
        self,
        user_id: int,
        location: str | None,
    ) -> tuple[Place, list[Place], Units, str]:
        settings = await self.bot.database.get_weather_settings(user_id)
        units = UNITS.get(settings.get("units", "metric"), UNITS["metric"])
        lang = settings.get("lang", "en")
        if lang not in LANGUAGES:
            lang = "en"

        if location and location.strip():
            places = await self.client.resolve(location, lang=lang, limit=5)
            return places[0], places, units, lang

        saved = settings.get("location")
        if saved:
            place = Place.from_dict(saved)
            return place, [place], units, lang

        msg = "You haven't set a default location yet. Provide a `<location>` or run `/weather settings` to save one."
        raise LocationNotFound(msg)

    async def _launch_dashboard(
        self,
        ctx: commands.Context[Bot],
        location: str | None,
        *,
        page: PageKey = "current",
        map_layer: str = "precipitation_new",
        zoom: int = 5,
        animated: bool = False,
    ) -> None:
        await ctx.defer()
        place, candidates, units, lang = await self._user_context(ctx.author.id, location)
        data = await self.client.bundle(place, units, lang)

        view = WeatherDashboard(
            self,
            ctx.author.id,
            place,
            units,
            lang,
            data,
            page=page,
            map_layer=map_layer,
            zoom=zoom,
            animated=animated,
            candidates=candidates,
        )
        file = await view.render_active_page()
        await ctx.typing()

        if file is not None:
            view.message = await ctx.reply(view=view, file=file)
        else:
            view.message = await ctx.reply(view=view)

    async def build_history_view(
        self,
        *,
        place: Place,
        units: Units,
        lang: str,
        target_date: date,
        timestamp: int | None,
        fallback_offset: int = 0,
    ) -> tuple[discord.File, CardLayoutView]:
        filename = "weather_history.png"
        if timestamp is not None:
            payload = await self.client.timemachine(place, timestamp, units, lang)
            offset = payload.get("timezone_offset", fallback_offset)
            point = payload["data"][0]
            weather = point["weather"][0]
            icon_bytes = await self.client.icon(weather["icon"])
            raw = await asyncio.to_thread(
                render.current_card,
                place=place.title,
                current=point,
                units=units,
                offset=offset,
                icon=icon_bytes,
                hi_lo=None,
                pop=None,
                aqi=None,
                moon_phase=None,
                banner=f"Archive \N{MIDDLE DOT} {target_date.isoformat()}",
            )
            when = render.local(point["dt"], offset)
            view = CardLayoutView(
                heading=f"### \N{CALENDAR} Historical Snapshot \N{EM DASH} {place.title}",
                body=(
                    f"**{when:%A, %d %B %Y} at {render.clock(point['dt'], offset)}**\n"
                    f"**{units.temp(point['temp'])}** ({weather['description'].title()}, feels like {units.temp(point['feels_like'])})"
                ),
                footer=f"OpenWeather Time Machine \N{BULLET} {units.label}",
                colour=_accent_colour(weather["id"], weather["icon"].endswith("n")),
                thumbnail_url=icon_url(weather["icon"]),
                filename=filename,
            )
        else:
            payload = await self.client.day_summary(place, target_date.isoformat(), units, lang)
            day_dict = from_day_summary(payload, units, fallback_offset)
            offset = day_dict.get("_offset", fallback_offset)
            weather = day_dict["weather"][0]
            icon_bytes = await self.client.icon(weather["icon"])
            raw = await asyncio.to_thread(
                render.day_card,
                place=place.title,
                day=day_dict,
                icon=icon_bytes,
                units=units,
                offset=offset,
            )
            view = CardLayoutView(
                heading=f"### \N{SPIRAL CALENDAR PAD} Daily Summary Archive \N{EM DASH} {place.title}",
                body=(
                    f"**{target_date:%A, %d %B %Y}**\n"
                    f"High **{units.temp(day_dict['temp']['max'])}**  \N{MIDDLE DOT}  "
                    f"Low **{units.temp(day_dict['temp']['min'])}**  \N{MIDDLE DOT}  "
                    f"Afternoon **{units.temp(day_dict['temp']['day'])}**"
                ),
                footer=f"OpenWeather Daily Aggregation \N{BULLET} {units.label}",
                colour=_accent_colour(weather["id"], False),
                thumbnail_url=icon_url(weather["icon"]),
                filename=filename,
            )

        return discord.File(BytesIO(raw), filename=filename), view

    @commands.group(name="weather", aliases=("w", "forecast"), invoke_without_command=True)
    async def weather(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates (uses saved default if omitted)",
            default=None,
        ),
    ) -> None:
        """View live weather conditions, forecasts, air quality, and interactive radar maps."""
        await self._launch_dashboard(ctx, location, page="current")

    @weather.command(name="hourly", aliases=("hours", "24h"))
    async def weather_hourly(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates",
            default=None,
        ),
    ) -> None:
        """View the hourly temperature curve, wind speeds, and rain probability chart."""
        await self._launch_dashboard(ctx, location, page="hourly")

    @weather.command(name="daily", aliases=("week", "7day", "days"))
    async def weather_daily(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates",
            default=None,
        ),
    ) -> None:
        """View the multi-day forecast with temperature range bars and per-day breakdown."""
        await self._launch_dashboard(ctx, location, page="daily")

    @weather.command(name="rain", aliases=("minutely", "precip", "precipitation"))
    async def weather_rain(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates",
            default=None,
        ),
    ) -> None:
        """View the next-60-minute precipitation radar bar chart."""
        await self._launch_dashboard(ctx, location, page="minutely")

    @weather.command(name="air", aliases=("aqi", "pollution"))
    async def weather_air(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates",
            default=None,
        ),
    ) -> None:
        """View the Air Quality Index gauge, 8 pollutant levels, and 5-day AQI timeline."""
        await self._launch_dashboard(ctx, location, page="air")

    @weather.command(name="alerts", aliases=("advisories", "warnings"))
    async def weather_alerts(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates",
            default=None,
        ),
    ) -> None:
        """View active government severe weather alerts for a location."""
        await self._launch_dashboard(ctx, location, page="alerts")

    @weather.command(name="animate", aliases=("gif", "live"))
    async def weather_animate(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates",
            default=None,
        ),
    ) -> None:
        """View an animated GIF weather card with particle rain, snow, lightning, stars, and mist."""
        await self._launch_dashboard(ctx, location, page="current", animated=True)

    @weather.command(name="overview", aliases=("ai", "summary"))
    async def weather_overview(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates",
            default=None,
        ),
    ) -> None:
        """Fetch the OpenWeather One Call 3.0 AI Weather Overview alongside current conditions."""
        await ctx.defer()
        place, _, units, lang = await self._user_context(ctx.author.id, location)
        overview_data, bundle_data = await asyncio.gather(
            self.client.overview(place, units),
            self.client.bundle(place, units, lang),
        )
        current = bundle_data["current"]
        weather = current["weather"][0]
        offset = bundle_data.get("timezone_offset", 0)
        daily = bundle_data.get("daily") or []
        hi_lo = (daily[0]["temp"]["max"], daily[0]["temp"]["min"]) if daily else None
        icon_bytes = await self.client.icon(weather["icon"])
        card = await asyncio.to_thread(
            render.current_card,
            place=place.title,
            current=current,
            units=units,
            offset=offset,
            icon=icon_bytes,
            hi_lo=hi_lo,
            pop=(bundle_data.get("hourly") or [{}])[0].get("pop"),
            aqi=None,
            moon_phase=daily[0].get("moon_phase") if daily else None,
            banner="AI Overview",
        )
        filename = "weather.png"
        view = CardLayoutView(
            heading=f"### \N{MEMO} AI Weather Overview \N{EM DASH} {place.title}",
            body=overview_data.get("weather_overview") or "No overview available.",
            footer=f"OpenWeather One Call 3.0 Overview \N{BULLET} {units.label}",
            colour=_accent_colour(weather["id"], weather["icon"].endswith("n")),
            thumbnail_url=icon_url(weather["icon"]),
            filename=filename,
        )
        await ctx.send(view=view, file=discord.File(BytesIO(card), filename=filename))

    @weather.command(name="history", aliases=("timemachine", "archive", "past"))
    async def weather_history(
        self,
        ctx: commands.Context[Bot],
        date: str = commands.parameter(
            description="Date in YYYY-MM-DD format (from 1979-01-01 onwards)", default=lambda _: datetime.now(UTC).strftime("%Y-%m-%d")
        ),
        time: str | None = commands.parameter(
            description="Optional 24h local time in HH:MM format (uses Time Machine if given, or Daily Summary if omitted)",
            default=None,
        ),
        *,
        location: str | None = commands.parameter(
            description="City name, postal/zip code, or lat, lon coordinates",
            default=None,
        ),
    ) -> None:
        """Look up historical or future daily weather via One Call 3.0 Time Machine & Daily Aggregation."""
        await ctx.defer()
        place, _, units, lang = await self._user_context(ctx.author.id, location)
        bundle_data = await self.client.bundle(place, units, lang)
        offset = bundle_data.get("timezone_offset", 0)
        target_date, timestamp = _parse_history_window(date, time, offset)
        file, view = await self.build_history_view(
            place=place,
            units=units,
            lang=lang,
            target_date=target_date,
            timestamp=timestamp,
            fallback_offset=offset,
        )
        await ctx.send(view=view, file=file)

    @weather.command(name="settings", aliases=("config", "preferences", "set"))
    async def weather_settings(self, ctx: commands.Context[Bot]) -> None:
        """Configure your default weather location, measurement units, and language."""
        settings = await self.bot.database.get_weather_settings(ctx.author.id)
        view = SettingsView(self, ctx.author.id, settings)
        await ctx.send(view=view, ephemeral=True)
