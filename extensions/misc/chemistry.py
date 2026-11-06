from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from textwrap import shorten
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands
from rapidfuzz import fuzz, process
from yarl import URL

from core.utils import BaseLayoutView, DisambiguatorView, NoticeLayout

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

ELEMENTS_PATH = Path("assets") / "elements.json"  # adjust if your working dir differs

ELEMENT_ALIASES = {"aluminum": "aluminium", "cesium": "caesium", "sulphur": "sulfur"}

AUTO_PICK_SCORE = 75.0
AUTO_PICK_LEAD = 4.0

# (substring of `category`, colour). Order matters, first match wins.
CATEGORY_COLOURS: list[tuple[str, int]] = [
    ("unknown", 0x99AABB),
    ("alkaline earth", 0xFFDEAD),
    ("alkali", 0xFF6666),
    ("lanthanide", 0xFFBFFF),
    ("actinide", 0xFF99CC),
    ("post-transition", 0xCCCCCC),
    ("transition", 0xFFC0C0),
    ("metalloid", 0xCCCC99),
    ("noble gas", 0xC0FFFF),
    ("nonmetal", 0xA0FFA0),
]


def _num(value: float | int | None, unit: str = "") -> str | None:
    if value is None:
        return None
    return f"{value:,.6g}{(' ' + unit) if unit else ''}"


def _kelvin(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value:,.2f} K ({value - 273.15:,.2f} °C)"


def _lines(*pairs: tuple[str, str | None]) -> str:
    """Bold-label lines, skipping anything that has no value."""
    return "\n".join(f"**{label}** {value}" for label, value in pairs if value)


def _clean(text: str, limit: int = 60) -> str:
    return shorten(discord.utils.escape_mentions(discord.utils.escape_markdown(text)), limit, placeholder="…")


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


class PeriodicTable:
    def __init__(self, raw: dict[str, dict[str, Any]]) -> None:
        self.by_number: dict[int, dict[str, Any]] = {}
        for name, data in raw.items():
            element = {**data, "name": name}
            self.by_number[element["number"]] = element

        self.max_number = max(self.by_number)
        self._names = {e["name"].lower(): n for n, e in self.by_number.items()}
        self._symbols = {e["symbol"].lower(): n for n, e in self.by_number.items()}

    def find(self, query: str) -> tuple[dict[str, Any] | None, list[str]]:
        """Resolve a name, symbol or atomic number. Returns (element, suggestions)."""
        q = query.strip().lower()
        if q.isdigit():
            return self.by_number.get(int(q)), []

        q = ELEMENT_ALIASES.get(q, q)
        number = self._names.get(q) or self._symbols.get(q)
        if number:
            return self.by_number[number], []

        close = process.extract(q, list(self._names), scorer=fuzz.WRatio, limit=3, score_cutoff=65)
        return None, [self.by_number[self._names[name]]["name"] for name, _, _ in close]


def category_colour(category: str | None) -> int:
    lowered = (category or "").lower()
    return next((colour for needle, colour in CATEGORY_COLOURS if needle in lowered), 0x5865F2)


