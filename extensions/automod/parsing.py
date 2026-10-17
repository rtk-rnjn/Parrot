from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from core.utils import format_compact_duration
from core.utils.time import ShortTime

_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)
_UNIT_FIELDS = {
    "y": "years",
    "mon": "months",
    "w": "weeks",
    "d": "days",
    "h": "hours",
    "m": "minutes",
    "s": "seconds",
}


def parse_duration(
    text: str,
    *,
    error: type[Exception],
    name: str,
    default_unit: str = "m",
    units: str = "smhdw",
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    text = text.strip().lower()
    if not text:
        seconds = 0
    else:
        argument = f"{text}{default_unit}" if text.isdecimal() else text
        match = ShortTime.compiled.fullmatch(argument)
        allowed_fields = {_UNIT_FIELDS[unit] for unit in units}
        if match is None or any(match.group(field) and field not in allowed_fields for field in _UNIT_FIELDS.values()):
            msg = f"**{name}** must look like `30m`, `12h`, `7d` or `1d 12h` (units: {', '.join(units)})."
            raise error(msg)

        seconds = int((ShortTime(argument, now=_EPOCH).dt - _EPOCH).total_seconds())

    if seconds < minimum or (maximum is not None and seconds > maximum):
        low = format_duration(minimum)
        bounds = f"at least {low}" if maximum is None else f"between {low} and {format_duration(maximum)}"
        msg = f"**{name}** must be {bounds}."
        raise error(msg)
    return seconds


format_duration = format_compact_duration


class ParserSupport[ErrorT: Exception]:
    def __init__(self, error: type[ErrorT]) -> None:
        self.error = error

    def require_dict(self, value: object, name: str) -> Mapping[str, object]:
        if not isinstance(value, Mapping):
            raise self.error(name + " must be an object")
        return value

    def require_int(self, data: Mapping[str, object], key: str, *, minimum: int = 0) -> int:
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise self.error(repr(key) + " must be an integer")
        if value < minimum:
            raise self.error(repr(key) + " must be >= " + str(minimum))
        return value

    def optional_bool(self, data: Mapping[str, object], key: str, default: bool = False) -> bool:
        value = data.get(key, default)
        if not isinstance(value, bool):
            raise self.error(repr(key) + " must be a boolean")
        return value

    def optional_string(self, data: Mapping[str, object], key: str) -> str | None:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise self.error(repr(key) + " must be a string")
        return value

    def optional_int_or_none(self, data: Mapping[str, object], key: str, *, minimum: int = 0) -> int | None:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            raise self.error(repr(key) + " must be an integer or null")
        if value < minimum:
            raise self.error(repr(key) + " must be >= " + str(minimum))
        return value

    def require_int_tuple(self, data: Mapping[str, object], key: str) -> tuple[int, ...]:
        value = data.get(key)
        if not isinstance(value, list):
            raise self.error(repr(key) + " must be an array of integers")

        out: list[int] = []
        for item in value:
            if not isinstance(item, int) or isinstance(item, bool):
                raise self.error(repr(key) + " must contain only integers")
            if item < 0:
                raise self.error(repr(key) + " values must be >= 0")
            out.append(item)
        return tuple(out)
