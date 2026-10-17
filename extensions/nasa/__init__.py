from __future__ import annotations

import asyncio
import contextlib
import datetime
import html
import io
import json
import logging
import math
import os
import re
import time
import urllib.parse
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Annotated, Any, Literal

import aiohttp
import discord
from discord.ext import commands

from core.utils.date import HumanDate
from core.utils.views import BaseLayoutView

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

NASA_API_KEY = os.getenv("NASA_API_KEY") or "DEMO_KEY"
HOURLY_BUDGET = 25 if NASA_API_KEY == "DEMO_KEY" else 900
NASA_BLUE = discord.Colour.from_rgb(11, 61, 145)
USER_AGENT = "Mozilla/5.0 (compatible; ParrotBot; +https://github.com/rtk-rnjn/Parrot)"

APOD_URL = "https://api.nasa.gov/planetary/apod"
APOD_WP_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
EARTH_URL = "https://api.nasa.gov/planetary/earth/imagery"
GIBS_WMS_URL = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
NEO_FEED_URL = "https://api.nasa.gov/neo/rest/v1/feed"
NEO_LOOKUP_URL = "https://api.nasa.gov/neo/rest/v1/neo/{}"
JPL_CAD_URL = "https://ssd-api.jpl.nasa.gov/cad.api"
JPL_SBDB_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"
MARS_URL = "https://api.nasa.gov/mars-photos/api/v1/rovers"
DONKI_URL = "https://api.nasa.gov/DONKI/{}"
DONKI_FALLBACK_URL = "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/{}"
EPIC_URL = "https://epic.gsfc.nasa.gov/api"
EPIC_FALLBACK_URL = "https://api.nasa.gov/EPIC/api"
EPIC_ARCHIVE = "https://epic.gsfc.nasa.gov/archive"
LIBRARY_URL = "https://images-api.nasa.gov/search"

APOD_FIRST = datetime.date(1995, 6, 16)
APOD_TZ = datetime.timezone(datetime.timedelta(hours=-5))
ROVERS = ("curiosity", "perseverance", "opportunity", "spirit")
LIBRARY_MEDIA = (("all", "Everything"), ("image", "Images"), ("video", "Videos"), ("audio", "Audio"))
ASSET_QUALITY = ("~orig", "~large", "~medium", "~small", "~thumb")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

DONKI_KINDS: dict[str, tuple[str, str, str, tuple[tuple[str, str], ...]]] = {
    "CME": (
        "Coronal Mass Ejection",
        "activityID",
        "startTime",
        (
            ("Catalog", "catalog"),
            ("Source location", "sourceLocation"),
            ("Active region", "activeRegionNum"),
            ("Instruments", "instruments"),
            ("Note", "note"),
        ),
    ),
    "GST": (
        "Geomagnetic Storm",
        "gstID",
        "startTime",
        (("Kp index", "allKpIndex"), ("Linked events", "linkedEvents")),
    ),
    "IPS": (
        "Interplanetary Shock",
        "activityID",
        "eventTime",
        (("Catalog", "catalog"), ("Location", "location"), ("Instruments", "instruments")),
    ),
    "FLR": (
        "Solar Flare",
        "flrID",
        "beginTime",
        (
            ("Class", "classType"),
            ("Peak", "peakTime"),
            ("End", "endTime"),
            ("Source location", "sourceLocation"),
            ("Active region", "activeRegionNum"),
            ("Instruments", "instruments"),
            ("Linked events", "linkedEvents"),
        ),
    ),
    "SEP": ("Solar Energetic Particle", "sepID", "eventTime", (("Instruments", "instruments"), ("Linked events", "linkedEvents"))),
    "MPC": ("Magnetopause Crossing", "mpcID", "eventTime", (("Instruments", "instruments"), ("Linked events", "linkedEvents"))),
    "RBE": ("Radiation Belt Enhancement", "rbeID", "eventTime", (("Instruments", "instruments"), ("Linked events", "linkedEvents"))),
    "HSS": ("High Speed Stream", "hssID", "eventTime", (("Instruments", "instruments"), ("Linked events", "linkedEvents"))),
}