class ElementView(BaseLayoutView):
    """Element card with previous/next navigation (owner check and timeout handling come from BaseLayoutView)."""

    def __init__(self, table: PeriodicTable, author: discord.User | discord.Member, number: int) -> None:
        super().__init__(author, timeout=180)
        self.table = table
        self.number = number
        self.render()

    def render(self) -> None:
        self.clear_items()
        el = self.table.by_number[self.number]
        prev_el = self.table.by_number.get(self.number - 1)
        next_el = self.table.by_number.get(self.number + 1)

        period, xpos, ypos = el.get("period"), el.get("xpos"), el.get("ypos")
        position = f"Period {period}, f-block" if ypos and ypos >= 9 else f"Period {period}, Group {xpos}"
        header = (
            f"# {el['symbol']} — {el['name']}\n"
            f"-# No. {el['number']} · {(el.get('category') or 'unknown').capitalize()} · {el.get('phase') or '?'} · {position}"
        )

        density_unit = "g/L" if el.get("phase") == "Gas" else "g/cm³"
        physical = _lines(
            ("Appearance", (el.get("appearance") or "").capitalize() or None),
            ("Density", _num(el.get("density"), density_unit)),
            ("Melting point", _kelvin(el.get("melt"))),
            ("Boiling point", _kelvin(el.get("boil"))),
            ("Molar heat", _num(el.get("molar_heat"), "J/(mol·K)")),
        )

        energies = el.get("ionization_energies") or []
        ionization = " · ".join(f"{_ordinal(i)}: {e:,.6g}" for i, e in enumerate(energies[:3], start=1))
        if ionization:
            ionization += " kJ/mol" + (f" (+{len(energies) - 3} more)" if len(energies) > 3 else "")

        config = el.get("electron_configuration")
        atomic = _lines(
            ("Atomic mass", _num(el.get("atomic_mass"), "u")),
            ("Electron configuration", f"`{config}`" if config else None),
            ("Shells", ", ".join(map(str, el["shells"])) if el.get("shells") else None),
            ("Electronegativity", _num(el.get("electronegativity_pauling"), "(Pauling)")),
            ("Electron affinity", _num(el.get("electron_affinity"), "kJ/mol")),
            ("Ionization energy", ionization or None),
        )
        history = _lines(("Discovered by", el.get("discovered_by")), ("Named by", el.get("named_by")))

        prev_btn = discord.ui.Button(label=f"◀ {prev_el['name']}" if prev_el else "◀", disabled=prev_el is None)
        next_btn = discord.ui.Button(label=f"{next_el['name']} ▶" if next_el else "▶", disabled=next_el is None)
        prev_btn.callback = partial(self._go, -1)
        next_btn.callback = partial(self._go, +1)
        nav = discord.ui.ActionRow(prev_btn, next_btn)
        for label, url in (
            ("Wikipedia", el.get("source")),
            ("PubChem", f"https://pubchem.ncbi.nlm.nih.gov/element/{el['number']}"),
            ("Spectrum", el.get("spectral_img")),
        ):
            if url and str(url).startswith("http"):
                nav.add_item(discord.ui.Button(label=label, url=url))

        children: list[discord.ui.Item] = [discord.ui.TextDisplay(header), discord.ui.Separator()]
        if el.get("summary"):
            children += [discord.ui.TextDisplay(shorten(el["summary"], 650, placeholder="…")), discord.ui.Separator()]
        for title, body in (("Physical", physical), ("Atomic", atomic), ("History", history)):
            if body:
                children.append(discord.ui.TextDisplay(f"### {title}\n{body}"))
        children += [discord.ui.Separator(), nav]

        self.add_item(discord.ui.Container(*children, accent_colour=category_colour(el.get("category"))))

    async def _go(self, delta: int, interaction: discord.Interaction) -> None:
        self.number = min(max(self.number + delta, 1), self.table.max_number)
        self.render()
        await interaction.response.edit_message(view=self)


type Namespace = Literal["name", "cid", "smiles", "inchikey"]

CAS_RE = re.compile(r"\d{2,7}-\d{2}-\d")
ID_LIKE_RE = re.compile(r"[A-Z]{2,}[-_ ]?[\w-]*\d[\w-]*")

PROPERTY_HEADINGS = (
    "Melting Point", "Boiling Point", "Flash Point", "Density", "Solubility",
    "Vapor Pressure", "LogP", "Viscosity", "Refractive Index",
)  # fmt: skip


class PubChemError(Exception):
    """Anything that went wrong talking to PubChem."""


class PubChemNotFound(PubChemError):
    """No such compound (or the input could not be parsed)."""


class PubChemBusy(PubChemError):
    """PubChem is throttling us or overloaded (HTTP 429/503)."""


@dataclass(slots=True)
class Compound:
    cid: int
    title: str
    formula: str | None
    weight: float | None
    iupac: str | None
    smiles: str | None
    connectivity_smiles: str | None
    inchikey: str | None
    xlogp: float | None
    exact_mass: float | None
    tpsa: float | None
    complexity: float | None
    charge: int | None
    hbd: int | None
    hba: int | None
    rotatable: int | None
    heavy_atoms: int | None
    description: str | None = None
    description_source: str | None = None
    description_url: str | None = None


