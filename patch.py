from __future__ import annotations

from discord.sinks import RawData, RecordingException, Sink
from discord import VoiceClient
from discord import opus

import struct
import threading
import time
import asyncio
import select
import gc
import nacl.secret  # type: ignore


class DecodeManager(threading.Thread, opus._OpusStruct):
    def __init__(self, client):
        super().__init__(daemon=True, name="DecodeManager")

        self.client = client
        self.decode_queue = []

        self.decoder = {}

        self._end_thread = threading.Event()

    def decode(self, opus_frame):
        if not isinstance(opus_frame, RawData):
            raise TypeError("opus_frame should be a RawData object.")
        self.decode_queue.append(opus_frame)

    def run(self):
        while not self._end_thread.is_set():
            try:
                data = self.decode_queue.pop(0)
            except IndexError:
                continue

            try:
                if data.decrypted_data is None:
                    continue
                else:
                    data.decoded_data = self.get_decoder(data.ssrc).decode(data.decrypted_data)
            except opus.OpusError:
                print("Error occurred while decoding opus frame.")
                continue

            self.client.recv_decoded_audio(data)

    def stop(self):
        while self.decoding:
            time.sleep(0.1)
            self.decoder = {}
            gc.collect()
            print("Decoder Process Killed")
        self._end_thread.set()

    def get_decoder(self, ssrc):
        d = self.decoder.get(ssrc)
        if d is not None:
            return d
        self.decoder[ssrc] = opus.Decoder()
        return self.decoder[ssrc]

    @property
    def decoding(self):
        return bool(self.decode_queue)

class ParrotVoiceClient(VoiceClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.paused = False
        self.recording = False
        self.user_timestamps = {}
        self.sink = None
        self.starting_time = None
        self.stopping_time = None

    def _decrypt_xsalsa20_poly1305(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))

        nonce = bytearray(24)
        nonce[:12] = header

        return self.strip_header_ext(box.decrypt(bytes(data), bytes(nonce)))

    def _decrypt_xsalsa20_poly1305_suffix(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))

        nonce_size = nacl.secret.SecretBox.NONCE_SIZE
        nonce = data[-nonce_size:]

        return self.strip_header_ext(box.decrypt(bytes(data[:-nonce_size]), nonce))

    def _decrypt_xsalsa20_poly1305_lite(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))

        nonce = bytearray(24)
        nonce[:4] = data[-4:]
        data = data[:-4]

        return self.strip_header_ext(box.decrypt(bytes(data), bytes(nonce)))

    @staticmethod
    def strip_header_ext(data):
        if data[0] == 0xBE and data[1] == 0xDE and len(data) > 4:
            _, length = struct.unpack_from(">HH", data)
            offset = 4 + length * 4
            data = data[offset:]
        return data

    def get_ssrc(self, user_id):
        return {info["user_id"]: ssrc for ssrc, info in self.ws.ssrc_map.items()}[user_id]

    def unpack_audio(self, data):
        """Takes an audio packet received from Discord and decodes it into pcm audio data.
        If there are no users talking in the channel, `None` will be returned.
        You must be connected to receive audio.
    
        Parameters
        ---------
        data: :class:`bytes`
            Bytes received by Discord via the UDP connection used for sending and receiving voice data.
        """
        if 200 <= data[1] <= 204:
            # RTCP received.
            # RTCP provides information about the connection
            # as opposed to actual audio data, so it's not
            # important at the moment.
            return
        if self.paused:
            return

        data = RawData(data, self)

        if data.decrypted_data == b"\xf8\xff\xfe":  # Frame of silence
            return

        self.decoder.decode(data)

    def start_recording(self, sink, callback, *args):
        """The bot will begin recording audio from the current voice channel it is in.
        This function uses a thread so the current code line will not be stopped.
        Must be in a voice channel to use.
        Must not be already recording.

        Parameters
        ----------
        sink: :class:`.Sink`
            A Sink which will "store" all the audio data.
        callback: :ref:`coroutine <coroutine>`
            A function which is called after the bot has stopped recording.
        *args:
            Args which will be passed to the callback function.
        Raises
        ------
        RecordingException
            Not connected to a voice channel.
        RecordingException
            Already recording.
        RecordingException
            Must provide a Sink object.
        """
        if not self.is_connected():
            raise RecordingException("Not connected to voice channel.")
        if self.recording:
            raise RecordingException("Already recording.")
        if not isinstance(sink, Sink):
            raise RecordingException("Must provide a Sink object.")

        self.empty_socket()

        self.decoder = DecodeManager(self)
        self.decoder.start()
        self.recording = True
        self.sink = sink
        sink.init(self)

        t = threading.Thread(
            target=self.recv_audio,
            args=(
                sink,
                callback,
                *args,
            ),
        )
        t.start()

    def stop_recording(self):
        """Stops the recording.
        Must be already recording.

        Raises
        ------
        RecordingException
            Not currently recording.
        """
        if not self.recording:
            raise RecordingException("Not currently recording audio.")
        self.decoder.stop()
        self.recording = False
        self.paused = False

    def toggle_pause(self):
        """Pauses or unpauses the recording.
        Must be already recording.

        Raises
        ------
        RecordingException
            Not currently recording.
        """
        if not self.recording:
            raise RecordingException("Not currently recording audio.")
        self.paused = not self.paused

    def empty_socket(self):
        while True:
            ready, _, _ = select.select([self.socket], [], [], 0.0)
            if not ready:
                break
            for s in ready:
                s.recv(4096)

    def recv_audio(self, sink, callback, *args):
        # Gets data from _recv_audio and sorts
        # it by user, handles pcm files and
        # silence that should be added.

        self.user_timestamps = {}
        self.starting_time = time.perf_counter()
        while self.recording:
            ready, _, err = select.select([self.socket], [], [self.socket], 0.01)
            if not ready:
                if err:
                    print(f"Socket error: {err}")
                continue

            try:
                data = self.socket.recv(4096)
            except OSError:
                self.stop_recording()
                continue

            self.unpack_audio(data)

        self.stopping_time = time.perf_counter()
        self.sink.cleanup()
        callback = asyncio.run_coroutine_threadsafe(callback(self.sink, *args), self.loop)
        result = callback.result()

        if result is not None:
            print(result)

    def recv_decoded_audio(self, data):
        if data.ssrc not in self.user_timestamps:
            self.user_timestamps.update({data.ssrc: data.timestamp})
            # Add silence when they were not being recorded.
            silence = 0
        else:
            silence = data.timestamp - self.user_timestamps[data.ssrc] - 960
            self.user_timestamps[data.ssrc] = data.timestamp

        data.decoded_data = struct.pack("<h", 0) * silence * opus._OpusStruct.CHANNELS + data.decoded_data
        while data.ssrc not in self.ws.ssrc_map:
            time.sleep(0.05)
        self.sink.write(data.decoded_data, self.ws.ssrc_map[data.ssrc]["user_id"])