DOT = " \N{MIDDLE DOT} "
SELECT_LIMIT = 25
THROTTLE = 1.0
CACHE_MAX = 256
RETRIES = 3
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class NasaError(Exception):
    def __init__(self, message: str, *, status: int | None = None, server_error: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.server_error = server_error or (status is not None and status >= 500)


@dataclass(slots=True)
class Field:
    label: str
    placeholder: str = ""
    default: str = ""
    required: bool = True
    max_length: int = 100


def clip(text: object, limit: int) -> str:
    value = "" if text is None else str(text)
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"


def clean(text: object) -> str:
    return "" if text is None else discord.utils.escape_mentions(str(text).strip())


def strip_html(text: object) -> str:
    if text is None:
        return ""
    raw = html.unescape(str(text))
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.sub(r"^\s*Explanation:\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return clean(raw)


def safe_url(value: object) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")) and len(value) <= 512:
        return value.strip().replace(" ", "%20")
    return None


def secure(value: object) -> str | None:
    url = safe_url(value)
    return url.replace("http://", "https://", 1) if url else None


def is_image_url(url: str | None) -> bool:
    if not url:
        return False
    path = urllib.parse.urlsplit(url).path.lower()
    return path.endswith(IMAGE_EXTENSIONS) or "assets.science.nasa.gov" in url or "images-assets.nasa.gov" in url


def number(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except TypeError, ValueError:
        return 0.0


def apod_today() -> datetime.date:
    return datetime.datetime.now(APOD_TZ).date()


def stamp(value: object, style: Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"] = "f") -> str:
    if not isinstance(value, str) or not value:
        return "unknown"
    try:
        moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return clean(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.UTC)
    return discord.utils.format_dt(moment, style)


def link_button(label: str, url: object, emoji: str | None = None) -> discord.ui.Button | None:
    target = safe_url(url)
    if target is None:
        return None
    return discord.ui.Button(label=label, url=target, emoji=emoji)


async def idle() -> None:
    return None


class NasaClient:
    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.cache: dict[str, tuple[float, Any]] = {}
        self.stale_cache: dict[str, Any] = {}
        self.inflight: dict[str, asyncio.Task[Any]] = {}
        self.semaphore = asyncio.Semaphore(4)
        self.window: deque[float] = deque()
        self.blocked_until = 0.0
        self.remaining: int | None = None

    async def start(self) -> None:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10, connect=4),
                headers={"User-Agent": USER_AGENT},
            )

    async def close(self) -> None:
        if self.session is not None and not self.session.closed:
            await self.session.close()

    def reserve(self) -> None:
        now = time.monotonic()
        if now < self.blocked_until:
            minutes = math.ceil((self.blocked_until - now) / 60)
            msg = f"NASA's rate limit was reached. Try again in about {minutes} minute(s)."
            raise NasaError(msg, status=429)
        while self.window and now - self.window[0] > 3600:
            self.window.popleft()
        if len(self.window) >= HOURLY_BUDGET:
            minutes = math.ceil((3600 - (now - self.window[0])) / 60)
            msg = f"The hourly NASA request budget is used up. Try again in about {minutes} minute(s)."
            raise NasaError(msg, status=429)
        self.window.append(now)

    def track(self, response: aiohttp.ClientResponse) -> None:
        value = response.headers.get("X-RateLimit-Remaining")
        if value is not None and value.isdigit():
            self.remaining = int(value)

    def block(self, response: aiohttp.ClientResponse) -> None:
        retry = response.headers.get("Retry-After", "")
        self.blocked_until = time.monotonic() + (int(retry) if retry.isdigit() else 900)

    async def explain(self, response: aiohttp.ClientResponse) -> str:
        if response.status in (401, 403):
            return "NASA rejected the API key."
        try:
            data = await response.json(content_type=None)
        except aiohttp.ClientError, ValueError:
            data = None
        if isinstance(data, dict):
            error = data.get("error")
            for candidate in (data.get("msg"), error.get("message") if isinstance(error, dict) else error, data.get("message")):
                if isinstance(candidate, str) and candidate:
                    return clip(clean(candidate), 300)
        if response.status == 404:
            return "NASA couldn't find any data for that request (HTTP 404)."
        return f"NASA rejected the request (HTTP {response.status})."

    async def read(self, response: aiohttp.ClientResponse, raw: bool) -> Any:
        if raw:
            if response.content_length is not None and response.content_length > MAX_IMAGE_BYTES:
                msg = "NASA sent a file that is too large."
                raise NasaError(msg)
            payload = await response.read()
            if len(payload) > MAX_IMAGE_BYTES:
                msg = "NASA sent a file that is too large."
                raise NasaError(msg)
            return payload
        text = await response.text()
        if not text.strip():
            return None
        try:
            return json.loads(text)
        except ValueError:
            msg = "NASA sent an unreadable response."
            raise NasaError(msg, server_error=True) from None

    async def fetch(self, url: str, params: dict[str, Any], auth: bool, raw: bool = False) -> Any:
        if self.session is None or self.session.closed:
            await self.start()
        assert self.session is not None
        query = {key: str(value) for key, value in params.items() if value is not None}
        if auth:
            self.reserve()
            query["api_key"] = NASA_API_KEY
        failure = "Bot couldn't reach NASA right now."
        last_status: int | None = None
        for attempt in range(RETRIES):
            try:
                async with self.semaphore, self.session.get(url, params=query or None) as response:
                    self.track(response)
                    status = response.status
                    last_status = status
                    if status == 200:
                        return await self.read(response, raw)
                    if status == 429:
                        self.block(response)
                        msg = "NASA's rate limit was reached. Please try again in a while."
                        raise NasaError(msg, status=429)
                    if status < 500:
                        raise NasaError(await self.explain(response), status=status)
                    failure = f"NASA is having problems right now (HTTP {status})."
            except aiohttp.ClientError, TimeoutError:
                failure = "Bot couldn't reach NASA right now."
            if attempt < RETRIES - 1:
                await asyncio.sleep(0.4 * (2**attempt))
        raise NasaError(failure, status=last_status, server_error=True)

    def store(self, key: str, data: Any, ttl: float, auth: bool) -> None:
        if auth and self.remaining is not None and self.remaining < 50:
            ttl *= 4
        if len(self.cache) >= CACHE_MAX:
            now = time.monotonic()
            for stale in [name for name, (expires, _) in self.cache.items() if expires <= now]:
                del self.cache[stale]
            while len(self.cache) >= CACHE_MAX:
                self.cache.pop(next(iter(self.cache)))
        while len(self.stale_cache) >= CACHE_MAX * 2:
            self.stale_cache.pop(next(iter(self.stale_cache)))
        self.cache[key] = (time.monotonic() + ttl, data)
        self.stale_cache[key] = data

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        ttl: float = 300.0,
        auth: bool = True,
        raw: bool = False,
    ) -> Any:
        params = params or {}
        if raw:
            return await self.fetch(url, params, auth, raw=True)

        key = f"{url}?{sorted(params.items())}"
        hit = self.cache.get(key)
        if hit is not None and hit[0] > time.monotonic():
            return hit[1]

        task = self.inflight.get(key)
        if task is None:
            task = asyncio.create_task(self.fetch(url, params, auth))
            self.inflight[key] = task
            task.add_done_callback(lambda _task, name=key: self.inflight.pop(name, None))

        try:
            data = await asyncio.shield(task)
        except NasaError as exc:
            if (exc.server_error or exc.status == 429) and key in self.stale_cache:
                _log.warning("Serving stale cache for %s after error: %s", url, exc)
                return self.stale_cache[key]
            raise

        if ttl > 0:
            self.store(key, data, ttl, auth)
        return data


class PromptModal(discord.ui.Modal):
    def __init__(
        self,
        title: str,
        fields: list[Field],
        submit: Callable[[discord.Interaction, list[str]], Awaitable[None]],
    ) -> None:
        super().__init__(title=title[:45], timeout=300)
        self.submit = submit
        self.inputs = [
            discord.ui.TextInput(
                label=field.label[:45],
                placeholder=field.placeholder or None,
                default=field.default or None,
                required=field.required,
                max_length=field.max_length,
            )
            for field in fields
        ]
        for item in self.inputs:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.submit(interaction, [item.value.strip() for item in self.inputs])

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, discord.NotFound) and error.code == 10062:
            _log.warning("NASA modal interaction expired before acknowledgement (10062)")
            return
        _log.error("NASA modal failed", exc_info=error)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("Something went wrong.", ephemeral=True)
            else:
                await interaction.followup.send("Something went wrong.", ephemeral=True)
        except discord.HTTPException:
            pass


class Page:
    label = ""
    emoji: str | None = None

    def __init__(self, client: NasaClient) -> None:
        self.client = client
        self.loaded = False
        self.view: NasaLayout
        self.index = 0

    async def load(self) -> None:
        if not self.loaded:
            await self.refresh()
            self.loaded = True

    async def refresh(self) -> None:
        return None

    async def changed(self) -> None:
        return None

    def build(self) -> list[discord.ui.Item]:
        raise NotImplementedError


