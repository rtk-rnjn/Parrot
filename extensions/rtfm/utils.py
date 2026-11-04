from __future__ import annotations

import re
import zlib
from dataclasses import dataclass

SPHINX_INV_LINE = re.compile(r"(.+?)\s+(\S+:\S+)\s+(-?\d+)\s+(\S+)\s+(.*)")
INV_MAGIC = b"# Sphinx inventory version 2"

ROLE_LABELS = {
    "data": "constant / data",
    "label": "section",
    "term": "glossary term",
}


@dataclass(frozen=True, slots=True)
class SphinxEntry:
    name: str
    domain_role: str
    priority: int
    url: str
    dispname: str

    @property
    def domain(self) -> str:
        return self.domain_role.partition(":")[0]

    @property
    def role(self) -> str:
        role = self.domain_role.partition(":")[2]
        return "label" if self.domain_role == "std:doc" else role

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role)


def _split_inventory(raw: bytes) -> tuple[str, bytes] | None:
    parts = raw.split(b"\n", 4)
    if len(parts) < 5 or not parts[0].startswith(INV_MAGIC) or b"zlib" not in parts[3]:
        return None
    project = parts[1].decode("utf-8", "replace").strip().removeprefix("# Project: ")
    return project, parts[4]


def inventory_project(raw: bytes) -> str:
    split = _split_inventory(raw)
    return split[0] if split else ""


def parse_sphinx_inventory(raw: bytes, base_url: str) -> list[SphinxEntry]:
    """Parse a Sphinx v2 ``objects.inv`` into :class:`SphinxEntry` items. Raises ValueError if it isn't one."""
    split = _split_inventory(raw)
    if split is None:
        msg = "not a v2 zlib Sphinx inventory"
        raise ValueError(msg)
    try:
        body = zlib.decompress(split[1]).decode("utf-8", "replace")
    except zlib.error as exc:
        msg = f"corrupt inventory: {exc}"
        raise ValueError(msg) from exc

    base = base_url.rstrip("/")
    entries: list[SphinxEntry] = []
    for line in body.splitlines():
        match = SPHINX_INV_LINE.match(line.strip())
        if not match:
            continue
        name, domain_role, priority, location, dispname = match.groups()
        if location.endswith("$"):
            location = location[:-1] + name
        entries.append(
            SphinxEntry(
                name=name,
                domain_role=domain_role,
                priority=int(priority),
                url=f"{base}/{location.lstrip('/')}",
                dispname=name if dispname == "-" else dispname,
            )
        )
    return entries
