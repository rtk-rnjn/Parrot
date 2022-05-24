from __future__ import annotations

from .core import Filters, Sink, default_filters


class PCMSink(Sink):
    """A special sink for .pcm files.
    """

    def __init__(self, *, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)

        self.encoding = "pcm"
        self.vc = None
        self.audio_data = {}

    def format_audio(self, audio):
        return