class NasaLayout(BaseLayoutView):
    def __init__(self, ctx: commands.Context[Bot], pages: dict[str, Page], start: str) -> None:
        super().__init__(ctx.author, timeout=300)
        self.bot = ctx.bot
        self.user_id = ctx.author.id
        self.pages = pages
        self.tab = start
        self.notice: str | None = None
        self.last = 0.0
        self.lock = asyncio.Lock()
        self.message: discord.Message | None = None
        for page in pages.values():
            page.view = self
        self.container = discord.ui.Container(accent_colour=NASA_BLUE)
        self.add_item(self.container)

    async def parse_date(self, text: str, *, prefer: str = "current") -> datetime.date:
        reminder = self.bot.reminder
        tzinfo = await reminder.get_tzinfo(self.user_id) if reminder is not None else datetime.UTC
        try:
            return HumanDate(text, now=discord.utils.utcnow(), tzinfo=tzinfo, prefer=prefer).date  # type: ignore[arg-type]
        except commands.BadArgument as exc:
            raise NasaError(str(exc)) from None

    async def _ack(self, interaction: discord.Interaction) -> bool:
        if interaction.response.is_done():
            return True
        try:
            await interaction.response.defer()
            return True
        except discord.NotFound:
            _log.warning("Interaction expired before defer (10062); falling back to direct message edit")
            return False
        except discord.HTTPException:
            return interaction.response.is_done()

    async def _update_view(self, interaction: discord.Interaction, acked: bool) -> None:
        if self.message is None and interaction.message is not None:
            self.message = interaction.message
        if acked and interaction.type is discord.InteractionType.component:
            try:
                await interaction.edit_original_response(view=self)
                return
            except discord.HTTPException:
                pass
        if self.message is not None:
            try:
                await self.message.edit(view=self)
                return
            except discord.HTTPException:
                pass
        if acked:
            try:
                await interaction.edit_original_response(view=self)
                return
            except discord.HTTPException:
                _log.exception("NASA view could not be updated")
                with contextlib.suppress(discord.HTTPException):
                    await interaction.followup.send("Bot couldn't display that result.", ephemeral=True)

    async def run(self, interaction: discord.Interaction, action: Callable[[], Awaitable[None]]) -> None:
        now = time.monotonic()
        if now - self.last < THROTTLE:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Easy there, give it a second.", ephemeral=True)
            except discord.HTTPException:
                pass
            return
        self.last = now
        acked = await self._ack(interaction)
        async with self.lock:
            self.notice = None
            try:
                await action()
            except NasaError as exc:
                self.notice = str(exc)
            except Exception:
                _log.exception("NASA view action failed")
                self.notice = "Something went wrong while talking to NASA."
            self.render()
            await self._update_view(interaction, acked)

    async def switch(self, key: str) -> None:
        await self.pages[key].load()
        self.tab = key

    def button(
        self,
        label: str,
        action: Callable[[], Awaitable[None]],
        *,
        emoji: str | None = None,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        disabled: bool = False,
    ) -> discord.ui.Button:
        button = discord.ui.Button(label=label, emoji=emoji, style=style, disabled=disabled)

        async def callback(interaction: discord.Interaction) -> None:
            await self.run(interaction, action)

        button.callback = callback
        return button

    def select(
        self,
        placeholder: str,
        options: list[discord.SelectOption],
        handler: Callable[[str], Awaitable[None]],
    ) -> discord.ui.Select:
        select = discord.ui.Select(placeholder=placeholder, options=options)

        async def callback(interaction: discord.Interaction) -> None:
            await self.run(interaction, lambda: handler(select.values[0]))

        select.callback = callback
        return select

    def modal_button(
        self,
        label: str,
        title: str,
        fields: list[Field],
        handler: Callable[[list[str]], Awaitable[None]],
        *,
        emoji: str | None = None,
    ) -> discord.ui.Button:
        button = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.secondary)

        async def submitted(interaction: discord.Interaction, values: list[str]) -> None:
            await self.run(interaction, lambda: handler(values))

        async def callback(interaction: discord.Interaction) -> None:
            if interaction.message is not None and self.message is None:
                self.message = interaction.message
            with contextlib.suppress(discord.HTTPException):
                await interaction.response.send_modal(PromptModal(title, fields, submitted))

        button.callback = callback
        return button

    def render(self) -> None:
        self.container.clear_items()
        if len(self.pages) > 1:
            tabs = []
            for key, page in self.pages.items():
                active = key == self.tab
                tabs.append(
                    self.button(
                        page.label,
                        partial(self.switch, key),
                        emoji=page.emoji,
                        style=discord.ButtonStyle.primary if active else discord.ButtonStyle.secondary,
                        disabled=active,
                    )
                )
            self.container.add_item(discord.ui.ActionRow(*tabs))
            self.container.add_item(discord.ui.Separator())
        for item in self.pages[self.tab].build():
            self.container.add_item(item)
        if self.notice:
            self.container.add_item(discord.ui.Separator())
            self.container.add_item(discord.ui.TextDisplay(f"-# \N{WARNING SIGN}\N{VARIATION SELECTOR-16} {clip(self.notice, 300)}"))


