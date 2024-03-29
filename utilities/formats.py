from __future__ import annotations

import datetime
import re
from typing import Any


class plural:
    def __init__(self, value: int) -> None:
        self.value = value

    def __format__(self, format_spec: str) -> str:
        v = self.value
        singular, sep, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        return f"{v} {plural}" if abs(v) != 1 else f"{v} {singular}"


def human_join(seq, delim=", ", final="or"):
    size = len(seq)
    if size == 0:
        return ""
    if size == 1:
        return seq[0]
    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"
    return f"{delim.join(seq[:-1])} {final} {seq[-1]}"


class TabularData:
    def __init__(self) -> None:
        self._widths = []
        self._columns = []
        self._rows = []

    def set_columns(self, columns):
        self._columns = columns
        self._widths = [len(c) + 2 for c in columns]

    def add_row(self, row):
        rows = [str(r) for r in row]
        self._rows.append(rows)
        for index, element in enumerate(rows):
            width = len(element) + 2
            if width > self._widths[index]:
                self._widths[index] = width

    def add_rows(self, rows):
        for row in rows:
            self.add_row(row)

    def render(self):
        """Renders a table in rST format.

        Example:
        -------
        +-------+-----+
        | Name  | Age |
        +-------+-----+
        | Alice | 24  |
        |  Bob  | 19  |
        +-------+-----+.
        """
        sep = "+".join("-" * w for w in self._widths)
        sep = f"+{sep}+"

        to_draw = [sep]

        def get_entry(d):
            elem = "|".join(f"{e:^{self._widths[i]}}" for i, e in enumerate(d))
            return f"|{elem}|"

        to_draw.append(get_entry(self._columns))
        to_draw.append(sep)

        for row in self._rows:
            to_draw.append(get_entry(row))

        to_draw.append(sep)
        return "\n".join(to_draw)


def format_dt(dt: datetime.datetime | int | float, style: str = None) -> str:
    """Formats a datetime object or timestamp into a Discord-style timestamp."""
    if isinstance(dt, int | float):
        dt = datetime.datetime.utcfromtimestamp(dt)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f"<t:{int(dt.timestamp())}>"
    return f"<t:{int(dt.timestamp())}:{style}>"


def suppress_links(message: str) -> str:
    """Accepts a message that may contain links, suppresses them, and returns them."""
    for link in set(re.findall(r"https?://[^\s]+", message, re.IGNORECASE)):
        message = message.replace(link, f"<{link}>")
    return message


def get_flag(ls: list, ann: Any, *, deli: Any, pref: Any, alis: Any, default: bool) -> list:
    for flag in ann.get_flags().values():
        if flag.required:
            ls.append(f"<{pref}{flag.name}{'|'.join(alis)}{deli}>")
        elif default:
            ls.append(f"[{pref}{flag.name}{'|'.join(list(alis))}{deli}={flag.default}]")
        else:
            ls.append(f"[{pref}{flag.name}{'|'.join(list(alis))}{deli}]")
    return ls
