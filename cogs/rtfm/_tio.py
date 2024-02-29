from __future__ import annotations

import zlib
from functools import partial

import aiohttp

to_bytes = partial(bytes, encoding="utf-8")


def _to_tio_string(couple):
    name, obj = couple[0], couple[1]
    if not obj:
        return b""
    if isinstance(obj, list):
        content = [f"V{name}", str(len(obj))] + obj
        return to_bytes("\x00".join(content) + "\x00")
    return to_bytes(f"F{name}\x00{len(to_bytes(obj))}\x00{obj}\x00")


class Tio:
    def __init__(
        self,
        language: str,
        code: str,
        inputs="",
        compiler_flags=None,
        command_line_options=None,
        args=None,
    ) -> None:
        compiler_flags = compiler_flags or []
        command_line_options = command_line_options or []
        args = args or []
        self.backend = "https://tio.run/cgi-bin/run/api/"
        self.json = "https://tio.run/languages.json"

        strings = {
            "lang": [language],
            ".code.tio": code,
            ".input.tio": inputs,
            "TIO_CFLAGS": compiler_flags,
            "TIO_OPTIONS": command_line_options,
            "args": args,
        }

        bytes_ = b"".join(map(_to_tio_string, zip(strings.keys(), strings.values(), strict=False))) + b"R"

        # This returns a DEFLATE-compressed bytestring, which is what the API requires
        self.request = zlib.compress(bytes_, 9)[2:-4]

    async def send(self) -> str | None:
        async with aiohttp.ClientSession() as client_session:
            res = await client_session.post(self.backend, data=self.request)
            if res.status != 200:
                msg = f"Failed to get response from TIO: {res.status}"
                raise aiohttp.ClientError(msg)

            data = await res.read()
            data = data.decode("utf-8")
            return data.replace(data[:16], "")  # remove token
