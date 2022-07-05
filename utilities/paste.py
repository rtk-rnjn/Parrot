from __future__ import annotations

import datetime
import re
from textwrap import dedent
from typing import Any, Dict, Optional

import aiohttp  # type: ignore

MB_URL_RE = re.compile(
    r"(?:(?:https?://)?mystb\.in/)?(?P<ID>[a-zA-Z]+)(?:\.(?P<syntax>[a-zA-Z0-9]+))?"
)

API_BASE_URL = "https://mystb.in/api/pastes"
PASTE_BASE = "https://mystb.in/{}{}"

CLIENT_TIMEOUT = 15


async def paste(text: str) -> Optional[str]:
    """Return an online bin of given text"""
    async with aiohttp.ClientSession() as aioclient:
        post = await aioclient.post("https://hastebin.com/documents", data=text)
        if post.status == 200:
            response = await post.text()
            return f"https://hastebin.com/{response[8:-2]}"

        # Rollback bin
        post = await aioclient.post(
            "https://bin.readthedocs.fr/new", data={"code": text, "lang": "txt"}
        )
        if post.status == 200:
            return post.url


class BadPasteID(ValueError):
    """Bad Paste ID."""


class MystbinException(Exception):
    """Error when interacting with Mystbin."""


class APIError(MystbinException):
    """
    Exception relationg to the API of Mystbin.
    Attributes
    ----------
    status_code: :class:`int`
        The HTTP Status code return from the API.
    message: :class:`str`
        The Message supplied with the HTTP status code from the API.
    """

    def __init__(self, status_code: int, message: str):
        self.status_code: int = status_code
        self.message: str = message

    def __repr__(self) -> str:
        return f"<MystbinError status_code={self.status_code} message={self.message}>"

    def __str__(self) -> str:
        return self.message


class Paste:
    """
    A class representing the return data from the API after performing a POST request.
    Attributes
    ----------
    paste_id: :class:`str`
        The ID returned from the API. Genertally it is 3 random choice English words.
    nick: :class:`str`
        The nickname you requested the paste be named.
    syntax: :class:`str`
        The syntax (or syntax highlighting) you requested when creating the Paste. Returns as a suffix on the URL.
    """

    def __init__(self, json_data: Dict[str, Any], syntax: str = None):
        self.paste_id: str = json_data["pastes"][0]["id"]
        self.nick: Optional[str] = json_data["pastes"][0]["nick"]
        self.syntax: Optional[str] = syntax

    def __str__(self) -> str:
        return self.url

    def __repr__(self) -> str:
        return f"<Paste id={self.paste_id} nick={self.nick} syntax={self.syntax}>"

    @property
    def url(self) -> str:
        """:class:`str`: Returns the formatted url of ID and syntax."""
        syntax = f".{self.syntax}" if self.syntax else ""
        return PASTE_BASE.format(self.paste_id, syntax)

    def with_syntax(self, new_syntax: Optional[str]) -> str:
        """
        Changes the syntax of the current Paste to `new_syntax`
        Parameters
        ----------
        new_syntax: :class:`str`
            The new suffix to append to the Paste.
        """
        new_syntax = f".{new_syntax}" if new_syntax else None
        return PASTE_BASE.format(self.paste_id, new_syntax)


class PasteData:
    """
    A class representing the return data from the API after performing a GET request.
    Attributes
    ----------
    paste_id: :class:`str`
        The ID you wish to retrieve from the API.
    paste_content: :class:`str`
        The content returned from the paste.
    paste_syntax: :class:`str`
        The syntax you specified that this Paste is in.
    paste_nick: Optional[:class:`str`]
        The nick set for this paste on the API.
    paste_date: :class:`str`
        The date this paste was created on the API.
    """

    def __init__(self, paste_id: str, paste_data: Dict[str, Any]):
        self.paste_id: str = paste_id
        self._paste_data: Dict[str, Any] = paste_data
        self.paste_content: str = paste_data["data"]
        self.paste_syntax: str = paste_data["syntax"]
        self.paste_nick: Optional[str] = paste_data["nick"]
        self.paste_date: str = paste_data["created_at"]

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return f"<PasteData id={self.paste_id} nick={self.paste_nick} syntax={self.paste_syntax}>"

    @property
    def url(self) -> str:
        """:class:`str`: The Paste ID's URL."""
        syntax = f".{self.paste_syntax}" if self.paste_syntax else ""
        return PASTE_BASE.format(self.paste_id, syntax)

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: Returns a UTC datetime of when the paste was created."""
        return datetime.datetime.strptime(self.paste_date, "%Y-%m-%dT%H:%M:%S.%f")

    @property
    def content(self) -> str:
        """:class:`str`: Return the paste content but dedented correctly."""
        return dedent(self.paste_content)


class Client:
    """
    Client for interacting with the Mystb.in API.
    Attributes
    ----------
    session: Optional[Union[:class:`aiohttp.ClientSession`, :class:`requests.Session`]]
        Optional session to be passed to the creation of the client.
    """

    def __init__(
        self,
        *,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.session: Optional[aiohttp.ClientSession] = session

    async def _generate_async_session(self) -> None:
        """
        This method will create a new and blank `aiohttp.ClientSession` instance for use.
        This method should not be called if a session is passed to the constructor.
        """
        self.session = aiohttp.ClientSession()

    async def post(self, content: str, syntax: str = None) -> Paste:
        """
        This will post to the Mystb.in API and return the url.
        Can pass an optional suffix for the syntax highlighting.
        Parameters
        -----------
        content: :class:`str`
            The content you are posting to the Mystb.in API.
        syntax: :class:`str`
            The optional suffix to append the returned URL which is used for syntax highlighting on the paste.
        """
        if not self.session:
            await self._generate_async_session()

        if self.session is None:
            raise AssertionError

        multi_part_write = aiohttp.MultipartWriter()
        paste_content = multi_part_write.append(content)
        paste_content.set_content_disposition("form-data", name="data")
        paste_content = multi_part_write.append_json(
            {"meta": [{"index": 0, "syntax": syntax}]}
        )
        paste_content.set_content_disposition("form-data", name="meta")

        async with self.session.post(
            API_BASE_URL,
            data=multi_part_write,
            timeout=aiohttp.ClientTimeout(CLIENT_TIMEOUT),
        ) as response:
            status_code = response.status
            response_text = await response.text()

            if not 200 <= status_code < 300:
                raise APIError(status_code, response_text)

            response_data = await response.json()

        return Paste(response_data, syntax)

    async def get(self, paste_id: str) -> PasteData:
        """
        This will perform a GET request against the Mystb.in API and return the url.
        Must be passed a valid paste ID or URL.
        Parameters
        ----------
        paste_id: :class:`str`
            The ID of the paste you are going to retrieve.
        """
        paste_id_match = MB_URL_RE.match(paste_id)

        if not paste_id_match:
            raise BadPasteID("This is an invalid Mystb.in paste ID.")

        paste_id = paste_id_match.group("ID")

        if not self.session:
            await self._generate_async_session()

        if self.session is None:
            raise AssertionError

        async with self.session.get(
            f"{API_BASE_URL}/{paste_id}", timeout=aiohttp.ClientTimeout(CLIENT_TIMEOUT)
        ) as response:
            if 200 <= response.status < 300:
                raise BadPasteID("This is an invalid Mystb.in paste ID.")
            paste_data = await response.json()

        return PasteData(paste_id, paste_data)

    async def close(self) -> None:
        """Async only - close the session."""
        if self.session and isinstance(self.session, aiohttp.ClientSession):
            await self.session.close()
