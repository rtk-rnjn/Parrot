from __future__ import annotations

from typing import Literal, Optional

from discord.ext import commands
from utilities.converters import convert_bool


class TTFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    var: str
    con: str
    ascending: convert_bool = True
    table_format: str = "psql"
    align: str = "center"
    valuation: convert_bool = False
    latex: convert_bool = False


class SearchFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    c2coff: Optional[int] = 0
    exact_terms: Optional[str] = None
    exclude_terms: Optional[str] = None
    file_type: Optional[str] = None
    filter: Optional[str] = None
    gl: Optional[str] = None
    high_range: Optional[str] = None
    hl: Optional[str] = None
    hq: Optional[str] = None
    img_color_type: Optional[Literal["color", "gray", "mono", "trans"]] = None
    img_dominant_color: Optional[
        Literal[
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
        ]
    ] = None
    img_size: Optional[Literal["huge", "icon", "large", "medium", "small", "xlarge", "xxlarge"]] = None
    img_type: Optional[Literal["face", "photo", "clipart", "lineart", "stock", "animated"]] = None
    link_site: Optional[str] = None
    low_range: Optional[str] = None
    lr: Optional[
        Literal[
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
        ]
    ] = None
    num: Optional[Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]] = None
    or_terms: Optional[str] = None
    q: str
    related_site: Optional[str] = None
    rights: Optional[
        Literal[
            "cc_publicdomain",
            "cc_attribute",
            "cc_sharealike",
            "cc_noncommercial",
            "cc_nonderived",
        ]
    ] = None
    safe: Optional[Literal["active", "off"]] = None
    search_type: Optional[Literal["image"]] = None
    site_search: Optional[str] = None
    site_search_filter: Optional[Literal["i", "e"]] = None
    sort: Optional[str] = None
    start: Optional[int] = None
