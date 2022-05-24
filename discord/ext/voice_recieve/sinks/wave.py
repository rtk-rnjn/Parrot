from __future__ import annotations

import wave

from .core import Filters, Sink, default_filters
from .errors import WaveSinkError


class WaveSink(Sink):
    """A special sink for .wav(wave) files.
    """

    def __init__(self, *, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)

        self.encoding = "wav"
        self.vc = None
        self.audio_data = {}

    def format_audio(self, audio):
        """Formats the recorded audio.
        Raises
        ------
        WaveSinkError
            Audio may only be formatted after recording is finished.
        WaveSinkError
            Formatting the audio failed.
        """
        if self.vc.recording:
            raise WaveSinkError("Audio may only be formatted after recording is finished.")
        data = audio.file

        with wave.open(data, "wb") as f:
            f.setnchannels(self.vc.decoder.CHANNELS)
            f.setsampwidth(self.vc.decoder.SAMPLE_SIZE // self.vc.decoder.CHANNELS)
            f.setframerate(self.vc.decoder.SAMPLING_RATE)

        data.seek(0)
        audio.on_format(self.encoding)