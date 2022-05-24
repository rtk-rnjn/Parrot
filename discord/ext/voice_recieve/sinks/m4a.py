from __future__ import annotations

import io
import os
import subprocess
import time

from .core import CREATE_NO_WINDOW, Filters, Sink, default_filters
from .errors import M4ASinkError


class M4ASink(Sink):
    """A special sink for .m4a files.
    """

    def __init__(self, *, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)

        self.encoding = "m4a"
        self.vc = None
        self.audio_data = {}

    def format_audio(self, audio):
        """Formats the recorded audio.
        Raises
        ------
        M4ASinkError
            Audio may only be formatted after recording is finished.
        M4ASinkError
            Formatting the audio failed.
        """
        if self.vc.recording:
            raise M4ASinkError("Audio may only be formatted after recording is finished.")
        m4a_file = f"{time.time()}.tmp"
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
            "ipod",
            m4a_file,
        ]
        if os.path.exists(m4a_file):
            os.remove(m4a_file)  # process will get stuck asking whether or not to overwrite, if file already exists.
        try:
            process = subprocess.Popen(args, creationflags=CREATE_NO_WINDOW, stdin=subprocess.PIPE)
        except FileNotFoundError:
            raise M4ASinkError("ffmpeg was not found.") from None
        except subprocess.SubprocessError as exc:
            raise M4ASinkError("Popen failed: {0.__class__.__name__}: {0}".format(exc)) from exc

        process.communicate(audio.file.read())

        with open(m4a_file, "rb") as f:
            audio.file = io.BytesIO(f.read())
            audio.file.seek(0)
        os.remove(m4a_file)

        audio.on_format(self.encoding)