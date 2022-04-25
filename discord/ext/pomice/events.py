from discord import Client

from .pool import NodePool


class PomiceEvent:
    """The base class for all events dispatched by a node. 
       Every event must be formatted within your bot's code as a listener.
       i.e: If you want to listen for when a track starts, the event would be:
       ```py
       @bot.listen
       async def on_pomice_track_start(self, event):
       ```
    """
    name = "event"
    handler_args = ()

    def dispatch(self, bot: Client):
        bot.dispatch(f"pomice_{self.name}", *self.handler_args)


class TrackStartEvent(PomiceEvent):
    """Fired when a track has successfully started.
       Returns the player associated with the event and the pomice.Track object.
    """
    name = "track_start"

    def __init__(self, data: dict, player):
        self.player = player
        self.track = self.player._current

        # on_pomice_track_start(player, track)
        self.handler_args = self.player, self.track

    def __repr__(self) -> str:
        return f"<Pomice.TrackStartEvent player={self.player} track_id={self.track.track_id}>"


class TrackEndEvent(PomiceEvent):
    """Fired when a track has successfully ended.
       Returns the player associated with the event along with the pomice.Track object and reason.
    """
    name = "track_end"

    def __init__(self, data: dict, player):
        self.player = player
        self.track = self.player._ending_track
        self.reason: str = data["reason"]

        # on_pomice_track_end(player, track, reason)
        self.handler_args = self.player, self.track, self.reason

    def __repr__(self) -> str:
        return (
            f"<Pomice.TrackEndEvent player={self.player} track_id={self.track.track_id} "
            f"reason={self.reason}>"
        )


class TrackStuckEvent(PomiceEvent):
    """Fired when a track is stuck and cannot be played. Returns the player
       associated with the event along with the pomice.Track object
       to be further parsed by the end user.
    """
    name = "track_stuck"

    def __init__(self, data: dict, player):
        self.player = player
        self.track = self.player._ending_track
        self.threshold: float = data["thresholdMs"]

        # on_pomice_track_stuck(player, track, threshold)
        self.handler_args = self.player, self.track, self.threshold

    def __repr__(self) -> str:
        return f"<Pomice.TrackStuckEvent player={self.player!r} track={self.track!r} " \
               f"threshold={self.threshold!r}>"


class TrackExceptionEvent(PomiceEvent):
    """Fired when a track error has occured.
       Returns the player associated with the event along with the error code and exception.
    """
    name = "track_exception"

    def __init__(self, data: dict, player):
        self.player = player
        self.track = self.player._ending_track
        if data.get('error'):
            # User is running Lavalink <= 3.3
            self.exception: str = data["error"]
        else:
            # User is running Lavalink >=3.4
            self.exception: str = data["exception"]

        # on_pomice_track_exception(player, track, error)
        self.handler_args = self.player, self.track, self.exception

    def __repr__(self) -> str:
        return f"<Pomice.TrackExceptionEvent player={self.player!r} exception={self.exception!r}>"


class WebSocketClosedPayload:
    def __init__(self, data: dict):
        self.guild = NodePool.get_node().bot.get_guild(int(data["guildId"]))
        self.code: int = data["code"]
        self.reason: str = data["code"]
        self.by_remote: bool = data["byRemote"]

    def __repr__(self) -> str:
        return f"<Pomice.WebSocketClosedPayload guild={self.guild!r} code={self.code!r} " \
               f"reason={self.reason!r} by_remote={self.by_remote!r}>"


class WebSocketClosedEvent(PomiceEvent):
    """Fired when a websocket connection to a node has been closed.
       Returns the reason and the error code.
    """
    name = "websocket_closed"

    def __init__(self, data: dict, _):
        self.payload = WebSocketClosedPayload(data)

        # on_pomice_websocket_closed(payload)
        self.handler_args = self.payload,

    def __repr__(self) -> str:
        return f"<Pomice.WebsocketClosedEvent payload={self.payload!r}>"


class WebSocketOpenEvent(PomiceEvent):
    """Fired when a websocket connection to a node has been initiated.
       Returns the target and the session SSRC.
    """
    name = "websocket_open"

    def __init__(self, data: dict, _):
        self.target: str = data["target"]
        self.ssrc: int = data["ssrc"]

        # on_pomice_websocket_open(target, ssrc)
        self.handler_args = self.target, self.ssrc

    def __repr__(self) -> str:
        return f"<Pomice.WebsocketOpenEvent target={self.target!r} ssrc={self.ssrc!r}>"