def browse_rows(view: NasaLayout, page: Page, labels: list[tuple[str, str]], placeholder: str) -> list[discord.ui.Item]:
    total = len(labels)
    page.index = min(max(page.index, 0), max(total - 1, 0))
    first = (page.index // SELECT_LIMIT) * SELECT_LIMIT
    last = min(first + SELECT_LIMIT, total)
    options = [
        discord.SelectOption(
            label=clip(labels[i][0] or "Untitled", 100),
            value=str(i),
            description=clip(labels[i][1], 100) or None,
            default=i == page.index,
        )
        for i in range(first, last)
    ]
    hint = f"{placeholder} ({first + 1}\N{EN DASH}{last} of {total})" if total > SELECT_LIMIT else placeholder

    async def pick(value: str) -> None:
        page.index = int(value)
        await page.changed()

    async def step(delta: int) -> None:
        page.index = min(max(page.index + delta, 0), total - 1)
        await page.changed()

    return [
        discord.ui.ActionRow(view.select(hint, options, pick)),
        discord.ui.ActionRow(
            view.button("Previous", partial(step, -1), emoji="\N{BLACK LEFT-POINTING TRIANGLE}", disabled=page.index == 0),
            view.button(f"{page.index + 1} / {total}", idle, disabled=True),
            view.button("Next", partial(step, 1), emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", disabled=page.index >= total - 1),
        ),
    ]


def apod_image_url(entry: dict[str, Any]) -> str | None:
    media_type = str(entry.get("media_type") or "image").lower()
    url = secure(entry.get("url"))
    hdurl = secure(entry.get("hdurl"))
    thumb = secure(entry.get("thumbnail_url"))
    permalink = secure(entry.get("permalink"))
    if media_type == "image":
        if url and url != permalink and is_image_url(url):
            return url
        if hdurl and is_image_url(hdurl):
            return hdurl
        return hdurl or (url if url != permalink else None) or thumb
    return thumb or (hdurl if is_image_url(hdurl) else None)


def apod_items(entry: dict[str, Any]) -> list[discord.ui.Item]:
    title = clip(strip_html(entry.get("title")), 200) or "Untitled"
    link = secure(entry.get("permalink")) or secure(entry.get("hdurl")) or secure(entry.get("url"))
    heading = f"### [{title}]({link})" if link else f"### {title}"
    meta = [str(entry.get("date", ""))]
    credit = strip_html(entry.get("copyright") or entry.get("credit"))
    if credit:
        credit = re.sub(r"^(?:Image\s+Credit\s*(?:&\s*Copyright)?|Copyright)\s*:\s*", "", credit, flags=re.IGNORECASE)
        if credit:
            meta.append(f"\N{COPYRIGHT SIGN} {credit.replace(chr(10), ' ')}")
    explanation = strip_html(entry.get("explanation")) or "No explanation available."
    items: list[discord.ui.Item] = [
        discord.ui.TextDisplay(f"## \N{MILKY WAY} Astronomy Picture of the Day\n{heading}\n-# {DOT.join(part for part in meta if part)}"),
        discord.ui.TextDisplay(clip(explanation, 1800)),
    ]
    image = apod_image_url(entry)
    if image:
        items.append(discord.ui.MediaGallery(discord.MediaGalleryItem(image, description=clip(title, 100) or None)))
    return items


def apod_link(entry: dict[str, Any]) -> discord.ui.Button | None:
    if str(entry.get("media_type") or "image").lower() == "image":
        return link_button("Open HD image", entry.get("hdurl") or apod_image_url(entry) or entry.get("url"), "\N{FRAME WITH PICTURE}")
    return link_button("Watch video", entry.get("url") or entry.get("permalink"), "\N{MOVIE CAMERA}")


def apod_layout(entry: dict[str, Any]) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=None)
    items = apod_items(entry)
    button = apod_link(entry)
    if button is not None:
        items.append(discord.ui.ActionRow(button))
    view.add_item(discord.ui.Container(*items, accent_colour=NASA_BLUE))
    return view


class ApodPage(Page):
    label = "APOD"
    emoji = "\N{MILKY WAY}"

    def __init__(self, client: NasaClient) -> None:
        super().__init__(client)
        self.date: datetime.date | None = None
        self.entry: dict[str, Any] | None = None

    async def refresh(self) -> None:
        await self.fetch(self.date)

    async def _request_apod(self, params: dict[str, Any], ttl: float) -> dict[str, Any]:
        last_err: NasaError | None = None
        for url, auth in ((APOD_URL, True), (APOD_WP_URL, False)):
            query = dict(params)
            if url == APOD_WP_URL:
                query.pop("thumbs", None)
            try:
                data = await self.client.get(url, query, ttl=ttl, auth=auth)
            except NasaError as exc:
                last_err = exc
                continue
            entry = data[0] if isinstance(data, list) and data else data
            if isinstance(entry, dict) and "title" in entry:
                return entry
        raise last_err or NasaError("NASA sent an unexpected APOD response.")

    async def _library_fallback(self, date: datetime.date | None) -> dict[str, Any]:
        data = await self.client.get(
            LIBRARY_URL,
            {"q": "Hubble Space Telescope nebula galaxy", "media_type": "image", "page_size": 25},
            auth=False,
            ttl=3600.0,
        )
        items = ((data.get("collection") or {}).get("items") or []) if isinstance(data, dict) else []
        valid = [item for item in items if isinstance(item, dict) and item.get("data") and item.get("links")]
        if not valid:
            msg = "NASA's APOD service is currently unavailable (HTTP 500)."
            raise NasaError(msg)
        chosen = valid[int(time.time()) % len(valid)]
        meta = chosen["data"][0]
        image = secure(chosen["links"][0].get("href"))
        return {
            "title": meta.get("title") or "NASA Featured Astronomy Image",
            "date": (date or apod_today()).isoformat(),
            "explanation": meta.get("description") or "Retrieved from the NASA Image Library while APOD is undergoing maintenance.",
            "media_type": "image",
            "url": image,
            "hdurl": image,
            "copyright": meta.get("center") or "NASA",
        }

    async def fetch(self, date: datetime.date | None, *, random: bool = False) -> None:
        today_et = apod_today()
        target = min(date, today_et) if date is not None else None
        params: dict[str, Any] = {"thumbs": "true"}
        ttl = 1800.0
        if random:
            params["count"] = 1
            ttl = 0.0
        elif target is not None:
            params["date"] = target.isoformat()
            ttl = 86400.0

        try:
            entry = await self._request_apod(params, ttl)
        except NasaError as exc:
            if not random and (exc.status == 404 or exc.server_error):
                fallback_date = (target or today_et) - datetime.timedelta(days=1)
                try:
                    entry = await self._request_apod({"date": fallback_date.isoformat(), "thumbs": "true"}, 3600.0)
                    target = fallback_date
                except NasaError as retry_exc:
                    if retry_exc.server_error:
                        entry = await self._library_fallback(target)
                    else:
                        raise
            elif exc.server_error:
                entry = await self._library_fallback(target)
            else:
                raise

        self.entry = entry
        self.date = target

    async def pick(self, values: list[str]) -> None:
        date = await self.view.parse_date(values[0], prefer="past")
        if date < APOD_FIRST:
            msg = f"APOD starts on {APOD_FIRST.isoformat()}."
            raise NasaError(msg)
        if date > discord.utils.utcnow().date() + datetime.timedelta(days=1):
            msg = "That date is in the future."
            raise NasaError(msg)
        await self.fetch(date)

    async def random(self) -> None:
        await self.fetch(None, random=True)

    async def today(self) -> None:
        await self.fetch(None)

    def build(self) -> list[discord.ui.Item]:
        assert self.entry is not None
        view = self.view
        buttons: list[discord.ui.Button] = [
            view.modal_button(
                "Pick date",
                "Pick an APOD date",
                [Field("Date", "e.g. 2004-03-23 or 23 March 2004", default=self.date.isoformat() if self.date else "", max_length=40)],
                self.pick,
                emoji="\N{CALENDAR}",
            ),
            view.button("Random", self.random, emoji="\N{GAME DIE}"),
            view.button("Today", self.today, emoji="\N{SUN WITH FACE}"),
        ]
        extra = apod_link(self.entry)
        if extra is not None:
            buttons.append(extra)
        return [*apod_items(self.entry), discord.ui.ActionRow(*buttons)]


class EpicPage(Page):
    label = "EPIC"
    emoji = "\N{EARTH GLOBE EUROPE-AFRICA}"

    def __init__(self, client: NasaClient) -> None:
        super().__init__(client)
        self.date: datetime.date | None = None
        self.collection = "natural"
        self.images: list[dict[str, Any]] = []
        self.index = 0

    async def refresh(self) -> None:
        await self.fetch(self.date, self.collection)

    async def fetch(self, date: datetime.date | None, collection: str) -> None:
        suffix = f"/{collection}" + (f"/date/{date.isoformat()}" if date else "")
        ttl = 1800.0 if date is None else 21600.0
        data: Any = None
        last_err: NasaError | None = None
        for base, auth in ((EPIC_URL, False), (EPIC_FALLBACK_URL, True)):
            try:
                data = await self.client.get(f"{base}{suffix}", auth=auth, ttl=ttl)
                last_err = None
                break
            except NasaError as exc:
                if exc.status == 404:
                    data = []
                    last_err = None
                    break
                last_err = exc

        if last_err is not None and not last_err.server_error:
            raise last_err

        entries = data if isinstance(data, list) else []
        self.images = [entry for entry in entries if isinstance(entry, dict) and (entry.get("image") or entry.get("url")) and entry.get("date")]
        self.date = date
        self.collection = collection
        self.index = 0

    def archive(self, entry: dict[str, Any], extension: str) -> str:
        if entry.get("url"):
            return str(entry["url"])
        day = str(entry["date"])[:10].replace("-", "/")
        return f"{EPIC_ARCHIVE}/{self.collection}/{day}/{extension}/{entry['image']}.{extension}"

    async def swap(self, value: str) -> None:
        await self.fetch(self.date, value)

    async def latest(self) -> None:
        await self.fetch(None, self.collection)

    async def pick(self, values: list[str]) -> None:
        date = await self.view.parse_date(values[0], prefer="past")
        if date > discord.utils.utcnow().date():
            msg = "That date is in the future."
            raise NasaError(msg)
        await self.fetch(date, self.collection)

    def build(self) -> list[discord.ui.Item]:
        view = self.view
        collection = view.select(
            "Image collection",
            [
                discord.SelectOption(label="Natural color", value="natural", default=self.collection == "natural"),
                discord.SelectOption(label="Enhanced color", value="enhanced", default=self.collection == "enhanced"),
            ],
            self.swap,
        )
        buttons = [
            view.modal_button(
                "Pick date",
                "EPIC imagery by date",
                [Field("Date", "e.g. 2024-03-23 or 23 March 2024", default=self.date.isoformat() if self.date else "", max_length=40)],
                self.pick,
                emoji="\N{CALENDAR}",
            ),
            view.button("Latest", self.latest, emoji="\N{SUN WITH FACE}"),
        ]
        if not self.images:
            when = self.date.isoformat() if self.date else "the latest day"
            return [
                discord.ui.TextDisplay(
                    f"## \N{EARTH GLOBE EUROPE-AFRICA} Earth from DSCOVR\nNo {self.collection} imagery for {when}. Try another date or collection."
                ),
                discord.ui.ActionRow(collection),
                discord.ui.ActionRow(*buttons),
            ]

        entry = self.images[self.index]
        coords = entry.get("centroid_coordinates") or {}
        position = f"lat {number(coords.get('lat')):.2f}, lon {number(coords.get('lon')):.2f}"
        caption = clip(clean(entry.get("caption")), 200) or "Earth from DSCOVR EPIC"
        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay(
                f"## \N{EARTH GLOBE EUROPE-AFRICA} Earth from DSCOVR\n### {caption}\n-# {entry['date']} UTC{DOT}{self.collection.title()}{DOT}{position}"
            ),
            discord.ui.MediaGallery(discord.MediaGalleryItem(self.archive(entry, "jpg"), description=clip(caption, 100) or None)),
        ]
        full = link_button("Full resolution", self.archive(entry, "png"), "\N{FRAME WITH PICTURE}")
        if full is not None:
            buttons.append(full)
        labels = [(f"{str(item['date'])[11:16] or str(item['date'])[:10]} UTC", str(item.get("image") or "EPIC")) for item in self.images]
        items += browse_rows(view, self, labels, "Pick a time")
        items += [discord.ui.ActionRow(collection), discord.ui.ActionRow(*buttons)]
        return items


