import io
import os
import subprocess
import time

from .core import CREATE_NO_WINDOW, Filters, Sink, default_filters
from .errors import MP4SinkError


class MP4Sink(Sink):
    """A special sink for .mp4 files.
    """

    def __init__(self, *, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)

        self.encoding = "mp4"
        self.vc = None
        self.audio_data = {}

    def format_audio(self, audio):
        """Formats the recorded audio.
        Raises
        ------
        MP4SinkError
            Audio may only be formatted after recording is finished.
        MP4SinkError
            Formatting the audio failed.
        """
        if self.vc.recording:
            raise MP4SinkError("Audio may only be formatted after recording is finished.")
        mp4_file = f"{time.time()}.tmp"
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
            "mp4",
            mp4_file,
        ]
        if os.path.exists(mp4_file):
            os.remove(mp4_file)  # process will get stuck asking whether or not to overwrite, if file already exists.
        try:
            process = subprocess.Popen(args, creationflags=CREATE_NO_WINDOW, stdin=subprocess.PIPE)
        except FileNotFoundError:
            raise MP4SinkError("ffmpeg was not found.") from None
        except subprocess.SubprocessError as exc:
            raise MP4SinkError("Popen failed: {0.__class__.__name__}: {0}".format(exc)) from exc

        process.communicate(audio.file.read())

        with open(mp4_file, "rb") as f:
            audio.file = io.BytesIO(f.read())
            audio.file.seek(0)
        os.remove(mp4_file)

        audio.on_format(self.encoding)