# local.py

from __future__ import annotations

import contextlib
import functools
import importlib
import inspect
import logging
import pkgutil
import re
from importlib import metadata

from .references import Entries, Entry

log = logging.getLogger(__name__)

LOCAL_SITE = "<local>"

MAX_MODULES = 150  # imported submodules per package, so a huge package cannot stall the bot
MAX_ENTRIES = 6000
SKIPPED_MODULES = frozenset({"tests", "test", "testing", "conftest", "setup", "__main__"})
DENIED_ROOTS = frozenset({"_distutils_hack", "pip"})
HOME_LABELS = ("documentation", "docs", "homepage", "home", "source")


@functools.cache
def installed() -> dict[str, str]:
    """Top-level import name -> distribution name, for every third-party package in this environment."""
    found = metadata.packages_distributions()
    return {root: dists[0] for root, dists in found.items() if root.isidentifier() and not root.startswith("_") and root not in DENIED_ROOTS}


def is_installed_root(root: str) -> bool:
    return root in installed()


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def find_root(token: str) -> str | None:
    """`pomice`, `Pomice` or the distribution name (`python-dotenv` -> `dotenv`) to an importable root."""
    roots = installed()
    if token in roots:
        return token
    wanted = _normalize(token)
    for root, dist in roots.items():
        if wanted in (_normalize(root), _normalize(dist)):
            return root
    return None


def project_url(root: str) -> str:
    dist = installed()[root]
    pypi = f"https://pypi.org/project/{dist}/"
    try:
        meta = metadata.metadata(dist)
    except metadata.PackageNotFoundError:
        return pypi
    urls: dict[str, str] = {}
    for item in meta.get_all("Project-URL") or []:
        label, _, url = item.partition(",")
        urls[label.strip().lower()] = url.strip()
    urls["home"] = urls.get("home") or meta.get("Home-page") or ""
    return next((urls[label] for label in HOME_LABELS if urls.get(label, "").startswith("http")), pypi)


def version_of(root: str) -> str | None:
    with contextlib.suppress(metadata.PackageNotFoundError, KeyError):
        return metadata.version(installed()[root])
    return None


def _classify(member: object, *, in_class: bool) -> str | None:
    if isinstance(member, (staticmethod, classmethod)):
        return "method"
    if isinstance(member, (property, functools.cached_property)):
        return "property"
    if inspect.ismodule(member):
        return "module"
    if inspect.isclass(member):
        return "class"
    if inspect.isroutine(member):
        return "method" if in_class else "function"
    return None  # plain values are left out, so their repr never ends up in chat


def _members(obj: object) -> list[tuple[str, object]]:
    if inspect.ismodule(obj):
        try:
            names = list(getattr(obj, "__all__", None) or vars(obj))
        except TypeError:
            names = list(vars(obj))
        found: list[tuple[str, object]] = []
        for name in names:
            if isinstance(name, str) and not name.startswith("_"):
                with contextlib.suppress(Exception):
                    found.append((name, getattr(obj, name)))
        return found
    return [(name, value) for name, value in vars(obj).items() if not name.startswith("_")]


def _owned(member: object, root: str) -> bool:
    """Re-exported names from other packages (`from typing import Any`) are not this package's documentation."""
    owner = getattr(member, "__module__", None)
    return isinstance(owner, str) and owner.split(".", 1)[0] == root


def build_local_entries(root: str) -> Entries:
    """Blocking: imports the package and its public submodules. Call through asyncio.to_thread."""
    home = project_url(root)
    entries: Entries = {}
    done: set[int] = set()

    def add(qualname: str, role: str) -> None:
        entries[qualname] = Entry(url=home, qualname=qualname, role=role, detail="local")

    def walk(obj: object, qualname: str, *, in_class: bool) -> None:
        for name, member in _members(obj):
            if len(entries) >= MAX_ENTRIES:
                return
            role = _classify(member, in_class=in_class)
            if role is None or role == "module":
                continue
            if not in_class and role in ("class", "function"):
                if not _owned(member, root) or id(member) in done:
                    continue
                done.add(id(member))
            child = f"{qualname}.{name}"
            add(child, role)
            if role == "class":
                walk(member, child, in_class=True)

    top = importlib.import_module(root)
    queue = [top]
    imported = 0
    while queue:
        module = queue.pop(0)
        add(module.__name__, "module")
        walk(module, module.__name__, in_class=False)
        for info in pkgutil.iter_modules(getattr(module, "__path__", ()), f"{module.__name__}."):
            leaf = info.name.rsplit(".", 1)[-1]
            if leaf.startswith("_") or leaf in SKIPPED_MODULES or imported >= MAX_MODULES:
                continue
            try:
                queue.append(importlib.import_module(info.name))
            except Exception, SystemExit:  # optional dependencies, platform modules, scripts that exit
                log.debug("Failed to import %r: %s", info.name, info.module_finder, exc_info=True)
                continue
            imported += 1
    return entries
