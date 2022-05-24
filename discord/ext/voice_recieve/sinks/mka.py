from __future__ import annotations

import io
import os
import subprocess

from .core import CREATE_NO_WINDOW, Filters, Sink, default_filters
from .errors import MKASinkError


class MKASink(Sink):
    """A special sink for .mka files.
    """

    def __init__(self, *, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)

        self.encoding = "mka"
        self.vc = None
        self.audio_data = {}

    def format_audio(self, audio):
        """Formats the recorded audio.
        Raises
        ------
        MKASinkError
            Audio may only be formatted after recording is finished.
        MKASinkError
            Formatting the audio failed.
        """
        if self.vc.recording:
            raise MKASinkError("Audio may only be formatted after recording is finished.")
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
            "matroska",
            "pipe:1",
        ]
        try:
            process = subprocess.Popen(
                args,
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise MKASinkError("ffmpeg was not found.") from None
        except subprocess.SubprocessError as exc:
            raise MKASinkError("Popen failed: {0.__class__.__name__}: {0}".format(exc)) from exc

        out = process.communicate(audio.file.read())[0]
        out = io.BytesIO(out)
        out.seek(0)
        audio.file = out
        audio.on_format(self.encoding)