from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import math
import random
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final, Literal, Self, override

import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter
from rapidfuzz import fuzz, process

from core.utils.formats import human_join, plural, safe_text, truncate
from core.utils.views import Author, BaseLayoutView, NoticeLayout

if TYPE_CHECKING:
    from core import Bot

__all__ = ("Pokemon", "setup")

_log = logging.getLogger(__name__)

POKEAPI_BASE_URL: Final[str] = "https://pokeapi.co/api/v2"
MAX_CACHE_ENTRIES: Final[int] = 256
WTP_TIMEOUT_SECONDS: Final[float] = 45.0
POKEDEX_TIMEOUT_SECONDS: Final[float] = 300.0

TYPE_COLOURS: Final[dict[str, int]] = {
    "normal": 0xA8A77A,
    "fire": 0xEE8130,
    "water": 0x6390F0,
    "electric": 0xF7D02C,
    "grass": 0x7AC74C,
    "ice": 0x96D9D6,
    "fighting": 0xC22E28,
    "poison": 0xA33EA1,
    "ground": 0xE2BF65,
    "flying": 0xA98FF3,
    "psychic": 0xF95587,
    "bug": 0xA6B91A,
    "rock": 0xB6A136,
    "ghost": 0x735797,
    "dragon": 0x6F35FC,
    "dark": 0x705746,
    "steel": 0xB7B7CE,
    "fairy": 0xD685AD,
}

TYPE_EMOJIS: Final[dict[str, str]] = {
    "normal": "\N{MEDIUM WHITE CIRCLE}",
    "fire": "\N{FIRE}",
    "water": "\N{DROPLET}",
    "electric": "\N{HIGH VOLTAGE SIGN}",
    "grass": "\N{HERB}",
    "ice": "\N{SNOWFLAKE}\N{VARIATION SELECTOR-16}",
    "fighting": "\N{BOXING GLOVE}",
    "poison": "\N{SKULL AND CROSSBONES}\N{VARIATION SELECTOR-16}",
    "ground": "\N{DESERT}\N{VARIATION SELECTOR-16}",
    "flying": "\U0001fabd",
    "psychic": "\N{CRYSTAL BALL}",
    "bug": "\N{BUG}",
    "rock": "\N{ROCK}",
    "ghost": "\N{GHOST}",
    "dragon": "\N{DRAGON}",
    "dark": "\N{NEW MOON SYMBOL}",
    "steel": "\N{GEAR}\N{VARIATION SELECTOR-16}",
    "fairy": "\N{SPARKLES}",
}

STAT_LABELS: Final[dict[str, str]] = {
    "hp": "HP ",
    "attack": "Atk",
    "defense": "Def",
    "special-attack": "SpA",
    "special-defense": "SpD",
    "speed": "Spe",
}

GENERATION_RANGES: Final[dict[int, tuple[int, int]]] = {
    1: (1, 151),
    2: (152, 251),
    3: (252, 386),
    4: (387, 493),
    5: (494, 649),
    6: (650, 721),
    7: (722, 809),
    8: (810, 905),
    9: (906, 1025),
}

ROMAN_GENERATIONS: Final[dict[str, str]] = {
    "generation-i": "Gen I (Kanto)",
    "generation-ii": "Gen II (Johto)",
    "generation-iii": "Gen III (Hoenn)",
    "generation-iv": "Gen IV (Sinnoh)",
    "generation-v": "Gen V (Unova)",
    "generation-vi": "Gen VI (Kalos)",
    "generation-vii": "Gen VII (Alola)",
    "generation-viii": "Gen VIII (Galar/Hisui)",
    "generation-ix": "Gen IX (Paldea)",
}

type PokedexTab = Literal["overview", "stats", "evolutions", "media"]


def _clean_name(raw_name: str) -> str:
    """Format a Pok\N{LATIN SMALL LETTER E WITH ACUTE}API slug into a clean human-readable title."""
    special = {
        "nidoran-f": "Nidoran\N{FEMALE SIGN}",
        "nidoran-m": "Nidoran\N{MALE SIGN}",
        "mr-mime": "Mr. Mime",
        "mr-rime": "Mr. Rime",
        "mime-jr": "Mime Jr.",
        "farfetchd": "Farfetch'd",
        "sirfetchd": "Sirfetch'd",
        "flabebe": "Flab\N{LATIN SMALL LETTER E WITH ACUTE}b\N{LATIN SMALL LETTER E WITH ACUTE}",
        "type-null": "Type: Null",
        "jangmo-o": "Jangmo-o",
        "hakamo-o": "Hakamo-o",
        "kommo-o": "Kommo-o",
        "tapu-koko": "Tapu Koko",
        "tapu-lele": "Tapu Lele",
        "tapu-bulu": "Tapu Bulu",
        "tapu-fini": "Tapu Fini",
        "ho-oh": "Ho-Oh",
        "porygon-z": "Porygon-Z",
        "wo-chien": "Wo-Chien",
        "chien-pao": "Chien-Pao",
        "ting-lu": "Ting-Lu",
        "chi-yu": "Chi-Yu",
    }
    lowered = raw_name.lower()
    if lowered in special:
        return special[lowered]
    return raw_name.replace("-", " ").title()


def _normalize_guess(text: str) -> str:
    """Normalize a user guess or species name for comparison."""
    cleaned = text.lower().strip()
    cleaned = cleaned.replace("\N{FEMALE SIGN}", "f").replace("\N{MALE SIGN}", "m")
    return re.sub(r"[^a-z0-9]", "", cleaned)


def _extract_id_from_url(url: str) -> int | None:
    """Extract the trailing integer resource ID from a Pok\N{LATIN SMALL LETTER E WITH ACUTE}API URL."""
    match = re.search(r"/(\d+)/?$", url)
    return int(match.group(1)) if match else None


def _stat_bar(value: int, *, max_value: int = 255, width: int = 12) -> str:
    """Render a compact unicode block bar for a base stat."""
    filled = max(1, min(width, round((value / max_value) * width))) if value > 0 else 0
    return "\N{FULL BLOCK}" * filled + "\N{LIGHT SHADE}" * (width - filled)


