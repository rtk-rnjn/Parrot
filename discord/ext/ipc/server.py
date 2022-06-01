from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

import aiohttp.web  # type: ignore
from discord.ext.ipc.errors import JSONEncodeError

from core import Parrot

log = logging.getLogger(__name__)


def route(name: Optional[str] = None) -> Callable:
    """
    Used to register a coroutine as an endpoint when you don't have
    access to an instance of :class:`.Server`
    Parameters
    ----------
    name: str
        The endpoint name. If not provided the method name will be
        used.
    """

    def decorator(func):
        if not name:
            Server.ROUTES[func.__name__] = func
        else:
            Server.ROUTES[name] = func

        return func

    return decorator


class IpcServerResponse:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._json = data
        self.length = len(data)

        self.endpoint = data["endpoint"]

        self.__refresh()

    def __refresh(self) -> None:
        for key, value in self._json["data"].items():
            setattr(self, key, value)

    def __getitem__(self, key: Any) -> Any:
        data = self._json.__getitem__(key)
        self.__refresh()
        return data

    def __contains__(self, k: Any) -> bool:
        return self._json.__contains__(k)

    def __delitem__(self, k: Any):
        self._json.__delitem__(k)
        self.__refresh()

    def get(self, k: Any, default: Any = None) -> Any:
        return self._json.get(k, default)

    def pop(self, k: Any, default: Any = None) -> Any:
        data = self._json.pop(k, default)
        self.__refresh()
        return data

    def __setitem__(self, k: Any, v: Any) -> None:
        self._json(k, v)
        self.__refresh()

    def to_json(self) -> Dict[str, Any]:
        return self._json

    def __repr__(self) -> str:
        return "<IpcServerResponse length={0.length}>".format(self)

    def __str__(self) -> str:
        return self.__repr__()


class Server:
    """The IPC server. Usually used on the bot process for receiving
    requests from the client.
    Attributes
    ----------
    bot: :class:`~discord.ext.commands.Bot`
        Your bot instance
    host: str
        The host to run the IPC Server on. Defaults to localhost.
    port: int
        The port to run the IPC Server on. Defaults to 8765.
    secret_key: str
        A secret key. Used for authentication and should be the same as
        your client's secret key.
    do_multicast: bool
        Turn multicasting on/off. Defaults to True
    multicast_port: int
        The port to run the multicasting server on. Defaults to 20000
    """

    ROUTES = {}

    def __init__(
        self,
        *,
        bot: Parrot,
        host: str = "localhost",
        port: int = 1730,
        secret_key: Optional[str] = None,
        do_multicast: bool = True,
        multicast_port=20000,
    ):
        self.bot = bot
        self.loop = bot.loop

        self.secret_key = secret_key

        self.host = host
        self.port = port

        self._server = None
        self._multicast_server = None

        self.do_multicast = do_multicast
        self.multicast_port = multicast_port

        self.endpoints: Dict[str, Callable] = {}

    def route(self, name=None):
        """Used to register a coroutine as an endpoint when you have
        access to an instance of :class:`.Server`.
        Parameters
        ----------
        name: str
            The endpoint name. If not provided the method name will be used.
        """

        def decorator(func):
            if not name:
                self.endpoints[func.__name__] = func
            else:
                self.endpoints[name] = func

            return func

        return decorator

    def update_endpoints(self):
        """Called internally to update the server's endpoints for cog routes."""
        self.endpoints = {**self.endpoints, **self.ROUTES}

        self.ROUTES = {}

    async def handle_accept(self, request):
        """Handles websocket requests from the client process.
        Parameters
        ----------
        request: :class:`~aiohttp.web.Request`
            The request made by the client, parsed by aiohttp.
        """
        self.update_endpoints()

        websocket = aiohttp.web.WebSocketResponse()
        await websocket.prepare(request)

        async for message in websocket:
            request = message.json()

            endpoint = request.get("endpoint")

            headers = request.get("headers")

            if not headers or headers.get("Authorization") != self.secret_key:
                response = {"error": "Invalid or no token provided.", "code": 403}
            else:
                if not endpoint or endpoint not in self.endpoints:
                    response = {"error": "Invalid or no endpoint given.", "code": 400}
                else:
                    server_response = IpcServerResponse(request)
                    try:
                        attempted_cls = self.bot.cogs.get(
                            self.endpoints[endpoint].__qualname__.split(".")[0]
                        )

                        if attempted_cls:
                            arguments = (attempted_cls, server_response)
                        else:
                            arguments = (server_response,)
                    except AttributeError:
                        # Support base Client
                        arguments = (server_response,)

                    try:
                        ret = await self.endpoints[endpoint](*arguments)
                        response = ret
                    except Exception as error:
                        self.bot.dispatch("ipc_error", endpoint, error)

                        response = {
                            "error": "IPC route raised error of type {}".format(
                                type(error).__name__
                            ),
                            "code": 500,
                        }

            try:
                await websocket.send_json(response)
            except TypeError as error:
                if str(error).startswith("Object of type") and str(error).endswith(
                    "is not JSON serializable"
                ):
                    error_response = (
                        "IPC route returned values which are not able to be sent over sockets."
                        " If you are trying to send a discord.py object,"
                        " please only send the data you need."
                    )

                    response = {"error": error_response, "code": 500}

                    await websocket.send_json(response)

                    raise JSONEncodeError(error_response)

    async def handle_multicast(self, request):
        """Handles multicasting websocket requests from the client.
        Parameters
        ----------
        request: :class:`~aiohttp.web.Request`
            The request made by the client, parsed by aiohttp.
        """
        websocket = aiohttp.web.WebSocketResponse()
        await websocket.prepare(request)

        async for message in websocket:
            request = message.json()

            headers = request.get("headers")

            if not headers or headers.get("Authorization") != self.secret_key:
                response = {"error": "Invalid or no token provided.", "code": 403}
            else:
                response = {
                    "message": "Connection success",
                    "port": self.port,
                    "code": 200,
                }

            await websocket.send_json(response)

    async def __start(self, application, port):
        """Start both servers"""
        runner = aiohttp.web.AppRunner(application)
        await runner.setup()

        site = aiohttp.web.TCPSite(runner, self.host, port)
        await site.start()

    async def start(self):
        """Starts the IPC server."""
        # self.bot.dispatch("ipc_ready")

        self._server = aiohttp.web.Application()
        self._server.router.add_route("GET", "/", self.handle_accept)

        if self.do_multicast:
            self._multicast_server = aiohttp.web.Application()
            self._multicast_server.router.add_route("GET", "/", self.handle_multicast)

            self.bot.loop.create_task(
                self.__start(self._multicast_server, self.multicast_port)
            )
        self.bot.loop.create_task(self.__start(self._server, self.port))
