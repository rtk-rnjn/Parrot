import asyncio
import logging

import aiohttp
from discord.ext.ipc.errors import NotConnected

log = logging.getLogger(__name__)


class Client:
    """
    Handles webserver side requests to the bot process.
    Parameters
    ----------
    host: str
        The IP or host of the IPC server, defaults to localhost
    port: int
        The port of the IPC server. If not supplied the port will be found automatically, defaults to None
    secret_key: Union[str, bytes]
        The secret key for your IPC server. Must match the server secret_key or requests will not go ahead, defaults to None
    """

    def __init__(
        self, host="localhost", port=None, multicast_port=20000, secret_key=None
    ):
        """Constructor"""
        self.loop = asyncio.get_event_loop()

        self.secret_key = secret_key

        self.host = host
        self.port = port

        self.session = None

        self.websocket = None
        self.multicast = None

        self.multicast_port = multicast_port

    @property
    def url(self):
        return "ws://{0.host}:{1}".format(
            self, self.port if self.port else self.multicast_port
        )

    async def init_sock(self):
        """Attempts to connect to the server
        Returns
        -------
        :class:`~aiohttp.ClientWebSocketResponse`
            The websocket connection to the server
        """
        self.session = aiohttp.ClientSession()

        if not self.port:
            self.multicast = await self.session.ws_connect(self.url, autoping=False)

            payload = {"connect": True, "headers": {"Authorization": self.secret_key}}
            await self.multicast.send_json(payload)
            recv = await self.multicast.receive()

            if recv.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                raise NotConnected("Multicast server connection failed.")

            port_data = recv.json()
            self.port = port_data["port"]

        self.websocket = await self.session.ws_connect(
            self.url, autoping=False, autoclose=False
        )

        return self.websocket

    async def request(self, endpoint, **kwargs):
        """Make a request to the IPC server process.
        Parameters
        ----------
        endpoint: str
            The endpoint to request on the server
        **kwargs
            The data to send to the endpoint
        """
        if not self.session:
            await self.init_sock()

        payload = {
            "endpoint": endpoint,
            "data": kwargs,
            "headers": {"Authorization": self.secret_key},
        }

        await self.websocket.send_json(payload)

        recv = await self.websocket.receive()

        if recv.type == aiohttp.WSMsgType.PING:
            await self.websocket.ping()

            return await self.request(endpoint, **kwargs)

        if recv.type == aiohttp.WSMsgType.PONG:
            return await self.request(endpoint, **kwargs)

        if recv.type == aiohttp.WSMsgType.CLOSED:
            await self.session.close()

            await asyncio.sleep(5)

            await self.init_sock()

            return await self.request(endpoint, **kwargs)

        return recv.json()
