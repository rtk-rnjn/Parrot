"""
pastebin_client
===============

Async, rate-limited wrapper for the Pastebin API (https://pastebin.com/doc_api),
designed for use inside a Discord bot (discord.py / py-cord / nextcord / disnake).

Requires: ``aiohttp>=3.8``  (Python 3.9+)

Features
--------
* Fully async (``aiohttp``), never blocks the bot's event loop.
* Sliding-window rate limiter + minimum spacing between requests, shared by all
  tasks using the same client. Honors ``Retry-After`` on HTTP 429.
* Local rolling-24h paste quota tracking so you fail fast with a clear error
  (and a ``retry_after``) instead of burning API calls on a limit you know you hit.
* Retries with exponential backoff + jitter on network errors / 5xx.
* Pastebin's quirky "errors as 200 OK plain text" responses are parsed into a
  proper exception hierarchy.
* Lazy login with a cached user key (safe under concurrent use).
* Typed results (``Paste`` dataclass), enums for visibility / expiry.
* Secrets (dev key, password, user key) are never logged or shown in ``repr``.

Quick start (discord.py)
------------------------
::

    import os
    import discord
    from discord.ext import commands
    from pastebin_client import PastebinClient, Visibility, Expiry, PastebinError


    class MyBot(commands.Bot):
        async def setup_hook(self) -> None:
            self.pastebin = PastebinClient(
                os.environ["PASTEBIN_DEV_KEY"],
                username=os.environ.get("PASTEBIN_USER"),  # optional
                password=os.environ.get("PASTEBIN_PASSWORD"),  # optional
            )

        async def close(self) -> None:
            await self.pastebin.close()
            await super().close()


    @bot.command()
    async def logs(ctx):
        text = build_big_report()
        if len(text) <= 2000:
            return await ctx.send(text)
        try:
            paste = await ctx.bot.pastebin.create_paste(
                text,
                title="Report",
                syntax="text",
                visibility=Visibility.UNLISTED,
                expiry=Expiry.ONE_DAY,
            )
        except PastebinError as exc:
            return await ctx.send(f"Couldn't upload the paste: {exc}")
        await ctx.send(f"Too long for Discord, so here's a paste: {paste.url}")

Notes on Pastebin limits (as of writing; verify on your account)
----------------------------------------------------------------
* Guests: ~10 pastes / 24h. Free accounts: ~20 / 24h. PRO: far higher.
* Max paste size: 512 KB (free) / 10 MB (PRO). Pass ``max_paste_bytes`` and
  ``daily_paste_limit=None`` if you are on PRO.
* The local quota tracker is in-memory only: it resets when the bot restarts
  and cannot see pastes created elsewhere. The server remains the authority and
  its errors are still mapped properly.
"""

from __future__ import annotations

import asyncio
import contextlib
import enum
import logging
import random
import time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import aiohttp

__all__ = [
    "AuthenticationError",
    "Expiry",
    "IPBlockedError",
    "Paste",
    "PasteNotFoundError",
    "PasteTooLargeError",
    "PastebinAPIError",
    "PastebinClient",
    "PastebinConnectionError",
    "PastebinError",
    "PastebinHTTPError",
    "QuotaExceededError",
    "QuotaTracker",
    "RateLimitedError",
    "RateLimiter",
    "ValidationError",
    "Visibility",
    "fits_in_discord",
]

log = logging.getLogger(__name__)

API_POST_URL = "https://pastebin.com/api/api_post.php"
API_LOGIN_URL = "https://pastebin.com/api/api_login.php"
API_RAW_URL = "https://pastebin.com/api/api_raw.php"
RAW_URL = "https://pastebin.com/raw/{key}"
PASTE_URL = "https://pastebin.com/{key}"

DISCORD_MESSAGE_LIMIT = 2000