class MarsPage(Page):
    label = "Mars"
    emoji = "\N{ROBOT FACE}"

    def __init__(self, client: NasaClient) -> None:
        super().__init__(client)
        self.rover = "curiosity"
        self.date: datetime.date | None = None
        self.photos: list[dict[str, Any]] = []
        self.index = 0

    async def refresh(self) -> None:
        await self.fetch(self.rover, self.date)

    async def _fetch_library_mars(self, rover: str, date: datetime.date | None) -> list[dict[str, Any]]:
        query = f"{rover} mars rover"
        params: dict[str, Any] = {"q": query, "media_type": "image", "page_size": 50}
        if date is not None:
            params["year_start"] = date.year
            params["year_end"] = date.year
        data = await self.client.get(LIBRARY_URL, params, auth=False, ttl=3600.0)
        items = ((data.get("collection") or {}).get("items") or []) if isinstance(data, dict) else []
        status = "active" if rover in ("curiosity", "perseverance") else "complete"
        target_prefix = date.isoformat() if date is not None else None
        results: list[dict[str, Any]] = []
        fallback_results: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict) or not item.get("data") or not item.get("links"):
                continue
            meta = item["data"][0]
            href = secure(item["links"][0].get("href"))
            if not href:
                continue
            created = str(meta.get("date_created") or "")[:10]
            photo = {
                "img_src": href,
                "earth_date": created or (date.isoformat() if date else "Archive"),
                "sol": meta.get("nasa_id") or "NASA",
                "camera": {"full_name": strip_html(meta.get("title")) or f"{rover.title()} Camera"},
                "rover": {"status": status},
            }
            if target_prefix is None or created == target_prefix:
                results.append(photo)
            else:
                fallback_results.append(photo)
        return (results or fallback_results)[:100]

    async def fetch(self, rover: str, date: datetime.date | None) -> None:
        if date is None:
            url, params, key, ttl = f"{MARS_URL}/{rover}/latest_photos", {}, "latest_photos", 1800.0
        else:
            url, params, key, ttl = f"{MARS_URL}/{rover}/photos", {"earth_date": date.isoformat()}, "photos", 21600.0
        photos: list[dict[str, Any]] = []
        try:
            data = await self.client.get(url, params, ttl=ttl)
            raw_photos = data.get(key) if isinstance(data, dict) else None
            photos = [photo for photo in raw_photos or [] if isinstance(photo, dict) and secure(photo.get("img_src"))][:100]
        except NasaError as exc:
            if exc.status == 404 or exc.server_error:
                photos = await self._fetch_library_mars(rover, date)
            else:
                raise
        self.photos = photos
        self.rover = rover
        self.date = date
        self.index = 0

    async def swap(self, value: str) -> None:
        await self.fetch(value, self.date)

    async def latest(self) -> None:
        await self.fetch(self.rover, None)

    async def pick(self, values: list[str]) -> None:
        date = await self.view.parse_date(values[0], prefer="past")
        await self.fetch(self.rover, date)

    def build(self) -> list[discord.ui.Item]:
        view = self.view
        rover = self.rover.title()
        rovers = view.select(
            "Rover",
            [discord.SelectOption(label=name.title(), value=name, default=name == self.rover) for name in ROVERS],
            self.swap,
        )
        buttons = [
            view.modal_button(
                "Pick date",
                "Mars photos by Earth date",
                [Field("Earth date", "e.g. 2024-03-23 or 23 March 2024", default=self.date.isoformat() if self.date else "", max_length=40)],
                self.pick,
                emoji="\N{CALENDAR}",
            ),
            view.button("Latest", self.latest, emoji="\N{SUN WITH FACE}"),
        ]
        if not self.photos:
            when = self.date.isoformat() if self.date else "the latest sol"
            return [
                discord.ui.TextDisplay(f"## \N{ROBOT FACE} Mars rover photos\nNo photos from **{rover}** for {when}. Try another date or rover."),
                discord.ui.ActionRow(rovers),
                discord.ui.ActionRow(*buttons),
            ]

        photo = self.photos[self.index]
        camera = clean((photo.get("camera") or {}).get("full_name")) or "Unknown camera"
        status = clean((photo.get("rover") or {}).get("status")).title()
        image = secure(photo.get("img_src")) or ""
        sol_value = photo.get("sol")
        sol_label = f"Sol {sol_value}" if str(sol_value).isdigit() else f"ID {clean(sol_value)}"
        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay(
                f"## \N{ROBOT FACE} Mars rover photos\n### {rover}{DOT}{clip(camera, 200)}\n-# {sol_label}{DOT}{photo.get('earth_date')}{DOT}{status}"
            ),
            discord.ui.MediaGallery(discord.MediaGalleryItem(image, description=clip(camera, 100))),
        ]
        full = link_button("Full size", image, "\N{FRAME WITH PICTURE}")
        if full is not None:
            buttons.append(full)
        labels = [
            (
                clean((item.get("camera") or {}).get("full_name")) or "Photo",
                f"{'Sol' if str(item.get('sol')).isdigit() else 'ID'} {item.get('sol')}{DOT}{item.get('earth_date')}",
            )
            for item in self.photos
        ]
        items += browse_rows(view, self, labels, "Pick a photo")
        items += [discord.ui.ActionRow(rovers), discord.ui.ActionRow(*buttons)]
        return items


def approach(rock: dict[str, Any]) -> dict[str, Any]:
    entries = [entry for entry in rock.get("close_approach_data") or [] if isinstance(entry, dict)]
    if not entries:
        return {}
    now = time.time() * 1000
    return min(entries, key=lambda entry: abs(number(entry.get("epoch_date_close_approach")) - now))


