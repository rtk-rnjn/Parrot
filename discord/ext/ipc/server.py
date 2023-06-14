import logging

import aiohttp.web

from core import Cog, Parrot

from .errors import *  # noqa: F401, F403  # pylint: disable=unused-wildcard-import

log = logging.getLogger(__name__)


def route(name=None):
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
        route_name = name or func.__name__
        setattr(func, "__ipc_route__", route_name)

        return func

    return decorator


class IpcServerResponse:
    def __init__(self, data):
        self._json = data
        self.length = len(data)

        self.endpoint = data["endpoint"]

        for key, value in data["data"].items():
            setattr(self, key, value)

    def to_json(self):
        return self._json

    def __repr__(self):
        return "<IpcServerResponse length={0.length}>".format(self)

    def __str__(self):
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

    def __init__(
        self,
        bot: Parrot,
        host="localhost",
        port=8765,
        secret_key=None,
        do_multicast=True,
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

        self._add_cog = bot.add_cog
        bot.add_cog = self.add_cog

        self.endpoints = {}
        self.sorted_endpoints = {}

    def update_endpoints(self):
        """Ensures endpoints is up to date"""
        self.endpoints = {}
        for routes in self.sorted_endpoints.values():
            self.endpoints = {**self.endpoints, **routes}

    async def add_cog(self, cog: Cog, *, override: bool = False) -> None:
        """
        Hooks into add_cog and allows
        for easy route finding within classes
        """
        await self._add_cog(cog, override=override)

        method_list = [
            getattr(cog, func)
            for func in dir(cog)
            if callable(getattr(cog, func))
            and getattr(getattr(cog, func), "__ipc_route__", None)
        ]

        # Reset endpoints for this class
        cog_name = cog.__class__.__name__
        self.sorted_endpoints[cog_name] = {}

        for method in method_list:
            method_name = getattr(method, "__ipc_route__")
            if cog_name not in self.sorted_endpoints:
                self.sorted_endpoints[cog_name] = {}
            self.sorted_endpoints[cog_name][method_name] = method

        self.update_endpoints()

        log.debug("Updated routes for Cog %s", cog_name)

    def route(self, name=None):
        """Used to register a coroutine as an endpoint when you have
        access to an instance of :class:`.Server`.
        """

        def decorator(func):
            route_name = name or func.__name__
            setattr(func, "__ipc_route__", route_name)

            if "__main__" not in self.sorted_endpoints:
                self.sorted_endpoints["__main__"] = {}

            self.sorted_endpoints["__main__"][route_name] = func

            self.update_endpoints()
            log.debug("Added IPC route %s", route_name)

            return func

        return decorator

    async def handle_accept(self, request):
        """Handles websocket requests from the client process.

        Parameters
        ----------
        request: :class:`~aiohttp.web.Request`
            The request made by the client, parsed by aiohttp.
        """
        log.info("Initiating IPC Server.")

        websocket = aiohttp.web.WebSocketResponse()
        await websocket.prepare(request)

        async for message in websocket:
            request = message.json()

            log.debug("IPC Server < %r", request)

            endpoint = request.get("endpoint")

            headers = request.get("headers")

            if not headers or headers.get("Authorization") != self.secret_key:
                log.info(
                    "Received unauthorized request (Invalid or no token provided)."
                )
                response = {"error": "Invalid or no token provided.", "code": 403}
            else:
                if not endpoint or endpoint not in self.endpoints:
                    log.info("Received invalid request (Invalid or no endpoint given).")
                    response = {"error": "Invalid or no endpoint given.", "code": 400}
                else:
                    server_response = IpcServerResponse(request)

                    try:
                        ret = await self.endpoints[endpoint](server_response)
                        response = ret
                    except Exception as error:
                        log.error(
                            "Received error while executing %r with %r",
                            endpoint,
                            request,
                        )
                        self.bot.dispatch("ipc_error", endpoint, error)

                        response = {
                            "error": "IPC route raised error of type {}".format(
                                type(error).__name__
                            ),
                            "code": 500,
                        }

            try:
                await websocket.send_json(response)
                log.debug("IPC Server > %r", response)
            except TypeError as error:
                if str(error).startswith("Object of type") and str(error).endswith(
                    "is not JSON serializable"
                ):
                    error_response = (
                        "IPC route returned values which are not able to be sent over sockets."
                        " If you are trying to send a discord.py object,"
                        " please only send the data you need."
                    )
                    log.error(error_response)

                    response = {"error": error_response, "code": 500}

                    await websocket.send_json(response)
                    log.debug("IPC Server > %r", response)

                    raise JSONEncodeError(error_response)  # noqa: F405

    async def handle_multicast(self, request):
        """Handles multicasting websocket requests from the client.

        Parameters
        ----------
        request: :class:`~aiohttp.web.Request`
            The request made by the client, parsed by aiohttp.
        """
        log.info("Initiating Multicast Server.")
        websocket = aiohttp.web.WebSocketResponse()
        await websocket.prepare(request)

        async for message in websocket:
            request = message.json()

            log.debug("Multicast Server < %r", request)

            headers = request.get("headers")

            if not headers or headers.get("Authorization") != self.secret_key:
                response = {"error": "Invalid or no token provided.", "code": 403}
            else:
                response = {
                    "message": "Connection success",
                    "port": self.port,
                    "code": 200,
                }

            log.debug("Multicast Server > %r", response)

            await websocket.send_json(response)

    async def __start(self, application, port):
        """Start both servers"""
        runner = aiohttp.web.AppRunner(application)
        await runner.setup()

        site = aiohttp.web.TCPSite(runner, self.host, port)
        await site.start()

    async def start(self):
        """Starts the IPC server."""
        if self.bot.is_ready():
            self.bot.dispatch("ipc_ready")

        self._server = aiohttp.web.Application()
        self._server.router.add_route("GET", "/", self.handle_accept)

        if self.do_multicast:
            self._multicast_server = aiohttp.web.Application()
            self._multicast_server.router.add_route("GET", "/", self.handle_multicast)

            await self.__start(self._multicast_server, self.multicast_port)

        await self.__start(self._server, self.port)
