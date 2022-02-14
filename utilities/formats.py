from __future__ import annotations

import datetime
import re
from discord.ext import commands

from typing import Union, Literal, Any


class plural:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        v = self.value
        singular, sep, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        if abs(v) != 1:
            return f"{v} {plural}"
        return f"{v} {singular}"


def human_join(seq, delim=", ", final="or"):
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return delim.join(seq[:-1]) + f" {final} {seq[-1]}"


class TabularData:
    def __init__(self):
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
        +-------+-----+
        | Name  | Age |
        +-------+-----+
        | Alice | 24  |
        |  Bob  | 19  |
        +-------+-----+
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


def format_dt(dt, style=None) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f"<t:{int(dt.timestamp())}>"
    return f"<t:{int(dt.timestamp())}:{style}>"


def format_dt_with_int(dt: int, style=None) -> str:
    return f"<t:{dt}:{style if style else ''}>"


def suppress_links(message: str) -> str:
    """Accepts a message that may contain links, suppresses them, and returns them."""
    for link in set(re.findall(r"https?://[^\s]+", message, re.IGNORECASE)):
        message = message.replace(link, f"<{link}>")
    return message


def get_flag(
    ls: list,
    ann: Any,
    *,
    deli: Any,
    pref: Any,
    alis: Any,
) -> list:
    for flag in (ann).get_flags().values():
        if flag.required:
            ls.append(f"<{pref}{flag.name}{'|'.join(alis)}{deli}>")
        else:
            ls.append(f"[{pref}{flag.name}{'|'.join(list(alis))}{deli}={flag.default}]")
    return ls


def get_cmd_signature(cmd, *, default: bool = True):
    if cmd.usage is not None:
        return cmd.usage

    params = cmd.clean_params
    if not params:
        return ""

    result = []
    for name, param in params.items():
        greedy = isinstance(param.annotation, commands.Greedy)
        optional = False  # postpone evaluation of if it's an optional argument

        # for typing.Literal[...], typing.Optional[typing.Literal[...]], and Greedy[typing.Literal[...]], the
        # parameter signature is a literal list of it's values
        annotation = param.annotation.converter if greedy else param.annotation
        origin = getattr(annotation, "__origin__", None)
        if not greedy and origin is Union:
            none_cls = type(None)
            union_args = annotation.__args__
            optional = union_args[-1] is none_cls
            if len(union_args) == 2 and optional:
                annotation = union_args[0]
                origin = getattr(annotation, "__origin__", None)

        if origin is Literal:
            name = "|".join(
                f'"{v}"' if isinstance(v, str) else str(v) for v in annotation.__args__
            )
        if param.default is not param.empty:
            # We don't want None or '' to trigger the [name=value] case and instead it should
            # do [name] since [name=None] or [name=] are not exactly useful for the user.
            should_print = (
                param.default
                if isinstance(param.default, str)
                else param.default is not None
            )
            if should_print:
                result.append(
                    f"[{name}={param.default}]"
                    if not greedy
                    else f"[{name}={param.default}]..."
                )
                continue
            else:
                result.append(f"[{name}]")

        elif param.kind == param.VAR_POSITIONAL:
            if cmd.require_var_positional:
                result.append(f"<{name}...>")
            else:
                result.append(f"[{name}...]")
        elif greedy:
            result.append(f"[{name}]...")
        elif optional:
            result.append(f"[{name}]")
        elif isinstance(param.annotation, commands.flags.FlagsMeta):
            ann = param.annotation
            deli = ann.__commands_flag_delimiter__
            pref = ann.__commands_flag_prefix__
            alis = ann.__commands_flag_aliases__
            get_flag(result, param.annotation, deli=deli, pref=pref, alis=alis)
        else:
            result.append(f"<{name}>")

    return " ".join(result)