class AsteroidPage(Page):
    label = "Asteroids"
    emoji = "\N{COMET}"

    def __init__(self, client: NasaClient) -> None:
        super().__init__(client)
        self.start = self.end = discord.utils.utcnow().date()
        self.rocks: list[dict[str, Any]] = []
        self.index = 0
        self.lookup = False

    async def refresh(self) -> None:
        await self.feed(self.start, self.end)

    async def _cad_fallback(self, start: datetime.date, end: datetime.date) -> list[dict[str, Any]]:
        params = {
            "date-min": start.isoformat(),
            "date-max": (end + datetime.timedelta(days=1)).isoformat(),
            "dist-max": "0.5",
            "diameter": "true",
            "fullname": "true",
            "sort": "date",
        }
        data = await self.client.get(JPL_CAD_URL, params, auth=False, ttl=3600.0)
        if not isinstance(data, dict):
            msg = "NASA sent an unexpected asteroid response."
            raise NasaError(msg)
        fields = data.get("fields") or []
        rows = data.get("data") or []
        rocks: list[dict[str, Any]] = []
        for idx, row in enumerate(rows[:100]):
            if not isinstance(row, list):
                continue
            record = dict(zip(fields, row, strict=False))
            des = str(record.get("des") or "")
            fullname = str(record.get("fullname") or des).strip()
            dist_au = number(record.get("dist"))
            dist_km = dist_au * 149_597_870.7
            dist_ld = dist_km / 384_400.0
            v_kmh = number(record.get("v_rel")) * 3600.0
            h_val = number(record.get("h"))
            diam_km = number(record.get("diameter"))
            if diam_km > 0:
                d_min = diam_km * 1000 * 0.9
                d_max = diam_km * 1000 * 1.1
            elif h_val > 0:
                d_min = 1329.0 / math.sqrt(0.25) * (10 ** (-0.2 * h_val)) * 1000
                d_max = 1329.0 / math.sqrt(0.05) * (10 ** (-0.2 * h_val)) * 1000
            else:
                d_min = d_max = 0.0
            cd = str(record.get("cd") or "unknown")
            rocks.append(
                {
                    "name": fullname,
                    "neo_reference_id": des,
                    "nasa_jpl_url": f"https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={urllib.parse.quote(des)}",
                    "absolute_magnitude_h": record.get("h") or "unknown",
                    "is_potentially_hazardous_asteroid": dist_au <= 0.05 and 0 < h_val <= 22.0,
                    "is_sentry_object": False,
                    "estimated_diameter": {"meters": {"estimated_diameter_min": d_min, "estimated_diameter_max": d_max}},
                    "close_approach_data": [
                        {
                            "close_approach_date_full": cd,
                            "close_approach_date": cd[:11],
                            "epoch_date_close_approach": idx,
                            "relative_velocity": {"kilometers_per_hour": str(v_kmh)},
                            "miss_distance": {"kilometers": str(dist_km), "lunar": str(dist_ld)},
                            "orbiting_body": "Earth",
                        }
                    ],
                }
            )
        return rocks

    async def feed(self, start: datetime.date, end: datetime.date) -> None:
        if end < start:
            msg = "The end date comes before the start date."
            raise NasaError(msg)
        if (end - start).days > 6:
            msg = "NASA only allows up to 7 days at a time."
            raise NasaError(msg)
        try:
            data = await self.client.get(NEO_FEED_URL, {"start_date": start.isoformat(), "end_date": end.isoformat()}, ttl=3600.0)
            days = data.get("near_earth_objects") if isinstance(data, dict) else None
            if days is None:
                msg = "NASA sent an unexpected asteroid response."
                raise NasaError(msg, server_error=True)
            rocks = [rock for day in sorted(days or {}) for rock in days[day] if isinstance(rock, dict)]
            rocks.sort(key=lambda rock: number(approach(rock).get("epoch_date_close_approach")))
            self.rocks = rocks[:100]
        except NasaError as exc:
            if exc.server_error or exc.status in (404, 429):
                self.rocks = await self._cad_fallback(start, end)
            else:
                raise
        self.start, self.end = start, end
        self.index = 0
        self.lookup = False

    async def span(self, values: list[str]) -> None:
        start = await self.view.parse_date(values[0])
        end = await self.view.parse_date(values[1]) if values[1] else start
        await self.feed(start, end)

    async def find(self, values: list[str]) -> None:
        ident = values[0]
        if not ident.isdigit():
            msg = "Asteroid IDs are numbers, like `3542519`."
            raise NasaError(msg)
        try:
            data = await self.client.get(NEO_LOOKUP_URL.format(ident), ttl=21600.0)
        except NasaError as exc:
            if exc.status == 404:
                msg_0 = "NASA doesn't know that asteroid."
                raise NasaError(msg_0) from None
            raise
        if not isinstance(data, dict) or "name" not in data:
            msg = "NASA doesn't know that asteroid."
            raise NasaError(msg)
        self.rocks = [data]
        self.index = 0
        self.lookup = True

    def build(self) -> list[discord.ui.Item]:
        view = self.view
        buttons: list[discord.ui.Button] = [
            view.modal_button(
                "Date range",
                "Asteroids by date range",
                [
                    Field("Start date", "e.g. 2024-03-23 or today", default=self.start.isoformat(), max_length=40),
                    Field("End date (max 7 days)", "leave empty for one day", default=self.end.isoformat(), required=False, max_length=40),
                ],
                self.span,
                emoji="\N{CALENDAR}",
            ),
            view.modal_button(
                "Look up ID",
                "Look up an asteroid",
                [Field("Asteroid ID", "e.g. 3542519", max_length=20)],
                self.find,
                emoji="\N{LEFT-POINTING MAGNIFYING GLASS}",
            ),
        ]
        if not self.rocks:
            return [
                discord.ui.TextDisplay(f"## \N{COMET} Near-Earth asteroids\nNothing found for {self.start.isoformat()} to {self.end.isoformat()}."),
                discord.ui.ActionRow(*buttons),
            ]

        rock = self.rocks[self.index]
        close = approach(rock)
        meters = (rock.get("estimated_diameter") or {}).get("meters") or {}
        size = f"{number(meters.get('estimated_diameter_min')):,.0f}\N{EN DASH}{number(meters.get('estimated_diameter_max')):,.0f} m"
        distance = close.get("miss_distance") or {}
        speed = number((close.get("relative_velocity") or {}).get("kilometers_per_hour"))
        hazardous = bool(rock.get("is_potentially_hazardous_asteroid"))
        sentry = bool(rock.get("is_sentry_object"))
        name = clip(clean(rock.get("name")), 200)
        url = safe_url(rock.get("nasa_jpl_url"))
        scope = "Lookup" if self.lookup else f"{len(self.rocks)} found{DOT}{self.start.isoformat()} \N{RIGHTWARDS ARROW} {self.end.isoformat()}"
        heading = f"### [{name}]({url})" if url else f"### {name}"
        details = "\n".join(
            [
                f"**Closest approach:** {clean(close.get('close_approach_date_full') or close.get('close_approach_date') or 'unknown')}",
                f"**Speed:** {speed:,.0f} km/h",
                f"**Miss distance:** {number(distance.get('kilometers')):,.0f} km ({number(distance.get('lunar')):.1f} lunar distances)",
                f"**Diameter:** {size}",
                f"**Absolute magnitude:** {clean(rock.get('absolute_magnitude_h'))}",
                f"**Orbiting:** {clean(close.get('orbiting_body') or 'Earth')}",
                f"**Potentially hazardous:** {'yes' if hazardous else 'no'}{DOT}**Sentry object:** {'yes' if sentry else 'no'}",
            ]
        )
        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay(f"## \N{COMET} Near-Earth asteroids\n{heading}\n-# ID {clean(rock.get('neo_reference_id'))}{DOT}{scope}"),
            discord.ui.TextDisplay(details),
        ]
        jpl = link_button("JPL page", url, "\N{TELESCOPE}")
        if jpl is not None:
            buttons.append(jpl)
        labels = [
            (
                clean(item.get("name")),
                ("\N{WARNING SIGN}\N{VARIATION SELECTOR-16} " if item.get("is_potentially_hazardous_asteroid") else "")
                + clean(approach(item).get("close_approach_date_full") or approach(item).get("close_approach_date")),
            )
            for item in self.rocks
        ]
        items += browse_rows(view, self, labels, "Pick an asteroid")
        items.append(discord.ui.ActionRow(*buttons))
        return items


def donki_value(key: str, value: Any) -> str:
    if value is None or value in ("", []):
        return ""
    if key == "allKpIndex":
        peaks = [number(entry.get("kpIndex")) for entry in value if isinstance(entry, dict)]
        return f"peak Kp {max(peaks):g}" if peaks else ""
    if isinstance(value, list):
        parts = []
        for entry in value:
            if isinstance(entry, dict):
                parts.append(str(entry.get("displayName") or entry.get("activityID") or ""))
            else:
                parts.append(str(entry))
        return clip(clean(", ".join(part for part in parts if part)), 400)
    if key.endswith("Time"):
        return stamp(value)
    return clip(clean(value), 800)


