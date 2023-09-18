from __future__ import annotations

from typing import Annotated, Literal

from discord.ext import commands
from utilities.converters import convert_bool


class TTFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    var: str
    con: str
    ascending: Annotated[bool, convert_bool] = True
    table_format: str = "psql"
    align: str = "center"
    valuation: Annotated[bool, convert_bool] = False
    latex: Annotated[bool, convert_bool] = False


class SearchFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    c2coff: int | None = 0
    exact_terms: str | None = None
    exclude_terms: str | None = None
    file_type: str | None = None
    filter: str | None = None
    gl: str | None = None
    high_range: str | None = None
    hl: str | None = None
    hq: str | None = None
    img_color_type: Literal["color", "gray", "mono", "trans"] | None = None
    img_dominant_color: Literal[
        "black",
        "blue",
        "brown",
        "gray",
        "green",
        "orange",
        "ping",
        "purple",
        "red",
        "teal",
        "white",
        "yellow",
    ] | None = None
    img_size: Literal["huge", "icon", "large", "medium", "small", "xlarge", "xxlarge"] | None = None
    img_type: Literal["face", "photo", "clipart", "lineart", "stock", "animated"] | None = None
    link_site: str | None = None
    low_range: str | None = None
    lr: Literal[
        "lang_ar",
        "lang_bg",
        "lang_cs",
        "lang_da",
        "lang_de",
        "lang_ca",
        "lang_el",
        "lang_en",
        "lang_es",
        "lang_et",
        "lang_fi",
        "lang_fr",
        "lang_hr",
        "lang_hu",
        "lang_id",
        "lang_is",
        "lang_it",
        "lang_iw",
        "lang_ja",
        "lang_ko",
        "lang_lt",
        "lang_lv",
        "lang_nl",
        "lang_no",
        "lang_pl",
        "lang_pt",
        "lang_ro",
        "lang_ru",
        "lang_sk",
        "lang_sl",
        "lang_sr",
        "lang_sv",
        "lang_tr",
        "lang_zh-CN",
        "lang_zh-TW",
    ] | None = None
    num: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | None = None
    or_terms: str | None = None
    q: str
    related_site: str | None = None
    rights: Literal[
        "cc_publicdomain",
        "cc_attribute",
        "cc_sharealike",
        "cc_noncommercial",
        "cc_nonderived",
    ] | None = None
    safe: Literal["active", "off"] | None = None
    search_type: Literal["image"] | None = None
    site_search: str | None = None
    site_search_filter: Literal["i", "e"] | None = None
    sort: str | None = None
    start: int | None = None