@dataclass(slots=True)
class Candidate:
    name: str
    score: float


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _int(value: Any) -> int | None:
    number = _float(value)
    return None if number is None else int(number)


def _collect_information(node: dict[str, Any], out: dict[str, list[dict[str, Any]]]) -> None:
    """Flatten a PUG-View record into {TOCHeading: [Information, ...]}; nesting depth varies per record."""
    for section in node.get("Section") or []:
        infos = section.get("Information")
        if infos:
            out.setdefault(section.get("TOCHeading", ""), []).extend(infos)
        _collect_information(section, out)


def _info_text(info: dict[str, Any]) -> str | None:
    value = info.get("Value") or {}
    parts = value.get("StringWithMarkup")
    if parts:
        return (parts[0].get("String") or "").strip() or None
    numbers = value.get("Number")
    if numbers:
        return f"{numbers[0]:g} {value.get('Unit') or ''}".strip()
    return None


def parse_experimental(data: dict[str, Any]) -> dict[str, list[str]]:
    found: dict[str, list[dict[str, Any]]] = {}
    _collect_information(data.get("Record", {}), found)

    result: dict[str, list[str]] = {}
    for heading in PROPERTY_HEADINGS:
        values: list[str] = []
        for info in found.get(heading, []):
            text = _info_text(info)
            if text and text not in values:
                values.append(text)
        if values:
            result[heading] = values[:2]
    return result


def parse_ghs(data: dict[str, Any]) -> dict[str, Any] | None:
    found: dict[str, list[dict[str, Any]]] = {}
    _collect_information(data.get("Record", {}), found)
    infos = found.get("GHS Classification")
    if not infos:
        return None

    result: dict[str, Any] = {"signal": None, "pictograms": [], "statements": [], "precautions": None}
    for info in infos:
        name = (info.get("Name") or "").lower()
        parts = (info.get("Value") or {}).get("StringWithMarkup") or []
        if name.startswith("pictogram"):
            for part in parts:
                for markup in part.get("Markup") or []:
                    label = markup.get("Extra")
                    if label and label not in result["pictograms"]:
                        result["pictograms"].append(label)
        elif name == "signal" and parts:
            result["signal"] = parts[0].get("String")
        elif "hazard statements" in name:
            result["statements"] += [p["String"] for p in parts if p.get("String")]
        elif "precautionary statement codes" in name and parts:
            result["precautions"] = parts[0].get("String")
    return result


