from __future__ import annotations

import io
import os
import struct
import sys
import threading
import time

from .errors import SinkException

from discord.types import snowflake
from discord.channel import VoiceChannel


__all__ = (
    "Filters",
    "Sink",
    "AudioData",
    "RawData",
)


if sys.platform != "win32":
    CREATE_NO_WINDOW = 0
else:
    CREATE_NO_WINDOW = 0x08000000  # type: ignore


default_filters = {
    "time": 0,
    "users": [],
    "max_size": 0,
}


class Filters:
    """Filters for :class:`~.Sink`"""

    def __init__(self, **kwargs):
        self.filtered_users = kwargs.get("users", default_filters["users"])
        self.seconds = kwargs.get("time", default_filters["time"])
        self.max_size = kwargs.get("max_size", default_filters["max_size"])
        self.finished = False

    @staticmethod
    def container(func):  # Contains all filters
        def _filter(self, data, user):
            if not self.filtered_users or user in self.filtered_users:
                return func(self, data, user)

        return _filter

    def init(self):
        if self.seconds != 0:
            thread = threading.Thread(target=self.wait_and_stop)
            thread.start()

    def wait_and_stop(self):
        time.sleep(self.seconds)
        if self.finished:
            return
        self.vc.stop_recording()


class RawData:
    """Handles raw data from Discord so that it can be decrypted and decoded to be used."""

    def __init__(self, data, client):
        self.data = bytearray(data)
        self.client = client

        self.header = data[:12]
        self.data = self.data[12:]

        unpacker = struct.Struct(">xxHII")
        self.sequence, self.timestamp, self.ssrc = unpacker.unpack_from(self.header)
        self.decrypted_data = getattr(self.client, f"_decrypt_{self.client.mode}")(
            self.header, self.data
        )
        self.decoded_data = None

        self.user_id = None


class AudioData:
    """Handles data that's been completely decrypted and decoded and is ready to be saved to file."""

    def __init__(self, file):
        self.file = file
        self.finished = False

    def write(self, data):
        """Writes audio data.
        Raises
        ------
        ClientException
            The AudioData is already finished writing.
        """
        if self.finished:
            raise SinkException("The AudioData is already finished writing.")
        try:
            self.file.write(data)
        except ValueError:
            pass

    def cleanup(self):
        """Finishes and cleans up the audio data.
        Raises
        ------
        ClientException
            The AudioData is already finished writing.
        """
        if self.finished:
            raise SinkException("The AudioData is already finished writing.")
        self.file.seek(0)
        self.finished = True

    def on_format(self, encoding):
        """Called when audio data is formatted.
        Raises
        ------
        ClientException
            The AudioData is still writing.
        """
        if not self.finished:
            raise SinkException("The AudioData is still writing.")


class Sink(Filters):
    """A sink "stores" recorded audio data.
    Can be subclassed for extra customizablilty.
    .. warning::
        It is recommended you use
        the officially provided sink classes,
        such as :class:`~discord.sinks.WaveSink`.
    just replace the following like so: ::
        vc.start_recording(
            MySubClassedSink(),
            finished_callback,
            ctx.channel,
        )
    Raises
    ------
    ClientException
        An invalid encoding type was specified.
    ClientException
        Audio may only be formatted after recording is finished.
    """

    def __init__(self, *, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)
        self.vc: VoiceChannel = None
        self.audio_data = {}

    def init(self, vc):  # called under listen
        self.vc: VoiceChannel = vc
        super().init()

    @Filters.container
    def write(self, data, user):
        if user not in self.audio_data:
            file = io.BytesIO()
            self.audio_data.update({user: AudioData(file)})

        file = self.audio_data[user]
        file.write(data)

    def cleanup(self):
        self.finished = True
        for file in self.audio_data.values():
            file.cleanup()
            self.format_audio(file)

    def get_all_audio(self):
        """Gets all audio files."""
        return [x.file for x in self.audio_data.values()]

    def get_user_audio(self, user: snowflake.Snowflake):
        """Gets the audio file(s) of one specific user."""
        return os.path.realpath(self.audio_data.pop(user))
