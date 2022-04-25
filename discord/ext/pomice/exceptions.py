class PomiceException(Exception):
    """Base of all Pomice exceptions."""


class NodeException(Exception):
    """Base exception for nodes."""


class NodeCreationError(NodeException):
    """There was a problem while creating the node."""


class NodeConnectionFailure(NodeException):
    """There was a problem while connecting to the node."""


class NodeConnectionClosed(NodeException):
    """The node's connection is closed."""
    pass


class NodeNotAvailable(PomiceException):
    """The node is currently unavailable."""
    pass


class NoNodesAvailable(PomiceException):
    """There are no nodes currently available."""
    pass


class TrackInvalidPosition(PomiceException):
    """An invalid position was chosen for a track."""
    pass


class TrackLoadError(PomiceException):
    """There was an error while loading a track."""
    pass


class FilterInvalidArgument(PomiceException):
    """An invalid argument was passed to a filter."""
    pass


class SpotifyAlbumLoadFailed(PomiceException):
    """The pomice Spotify client was unable to load an album."""
    pass


class SpotifyTrackLoadFailed(PomiceException):
    """The pomice Spotify client was unable to load a track."""
    pass


class SpotifyPlaylistLoadFailed(PomiceException):
    """The pomice Spotify client was unable to load a playlist."""
    pass


class InvalidSpotifyClientAuthorization(PomiceException):
    """No Spotify client authorization was provided for track searching."""
    pass

