from __future__ import annotations

from collections.abc import Sequence

__all__ = ("plural", "human_join")


class plural:
    """Format a number together with its singular or plural noun.

    The class is intended to be used with Python's format syntax::

        f"{plural(1):apple}"
        f"{plural(2):apple}"

    A custom plural form can be supplied after ``|``::

        f"{plural(1):child|children}"
        f"{plural(2):child|children}"

    Appending ``!`` suppresses the numeric value::

        f"{plural(1):apple!}"   # "apple"
        f"{plural(2):apple!}"   # "apples"
    """

    def __init__(self, value: int):
        """Create a plural formatter for the given numeric value."""
        self.value: int = value

    def __format__(self, format_spec: str) -> str:
        """Format the value using the singular/plural forms in ``format_spec``.

        The value is considered singular only when its absolute value is
        exactly one, so negative values are handled naturally as well.

        ``format_spec`` may contain ``singular|plural`` to provide an explicit
        plural form. If no plural form is supplied, ``s`` is appended to the
        singular form.

        A trailing ``!`` omits the numeric value from the result.
        """
        v = self.value
        skip_value = format_spec.endswith("!")

        if skip_value:
            format_spec = format_spec[:-1]

        singular, _, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"

        if skip_value:
            if abs(v) != 1:
                return plural
            return singular

        if abs(v) != 1:
            return f"{v} {plural}"

        return f"{v} {singular}"


def human_join(
    seq: Sequence,
    delim: str = ", ",
    final: str = "or",
) -> str:
    """Join strings into natural-language list formatting.

    Examples
    --------
    ``["a"]`` becomes ``"a"``.

    ``["a", "b"]`` becomes ``"a or b"``.

    ``["a", "b", "c"]`` becomes ``"a, b or c"``.

    Parameters such as ``delim`` and ``final`` allow the same helper to be
    used for different styles, for example ``"a, b and c"``.
    """
    size = len(seq)

    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return delim.join(seq[:-1]) + f" {final} {seq[-1]}"
