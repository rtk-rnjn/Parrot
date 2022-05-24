from discord.errors import DiscordException


class SinkException(DiscordException):
    """Raised when a Sink error occurs."""


class RecordingException(SinkException):
    """Exception that's thrown when there is an error while trying to record
    audio from a voice channel.
    """

    pass


class MP3SinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`MP3Sink`"""

    pass


class MP4SinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`MP4Sink`"""

    pass


class OGGSinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`OGGSink`"""

    pass


class MKVSinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`MKVSink`"""

    pass


class WaveSinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`WaveSink`"""

    pass


class M4ASinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`M4ASink`"""

    pass


class MKASinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`MKAsSink`"""

    pass