def fits_in_discord(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> bool:
    """True if ``text`` can be sent as a single regular Discord message."""
    return len(text) <= limit


class PastebinError(Exception):
    """Base class for every error raised by this module."""


class PastebinConnectionError(PastebinError):
    """Network failure / timeout after all retries were exhausted."""


class PastebinHTTPError(PastebinError):
    """Unexpected HTTP status code."""

    def __init__(self, status: int, body: str = "") -> None:
        self.status = status
        self.body = body[:200]
        super().__init__(f"Pastebin returned HTTP {status}")


class PastebinAPIError(PastebinError):
    """Pastebin answered 200 OK but with an error message."""

    def __init__(self, message: str) -> None:
        self.api_message = message
        super().__init__(message)


class AuthenticationError(PastebinAPIError):
    """Bad dev key, bad credentials, bad user key, or login required."""


class ValidationError(PastebinAPIError):
    """Invalid parameters (rejected locally or by Pastebin)."""


class PasteTooLargeError(ValidationError):
    """Paste exceeds the maximum allowed size."""


class PasteNotFoundError(PastebinAPIError):
    """Paste doesn't exist, expired, or you lack permission to view it."""


class IPBlockedError(PastebinAPIError):
    """Pastebin has temporarily blocked this IP (too many bad/failed requests)."""


class RateLimitedError(PastebinError):
    """Pastebin throttled us (HTTP 429) and retries were exhausted."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limited by Pastebin; retry in ~{retry_after:.0f}s")


class QuotaExceededError(PastebinAPIError):
    """Paste creation quota (per 24h / per account) reached."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message)


# --------------------------------------------------------------------------- #
# Enums & models
# --------------------------------------------------------------------------- #
class Visibility(enum.IntEnum):
    PUBLIC = 0
    UNLISTED = 1
    PRIVATE = 2  # requires a logged-in user


class Expiry(enum.StrEnum):
    NEVER = "N"
    TEN_MINUTES = "10M"
    ONE_HOUR = "1H"
    ONE_DAY = "1D"
    ONE_WEEK = "1W"
    TWO_WEEKS = "2W"
    ONE_MONTH = "1M"
    SIX_MONTHS = "6M"
    ONE_YEAR = "1Y"


_EXPIRY_SECONDS = {
    Expiry.TEN_MINUTES: 600,
    Expiry.ONE_HOUR: 3600,
    Expiry.ONE_DAY: 86400,
    Expiry.ONE_WEEK: 7 * 86400,
    Expiry.TWO_WEEKS: 14 * 86400,
    Expiry.ONE_MONTH: 30 * 86400,
    Expiry.SIX_MONTHS: 182 * 86400,
    Expiry.ONE_YEAR: 365 * 86400,
}


@dataclass(frozen=True)
class Paste:
    """A paste. Fields not known for a given call are ``None``."""

    key: str
    url: str
    title: str | None = None
    syntax: str | None = None
    visibility: Visibility | None = None
    size: int | None = None  # bytes
    hits: int | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None  # None => never / unknown

    @property
    def raw_url(self) -> str:
        return RAW_URL.format(key=self.key)

    def __str__(self) -> str:
        return self.url


class RateLimiter:
    """
    Async sliding-window limiter: at most ``max_calls`` per ``period`` seconds,
    and at least ``min_interval`` seconds between consecutive calls.

    Waiters are served in FIFO order. ``block_for`` lets the client impose a
    global pause (e.g. after an HTTP 429).
    """

    def __init__(self, max_calls: int, period: float, *, min_interval: float = 0.0) -> None:
        if max_calls < 1 or period <= 0 or min_interval < 0:
            msg = "invalid rate limiter configuration"
            raise ValueError(msg)
        self._max_calls = max_calls
        self._period = period
        self._min_interval = min_interval
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._blocked_until = 0.0

    def block_for(self, seconds: float) -> None:
        self._blocked_until = max(self._blocked_until, time.monotonic() + seconds)

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                while self._calls and now - self._calls[0] >= self._period:
                    self._calls.popleft()

                wait = self._blocked_until - now
                if self._calls:
                    wait = max(wait, self._calls[-1] + self._min_interval - now)
                if len(self._calls) >= self._max_calls:
                    wait = max(wait, self._calls[0] + self._period - now)

                if wait <= 0:
                    break
                await asyncio.sleep(wait)
            self._calls.append(time.monotonic())


class QuotaTracker:
    """In-memory rolling-window counter (default 24h) for paste creation."""

    def __init__(self, limit: int | None, window: float = 86400.0) -> None:
        self._limit = limit
        self._window = window
        self._stamps: deque[float] = deque()

    def _purge(self, now: float) -> None:
        while self._stamps and now - self._stamps[0] >= self._window:
            self._stamps.popleft()

    def reserve(self) -> float:
        """Reserve one slot or raise ``QuotaExceededError``. Returns a token."""
        now = time.monotonic()
        self._purge(now)
        if self._limit is not None and len(self._stamps) >= self._limit:
            retry_after = self._stamps[0] + self._window - now
            msg = f"Local paste quota reached ({self._limit} per {self._window / 3600:.0f}h); try again in {retry_after / 60:.0f} min"
            raise QuotaExceededError(
                msg,
                retry_after=retry_after,
            )
        self._stamps.append(now)
        return now

    def release(self, token: float) -> None:
        """Give back a slot when the paste was not actually created."""
        with contextlib.suppress(ValueError):
            self._stamps.remove(token)

    @property
    def remaining(self) -> int | None:
        if self._limit is None:
            return None
        self._purge(time.monotonic())
        return max(0, self._limit - len(self._stamps))


class _Auto:
    def __repr__(self) -> str:
        return "AUTO"


AUTO: Any = _Auto()  # sentinel: pick a sensible daily limit automatically

_API_ERROR_MARKERS = ("bad api request", "post limit", "ip blocked")


def _is_api_error(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith(_API_ERROR_MARKERS)


def _map_api_error(message: str) -> PastebinAPIError:
    message = message.strip()
    low = message.lower()
    if "ip blocked" in low:
        return IPBlockedError(message)
    if "post limit" in low or "maximum number of" in low:
        return QuotaExceededError(message)
    if "maximum paste file size" in low:
        return PasteTooLargeError(message)
    if any(s in low for s in ("api_dev_key", "api_user_key", "invalid login", "account not active", "login")):
        return AuthenticationError(message)
    if "api_paste_key" in low or "invalid permission" in low:
        return PasteNotFoundError(message)
    return ValidationError(message)


def _to_key(paste: str | Paste) -> str:
    """Accept a Paste, a bare key, or a pastebin.com URL; return the key."""
    if isinstance(paste, Paste):
        return paste.key
    key = paste.strip().rstrip("/").rsplit("/", 1)[-1]
    if not key or not key.isalnum():
        msg = f"Invalid paste key or URL: {paste!r}"
        raise ValidationError(msg)
    return key


class PastebinClient:
    """
    Async Pastebin client.

    Parameters
    ----------
    dev_key:
        Your API developer key (https://pastebin.com/doc_api#1).
    username, password:
        Optional account credentials. If given, the client logs in lazily on
        first use and attaches the user key to every paste (needed for PRIVATE
        pastes, listing and deleting).
    user_key:
        Alternatively, a pre-obtained user key.
    session:
        Optional shared ``aiohttp.ClientSession`` (not closed by ``close()``).
    default_visibility, default_expiry:
        Defaults for ``create_paste``. UNLISTED / one week is a sane bot default.
    max_paste_bytes:
        Local size guard (512 KB free, 10 MB PRO).
    daily_paste_limit:
        Local rolling-24h creation cap. Default: 10 for guests, 20 for logged-in
        free accounts. Use ``None`` to disable (PRO) or an int to override.
    rate_limit_calls, rate_limit_period, min_interval:
        Request throttling across *all* endpoints (conservative defaults).
    max_retries:
        Retries on network errors / 5xx / 429.
    timeout:
        Per-request total timeout in seconds.
    """

    def __init__(
        self,
        dev_key: str,
        *,
        username: str | None = None,
        password: str | None = None,
        user_key: str | None = None,
        session: aiohttp.ClientSession | None = None,
        default_visibility: Visibility = Visibility.UNLISTED,
        default_expiry: Expiry = Expiry.ONE_WEEK,
        max_paste_bytes: int = 512 * 1024,
        daily_paste_limit: int | _Auto | None = AUTO,
        rate_limit_calls: int = 30,
        rate_limit_period: float = 60.0,
        min_interval: float = 1.0,
        max_retries: int = 3,
        timeout: float = 15.0,
    ) -> None:
        if not dev_key or not dev_key.strip():
            msg = "dev_key is required"
            raise ValueError(msg)
        if bool(username) != bool(password):
            msg = "username and password must be provided together"
            raise ValueError(msg)

        self._dev_key = dev_key.strip()
        self._username = username
        self._password = password
        self._user_key = user_key
        self._session = session
        self._owns_session = session is None
        self._default_visibility = default_visibility
        self._default_expiry = default_expiry
        self._max_paste_bytes = max_paste_bytes
        self._max_retries = max(0, max_retries)
        self._timeout = aiohttp.ClientTimeout(total=timeout)

        self._limiter = RateLimiter(rate_limit_calls, rate_limit_period, min_interval=min_interval)
        if daily_paste_limit is AUTO:
            daily_paste_limit = 20 if (username or user_key) else 10
        self._quota = QuotaTracker(daily_paste_limit)  # type: ignore[arg-type]

        self._login_lock = asyncio.Lock()
        self._closed = False

    def __repr__(self) -> str:  # never leak secrets
        return f"<PastebinClient authed={bool(self._user_key or self._username)} remaining_quota={self._quota.remaining}>"

    async def __aenter__(self) -> PastebinClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        self._closed = True
        if self._session is not None and self._owns_session and not self._session.closed:
            await self._session.close()

    @property
    def remaining_quota(self) -> int | None:
        """Pastes you can still create locally in the current 24h window."""
        return self._quota.remaining

    def _get_session(self) -> aiohttp.ClientSession:
        if self._closed:
            msg = "Client is closed"
            raise PastebinError(msg)
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={"User-Agent": "pastebin-client/1.0 (discord bot; aiohttp)"},
            )
            self._owns_session = True
        return self._session

    async def _request(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        api_errors: bool = True,
        not_found_on_404: bool = False,
    ) -> str:
        """
        Perform a throttled request with retries and return the response text.

        ``api_errors=False`` skips the "errors-as-text" check (used for public raw
        pastes, whose content could legitimately start with any string).
        """
        HTTP_TOO_MANY_REQUESTS = 429
        HTTP_SERVER_ERROR = 500
        HTTP_NOT_FOUND = 404
        HTTP_BAD_REQUEST = 400

        last_retry_after = 0.0
        for attempt in range(self._max_retries + 1):
            await self._limiter.acquire()
            try:
                async with self._get_session().request(method, url, data=data, timeout=self._timeout) as resp:
                    status = resp.status
                    text = await resp.text()
                    retry_after_hdr = resp.headers.get("Retry-After")
            except (TimeoutError, aiohttp.ClientError) as exc:
                if attempt >= self._max_retries:
                    msg = f"Could not reach Pastebin: {exc!r}"
                    raise PastebinConnectionError(msg) from exc
                delay = self._backoff(attempt)
                log.warning("Pastebin network error (%r); retrying in %.1fs", exc, delay)
                await asyncio.sleep(delay)
                continue

            if status == HTTP_TOO_MANY_REQUESTS:
                try:
                    last_retry_after = float(retry_after_hdr) if retry_after_hdr else 60.0
                except ValueError:
                    last_retry_after = 60.0
                last_retry_after = min(last_retry_after, 600.0)
                self._limiter.block_for(last_retry_after)
                if attempt >= self._max_retries:
                    raise RateLimitedError(last_retry_after)
                log.warning("Pastebin 429; pausing %.0fs", last_retry_after)
                continue  # acquire() will wait out the block

            if status >= HTTP_SERVER_ERROR:
                if attempt >= self._max_retries:
                    raise PastebinHTTPError(status, text)
                delay = self._backoff(attempt)
                log.warning("Pastebin HTTP %s; retrying in %.1fs", status, delay)
                await asyncio.sleep(delay)
                continue

            if status == HTTP_NOT_FOUND and not_found_on_404:
                msg = "Paste not found"
                raise PasteNotFoundError(msg)
            if status >= HTTP_BAD_REQUEST:
                raise PastebinHTTPError(status, text)

            if api_errors and _is_api_error(text):
                raise _map_api_error(text)
            return text

        msg = "Request failed"
        raise PastebinConnectionError(msg)  # pragma: no cover

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(2.0 * (2**attempt), 30.0) + random.uniform(0, 0.5)

    async def login(self) -> str:
        """Log in with the configured credentials and cache the user key."""
        if not (self._username and self._password):
            msg = "No username/password configured"
            raise AuthenticationError(msg)
        text = await self._request(
            "POST",
            API_LOGIN_URL,
            data={
                "api_dev_key": self._dev_key,
                "api_user_name": self._username,
                "api_user_password": self._password,
            },
        )
        key = text.strip()
        if not key or " " in key:
            msg = f"Unexpected login response: {key[:80]!r}"
            raise AuthenticationError(msg)
        self._user_key = key
        return key

    async def _ensure_user_key(self) -> str | None:
        if self._user_key:
            return self._user_key
        if not (self._username and self._password):
            return None
        async with self._login_lock:
            if not self._user_key:
                await self.login()
        return self._user_key

    async def _require_user_key(self) -> str:
        key = await self._ensure_user_key()
        if not key:
            msg = "This operation requires a logged-in user (username/password or user_key)"
            raise AuthenticationError(msg)
        return key

    async def create_paste(
        self,
        content: str,
        *,
        title: str | None = None,
        syntax: str = "text",
        visibility: Visibility | None = None,
        expiry: Expiry | None = None,
    ) -> Paste:
        """
        Create a paste and return it.

        ``syntax`` is a Pastebin format code, e.g. ``"text"``, ``"python"``,
        ``"json"``, ``"markdown"``, ``"diff"`` (see https://pastebin.com/doc_api#5).
        """
        if not isinstance(content, str) or not content.strip():
            msg = "Paste content must be a non-empty string"
            raise ValidationError(msg)
        size = len(content.encode("utf-8"))
        if size > self._max_paste_bytes:
            msg = f"Paste is {size:,} bytes; the limit is {self._max_paste_bytes:,} bytes"
            raise PasteTooLargeError(msg)

        visibility = self._default_visibility if visibility is None else Visibility(visibility)
        expiry = self._default_expiry if expiry is None else Expiry(expiry)

        user_key = await self._ensure_user_key()
        if visibility is Visibility.PRIVATE and not user_key:
            msg = "Private pastes require a logged-in user"
            raise ValidationError(msg)

        payload: dict[str, Any] = {
            "api_option": "paste",
            "api_dev_key": self._dev_key,
            "api_paste_code": content,
            "api_paste_private": int(visibility),
            "api_paste_expire_date": expiry.value,
            "api_paste_format": syntax,
        }
        if title:
            payload["api_paste_name"] = title
        if user_key:
            payload["api_user_key"] = user_key

        token = self._quota.reserve()
        try:
            text = await self._request("POST", API_POST_URL, data=payload)
        except BaseException:
            self._quota.release(token)
            raise

        url = text.strip()
        if not url.startswith("http"):
            self._quota.release(token)
            msg = f"Unexpected response from Pastebin: {url[:120]!r}"
            raise PastebinAPIError(msg)

        now = datetime.now(UTC)
        seconds = _EXPIRY_SECONDS.get(expiry)
        return Paste(
            key=_to_key(url),
            url=url,
            title=title,
            syntax=syntax,
            visibility=visibility,
            size=size,
            hits=0,
            created_at=now,
            expires_at=datetime.fromtimestamp(now.timestamp() + seconds, UTC) if seconds else None,
        )

    async def get_raw(self, paste: str | Paste) -> str:
        """
        Fetch a paste's raw text. Tries the public ``/raw/`` endpoint first and,
        if the client is authenticated, falls back to the authenticated API
        (which also works for your own private pastes).
        """
        key = _to_key(paste)
        try:
            return await self._request("GET", RAW_URL.format(key=key), api_errors=False, not_found_on_404=True)
        except PasteNotFoundError:
            user_key = await self._ensure_user_key()
            if not user_key:
                raise
        return await self._request(
            "POST",
            API_RAW_URL,
            data={
                "api_option": "show_paste",
                "api_dev_key": self._dev_key,
                "api_user_key": user_key,
                "api_paste_key": key,
            },
        )

    async def list_pastes(self, limit: int = 50) -> list[Paste]:
        """List the logged-in user's pastes (1-1000, newest first)."""
        if not 1 <= limit <= 1000:
            msg = "limit must be between 1 and 1000"
            raise ValidationError(msg)
        user_key = await self._require_user_key()
        text = await self._request(
            "POST",
            API_POST_URL,
            data={
                "api_option": "list",
                "api_dev_key": self._dev_key,
                "api_user_key": user_key,
                "api_results_limit": limit,
            },
        )
        if text.strip().lower().startswith("no pastes found"):
            return []
        # The API returns a sequence of <paste> elements with no root element.
        try:
            root = ET.fromstring(f"<root>{text}</root>")  # noqa: S314
        except ET.ParseError as exc:
            msg = "Could not parse paste list from Pastebin"
            raise PastebinAPIError(msg) from exc

        def _int(el: ET.Element, tag: str) -> int | None:
            val = el.findtext(tag)
            try:
                return int(val) if val not in (None, "") else None
            except ValueError:
                return None

        pastes: list[Paste] = []
        for el in root.iter("paste"):
            created = _int(el, "paste_date")
            expires = _int(el, "paste_expire_date")
            priv = _int(el, "paste_private")
            key = el.findtext("paste_key") or ""
            pastes.append(
                Paste(
                    key=key,
                    url=el.findtext("paste_url") or PASTE_URL.format(key=key),
                    title=el.findtext("paste_title") or None,
                    syntax=el.findtext("paste_format_short") or None,
                    visibility=Visibility(priv) if priv in (0, 1, 2) else None,
                    size=_int(el, "paste_size"),
                    hits=_int(el, "paste_hits"),
                    created_at=datetime.fromtimestamp(created, UTC) if created else None,
                    expires_at=datetime.fromtimestamp(expires, UTC) if expires else None,
                )
            )
        return pastes

    async def delete_paste(self, paste: str | Paste) -> None:
        """Delete one of the logged-in user's pastes."""
        key = _to_key(paste)
        user_key = await self._require_user_key()
        text = await self._request(
            "POST",
            API_POST_URL,
            data={
                "api_option": "delete",
                "api_dev_key": self._dev_key,
                "api_user_key": user_key,
                "api_paste_key": key,
            },
        )
        if "paste removed" not in text.lower():
            msg = f"Unexpected delete response: {text.strip()[:120]!r}"
            raise PastebinAPIError(msg)