class PubChemClient:
    BASE = "https://pubchem.ncbi.nlm.nih.gov/rest"
    # `SMILES` (stereo + isotopes) and `ConnectivitySMILES` replaced the deprecated
    # IsomericSMILES / CanonicalSMILES names in 2025.
    PROPERTIES = ",".join(
        (
            "Title",
            "MolecularFormula",
            "MolecularWeight",
            "IUPACName",
            "SMILES",
            "ConnectivitySMILES",
            "InChIKey",
            "XLogP",
            "ExactMass",
            "TPSA",
            "Complexity",
            "Charge",
            "HBondDonorCount",
            "HBondAcceptorCount",
            "RotatableBondCount",
            "HeavyAtomCount",
        )
    )
    MIN_INTERVAL = 0.25  # seconds between request starts -> 4 req/s max
    CACHE_TTL = 3600.0
    CACHE_MAX = 512

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._lock = asyncio.Lock()
        self._next_slot = 0.0
        self._cache: dict[str, tuple[float, Any]] = {}

    def _recall(self, key: str) -> Any | None:
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < self.CACHE_TTL:
            return hit[1]
        return None

    def _remember(self, key: str, value: Any) -> None:
        if len(self._cache) >= self.CACHE_MAX:
            self._cache.pop(next(iter(self._cache)))  # dicts keep insertion order -> oldest first
        self._cache[key] = (time.monotonic(), value)

    async def _throttle(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._next_slot - now
            self._next_slot = max(now, self._next_slot) + self.MIN_INTERVAL
        if wait > 0:
            await asyncio.sleep(wait)

    async def _get_json(self, url: str) -> dict[str, Any]:
        await self._throttle()
        timeout = aiohttp.ClientTimeout(total=20)
        # encoded=True: we percent-encode ourselves, don't let yarl re-quote it.
        async with self.bot.http_session.get(URL(url, encoded=True), timeout=timeout) as resp:
            if resp.status in (400, 404):
                raise PubChemNotFound(url)
            if resp.status in (429, 503):
                raise PubChemBusy(url)
            if resp.status >= 400:
                msg = f"HTTP {resp.status} for {url}"
                raise PubChemError(msg)
            return await resp.json(content_type=None)

    async def lookup(self, namespace: Namespace, value: str) -> Compound:
        value = value.strip()
        if not value or len(value) > 300 or (namespace == "cid" and not value.isdigit()):
            raise PubChemNotFound(value)

        key = f"compound:{namespace}:{value.lower()}"
        cached = self._recall(key)
        if cached is not None:
            return cached

        encoded = quote(value, safe="")  # percent-encode everything, SMILES contain / # ( ) = etc.
        data = await self._get_json(f"{self.BASE}/pug/compound/{namespace}/{encoded}/property/{self.PROPERTIES}/JSON")
        try:
            row = data["PropertyTable"]["Properties"][0]
        except (KeyError, IndexError, TypeError) as exc:
            msg = "Unexpected PubChem response"
            raise PubChemError(msg) from exc

        compound = Compound(
            cid=int(row["CID"]),
            title=row.get("Title") or row.get("IUPACName") or value,
            formula=row.get("MolecularFormula"),
            weight=_float(row.get("MolecularWeight")),
            iupac=row.get("IUPACName"),
            smiles=row.get("SMILES") or row.get("IsomericSMILES"),
            connectivity_smiles=row.get("ConnectivitySMILES") or row.get("CanonicalSMILES"),
            inchikey=row.get("InChIKey"),
            xlogp=_float(row.get("XLogP")),
            exact_mass=_float(row.get("ExactMass")),
            tpsa=_float(row.get("TPSA")),
            complexity=_float(row.get("Complexity")),
            charge=_int(row.get("Charge")),
            hbd=_int(row.get("HBondDonorCount")),
            hba=_int(row.get("HBondAcceptorCount")),
            rotatable=_int(row.get("RotatableBondCount")),
            heavy_atoms=_int(row.get("HeavyAtomCount")),
        )
        await self._fill_description(compound)
        self._remember(key, compound)
        return compound

    async def _fill_description(self, compound: Compound) -> None:
        """Best effort: a missing description must not fail the whole lookup."""
        try:
            data = await self._get_json(f"{self.BASE}/pug/compound/cid/{compound.cid}/description/JSON")
        except PubChemError, aiohttp.ClientError, TimeoutError:
            return
        for info in data.get("InformationList", {}).get("Information", []):
            text = (info.get("Description") or "").strip()
            if text:
                compound.description = text
                compound.description_source = info.get("DescriptionSourceName")
                compound.description_url = info.get("DescriptionURL")
                return

    async def autocomplete(self, query: str, limit: int = 25) -> list[str]:
        """PubChem's name autocomplete. Not a documented PUG endpoint, so best effort (errors -> [])."""
        key = f"autocomplete:{limit}:{query.lower()}"
        cached = self._recall(key)
        if cached is not None:
            return cached
        try:
            data = await self._get_json(f"{self.BASE}/autocomplete/compound/{quote(query, safe='')}/json?limit={limit}")
        except PubChemError, aiohttp.ClientError, TimeoutError:
            return []
        names = list(data.get("dictionary_terms", {}).get("compound", []))[:limit]
        self._remember(key, names)
        return names

    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        """Ranked name candidates for a possibly misspelled query.

        Autocomplete is prefix based, so if the full query finds nothing (a typo) we also probe with
        shorter prefixes ("beneze" -> "bene", "ben") and rank the pooled names locally with RapidFuzz.
        """
        query = query.strip()
        if not query or len(query) > 100:
            return []

        names = list(await self.autocomplete(query))
        if not names:
            probes: list[str] = []
            for probe in (query[: max(3, len(query) - 2)], query[:3]):
                if len(probe) >= 2 and probe.lower() != query.lower() and probe not in probes:
                    probes.append(probe)
            for probe in probes:
                names += await self.autocomplete(probe)

        seen: set[str] = set()
        ranked: list[Candidate] = []
        for name in names:
            if name.lower() not in seen:
                seen.add(name.lower())
                ranked.append(Candidate(name, fuzz.WRatio(query.lower(), name.lower())))
        ranked.sort(key=lambda c: c.score, reverse=True)  # stable: ties keep PubChem's popularity order
        return ranked[:limit]

    async def synonyms(self, cid: int) -> list[str]:
        key = f"synonyms:{cid}"
        cached = self._recall(key)
        if cached is not None:
            return cached
        data = await self._get_json(f"{self.BASE}/pug/compound/cid/{cid}/synonyms/JSON")
        info = (data.get("InformationList", {}).get("Information") or [{}])[0]
        names = list(info.get("Synonym") or [])
        self._remember(key, names)
        return names

    async def experimental(self, cid: int) -> dict[str, list[str]]:
        key = f"experimental:{cid}"
        cached = self._recall(key)
        if cached is not None:
            return cached
        try:
            data = await self._get_json(f"{self.BASE}/pug_view/data/compound/{cid}/JSON?heading=Experimental+Properties")
        except PubChemNotFound:
            data = {}
        result = parse_experimental(data)
        self._remember(key, result)
        return result

    async def ghs(self, cid: int) -> dict[str, Any] | None:
        key = f"ghs:{cid}"
        cached = self._recall(key)
        if cached is not None:
            return cached or None
        try:
            data = await self._get_json(f"{self.BASE}/pug_view/data/compound/{cid}/JSON?heading=GHS+Classification")
        except PubChemNotFound:
            data = {}
        result = parse_ghs(data)
        self._remember(key, result or {})  # cache "nothing on record" too
        return result


def format_names(synonyms: list[str]) -> str:
    cas = [s for s in synonyms if CAS_RE.fullmatch(s)]
    others = [s for s in synonyms if not CAS_RE.fullmatch(s) and len(s) <= 40 and not ID_LIKE_RE.fullmatch(s)]
    body = _lines(
        ("CAS", " · ".join(dict.fromkeys(cas[:3])) or None),
        ("Also known as", " · ".join(dict.fromkeys(others[:12])) or None),
    )
    return f"### Names\n{body or 'No synonyms on record.'}\n-# {len(synonyms):,} synonyms on PubChem"


def format_properties(values: dict[str, list[str]]) -> str:
    if not values:
        return "### Experimental properties\nNothing on record for this compound."
    lines = [f"**{heading}** " + " · ".join(shorten(v, 110, placeholder="…") for v in vals) for heading, vals in values.items()]
    return "### Experimental properties\n" + "\n".join(lines) + "\n-# Collected from several sources, see PubChem for references"


def format_safety(ghs: dict[str, Any] | None) -> str:
    if not ghs:
        return "### Safety (GHS)\nNo GHS classification on record. That does **not** mean the compound is safe."

    statements = ghs["statements"]
    body = _lines(("Signal", ghs["signal"]), ("Pictograms", " · ".join(ghs["pictograms"]) or None))
    if statements:
        shown = "\n".join(f"- {shorten(s, 130, placeholder='…')}" for s in statements[:8])
        if len(statements) > 8:
            shown += f"\n-# +{len(statements) - 8} more on PubChem"
        body += f"\n**Hazard statements**\n{shown}"
    if ghs["precautions"]:
        body += f"\n**Precautionary codes** {shorten(ghs['precautions'], 300, placeholder='…')}"
    return f"### Safety (GHS)\n{body}\n-# Aggregated from notifier reports. Reference only, check the SDS before handling anything."


class CompoundView(BaseLayoutView):
    """Tabbed compound card. Tabs after Overview load their data when first opened."""

    TABS = ("Overview", "Names", "Properties", "Safety")

    def __init__(
        self,
        client: PubChemClient,
        compound: Compound,
        author: discord.User | discord.Member,
        *,
        note: str | None = None,
    ) -> None:
        super().__init__(author, timeout=600)
        self.client = client
        self.compound = compound
        self.note = note
        self.tab = "Overview"
        self._tab_text: dict[str, str] = {}
        self.render()

    def _overview_items(self) -> list[discord.ui.Item]:
        c = self.compound
        png = f"{PubChemClient.BASE}/pug/compound/cid/{c.cid}/PNG?image_size=large"
        items: list[discord.ui.Item] = [
            discord.ui.MediaGallery(discord.MediaGalleryItem(png, description=f"2D structure of {c.title}")),
            discord.ui.Separator(),
        ]

        if c.description:
            text = shorten(c.description, 700, placeholder="…")
            if c.description_source and c.description_url:
                text += f"\n-# Source: [{shorten(c.description_source, 60, placeholder='…')}]({c.description_url})"
            elif c.description_source:
                text += f"\n-# Source: {shorten(c.description_source, 60, placeholder='…')}"
            items += [discord.ui.TextDisplay(text), discord.ui.Separator()]

        identifiers = _lines(
            ("IUPAC name", shorten(c.iupac, 250, placeholder="…") if c.iupac else None),
            ("SMILES", f"`{shorten(c.smiles, 300, placeholder='…')}`" if c.smiles else None),
            (
                "Connectivity SMILES",
                f"`{shorten(c.connectivity_smiles, 300, placeholder='…')}`" if c.connectivity_smiles and c.connectivity_smiles != c.smiles else None,
            ),
            ("InChIKey", f"`{c.inchikey}`" if c.inchikey else None),
        )
        computed = _lines(
            ("Exact mass", _num(c.exact_mass, "Da")),
            ("XLogP", _num(c.xlogp)),
            ("TPSA", _num(c.tpsa, "Å²")),
            ("Complexity", _num(c.complexity)),
            ("Charge", None if c.charge is None else f"{c.charge:+d}" if c.charge else "0"),
            ("H-bond donors / acceptors", f"{c.hbd} / {c.hba}" if c.hbd is not None and c.hba is not None else None),
            ("Rotatable bonds", _num(c.rotatable)),
            ("Heavy atoms", _num(c.heavy_atoms)),
        )  # fmt: skip
        if identifiers:
            items.append(discord.ui.TextDisplay(f"### Identifiers\n{identifiers}"))
        if computed:
            items.append(discord.ui.TextDisplay(f"### Computed properties\n{computed}\n-# Data from PubChem (NIH / NLM)"))
        return items

    def render(self, body: str | None = None) -> None:
        """Rebuild the card. `body` overrides the active tab's text (used to show an uncached error once)."""
        self.clear_items()
        c = self.compound

        weight = f" · {c.weight:,.2f} g/mol" if c.weight is not None else ""
        header = f"# {shorten(c.title, 120, placeholder='…')}\n-# CID {c.cid} · {c.formula or '?'}{weight}"
        if self.note:
            header += f"\n-# {self.note}"
        children: list[discord.ui.Item] = [discord.ui.TextDisplay(header)]

        if self.tab == "Overview":
            children += self._overview_items()
        else:
            text = body or self._tab_text.get(self.tab, "Loading…")
            children += [discord.ui.Separator(), discord.ui.TextDisplay(text)]

        tabs = discord.ui.ActionRow()
        for tab in self.TABS:
            button = discord.ui.Button(label=tab, style=discord.ButtonStyle.primary if tab == self.tab else discord.ButtonStyle.secondary)
            button.callback = partial(self._open_tab, tab)
            tabs.add_item(button)

        page = f"https://pubchem.ncbi.nlm.nih.gov/compound/{c.cid}"
        links = discord.ui.ActionRow(
            discord.ui.Button(label="PubChem", url=page),
            discord.ui.Button(label="3D conformer", url=f"{page}#section=3D-Conformer"),
        )
        children += [discord.ui.Separator(), tabs, links]
        self.add_item(discord.ui.Container(*children, accent_colour=0x5865F2))

    async def _load_tab(self, tab: str) -> tuple[str, bool]:
        """Fetch and format one tab. Returns (text, ok); failures become tab text instead of raising."""
        try:
            if tab == "Names":
                return format_names(await self.client.synonyms(self.compound.cid)), True
            if tab == "Properties":
                return format_properties(await self.client.experimental(self.compound.cid)), True
            return format_safety(await self.client.ghs(self.compound.cid)), True
        except PubChemBusy:
            return f"### {tab}\nPubChem is busy right now, click the tab again in a moment.", False
        except PubChemError, aiohttp.ClientError, TimeoutError:
            _log.exception("Failed loading %s tab for CID %s", tab, self.compound.cid)
            return f"### {tab}\nCouldn't load this from PubChem, try again later.", False

    async def _open_tab(self, tab: str, interaction: discord.Interaction) -> None:
        await interaction.response.defer()  # fetching can outlast the 3s interaction window

        body = None
        if tab != "Overview" and tab not in self._tab_text:
            body, ok = await self._load_tab(tab)
            if ok:
                self._tab_text[tab] = body  # only successes are kept, errors retry on the next click

        self.tab = tab
        self.render(body)
        await interaction.edit_original_response(view=self)


class CompoundFlags(commands.FlagConverter, prefix="--", delimiter=" ", case_insensitive=True):
    """Pick exactly one way to identify the compound."""

    name: str | None = commands.flag(positional=True, default=None, description="Compound name, e.g. benzene. Typos are fuzzy-matched.")
    cid: int | None = commands.flag(default=None, description="PubChem compound ID, e.g. 241.")
    smiles: str | None = commands.flag(default=None, description="A SMILES string, e.g. c1ccccc1.")
    inchikey: str | None = commands.flag(default=None, description="An InChIKey, e.g. UHOVQNZJYSORNB-UHFFFAOYSA-N.")


class SearchFlags(commands.FlagConverter, prefix="--", delimiter=" ", case_insensitive=True):
    """Options for `compound search`."""

    query: str = commands.flag(positional=True, description="Full or partial compound name to search for.")
    limit: commands.Range[int, 1, 25] = commands.flag(default=10, description="How many candidates to offer (1-25).")


class Chemistry(commands.Cog, command_attrs={"hidden": True}):
    """Periodic table and compound lookups."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.table: PeriodicTable | None = None
        self.pubchem = PubChemClient(bot)

    async def cog_load(self) -> None:
        raw = await asyncio.to_thread(lambda: json.loads(ELEMENTS_PATH.read_text(encoding="utf-8")))
        self.table = PeriodicTable(raw)
        _log.debug("Loaded %d elements", len(self.table.by_number))

    async def _pick(self, ctx: commands.Context[Bot], prompt: str, options: list[str]) -> str | None:
        """Let the user choose between `options` with a select menu. Returns None on timeout."""
        view = DisambiguatorView(ctx, options, entry=lambda s: discord.SelectOption(label=shorten(s, 100, placeholder="…")))
        view.message = await ctx.reply(prompt, view=view)
        await view.wait()
        return getattr(view, "selected", None)

    async def _fetch(self, ctx: commands.Context[Bot], namespace: Namespace, value: str) -> Compound | None:
        """Look a compound up. `PubChemNotFound` propagates; other failures tell the user and return None."""
        try:
            return await self.pubchem.lookup(namespace, value)
        except PubChemNotFound:
            raise
        except PubChemBusy:
            await ctx.reply(view=NoticeLayout.warning("PubChem is busy or rate limiting right now, try again in a minute."))
        except PubChemError, aiohttp.ClientError, TimeoutError:
            _log.exception("PubChem lookup failed for %s=%r", namespace, value)
            await ctx.reply(view=NoticeLayout.error("Something went wrong talking to PubChem, try again later."))
        return None

    async def _show(self, ctx: commands.Context[Bot], namespace: Namespace, value: str, note: str | None = None) -> bool:
        """Fetch + send the compound card. Returns False if the compound wasn't found (nothing is sent then)."""
        async with ctx.typing():
            try:
                compound = await self._fetch(ctx, namespace, value)
            except PubChemNotFound:
                return False
        if compound is not None:
            view = CompoundView(self.pubchem, compound, ctx.author, note=note)
            view.message = await ctx.reply(view=view)
        return True

    async def _not_found(self, ctx: commands.Context[Bot], body: str) -> None:
        await ctx.reply(view=NoticeLayout.warning(body, title="Compound not found"))

    @commands.command(name="element", aliases=["el", "elem"], usage="<name | symbol | number>")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def element(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="Element name, symbol or atomic number, e.g. gold, Au or 79."),
    ) -> None:
        """Look up an element by name, symbol or atomic number."""
        assert self.table is not None
        element, suggestions = self.table.find(query)
        shown = _clean(query)

        if element is None and suggestions:
            picked = await self._pick(ctx, f"I couldn't find an element matching `{shown}`. Did you mean:", suggestions)
            if picked is None:
                return  # timed out without choosing
            element = self.table.find(picked)[0]

        if element is None:
            if query.strip().isdigit():
                body = f"There's no element with atomic number `{shown}`. Valid numbers are 1 to {self.table.max_number}."
            else:
                body = f"I couldn't find an element matching `{shown}`."
            await ctx.reply(view=NoticeLayout.warning(body, title="Element not found"))
            return

        view = ElementView(self.table, ctx.author, element["number"])
        view.message = await ctx.reply(view=view)

    @commands.group(
        name="compound",
        aliases=["chem", "pubchem", "molecule"],
        invoke_without_command=True,
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def compound(
        self,
        ctx: commands.Context[Bot],
        *,
        flags: CompoundFlags,
    ) -> None:
        """Look up a compound on PubChem: structure, names, properties and safety data in tabs.

        Misspelled names are fuzzy-matched, e.g. `compound beneze`. Use `compound search` to browse candidates.
        """
        given = {
            key: value
            for key, value in (("name", flags.name), ("cid", flags.cid), ("smiles", flags.smiles), ("inchikey", flags.inchikey))
            if value not in (None, "")
        }
        if len(given) != 1:
            await ctx.reply(
                view=NoticeLayout.warning(
                    "Give a compound name, **or exactly one** of `--cid`, `--smiles`, `--inchikey`.\n"
                    "Examples: `compound benzene` · `compound --cid 241` · `compound --smiles c1ccccc1`",
                    title="Which compound?",
                )
            )
            return

        namespace, raw = next(iter(given.items()))
        value, shown = str(raw), _clean(str(raw))

        # 1. Exact lookup (also the only path for --cid / --smiles / --inchikey).
        if await self._show(ctx, namespace, value):  # type: ignore[arg-type]
            return
        if namespace != "name":
            await self._not_found(ctx, f"PubChem has no compound for `--{namespace} {shown}`.")
            return

        # 2. Fuzzy fallback for names: auto-pick a clear winner, otherwise let the user choose.
        async with ctx.typing():
            ranked = await self.pubchem.search(value, limit=10)
        if not ranked:
            await self._not_found(ctx, f"PubChem has nothing matching `{shown}`.")
            return

        clear_winner = len(ranked) == 1 or (ranked[0].score >= AUTO_PICK_SCORE and ranked[0].score - ranked[1].score >= AUTO_PICK_LEAD)
        name = (
            ranked[0].name if clear_winner else await self._pick(ctx, f"I couldn't find `{shown}` exactly. Did you mean:", [c.name for c in ranked])
        )
        if name is None:
            return  # timed out without choosing

        note = f"Showing results for **{_clean(name, 80)}** (you searched `{shown}`)"
        if not await self._show(ctx, "name", name, note):
            await self._not_found(ctx, f"PubChem has nothing for `{_clean(name)}`.")

    @compound.command(name="search", aliases=["find"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def compound_search(
        self,
        ctx: commands.Context[Bot],
        *,
        flags: SearchFlags,
    ) -> None:
        """Browse PubChem name candidates for a full or partial name, then open the one you pick."""
        shown = _clean(flags.query)
        async with ctx.typing():
            ranked = await self.pubchem.search(flags.query, limit=flags.limit)
        if not ranked:
            await self._not_found(ctx, f"PubChem has nothing matching `{shown}`.")
            return

        names = [c.name for c in ranked]
        name = names[0] if len(names) == 1 else await self._pick(ctx, f"Results for `{shown}`:", names)
        if name is None:
            return  # timed out without choosing

        if not await self._show(ctx, "name", name):
            await self._not_found(ctx, f"PubChem has nothing for `{_clean(name)}`.")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Chemistry(bot))
