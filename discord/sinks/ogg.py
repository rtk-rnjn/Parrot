from __future__ import annotations

import io
import subprocess

from .core import CREATE_NO_WINDOW, Filters, Sink, default_filters
from .errors import OGGSinkError


class OGGSink(Sink):
    """A special sink for .ogg files."""

    def __init__(self, *, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)

        self.encoding = "ogg"
        self.vc = None
        self.audio_data = {}

    def format_audio(self, audio):
        """Formats the recorded audio.
        Raises
        ------
        OGGSinkError
            Audio may only be formatted after recording is finished.
        OGGSinkError
            Formatting the audio failed.
        """
        if self.vc.recording:
            raise OGGSinkError(
                "Audio may only be formatted after recording is finished."
            )
        args = [
            "ffmpeg",
            "-f",
            "s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-i",
            "-",
            "-f",
            "ogg",
            "pipe:1",
        ]
        try:
            process = subprocess.Popen(
                args,
                creationflags=CREATE_NO_WINDOW,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise OGGSinkError("ffmpeg was not found.") from None
        except subprocess.SubprocessError as exc:
            raise OGGSinkError(
                "Popen failed: {0.__class__.__name__}: {0}".format(exc)
            ) from exc

        out = process.communicate(audio.file.read())[0]
        out = io.BytesIO(out)
        out.seek(0)
        audio.file = out
        audio.on_format(self.encoding)