class DonkiPage(Page):
    label = "Space Weather"
    emoji = "\N{SUN WITH FACE}"

    def __init__(self, client: NasaClient) -> None:
        super().__init__(client)
        today = discord.utils.utcnow().date()
        self.kind = "FLR"
        self.end = today
        self.start = today - datetime.timedelta(days=7)
        self.events: list[dict[str, Any]] = []
        self.index = 0

    async def refresh(self) -> None:
        await self.fetch(self.kind, self.start, self.end)

    async def fetch(self, kind: str, start: datetime.date, end: datetime.date) -> None:
        if end < start:
            msg = "The end date comes before the start date."
            raise NasaError(msg)
        if (end - start).days > 90:
            msg = "Please keep the range within 90 days."
            raise NasaError(msg)
        params = {"startDate": start.isoformat(), "endDate": end.isoformat()}
        data: Any = None
        last_err: NasaError | None = None
        for template, auth in ((DONKI_URL, True), (DONKI_FALLBACK_URL, False)):
            try:
                data = await self.client.get(template.format(kind), params, ttl=900.0, auth=auth)
                last_err = None
                break
            except NasaError as exc:
                if exc.status == 404:
                    data = []
                    last_err = None
                    break
                last_err = exc
        if last_err is not None:
            raise last_err
        time_key = DONKI_KINDS[kind][2]
        events = [event for event in data or [] if isinstance(event, dict)] if isinstance(data, list) else []
        events.sort(key=lambda event: str(event.get(time_key) or ""), reverse=True)
        self.events = events[:100]
        self.kind, self.start, self.end = kind, start, end
        self.index = 0

    async def swap(self, value: str) -> None:
        await self.fetch(value, self.start, self.end)

    async def span(self, values: list[str]) -> None:
        start = await self.view.parse_date(values[0])
        end = await self.view.parse_date(values[1]) if values[1] else discord.utils.utcnow().date()
        await self.fetch(self.kind, start, end)

    def build(self) -> list[discord.ui.Item]:
        view = self.view
        label, id_key, time_key, fields = DONKI_KINDS[self.kind]
        kinds = view.select(
            "Event type",
            [
                discord.SelectOption(label=name, value=code, description=code, default=code == self.kind)
                for code, (name, *_rest) in DONKI_KINDS.items()
            ],
            self.swap,
        )
        buttons: list[discord.ui.Button] = [
            view.modal_button(
                "Date range",
                f"{self.kind} events by date range",
                [
                    Field("Start date", "e.g. 2024-05-01 or 1 May 2024", default=self.start.isoformat(), max_length=40),
                    Field("End date (max 90 days)", "leave empty for today", default=self.end.isoformat(), required=False, max_length=40),
                ],
                self.span,
                emoji="\N{CALENDAR}",
            )
        ]
        if not self.events:
            return [
                discord.ui.TextDisplay(
                    f"## \N{SUN WITH FACE} Space weather\nNo **{label}** events from {self.start.isoformat()} to {self.end.isoformat()}."
                ),
                discord.ui.ActionRow(kinds),
                discord.ui.ActionRow(*buttons),
            ]

        event = self.events[self.index]
        lines = []
        for name, key in fields:
            text = donki_value(key, event.get(key))
            if text:
                lines.append(f"**{name}:** {text}")
        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay(
                f"## \N{SUN WITH FACE} Space weather\n### {label}\n-# {clean(event.get(id_key))}{DOT}{stamp(event.get(time_key))}{DOT}{self.start.isoformat()} \N{RIGHTWARDS ARROW} {self.end.isoformat()}"
            ),
            discord.ui.TextDisplay("\n".join(lines) or "No further details were published for this event."),
        ]
        open_link = link_button("Open in DONKI", event.get("link"), "\N{TELESCOPE}")
        if open_link is not None:
            buttons.append(open_link)
        labels = [(clean(item.get(id_key)), stamp(item.get(time_key), "d")) for item in self.events]
        labels = [
            (
                text,
                re.sub(
                    r"<t:(-?\d+):d>",
                    lambda m: datetime.datetime.fromtimestamp(int(m.group(1)), datetime.UTC).strftime("%Y-%m-%d %H:%M UTC"),
                    desc,
                ),
            )
            for text, desc in labels
        ]
        items += browse_rows(view, self, labels, f"Pick a {self.kind} event")
        items += [discord.ui.ActionRow(kinds), discord.ui.ActionRow(*buttons)]
        return items


def asset_label(url: str) -> str:
    return next((tag[1:] for tag in ASSET_QUALITY if tag in url), "link")


def asset_rank(url: str) -> int:
    return next((index for index, tag in enumerate(ASSET_QUALITY) if tag in url), len(ASSET_QUALITY))


class LibraryPage(Page):
    label = "Library"
    emoji = "\N{TELESCOPE}"

    def __init__(self, client: NasaClient, query: str) -> None:
        super().__init__(client)
        self.query = query
        self.media = "all"
        self.results: list[dict[str, Any]] = []
        self.assets: list[str] = []
        self.index = 0

    async def refresh(self) -> None:
        await self.fetch(self.query, self.media)

    async def fetch(self, query: str, media: str) -> None:
        params: dict[str, Any] = {"q": query, "page_size": 50}
        if media != "all":
            params["media_type"] = media
        try:
            data = await self.client.get(LIBRARY_URL, params, auth=False, ttl=3600.0)
        except NasaError as exc:
            if exc.status == 404:
                data = {}
            else:
                raise
        collection = data.get("collection") if isinstance(data, dict) else None
        items = collection.get("items") if isinstance(collection, dict) else None
        self.results = [item for item in items or [] if isinstance(item, dict) and item.get("data")]
        self.query, self.media, self.index = query, media, 0
        await self.changed()

    async def changed(self) -> None:
        self.assets = []
        if not self.results:
            return
        href = secure(self.results[self.index].get("href"))
        if href is None:
            return
        try:
            data = await self.client.get(href, auth=False, ttl=3600.0)
        except NasaError:
            return
        if isinstance(data, list):
            self.assets = [url for url in (secure(entry) for entry in data) if url]

    async def filter(self, value: str) -> None:
        await self.fetch(self.query, value)

    async def search(self, values: list[str]) -> None:
        await self.fetch(values[0], self.media)

    def build(self) -> list[discord.ui.Item]:
        view = self.view
        media = view.select(
            "Media type",
            [discord.SelectOption(label=label, value=value, default=value == self.media) for value, label in LIBRARY_MEDIA],
            self.filter,
        )
        search = view.modal_button(
            "New search",
            "Search NASA's library",
            [Field("Search for", "e.g. apollo 11, nebula, mars rover", default=self.query, max_length=100)],
            self.search,
            emoji="\N{LEFT-POINTING MAGNIFYING GLASS}",
        )
        title_text = "## \N{TELESCOPE} NASA Image and Video Library"
        if not self.results:
            query = discord.utils.escape_markdown(clip(clean(self.query), 100))
            return [
                discord.ui.TextDisplay(f"{title_text}\nNothing found for **{query}**. Try different words."),
                discord.ui.ActionRow(media),
                discord.ui.ActionRow(search),
            ]

        item = self.results[self.index]
        data = item["data"][0]
        title = clip(strip_html(data.get("title")), 200) or "Untitled"
        description = strip_html(data.get("description"))
        meta = [clean(data.get("nasa_id")), stamp(data.get("date_created"), "D")]
        if data.get("center"):
            meta.append(clean(data["center"]))
        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay(f"{title_text}\n### {title}\n-# {DOT.join(part for part in meta if part)}"),
            discord.ui.TextDisplay(clip(description, 1500) or "No description."),
        ]

        link = (item.get("links") or [{}])[0]
        preview = secure(link.get("href")) if link.get("render") == "image" else None
        if preview:
            items.append(discord.ui.MediaGallery(discord.MediaGalleryItem(preview, description=clip(title, 100))))

        groups = (
            ("Images", sorted((url for url in self.assets if url.lower().endswith((".jpg", ".jpeg", ".png"))), key=asset_rank)[:3]),
            ("Videos", sorted((url for url in self.assets if url.lower().endswith(".mp4")), key=asset_rank)[:3]),
            ("Audio", [url for url in self.assets if url.lower().endswith((".mp3", ".m4a", ".wav"))][:2]),
            ("Captions", [url for url in self.assets if url.lower().endswith((".srt", ".vtt"))][:2]),
        )
        lines = [f"**{name}:** " + ", ".join(f"[{asset_label(url)}]({url})" for url in urls) for name, urls in groups if urls]
        if lines:
            items.append(discord.ui.TextDisplay("\n".join(lines)))

        buttons: list[discord.ui.Button] = [search]
        details = link_button(
            "Open on NASA", f"https://images.nasa.gov/details/{data.get('nasa_id')}" if data.get("nasa_id") else None, "\N{TELESCOPE}"
        )
        if details is not None:
            buttons.append(details)
        labels = [(clean(entry["data"][0].get("title")), clean(entry["data"][0].get("media_type"))) for entry in self.results]
        items += browse_rows(view, self, labels, "Pick a result")
        items += [discord.ui.ActionRow(media), discord.ui.ActionRow(*buttons)]
        return items


