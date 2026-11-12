from __future__ import annotations

import os
from pathlib import Path


def load_environment(path: str | os.PathLike[str] = ".env") -> None:
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
    except ImportError:
        _load_environment_file(Path(path))
    else:
        load_dotenv(path)


def _load_environment_file(path: Path) -> None:
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or name in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[name] = value