def _calc_stat_range(stat_name: str, base: int) -> tuple[int, int]:
    """Return the (Min, Max) stat values at Level 100."""
    if stat_name == "hp":
        if base == 1:  # Shedinja
            return (1, 1)
        min_val = math.floor(2 * base + 110)
        max_val = math.floor(2 * base + 31 + (252 // 4) + 110)
        return (min_val, max_val)

    min_val = math.floor((2 * base + 5) * 0.9)
    max_val = math.floor((2 * base + 31 + (252 // 4) + 5) * 1.1)
    return (min_val, max_val)


@dataclass(slots=True, frozen=True)
class PokemonAbility:
    name: str
    slug: str
    is_hidden: bool
    slot: int


@dataclass(slots=True, frozen=True)
class EvolutionStep:
    species_name: str
    species_slug: str
    species_id: int
    trigger_summary: str | None = None
    children: tuple[EvolutionStep, ...] = ()


@dataclass(slots=True, frozen=True)
class PokemonVariety:
    name: str
    slug: str
    pokemon_id: int
    is_default: bool


@dataclass(slots=True, frozen=True)
class PokemonMoveSummary:
    level_up: tuple[tuple[int, str], ...]
    machine: tuple[str, ...]
    egg: tuple[str, ...]
    tutor: tuple[str, ...]


@dataclass(slots=True)
class PokemonEntry:
    """Complete, unified Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon data model shared between Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex and Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon."""

    id: int
    species_id: int
    slug: str
    name: str
    species_slug: str
    japanese_name: str | None
    romaji_name: str | None
    genus: str
    generation: str
    flavor_text: str
    types: tuple[str, ...]
    abilities: tuple[PokemonAbility, ...]
    stats: dict[str, int]
    height_m: float
    weight_kg: float
    base_experience: int | None
    capture_rate: int
    base_happiness: int | None
    growth_rate: str
    gender_rate: int  # -1 = genderless, else eighths female
    egg_groups: tuple[str, ...]
    hatch_counter: int | None
    habitat: str | None
    is_baby: bool
    is_legendary: bool
    is_mythical: bool
    artwork_url: str | None
    shiny_artwork_url: str | None
    front_sprite_url: str | None
    shiny_sprite_url: str | None
    showdown_sprite_url: str | None
    cry_url: str | None
    held_items: tuple[tuple[str, int], ...]
    moves: PokemonMoveSummary
    evolution_root: EvolutionStep | None
    varieties: tuple[PokemonVariety, ...]
    type_defenses: dict[str, float] = field(default_factory=dict)

    @property
    def primary_colour(self) -> discord.Colour:
        first_type = self.types[0] if self.types else "normal"
        return discord.Colour(TYPE_COLOURS.get(first_type, 0x7289DA))

    @property
    def bst(self) -> int:
        return sum(self.stats.values())

    @property
    def formatted_types(self) -> str:
        return " / ".join(f"{TYPE_EMOJIS.get(t, '🔹')} {t.title()}" for t in self.types)

    @property
    def gender_display(self) -> str:
        if self.gender_rate < 0:
            return "Genderless"
        female_pct = (self.gender_rate / 8) * 100
        male_pct = 100.0 - female_pct
        return f"\N{MALE SIGN} {male_pct:g}% / \N{FEMALE SIGN} {female_pct:g}%"

    @property
    def rarity_badge(self) -> str | None:
        if self.is_mythical:
            return "\N{GLOWING STAR} Mythical"
        if self.is_legendary:
            return "\N{CROWN} Legendary"
        if self.is_baby:
            return "\N{BABY BOTTLE} Baby"
        return None

    @property
    def best_image_url(self) -> str | None:
        return self.artwork_url or self.front_sprite_url

    @property
    def best_shiny_url(self) -> str | None:
        return self.shiny_artwork_url or self.shiny_sprite_url or self.best_image_url

    def accepted_names(self) -> set[str]:
        """Return normalized strings accepted as valid guesses in 'Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon?'."""
        base_species = _clean_name(self.species_slug)
        names = {
            _normalize_guess(self.name),
            _normalize_guess(self.slug),
            _normalize_guess(self.species_slug),
            _normalize_guess(base_species),
        }
        if self.romaji_name:
            names.add(_normalize_guess(self.romaji_name))
        if self.japanese_name:
            names.add(self.japanese_name.strip())
        names.discard("")
        return names


class PokemonDataService:
    """Shared async client and LRU cache for Pok\N{LATIN SMALL LETTER E WITH ACUTE}API v2 data and silhouette rendering."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._entry_cache: OrderedDict[str | int, PokemonEntry] = OrderedDict()
        self._type_cache: dict[str, dict[str, set[str]]] = {}
        self._image_cache: OrderedDict[str, bytes] = OrderedDict()
        self._species_index: dict[str, int] = {}  # slug -> national dex id
        self._display_to_slug: dict[str, str] = {}  # display label -> slug
        self._index_lock = asyncio.Lock()

    async def _request_json(self, url: str) -> dict[str, Any] | None:
        session = self.bot.http_session
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as response:
                if response.status == 404:
                    return None
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            _log.warning("Pok\N{LATIN SMALL LETTER E WITH ACUTE}API request failed for %s: %s", url, exc)
            return None

    async def fetch_image_bytes(self, url: str) -> bytes | None:
        if url in self._image_cache:
            self._image_cache.move_to_end(url)
            return self._image_cache[url]

        session = self.bot.http_session
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as response:
                if response.status != 200:
                    return None
                data = await response.read()
        except (aiohttp.ClientError, TimeoutError) as exc:
            _log.warning("Failed to download Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon sprite %s: %s", url, exc)
            return None

        self._image_cache[url] = data
        if len(self._image_cache) > 128:
            self._image_cache.popitem(last=False)
        return data

    async def ensure_species_index(self) -> dict[str, int]:
        """Load and cache the full National Dex species index once."""
        if self._species_index:
            return self._species_index

        async with self._index_lock:
            if self._species_index:
                return self._species_index

            data = await self._request_json(f"{POKEAPI_BASE_URL}/pokemon-species?limit=2000")
            if not data or "results" not in data:
                return self._species_index

            for item in data["results"]:
                slug = str(item["name"]).lower()
                species_id = _extract_id_from_url(str(item["url"]))
                if species_id is not None:
                    self._species_index[slug] = species_id
                    display = f"#{species_id:04d} {_clean_name(slug)}"
                    self._display_to_slug[display] = slug

            return self._species_index

    async def search_species(self, query: str, *, limit: int = 15) -> list[tuple[str, int]]:
        """Search species by ID, exact name, or RapidFuzz fuzzy similarity."""
        index = await self.ensure_species_index()
        cleaned = query.strip().lower().lstrip("#")

        if cleaned.isdigit():
            target_id = int(cleaned)
            for slug, pid in index.items():
                if pid == target_id:
                    return [(slug, pid)]
            return []

        slug_candidate = re.sub(r"[\s_]+", "-", cleaned)
        if slug_candidate in index:
            return [(slug_candidate, index[slug_candidate])]

        norm_query = _normalize_guess(cleaned)
        for slug, pid in index.items():
            if _normalize_guess(slug) == norm_query or _normalize_guess(_clean_name(slug)) == norm_query:
                return [(slug, pid)]

        if not index:
            return []

        matches = process.extract(
            slug_candidate,
            list(index.keys()),
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=62,
        )
        return [(slug, index[slug]) for slug, _score, _idx in matches]

    async def get_random_pokemon(self, *, generation: int | None = None) -> PokemonEntry | None:
        """Pick a random Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon (optionally constrained to a generation) and fetch its full entry."""
        index = await self.ensure_species_index()
        if generation is not None and generation in GENERATION_RANGES:
            low, high = GENERATION_RANGES[generation]
            candidates = [pid for pid in index.values() if low <= pid <= high]
        else:
            candidates = list(index.values()) or list(range(1, 1026))

        if not candidates:
            return None

        for _ in range(3):
            chosen_id = random.choice(candidates)
            entry = await self.get_pokemon(chosen_id)
            if entry and entry.best_image_url:
                return entry
        return None

    async def _get_type_relations(self, type_name: str) -> dict[str, set[str]]:
        if type_name in self._type_cache:
            return self._type_cache[type_name]

        data = await self._request_json(f"{POKEAPI_BASE_URL}/type/{type_name}")
        relations: dict[str, set[str]] = {"double": set(), "half": set(), "zero": set()}
        if data and "damage_relations" in data:
            dmg = data["damage_relations"]
            relations["double"] = {x["name"] for x in dmg.get("double_damage_from", [])}
            relations["half"] = {x["name"] for x in dmg.get("half_damage_from", [])}
            relations["zero"] = {x["name"] for x in dmg.get("no_damage_from", [])}

        self._type_cache[type_name] = relations
        return relations

    async def compute_type_defenses(self, types: tuple[str, ...]) -> dict[str, float]:
        relations_list = await asyncio.gather(*(self._get_type_relations(t) for t in types))
        multipliers: dict[str, float] = dict.fromkeys(TYPE_COLOURS, 1.0)
        for rel in relations_list:
            for t in rel["double"]:
                if t in multipliers:
                    multipliers[t] *= 2.0
            for t in rel["half"]:
                if t in multipliers:
                    multipliers[t] *= 0.5
            for t in rel["zero"]:
                if t in multipliers:
                    multipliers[t] = 0.0
        return multipliers

    @staticmethod
    def _format_evolution_details(details_list: list[dict[str, Any]]) -> str | None:  # noqa: PLR0912
        if not details_list:
            return None

        d = details_list[0]
        trigger = (d.get("trigger") or {}).get("name", "")
        parts: list[str] = []

        if trigger == "level-up":
            if d.get("min_level"):
                parts.append(f"Lv. {d['min_level']}")
            else:
                parts.append("Level up")
        elif trigger == "use-item":
            item_name = (d.get("item") or {}).get("name")
            parts.append(f"Use {_clean_name(item_name)}" if item_name else "Use Item")
        elif trigger == "trade":
            parts.append("Trade")
        elif trigger == "shed":
            parts.append("Lv. 20 (Empty slot + Pok\N{LATIN SMALL LETTER E WITH ACUTE} Ball)")
        elif trigger:
            parts.append(_clean_name(trigger))

        if d.get("held_item"):
            parts.append(f"holding {_clean_name(d['held_item']['name'])}")
        if d.get("min_happiness"):
            parts.append(f"Happiness \N{GREATER-THAN OR EQUAL TO} {d['min_happiness']}")
        if d.get("min_affection"):
            parts.append(f"Affection \N{GREATER-THAN OR EQUAL TO} {d['min_affection']}")
        if d.get("min_beauty"):
            parts.append(f"Beauty \N{GREATER-THAN OR EQUAL TO} {d['min_beauty']}")
        if d.get("time_of_day"):
            parts.append(f"({str(d['time_of_day']).title()})")
        if d.get("known_move"):
            parts.append(f"knowing {_clean_name(d['known_move']['name'])}")
        if d.get("known_move_type"):
            parts.append(f"knowing {d['known_move_type']['name'].title()} move")
        if d.get("location"):
            parts.append(f"at {_clean_name(d['location']['name'])}")
        if d.get("gender") == 1:
            parts.append("(\N{FEMALE SIGN} only)")
        elif d.get("gender") == 2:
            parts.append("(\N{MALE SIGN} only)")
        if d.get("needs_overworld_rain"):
            parts.append("(Rain)")
        if d.get("turn_upside_down"):
            parts.append("(Turn upside down)")
        if d.get("relative_physical_stats") is not None:
            rel_stat = d["relative_physical_stats"]
            if rel_stat == 1:
                parts.append("(Atk > Def)")
            elif rel_stat == -1:
                parts.append("(Atk < Def)")
            else:
                parts.append("(Atk = Def)")

        return " ".join(parts) if parts else None

    def _parse_evolution_chain(self, node: dict[str, Any]) -> EvolutionStep:
        species_info = node.get("species") or {}
        slug = str(species_info.get("name", "unknown"))
        sid = _extract_id_from_url(str(species_info.get("url", ""))) or 0
        trigger_summary = self._format_evolution_details(node.get("evolution_details") or [])

        children = tuple(self._parse_evolution_chain(child) for child in (node.get("evolves_to") or []))
        return EvolutionStep(
            species_name=_clean_name(slug),
            species_slug=slug,
            species_id=sid,
            trigger_summary=trigger_summary,
            children=children,
        )

    @staticmethod
    def _parse_moves(moves_raw: list[dict[str, Any]]) -> PokemonMoveSummary:
        level_up: dict[str, int] = {}
        machine: set[str] = set()
        egg: set[str] = set()
        tutor: set[str] = set()

        for move_entry in moves_raw:
            move_name = _clean_name((move_entry.get("move") or {}).get("name", ""))
            if not move_name:
                continue
            details = move_entry.get("version_group_details") or []
            if not details:
                continue
            latest = details[-1]
            method = (latest.get("move_learn_method") or {}).get("name", "")
            level = int(latest.get("level_learned_at") or 0)

            if method == "level-up":
                if move_name not in level_up or level < level_up[move_name]:
                    level_up[move_name] = level
            elif method == "machine":
                machine.add(move_name)
            elif method == "egg":
                egg.add(move_name)
            elif method == "tutor":
                tutor.add(move_name)

        sorted_level_up = tuple(sorted(((lvl, name) for name, lvl in level_up.items()), key=lambda x: (x[0], x[1])))
        return PokemonMoveSummary(
            level_up=sorted_level_up,
            machine=tuple(sorted(machine)),
            egg=tuple(sorted(egg)),
            tutor=tuple(sorted(tutor)),
        )

    async def get_pokemon(self, identifier: str | int) -> PokemonEntry | None:  # noqa: PLR0911, PLR0912, PLR0915
        """Fetch a complete PokemonEntry by ID or slug, utilizing the in-memory LRU cache."""
        cache_key = identifier.lower().strip() if isinstance(identifier, str) else identifier
        if cache_key in self._entry_cache:
            self._entry_cache.move_to_end(cache_key)
            return self._entry_cache[cache_key]

        pokemon_data = await self._request_json(f"{POKEAPI_BASE_URL}/pokemon/{cache_key}")
        species_data: dict[str, Any] | None = None

        if pokemon_data is None:
            # Fallback: the user may have queried a species slug whose default variety has a suffix (e.g. deoxys -> deoxys-normal)
            species_data = await self._request_json(f"{POKEAPI_BASE_URL}/pokemon-species/{cache_key}")
            if species_data is None:
                return None

            varieties_raw = species_data.get("varieties") or []
            default_variety = next(
                (v for v in varieties_raw if v.get("is_default")),
                varieties_raw[0] if varieties_raw else None,
            )
            if not default_variety:
                return None
            default_poke_slug = (default_variety.get("pokemon") or {}).get("name")
            if not default_poke_slug:
                return None
            pokemon_data = await self._request_json(f"{POKEAPI_BASE_URL}/pokemon/{default_poke_slug}")
            if pokemon_data is None:
                return None

        species_url = (pokemon_data.get("species") or {}).get("url")
        if species_data is None and species_url:
            species_data = await self._request_json(species_url)

        if species_data is None:
            return None

        # Fetch evolution chain and type defenses concurrently
        evo_url = (species_data.get("evolution_chain") or {}).get("url")
        types = tuple(str(t["type"]["name"]) for t in sorted(pokemon_data.get("types") or [], key=lambda x: x.get("slot", 0)))

        evo_task = self._request_json(evo_url) if evo_url else asyncio.sleep(0, result=None)
        defenses_task = self.compute_type_defenses(types)
        evo_data, type_defenses = await asyncio.gather(evo_task, defenses_task)

        evolution_root: EvolutionStep | None = None
        if isinstance(evo_data, dict) and "chain" in evo_data:
            evolution_root = self._parse_evolution_chain(evo_data["chain"])

        # Localized names
        english_name: str | None = None
        japanese_name: str | None = None
        romaji_name: str | None = None
        for name_entry in species_data.get("names") or []:
            lang = (name_entry.get("language") or {}).get("name")
            if lang == "en":
                english_name = name_entry.get("name")
            elif lang == "ja-Hrkt":
                japanese_name = name_entry.get("name")
            elif lang == "roomaji":
                romaji_name = name_entry.get("name")

        poke_slug = str(pokemon_data.get("name", ""))
        species_slug = str(species_data.get("name", poke_slug))
        display_name = english_name or _clean_name(poke_slug)
        if poke_slug != species_slug and poke_slug.startswith(f"{species_slug}-"):
            suffix = _clean_name(poke_slug[len(species_slug) + 1 :])
            display_name = f"{display_name} ({suffix})"

        # Genus
        genus = "Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon"
        for g_entry in species_data.get("genera") or []:
            if (g_entry.get("language") or {}).get("name") == "en":
                genus = str(g_entry.get("genus", "Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon"))
                break

        # Flavor text (pick latest clean English entry)
        flavor_text = "No Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex description available for this Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon."
        en_flavors = [
            str(f.get("flavor_text", "")) for f in (species_data.get("flavor_text_entries") or []) if (f.get("language") or {}).get("name") == "en"
        ]
        if en_flavors:
            raw_flavor = en_flavors[-1]
            flavor_text = re.sub(r"[\n\f\r\s]+", " ", raw_flavor).strip()

        # Abilities
        abilities = tuple(
            PokemonAbility(
                name=_clean_name(str(ab["ability"]["name"])),
                slug=str(ab["ability"]["name"]),
                is_hidden=bool(ab.get("is_hidden", False)),
                slot=int(ab.get("slot", 1)),
            )
            for ab in sorted(pokemon_data.get("abilities") or [], key=lambda x: x.get("slot", 0))
            if ab.get("ability")
        )

        # Stats
        stats: dict[str, int] = {}
        for st in pokemon_data.get("stats") or []:
            st_name = str((st.get("stat") or {}).get("name", ""))
            if st_name:
                stats[st_name] = int(st.get("base_stat", 0))

        # Sprites & Artwork
        sprites = pokemon_data.get("sprites") or {}
        other_sprites = sprites.get("other") or {}
        official_art = other_sprites.get("official-artwork") or {}
        home_art = other_sprites.get("home") or {}
        showdown_art = other_sprites.get("showdown") or {}

        artwork_url = official_art.get("front_default") or home_art.get("front_default") or sprites.get("front_default")
        shiny_artwork_url = official_art.get("front_shiny") or home_art.get("front_shiny") or sprites.get("front_shiny")
        front_sprite_url = sprites.get("front_default")
        shiny_sprite_url = sprites.get("front_shiny")
        showdown_sprite_url = showdown_art.get("front_default")

        cries = pokemon_data.get("cries") or {}
        cry_url = cries.get("latest") or cries.get("legacy")

        # Held items
        held_items: list[tuple[str, int]] = []
        for hi in pokemon_data.get("held_items") or []:
            item_name = _clean_name(str((hi.get("item") or {}).get("name", "")))
            v_details = hi.get("version_details") or []
            rarity = int(v_details[-1].get("rarity", 0)) if v_details else 0
            if item_name:
                held_items.append((item_name, rarity))

        # Varieties
        varieties: list[PokemonVariety] = []
        for var in species_data.get("varieties") or []:
            p_obj = var.get("pokemon") or {}
            v_slug = str(p_obj.get("name", ""))
            v_id = _extract_id_from_url(str(p_obj.get("url", ""))) or 0
            if v_slug:
                varieties.append(
                    PokemonVariety(
                        name=_clean_name(v_slug),
                        slug=v_slug,
                        pokemon_id=v_id,
                        is_default=bool(var.get("is_default", False)),
                    )
                )

        gen_slug = str((species_data.get("generation") or {}).get("name", ""))
        generation = ROMAN_GENERATIONS.get(gen_slug, _clean_name(gen_slug) or "Unknown")

        egg_groups = tuple(_clean_name(str(eg.get("name", ""))) for eg in (species_data.get("egg_groups") or []) if eg.get("name"))
        habitat_raw = (species_data.get("habitat") or {}).get("name")
        growth_raw = (species_data.get("growth_rate") or {}).get("name")

        entry = PokemonEntry(
            id=int(pokemon_data.get("id", 0)),
            species_id=int(species_data.get("id", pokemon_data.get("id", 0))),
            slug=poke_slug,
            name=display_name,
            species_slug=species_slug,
            japanese_name=japanese_name,
            romaji_name=romaji_name,
            genus=genus,
            generation=generation,
            flavor_text=flavor_text,
            types=types,
            abilities=abilities,
            stats=stats,
            height_m=int(pokemon_data.get("height", 0)) / 10.0,
            weight_kg=int(pokemon_data.get("weight", 0)) / 10.0,
            base_experience=pokemon_data.get("base_experience"),
            capture_rate=int(species_data.get("capture_rate", 0)),
            base_happiness=species_data.get("base_happiness"),
            growth_rate=_clean_name(str(growth_raw)) if growth_raw else "Medium",
            gender_rate=int(species_data.get("gender_rate", -1)),
            egg_groups=egg_groups,
            hatch_counter=species_data.get("hatch_counter"),
            habitat=_clean_name(str(habitat_raw)) if habitat_raw else None,
            is_baby=bool(species_data.get("is_baby", False)),
            is_legendary=bool(species_data.get("is_legendary", False)),
            is_mythical=bool(species_data.get("is_mythical", False)),
            artwork_url=artwork_url,
            shiny_artwork_url=shiny_artwork_url,
            front_sprite_url=front_sprite_url,
            shiny_sprite_url=shiny_sprite_url,
            showdown_sprite_url=showdown_sprite_url,
            cry_url=cry_url,
            held_items=tuple(held_items),
            moves=self._parse_moves(pokemon_data.get("moves") or []),
            evolution_root=evolution_root,
            varieties=tuple(varieties),
            type_defenses=type_defenses,
        )

        # Cache under id, species_id, and slugs so all future lookups reuse this instance
        for key in {entry.id, entry.species_id, entry.slug, entry.species_slug}:
            self._entry_cache[key] = entry
        while len(self._entry_cache) > MAX_CACHE_ENTRIES:
            self._entry_cache.popitem(last=False)

        return entry

    @staticmethod
    def _build_wtp_card_sync(sprite_bytes: bytes, *, reveal: bool) -> bytes:
        """Render the 'Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon?' canvas (silhouette when reveal=False, full color when reveal=True)."""
        width, height = 720, 420
        bg = Image.new("RGBA", (width, height), (18, 25, 54, 255))
        draw = ImageDraw.Draw(bg)

        # Radial burst rays from center-left
        cx, cy = width // 2, height // 2
        for angle_deg in range(0, 360, 20):
            rad1 = math.radians(angle_deg)
            rad2 = math.radians(angle_deg + 10)
            r = 520
            pts = [
                (cx, cy),
                (cx + int(r * math.cos(rad1)), cy + int(r * math.sin(rad1))),
                (cx + int(r * math.cos(rad2)), cy + int(r * math.sin(rad2))),
            ]
            draw.polygon(pts, fill=(28, 42, 88, 255))

        # Soft circular spotlight behind the Pokémon
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((cx - 165, cy - 165, cx + 165, cy + 165), fill=(66, 135, 245, 95))
        glow_draw.ellipse((cx - 125, cy - 125, cx + 125, cy + 125), fill=(255, 215, 70, 130 if reveal else 75))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=22))
        bg = Image.alpha_composite(bg, glow)

        # Load and fit the Pokémon artwork
        sprite = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA")
        sprite.thumbnail((310, 310), Image.Resampling.LANCZOS)
        sx = cx - sprite.width // 2
        sy = cy - sprite.height // 2

        alpha = sprite.getchannel("A")

        # Subtle drop shadow
        shadow = Image.new("RGBA", sprite.size, (5, 8, 20, 0))
        shadow.putalpha(alpha.point(lambda p: int(p * 0.55)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
        bg.paste(shadow, (sx + 8, sy + 10), shadow)

        if reveal:
            bg.paste(sprite, (sx, sy), sprite)
        else:
            silhouette = Image.new("RGBA", sprite.size, (14, 19, 38, 255))
            silhouette.putalpha(alpha)
            bg.paste(silhouette, (sx, sy), silhouette)

        # Outer border accent
        border_draw = ImageDraw.Draw(bg)
        border_colour = (250, 204, 21, 255) if reveal else (88, 101, 242, 255)
        border_draw.rounded_rectangle((6, 6, width - 7, height - 7), radius=18, outline=border_colour, width=4)

        out = io.BytesIO()
        bg.save(out, format="PNG", optimize=True)
        return out.getvalue()

    async def render_wtp_card(self, entry: PokemonEntry, *, reveal: bool) -> discord.File | None:
        url = entry.best_image_url
        if not url:
            return None
        raw = await self.fetch_image_bytes(url)
        if not raw:
            return None
        png_bytes = await asyncio.to_thread(self._build_wtp_card_sync, raw, reveal=reveal)
        filename = "wtp_revealed.png" if reveal else "wtp_hidden.png"
        return discord.File(io.BytesIO(png_bytes), filename=filename)


def _format_evolution_tree(node: EvolutionStep, current_slug: str, depth: int = 0) -> list[str]:
    indent = "\N{IDEOGRAPHIC SPACE}" * depth
    prefix = "\N{BOX DRAWINGS LIGHT UP AND RIGHT}\N{BOX DRAWINGS LIGHT HORIZONTAL} " if depth > 0 else "\N{SEEDLING} "
    marker = " \N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16} *(Current)*" if node.species_slug == current_slug else ""
    trigger_text = f" \N{EM DASH} `{node.trigger_summary}`" if node.trigger_summary else ""
    line = f"{indent}{prefix}**#{node.species_id:04d} {node.species_name}**{trigger_text}{marker}"
    lines = [line]
    for child in node.children:
        lines.extend(_format_evolution_tree(child, current_slug, depth + 1))
    return lines


def _collect_evolution_species(node: EvolutionStep | None) -> list[EvolutionStep]:
    if node is None:
        return []
    items = [node]
    for child in node.children:
        items.extend(_collect_evolution_species(child))
    return items


class PokedexLayoutView(BaseLayoutView):
    """Interactive Components V2 Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex view supporting Overview, Stats, Evolutions, and Sprites/Moves."""

    def __init__(
        self,
        author: Author,
        service: PokemonDataService,
        entry: PokemonEntry,
        *,
        initial_tab: PokedexTab = "overview",
        timeout: float | None = POKEDEX_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(author, timeout=timeout)
        self.service = service
        self.entry = entry
        self.current_tab: PokedexTab = initial_tab
        self.shiny: bool = False
        self.rebuild_layout()

    def _build_header_section(self) -> discord.ui.Item[Any]:
        e = self.entry
        jp_part = f" \N{BULLET} *{e.japanese_name}*" if e.japanese_name else ""
        romaji_part = f" ({e.romaji_name})" if e.romaji_name else ""
        badge = f" \N{BULLET} {e.rarity_badge}" if e.rarity_badge else ""
        shiny_tag = " \N{SPARKLES} **(Shiny)**" if self.shiny else ""

        header_lines = [
            f"## #{e.species_id:04d} {e.name}{shiny_tag}",
            f"-# {e.genus}{jp_part}{romaji_part} \N{BULLET} {e.generation}{badge}",
            f"**Types:** {e.formatted_types}",
        ]
        header_text = discord.ui.TextDisplay("\n".join(header_lines))
        thumb_url = e.best_shiny_url if self.shiny else e.best_image_url
        if thumb_url:
            return discord.ui.Section(
                header_text,
                accessory=discord.ui.Thumbnail(thumb_url, description=f"{e.name} artwork"),
            )
        return header_text

    def _build_overview_items(self) -> list[discord.ui.Item[Any]]:
        e = self.entry
        ability_parts: list[str] = []
        for ab in e.abilities:
            if ab.is_hidden:
                ability_parts.append(f"*{ab.name}* (Hidden)")
            else:
                ability_parts.append(f"**{ab.name}**")
        abilities_str = ", ".join(ability_parts) if ability_parts else "None"

        feet_total = e.height_m * 39.3701
        feet = int(feet_total // 12)
        inches = round(feet_total % 12)
        if inches == 12:
            feet += 1
            inches = 0
        lbs = e.weight_kg * 2.20462

        egg_groups_str = ", ".join(e.egg_groups) if e.egg_groups else "Undiscovered"
        egg_cycles = f"{e.hatch_counter} cycles (~{(e.hatch_counter or 0) * 255:,} steps)" if e.hatch_counter is not None else "\N{EM DASH}"
        held_str = ", ".join(f"{name} ({rarity}%)" for name, rarity in e.held_items) if e.held_items else "None"

        traits_md = (
            f"> *{e.flavor_text}*\n\n"
            f"### \N{CLIPBOARD} Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex Profile & Training\n"
            f"- **Height / Weight:** `{e.height_m:.1f} m` ({feet}'{inches:02d}\") \N{BULLET} `{e.weight_kg:.1f} kg` ({lbs:.1f} lbs)\n"
            f"- **Abilities:** {abilities_str}\n"
            f"- **Catch Rate:** `{e.capture_rate}` \N{BULLET} **Base Exp:** `{e.base_experience or '—'}` \N{BULLET} **Growth:** `{e.growth_rate}`\n"
            f"- **Base Happiness:** `{e.base_happiness if e.base_happiness is not None else '—'}` \N{BULLET} **Habitat:** `{e.habitat or 'Wild / Unknown'}`\n"
            f"- **Held Items:** {held_str}\n"
            f"### \N{EGG} Breeding Details\n"
            f"- **Gender Ratio:** {e.gender_display}\n"
            f"- **Egg Groups:** {egg_groups_str} \N{BULLET} **Hatch Time:** {egg_cycles}"
        )
        return [discord.ui.TextDisplay(traits_md)]

    def _build_stats_items(self) -> list[discord.ui.Item[Any]]:
        e = self.entry
        stat_lines: list[str] = ["### \N{BAR CHART} Base Stats & Level 100 Range"]
        for key, label in STAT_LABELS.items():
            val = e.stats.get(key, 0)
            low, high = _calc_stat_range(key, val)
            bar = _stat_bar(val)
            stat_lines.append(f"`{label}: {val:>3}` `{bar}` *(Lv.100: {low}\N{EN DASH}{high})*")
        stat_lines.append(f"**Base Stat Total (BST):** `{e.bst}`")

        # Group defensive multipliers
        quad_weak = [f"{TYPE_EMOJIS.get(t, '')} {t.title()} (4\N{MULTIPLICATION SIGN})" for t, m in e.type_defenses.items() if m >= 4.0]
        weak = [f"{TYPE_EMOJIS.get(t, '')} {t.title()} (2\N{MULTIPLICATION SIGN})" for t, m in e.type_defenses.items() if m == 2.0]
        resist = [
            f"{TYPE_EMOJIS.get(t, '')} {t.title()} (\N{VULGAR FRACTION ONE HALF}\N{MULTIPLICATION SIGN})"
            for t, m in e.type_defenses.items()
            if m == 0.5
        ]
        quad_resist = [
            f"{TYPE_EMOJIS.get(t, '')} {t.title()} (\N{VULGAR FRACTION ONE QUARTER}\N{MULTIPLICATION SIGN})"
            for t, m in e.type_defenses.items()
            if m == 0.25
        ]
        immune = [f"{TYPE_EMOJIS.get(t, '')} {t.title()} (0\N{MULTIPLICATION SIGN})" for t, m in e.type_defenses.items() if m == 0.0]

        weak_all = quad_weak + weak
        resist_all = quad_resist + resist

        stat_lines.extend(
            [
                "",
                "### \N{SHIELD}\N{VARIATION SELECTOR-16} Defensive Type Matchups",
                f"- **Weaknesses:** {', '.join(weak_all) if weak_all else 'None'}",
                f"- **Resistances:** {', '.join(resist_all) if resist_all else 'None'}",
                f"- **Immunities:** {', '.join(immune) if immune else 'None'}",
            ]
        )
        return [discord.ui.TextDisplay("\n".join(stat_lines))]

    def _build_evolutions_items(self) -> list[discord.ui.Item[Any]]:
        e = self.entry
        lines = ["### \N{DNA DOUBLE HELIX} Evolution Chain"]
        if e.evolution_root:
            lines.extend(_format_evolution_tree(e.evolution_root, e.species_slug))
        else:
            lines.append("This Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon does not belong to an evolution chain.")

        if len(e.varieties) > 1:
            lines.append("\n### \N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS} Regional & Alternate Forms")
            for var in e.varieties:
                default_tag = " *(Default)*" if var.is_default else ""
                active_tag = " \N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}" if var.slug == e.slug else ""
                lines.append(f"- **{var.name}** (`#{var.pokemon_id}`){default_tag}{active_tag}")

        return [discord.ui.TextDisplay("\n".join(lines))]

    def _build_media_items(self) -> list[discord.ui.Item[Any]]:
        e = self.entry
        items: list[discord.ui.Item[Any]] = []

        lvl_moves = [f"`Lv.{lvl:>2}` {name}" if lvl > 0 else f"`Evo ` {name}" for lvl, name in e.moves.level_up[:14]]
        tm_moves = e.moves.machine[:14]
        egg_moves = e.moves.egg[:10]

        move_lines = [
            "### \N{CROSSED SWORDS}\N{VARIATION SELECTOR-16} Notable Moveset Summary",
            f"- **Level-Up ({len(e.moves.level_up)} total):** {', '.join(lvl_moves) if lvl_moves else 'None'}",
            f"- **TM / Machine ({len(e.moves.machine)} total):** {', '.join(tm_moves) if tm_moves else 'None'}",
            f"- **Egg Moves ({len(e.moves.egg)} total):** {', '.join(egg_moves) if egg_moves else 'None'}",
        ]
        if e.cry_url:
            move_lines.append(f"- **Latest Battle Cry:** [Listen to {e.name}'s Cry (OGG)]({e.cry_url})")

        items.append(discord.ui.TextDisplay("\n".join(move_lines)))

        gallery_items: list[discord.MediaGalleryItem] = []
        if e.artwork_url:
            gallery_items.append(discord.MediaGalleryItem(e.artwork_url, description=f"{e.name} Official Artwork"))
        if e.shiny_artwork_url:
            gallery_items.append(discord.MediaGalleryItem(e.shiny_artwork_url, description=f"Shiny {e.name} Official Artwork"))
        if e.front_sprite_url and e.front_sprite_url != e.artwork_url:
            gallery_items.append(discord.MediaGalleryItem(e.front_sprite_url, description=f"{e.name} Sprite"))
        if e.shiny_sprite_url and e.shiny_sprite_url != e.shiny_artwork_url:
            gallery_items.append(discord.MediaGalleryItem(e.shiny_sprite_url, description=f"Shiny {e.name} Sprite"))

        if gallery_items:
            items.append(discord.ui.MediaGallery(*gallery_items[:4]))

        return items

    def _build_evolution_select_row(self) -> discord.ui.ActionRow[Self] | None:
        e = self.entry
        seen_slugs: set[str] = set()
        options: list[discord.SelectOption] = []

        for step in _collect_evolution_species(e.evolution_root):
            if step.species_slug not in seen_slugs:
                seen_slugs.add(step.species_slug)
                options.append(
                    discord.SelectOption(
                        label=truncate(f"#{step.species_id:04d} {step.species_name}", 100),
                        value=step.species_slug,
                        description=truncate(step.trigger_summary or "Evolution stage", 100),
                        emoji="\N{DNA DOUBLE HELIX}",
                        default=(step.species_slug == e.species_slug and e.slug == e.species_slug),
                    )
                )

        for var in e.varieties:
            if var.slug not in seen_slugs and len(options) < 25:
                seen_slugs.add(var.slug)
                options.append(
                    discord.SelectOption(
                        label=truncate(var.name, 100),
                        value=var.slug,
                        description="Alternate / Regional Form" if not var.is_default else "Default Form",
                        emoji="\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}",
                        default=(var.slug == e.slug),
                    )
                )

        if len(options) <= 1:
            return None

        select = discord.ui.Select[Self](
            placeholder="Switch to an evolution stage or alternate form\N{HORIZONTAL ELLIPSIS}",
            options=options[:25],
        )

        async def _on_select(interaction: discord.Interaction) -> None:
            target_slug = select.values[0]
            await interaction.response.defer()
            new_entry = await self.service.get_pokemon(target_slug)
            if new_entry is None:
                await interaction.followup.send("Could not load that Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon form right now.", ephemeral=True)
                return
            self.entry = new_entry
            self.rebuild_layout()
            await self.update_message()

        select.callback = _on_select
        return discord.ui.ActionRow(select)

    def _build_tab_row(self) -> discord.ui.ActionRow[Self]:
        tabs: list[tuple[PokedexTab, str, str]] = [
            ("overview", "Overview", "\N{OPEN BOOK}"),
            ("stats", "Stats & Types", "\N{BAR CHART}"),
            ("evolutions", "Evolutions", "\N{DNA DOUBLE HELIX}"),
            ("media", "Moves & Art", "\N{ARTIST PALETTE}"),
        ]
        row = discord.ui.ActionRow[Self]()
        for tab_id, label, emoji in tabs:
            is_active = self.current_tab == tab_id
            style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
            btn = discord.ui.Button[Self](label=label, emoji=emoji, style=style, disabled=is_active)

            async def _switch_tab(interaction: discord.Interaction, target: PokedexTab = tab_id) -> None:
                self.current_tab = target
                self.rebuild_layout()
                await interaction.response.edit_message(view=self)

            btn.callback = _switch_tab
            row.add_item(btn)
        return row

    def _build_navigation_row(self) -> discord.ui.ActionRow[Self]:
        e = self.entry
        row = discord.ui.ActionRow[Self]()

        prev_btn = discord.ui.Button[Self](
            label=f"#{max(1, e.species_id - 1):04d}",
            emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            style=discord.ButtonStyle.secondary,
            disabled=(e.species_id <= 1),
        )
        shiny_btn = discord.ui.Button[Self](
            label="Normal Art" if self.shiny else "Shiny Art",
            emoji="\N{SPARKLES}",
            style=discord.ButtonStyle.success if self.shiny else discord.ButtonStyle.secondary,
        )
        random_btn = discord.ui.Button[Self](
            label="Random",
            emoji="\N{GAME DIE}",
            style=discord.ButtonStyle.secondary,
        )
        next_btn = discord.ui.Button[Self](
            label=f"#{e.species_id + 1:04d}",
            emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            style=discord.ButtonStyle.secondary,
            disabled=(e.species_id >= 1025),
        )

        async def _go_prev(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            target = await self.service.get_pokemon(max(1, self.entry.species_id - 1))
            if target:
                self.entry = target
                self.rebuild_layout()
                await self.update_message()

        async def _toggle_shiny(interaction: discord.Interaction) -> None:
            self.shiny = not self.shiny
            self.rebuild_layout()
            await interaction.response.edit_message(view=self)

        async def _go_random(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            target = await self.service.get_random_pokemon()
            if target:
                self.entry = target
                self.rebuild_layout()
                await self.update_message()

        async def _go_next(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            target = await self.service.get_pokemon(self.entry.species_id + 1)
            if target:
                self.entry = target
                self.rebuild_layout()
                await self.update_message()

        prev_btn.callback = _go_prev
        shiny_btn.callback = _toggle_shiny
        random_btn.callback = _go_random
        next_btn.callback = _go_next

        row.add_item(prev_btn)
        row.add_item(shiny_btn)
        row.add_item(random_btn)
        row.add_item(next_btn)
        return row

    def rebuild_layout(self) -> None:
        self.clear_items()
        container = discord.ui.Container(accent_colour=self.entry.primary_colour)

        container.add_item(self._build_header_section())
        container.add_item(discord.ui.Separator())

        if self.current_tab == "overview":
            body_items = self._build_overview_items()
        elif self.current_tab == "stats":
            body_items = self._build_stats_items()
        elif self.current_tab == "evolutions":
            body_items = self._build_evolutions_items()
        else:
            body_items = self._build_media_items()

        for item in body_items:
            container.add_item(item)

        select_row = self._build_evolution_select_row()
        if select_row is not None and self.current_tab in ("evolutions", "overview"):
            container.add_item(discord.ui.Separator())
            container.add_item(select_row)

        container.add_item(discord.ui.Separator())
        container.add_item(self._build_tab_row())
        container.add_item(self._build_navigation_row())
        container.add_item(
            discord.ui.TextDisplay(
                f"-# Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex \N{BULLET} Requested by {safe_text(self.author.display_name, 32)} \N{BULLET} Data via Pok\N{LATIN SMALL LETTER E WITH ACUTE}API v2"
            )
        )
        self.add_item(container)


class PokemonCompareLayoutView(BaseLayoutView):
    """Side-by-side Components V2 comparison of two Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon reusing PokemonEntry."""

    def __init__(
        self,
        author: Author,
        first: PokemonEntry,
        second: PokemonEntry,
        *,
        timeout: float | None = 180.0,
    ) -> None:
        super().__init__(author, timeout=timeout)
        self.first = first
        self.second = second
        self._build()

    def _build(self) -> None:
        a, b = self.first, self.second
        container = discord.ui.Container(accent_colour=a.primary_colour)

        header = discord.ui.TextDisplay(
            f"## \N{CROSSED SWORDS}\N{VARIATION SELECTOR-16} Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon Comparison\n"
            f"**#{a.species_id:04d} {a.name}** ({a.formatted_types}) vs. "
            f"**#{b.species_id:04d} {b.name}** ({b.formatted_types})"
        )
        container.add_item(header)
        container.add_item(discord.ui.Separator())

        stat_rows = ["### \N{BAR CHART} Base Stat Breakdown"]
        for key, label in STAT_LABELS.items():
            va = a.stats.get(key, 0)
            vb = b.stats.get(key, 0)
            diff = va - vb
            indicator = "\N{LARGE GREEN CIRCLE}" if diff > 0 else ("\N{LARGE RED CIRCLE}" if diff < 0 else "\N{MEDIUM WHITE CIRCLE}")
            stat_rows.append(f"`{label}` **{a.name}:** `{va:>3}` | `{vb:<3}` **:{b.name}** {indicator} (`{diff:+d}`)")

        bst_diff = a.bst - b.bst
        stat_rows.append(f"\n**Total BST:** `{a.bst}` vs `{b.bst}` (`{bst_diff:+d}`)")
        stat_rows.append(f"**Height / Weight:** `{a.height_m:.1f}m / {a.weight_kg:.1f}kg` vs `{b.height_m:.1f}m / {b.weight_kg:.1f}kg`")
        container.add_item(discord.ui.TextDisplay("\n".join(stat_rows)))

        gallery_items: list[discord.MediaGalleryItem] = []
        if a.best_image_url:
            gallery_items.append(discord.MediaGalleryItem(a.best_image_url, description=a.name))
        if b.best_image_url:
            gallery_items.append(discord.MediaGalleryItem(b.best_image_url, description=b.name))
        if gallery_items:
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.MediaGallery(*gallery_items))

        self.add_item(container)


class WhosThatPokemonLayoutView(BaseLayoutView):
    """Components V2 layout for the 'Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon?' game reusing PokemonDataService & PokemonEntry."""

    def __init__(
        self,
        ctx: commands.Context[Bot],
        service: PokemonDataService,
        entry: PokemonEntry,
        *,
        generation: int | None = None,
        timeout: float = WTP_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(ctx.author, timeout=timeout)
        self.ctx = ctx
        self.service = service
        self.entry = entry
        self.generation = generation
        self.hints_revealed: int = 0
        self.settled: bool = False
        self.started_at: float = time.monotonic()
        self.done_event = asyncio.Event()
        self.rebuild_active_layout()

    @override
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Anyone in the channel can request a hint or open the Pokédex after reveal;
        # only the command author (or Manage Messages) can force-skip before timeout.
        return True

    def _current_hints(self) -> list[str]:
        e = self.entry
        all_hints = [
            f"**Hint 1 (Typing & Region):** {e.formatted_types} \N{BULLET} {e.generation}",
            f"**Hint 2 (Category & Ability):** {e.genus} \N{BULLET} Primary Ability: **{e.abilities[0].name if e.abilities else 'Unknown'}**",
            f"**Hint 3 (Stats & Size):** Base Stat Total `{e.bst}` \N{BULLET} Height `{e.height_m:.1f} m`, Weight `{e.weight_kg:.1f} kg`",
            f"**Hint 4 (Name Pattern):** Starts with **`{e.species_slug[0].upper()}`**, ends with **`{e.species_slug[-1].upper()}`** ({plural(len(_clean_name(e.species_slug))):character})",
        ]
        return all_hints[: self.hints_revealed]

    def rebuild_active_layout(self) -> None:
        self.clear_items()
        gen_subtitle = f"Generation {self.generation}" if self.generation else "All Generations (Gen I\N{EN DASH}IX)"
        hints = self._current_hints()
        hint_block = "\n".join(f"- {h}" for h in hints) if hints else "-# Need a clue? Click **Get Hint** below!"

        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        container.add_item(
            discord.ui.TextDisplay(
                f"## \N{BLACK QUESTION MARK ORNAMENT} Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon?\n"
                f"-# {gen_subtitle} \N{BULLET} Type your guess directly in chat within **{int(WTP_TIMEOUT_SECONDS)} seconds**!\n\n"
                f"{hint_block}"
            )
        )
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem("attachment://wtp_hidden.png", description="Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon silhouette")
            )
        )
        container.add_item(discord.ui.Separator())

        hint_btn = discord.ui.Button[Self](
            label=f"Get Hint ({self.hints_revealed}/4)",
            emoji="\N{ELECTRIC LIGHT BULB}",
            style=discord.ButtonStyle.primary,
            disabled=(self.hints_revealed >= 4),
        )
        give_up_btn = discord.ui.Button[Self](
            label="Give Up",
            emoji="\N{WAVING WHITE FLAG}\N{VARIATION SELECTOR-16}",
            style=discord.ButtonStyle.danger,
        )

        async def _on_hint(interaction: discord.Interaction) -> None:
            if self.settled:
                await interaction.response.defer()
                return
            if self.hints_revealed < 4:
                self.hints_revealed += 1
            self.rebuild_active_layout()
            await interaction.response.edit_message(view=self)

        async def _on_give_up(interaction: discord.Interaction) -> None:
            if interaction.user.id != self.author.id:
                await interaction.response.send_message(
                    f"Only {self.author.mention} can end this round early.",
                    ephemeral=True,
                )
                return
            if self.settled:
                await interaction.response.defer()
                return
            await interaction.response.defer()
            await self.settle_game(winner=None, reason="Round ended early by host.")

        hint_btn.callback = _on_hint
        give_up_btn.callback = _on_give_up

        container.add_item(discord.ui.ActionRow(hint_btn, give_up_btn))
        self.add_item(container)

    def _build_settled_layout(
        self,
        *,
        winner: discord.abc.User | None,
        elapsed: float,
        reason: str | None = None,
        has_revealed_attachment: bool = True,
    ) -> None:
        self.clear_items()
        e = self.entry
        colour = discord.Colour.green() if winner else discord.Colour.orange()

        if winner is not None:
            headline = f"\N{PARTY POPPER} {winner.mention} guessed it in `{elapsed:.1f}s`! It's **{e.name}**!"
        else:
            headline = f"\N{ALARM CLOCK} {reason or 'Time is up!'} It was **#{e.species_id:04d} {e.name}**!"

        jp_text = f" (*{e.japanese_name}*)" if e.japanese_name else ""
        summary_md = (
            f"## \N{SPARKLES} It's #{e.species_id:04d} {e.name}!{jp_text}\n"
            f"{headline}\n\n"
            f"- **Types:** {e.formatted_types} \N{BULLET} **Category:** {e.genus} ({e.generation})\n"
            f"- **BST:** `{e.bst}` \N{BULLET} **Abilities:** {', '.join(a.name for a in e.abilities)}\n"
            f"> *{e.flavor_text}*"
        )

        container = discord.ui.Container(accent_colour=colour)
        container.add_item(discord.ui.TextDisplay(summary_md))

        media_url = "attachment://wtp_revealed.png" if has_revealed_attachment else (e.best_image_url or "")
        if media_url:
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media_url, description=f"It's {e.name}!")))

        container.add_item(discord.ui.Separator())

        dex_btn = discord.ui.Button[Self](
            label=f"Open {e.name} in Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex",
            emoji="\N{OPEN BOOK}",
            style=discord.ButtonStyle.secondary,
        )

        async def _open_pokedex(interaction: discord.Interaction) -> None:
            dex_view = PokedexLayoutView(interaction.user, self.service, self.entry)
            await interaction.response.send_message(view=dex_view)
            dex_view.message = await interaction.original_response()

        dex_btn.callback = _open_pokedex
        container.add_item(discord.ui.ActionRow(dex_btn))
        self.add_item(container)

    async def settle_game(
        self,
        *,
        winner: discord.abc.User | None,
        reason: str | None = None,
    ) -> None:
        if self.settled:
            return
        self.settled = True
        self.done_event.set()
        self.stop()

        elapsed = time.monotonic() - self.started_at
        revealed_file = await self.service.render_wtp_card(self.entry, reveal=True)
        self._build_settled_layout(
            winner=winner,
            elapsed=elapsed,
            reason=reason,
            has_revealed_attachment=(revealed_file is not None),
        )

        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                if revealed_file is not None:
                    await self.message.edit(view=self, attachments=[revealed_file])
                else:
                    await self.message.edit(view=self, attachments=[])

    @override
    async def on_timeout(self) -> None:
        if not self.settled:
            await self.settle_game(winner=None, reason="Time's up! Nobody guessed in time.")


class Pokemon(commands.Cog, command_attrs={"hidden": True}):
    """Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex lookup, evolution & stat explorer, and 'Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon?' trivia using Components V2."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.service = PokemonDataService(bot)
        self._active_wtp_channels: set[int] = set()
        self._session_stats: dict[int, int] = {}  # user_id -> correct guesses in current runtime

    async def _resolve_pokemon_arg(self, ctx: commands.Context[Bot], query: str) -> PokemonEntry | None:
        """Resolve a user query to a single PokemonEntry, using bot.disambiguate when multiple matches exist."""
        cleaned = query.strip()
        # Try direct lookup first if numeric or exact slug
        if cleaned.lstrip("#").isdigit():
            entry = await self.service.get_pokemon(int(cleaned.lstrip("#")))
            if entry is not None:
                return entry

        matches = await self.service.search_species(cleaned, limit=15)
        if not matches:
            await ctx.reply(
                view=NoticeLayout.error(
                    f"Could not find any Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon matching `{safe_text(query, 50)}`.",
                    title="Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex Lookup Failed",
                )
            )
            return None

        # Exact match on first candidate
        top_slug, _ = matches[0]
        if _normalize_guess(top_slug) == _normalize_guess(cleaned) or len(matches) == 1:
            return await self.service.get_pokemon(top_slug)

        try:
            chosen_slug, _chosen_id = await self.bot.disambiguate(
                ctx,
                matches=matches,
                entry=lambda item: discord.SelectOption(
                    label=f"#{item[1]:04d} {_clean_name(item[0])}",
                    value=item[0],
                    description=f"National Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex #{item[1]:04d}",
                ),
            )
        except (ValueError, AttributeError) as exc:
            if isinstance(exc, ValueError):
                await ctx.reply(view=NoticeLayout.warning(str(exc), title="Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex Search"))
            return None

        if not chosen_slug:
            return None
        return await self.service.get_pokemon(chosen_slug)

    @commands.group(
        name="pokedex",
        aliases=("dex", "pokemon", "pkmn"),
        invoke_without_command=True,
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pokedex(self, ctx: commands.Context[Bot], *, query: str | None = None) -> None:
        """Look up a Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon in the interactive Components V2 Pok\N{LATIN SMALL LETTER E WITH ACUTE}dex (or pick a random one if omitted)."""
        async with ctx.typing():
            if query is None:
                entry = await self.service.get_random_pokemon()
                if entry is None:
                    await ctx.reply(
                        view=NoticeLayout.error("Could not reach Pok\N{LATIN SMALL LETTER E WITH ACUTE}API right now. Please try again shortly.")
                    )
                    return
            else:
                entry = await self._resolve_pokemon_arg(ctx, query)
                if entry is None:
                    return

        view = PokedexLayoutView(ctx.author, self.service, entry, initial_tab="overview")
        view.message = await ctx.reply(view=view)

    @pokedex.command(name="evolution", aliases=("evo", "chain", "forms"))
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pokedex_evolution(self, ctx: commands.Context[Bot], *, query: str) -> None:
        """Inspect the full evolution tree and regional/alternate forms for a Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon."""
        async with ctx.typing():
            entry = await self._resolve_pokemon_arg(ctx, query)
            if entry is None:
                return

        view = PokedexLayoutView(ctx.author, self.service, entry, initial_tab="evolutions")
        view.message = await ctx.reply(view=view)

    @pokedex.command(name="stats", aliases=("bst", "defenses", "weakness"))
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pokedex_stats(self, ctx: commands.Context[Bot], *, query: str) -> None:
        """View a Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon's base stats, Lv.100 min/max ranges, and type effectiveness multipliers."""
        async with ctx.typing():
            entry = await self._resolve_pokemon_arg(ctx, query)
            if entry is None:
                return

        view = PokedexLayoutView(ctx.author, self.service, entry, initial_tab="stats")
        view.message = await ctx.reply(view=view)

    @pokedex.command(name="compare", aliases=("vs", "diff"))
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def pokedex_compare(self, ctx: commands.Context[Bot], first: str, second: str) -> None:
        """Compare two Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon side-by-side across base stats, types, and physical traits."""
        async with ctx.typing():
            entry_a = await self._resolve_pokemon_arg(ctx, first)
            if entry_a is None:
                return
            entry_b = await self._resolve_pokemon_arg(ctx, second)
            if entry_b is None:
                return

        view = PokemonCompareLayoutView(ctx.author, entry_a, entry_b)
        view.message = await ctx.reply(view=view)

    @commands.command(
        name="whosthatpokemon",
        aliases=("wtp", "pokequiz", "guesspokemon"),
    )
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def whos_that_pokemon(self, ctx: commands.Context[Bot], generation: str | None = None) -> None:  # noqa: PLR0912, PLR0915
        """Start a 'Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon?' silhouette guessing game in the current channel.

        Optionally specify a generation (e.g. ``1``\N{EN DASH}``9`` or ``gen1``\N{EN DASH}``gen9``).
        """
        if ctx.channel.id in self._active_wtp_channels:
            await ctx.reply(
                view=NoticeLayout.warning(
                    "A **Who's That Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon?** round is already active in this channel! Guess the current Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon first.",
                    title="Game Already Active",
                )
            )
            return

        gen_num: int | None = None
        if generation is not None:
            cleaned_gen = generation.lower().strip().removeprefix("gen").removeprefix("generation").strip()
            if not cleaned_gen.isdigit() or int(cleaned_gen) not in GENERATION_RANGES:
                valid_gens = human_join([str(g) for g in GENERATION_RANGES], final="or")
                await ctx.reply(
                    view=NoticeLayout.error(
                        f"Invalid generation `{safe_text(generation, 20)}`. Choose a generation from {valid_gens}.",
                        title="Invalid Generation",
                    )
                )
                return
            gen_num = int(cleaned_gen)

        self._active_wtp_channels.add(ctx.channel.id)
        try:
            async with ctx.typing():
                entry = await self.service.get_random_pokemon(generation=gen_num)
                if entry is None:
                    await ctx.reply(
                        view=NoticeLayout.error(
                            "Could not fetch a Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon for the game right now. Please try again."
                        )
                    )
                    return

                hidden_card = await self.service.render_wtp_card(entry, reveal=False)
                if hidden_card is None:
                    await ctx.reply(
                        view=NoticeLayout.error(
                            "Failed to generate the Pok\N{LATIN SMALL LETTER E WITH ACUTE}mon silhouette image. Please try again."
                        )
                    )
                    return

            view = WhosThatPokemonLayoutView(
                ctx,
                self.service,
                entry,
                generation=gen_num,
                timeout=WTP_TIMEOUT_SECONDS,
            )
            view.message = await ctx.reply(view=view, file=hidden_card)

            accepted = entry.accepted_names()

            def _check_guess(msg: discord.Message) -> bool:
                if msg.channel.id != ctx.channel.id or msg.author.bot:
                    return False
                candidate = _normalize_guess(msg.content)
                if not candidate or len(candidate) < 3:
                    return False
                if candidate in accepted:
                    return True
                # Allow minor 1-character typo on longer Pokémon names via RapidFuzz ratio
                return any(len(target) >= 6 and fuzz.ratio(candidate, target) >= 88 for target in accepted)

            while not view.settled:
                remaining = WTP_TIMEOUT_SECONDS - (time.monotonic() - view.started_at)
                if remaining <= 0:
                    await view.settle_game(winner=None, reason="Time's up! Nobody guessed in time.")
                    break

                msg_task = asyncio.create_task(self.bot.wait_for("message", check=_check_guess, timeout=remaining))
                done_task = asyncio.create_task(view.done_event.wait())

                done, pending = await asyncio.wait(
                    {msg_task, done_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

                if done_task in done and view.settled:
                    break

                if msg_task in done:
                    try:
                        winning_msg = msg_task.result()
                    except TimeoutError:
                        await view.settle_game(winner=None, reason="Time's up! Nobody guessed in time.")
                        break
                    else:
                        uid = winning_msg.author.id
                        self._session_stats[uid] = self._session_stats.get(uid, 0) + 1
                        with contextlib.suppress(discord.HTTPException):
                            await winning_msg.add_reaction("\N{PARTY POPPER}")
                        await view.settle_game(winner=winning_msg.author)
                        break
        finally:
            self._active_wtp_channels.discard(ctx.channel.id)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Pokemon(bot))