class NASA(commands.Cog, description="NASA data: pictures, imagery, asteroids and space weather.", command_attrs={"hidden": True}):
    help_emoji = "\N{ROCKET}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.client = NasaClient()

    async def cog_load(self) -> None:
        await self.client.start()

    async def cog_unload(self) -> None:
        await self.client.close()

    async def open_view(self, ctx: commands.Context[Bot], pages: dict[str, Page], start: str) -> None:
        view = NasaLayout(ctx, pages, start)
        try:
            async with ctx.typing():
                await pages[start].load()
        except NasaError as exc:
            await ctx.reply(str(exc))
            return
        view.render()
        view.message = await ctx.reply(view=view)

    async def open_hub(self, ctx: commands.Context[Bot], start: str, date: HumanDate | None = None) -> None:
        pages: dict[str, Page] = {
            "apod": ApodPage(self.client),
            "epic": EpicPage(self.client),
            "mars": MarsPage(self.client),
            "neo": AsteroidPage(self.client),
            "donki": DonkiPage(self.client),
        }
        page = pages[start]
        if date is not None:
            if isinstance(page, ApodPage | EpicPage | MarsPage):
                page.date = date.date
            elif isinstance(page, AsteroidPage):
                page.start = page.end = date.date
        await self.open_view(ctx, pages, start)

    @commands.command(name="nasa", aliases=["space"])
    @commands.cooldown(2, 15, commands.BucketType.user)
    async def nasa(self, ctx: commands.Context[Bot]) -> None:
        """Open the NASA hub: picture of the day, Earth imagery, Mars photos, asteroids and space weather."""
        await self.open_hub(ctx, "apod")

    @commands.command(name="apod")
    @commands.cooldown(2, 15, commands.BucketType.user)
    async def apod(
        self,
        ctx: commands.Context[Bot],
        *,
        date: HumanDate | None = commands.parameter(  # noqa: B008
            description="The date to look up Astronomy Picture of the Day for, or leave empty for today.",
            default=None,
        ),
    ) -> None:
        """Astronomy Picture of the Day, for today or any date."""
        await self.open_hub(ctx, "apod", date)

    @commands.command(name="epic")
    @commands.cooldown(2, 15, commands.BucketType.user)
    async def epic(
        self,
        ctx: commands.Context[Bot],
        *,
        date: HumanDate | None = commands.parameter(  # noqa: B008
            description="The date to look up Earth imagery for, or leave empty for the latest.",
            default=None,
        ),
    ) -> None:
        """Earth Polychromatic Imaging Camera: full-disc photos of Earth from the DSCOVR satellite."""
        await self.open_hub(ctx, "epic", date)

    @commands.command(name="mars", aliases=["mrp"])
    @commands.cooldown(2, 15, commands.BucketType.user)
    async def mars(
        self,
        ctx: commands.Context[Bot],
        *,
        date: HumanDate | None = commands.parameter(  # noqa: B008
            description="The date to look up Mars rover photos for, or leave empty for the latest.",
            default=None,
        ),
    ) -> None:
        """Mars rover photos, latest or by Earth date."""
        await self.open_hub(ctx, "mars", date)

    @commands.command(name="asteroids", aliases=["asteroid", "neo", "finda", "findasteroid", "findaid", "asteroidid"])
    @commands.cooldown(2, 15, commands.BucketType.user)
    async def asteroids(
        self,
        ctx: commands.Context[Bot],
        *,
        date: HumanDate | None = commands.parameter(  # noqa: B008
            description="The date to look up asteroids for, or leave empty for today.",
            default=None,
        ),
    ) -> None:
        """Near-Earth asteroids by date, or look one up by ID."""
        await self.open_hub(ctx, "neo", date)

    @commands.command(name="donki", aliases=["spaceweather"])
    @commands.cooldown(2, 15, commands.BucketType.user)
    async def donki(self, ctx: commands.Context[Bot]) -> None:
        """Space weather events: flares, CMEs, geomagnetic storms and more."""
        await self.open_hub(ctx, "donki")

    @commands.command(name="nasasearch", aliases=["nsearch", "ns"])
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def nasasearch(self, ctx: commands.Context[Bot], *, query: str = commands.parameter(description="The search query.")) -> None:
        """Search NASA's image and video library."""
        await self.open_view(ctx, {"library": LibraryPage(self.client, clean(query)[:100])}, "library")

    async def _fetch_gibs_earth(self, longitude: float, latitude: float, date: datetime.date | None) -> bytes:
        half = 0.25
        min_lon = max(-180.0, longitude - half)
        max_lon = min(180.0, longitude + half)
        min_lat = max(-90.0, latitude - half)
        max_lat = min(90.0, latitude + half)
        target_date = date or (discord.utils.utcnow().date() - datetime.timedelta(days=1))
        params: dict[str, Any] = {
            "service": "WMS",
            "request": "GetMap",
            "version": "1.1.1",
            "layers": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "styles": "",
            "format": "image/jpeg",
            "bbox": f"{min_lon:.4f},{min_lat:.4f},{max_lon:.4f},{max_lat:.4f}",
            "width": 800,
            "height": 800,
            "srs": "EPSG:4326",
            "time": target_date.isoformat(),
        }
        return await self.client.get(GIBS_WMS_URL, params, auth=False, raw=True)

    @commands.command(name="earth", aliases=["sat", "satellite", "satelite"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def earth(
        self,
        ctx: commands.Context[Bot],
        longitude: Annotated[float, commands.Range[float, -180, 180]] = commands.parameter(
            description="Longitude of the location, between -180 and 180."
        ),
        latitude: Annotated[float, commands.Range[float, -90, 90]] = commands.parameter(
            description="Latitude of the location, between -90 and 90.",
        ),
        *,
        date: HumanDate | None = commands.parameter(  # noqa: B008
            description="The date to look up satellite imagery for, or leave empty for the latest.", default=None
        ),
    ) -> None:
        """Satellite imagery of a location. Longitude first, then latitude, then an optional date."""
        params: dict[str, Any] = {"lon": longitude, "lat": latitude, "dim": 0.15}
        target_date = date.date if date is not None else None
        if target_date is not None:
            params["date"] = target_date.isoformat()
        payload: bytes = b""
        try:
            async with ctx.typing():
                try:
                    payload = await self.client.get(EARTH_URL, params, raw=True)
                except NasaError as exc:
                    if exc.status == 404 or exc.server_error:
                        payload = await self._fetch_gibs_earth(longitude, latitude, target_date)
                    else:
                        raise
                if payload[:4] != b"\x89PNG" and payload[:2] != b"\xff\xd8":
                    payload = await self._fetch_gibs_earth(longitude, latitude, target_date)
        except NasaError as exc:
            if ctx.command:
                ctx.command.reset_cooldown(ctx)
            await ctx.reply(str(exc))
            return
        if payload[:4] == b"\x89PNG":
            filename = "earth.png"
        elif payload[:2] == b"\xff\xd8":
            filename = "earth.jpg"
        else:
            if ctx.command:
                ctx.command.reset_cooldown(ctx)
            await ctx.reply("NASA didn't return an image for that place and date.")
            return
        when = target_date.isoformat() if target_date is not None else "latest available"
        view = discord.ui.LayoutView()
        view.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"## \N{SATELLITE} Earth\n-# lon {longitude:.4f}, lat {latitude:.4f}{DOT}{when}"),
                discord.ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{filename}", description="Satellite imagery")),
                accent_colour=NASA_BLUE,
            )
        )
        await ctx.reply(view=view, file=discord.File(io.BytesIO(payload), filename=filename))


async def setup(bot: Bot) -> None:
    await bot.add_cog(NASA(bot))
