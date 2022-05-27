from discord.errors import DiscordException


class SinkException(DiscordException):
    """Raised when a Sink error occurs."""


class RecordingException(SinkException):
    """Exception that's thrown when there is an error while trying to record
    audio from a voice channel.
    """


class MP3SinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`MP3Sink`"""


class MP4SinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`MP4Sink`"""


class OGGSinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`OGGSink`"""


class MKVSinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`MKVSink`"""


class WaveSinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`WaveSink`"""


class M4ASinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`M4ASink`"""


class MKASinkError(SinkException):
    """Exception thrown when a exception occurs with :class:`MKAsSink`"""
