from __future__ import annotations

import re
from dataclasses import dataclass, field

import discord

# Maps canonical lowercase POS tokens to (Full Human-Readable Label, Emoji Icon, Hex Color)
POS_CANONICAL_MAP: dict[str, tuple[str, str, int]] = {
    # Nouns
    "n.": ("Noun", "📘", 0x5865F2),
    "n.pl.": ("Plural Noun", "📘", 0x5865F2),
    "n. pl.": ("Plural Noun", "📘", 0x5865F2),
    "pl. n.": ("Plural Noun", "📘", 0x5865F2),
    "pl.n.": ("Plural Noun", "📘", 0x5865F2),
    "n.sing.": ("Singular Noun", "📘", 0x5865F2),
    "n. sing.": ("Singular Noun", "📘", 0x5865F2),
    "sing. n.": ("Singular Noun", "📘", 0x5865F2),
    "prop. n.": ("Proper Noun", "📘", 0x5865F2),
    # Verbs
    "v.": ("Verb", "⚡", 0xF59E0B),
    "v.intr.": ("Intransitive Verb", "⚡", 0xF59E0B),
    "v. intr.": ("Intransitive Verb", "⚡", 0xF59E0B),
    "intr. v.": ("Intransitive Verb", "⚡", 0xF59E0B),
    "v.tr.": ("Transitive Verb", "⚡", 0xF59E0B),
    "v. tr.": ("Transitive Verb", "⚡", 0xF59E0B),
    "tr. v.": ("Transitive Verb", "⚡", 0xF59E0B),
    "v.aux.": ("Auxiliary Verb", "⚡", 0xF59E0B),
    "v. aux.": ("Auxiliary Verb", "⚡", 0xF59E0B),
    "aux. v.": ("Auxiliary Verb", "⚡", 0xF59E0B),
    "v.refl.": ("Reflexive Verb", "⚡", 0xF59E0B),
    "v. refl.": ("Reflexive Verb", "⚡", 0xF59E0B),
    "refl. v.": ("Reflexive Verb", "⚡", 0xF59E0B),
    "v.impers.": ("Impersonal Verb", "⚡", 0xF59E0B),
    "v. impers.": ("Impersonal Verb", "⚡", 0xF59E0B),
    "past": ("Past Tense", "⚡", 0xF59E0B),
    "past.": ("Past Tense", "⚡", 0xF59E0B),
    "past part.": ("Past Participle", "⚡", 0xF59E0B),
    "pres. part.": ("Present Participle", "⚡", 0xF59E0B),
    "past & past part.": ("Past Tense & Past Participle", "⚡", 0xF59E0B),
    "3rd sing. pres.": ("3rd Person Singular Present", "⚡", 0xF59E0B),
    # Adjectives
    "adj.": ("Adjective", "🎨", 0x10B981),
    "predic. adj.": ("Predicative Adjective (after a verb)", "🎨", 0x10B981),
    "attrib. adj.": ("Attributive Adjective (before a noun)", "🎨", 0x10B981),
    "poss. adj.": ("Possessive Adjective", "🎨", 0x10B981),
    "dem. adj.": ("Demonstrative Adjective", "🎨", 0x10B981),
    "interrog. adj.": ("Interrogative Adjective", "🎨", 0x10B981),
    "rel. adj.": ("Relative Adjective", "🎨", 0x10B981),
    "indef. adj.": ("Indefinite Adjective", "🎨", 0x10B981),
    "compar. adj.": ("Comparative Adjective", "🎨", 0x10B981),
    "superl. adj.": ("Superlative Adjective", "🎨", 0x10B981),
    # Adverbs
    "adv.": ("Adverb", "⏩", 0x8B5CF6),
    "interrog. adv.": ("Interrogative Adverb", "⏩", 0x8B5CF6),
    "rel. adv.": ("Relative Adverb", "⏩", 0x8B5CF6),
    "sentence adv.": ("Sentence Adverb", "⏩", 0x8B5CF6),
    # Prepositions, Conjunctions, Pronouns, Determiners, Articles
    "prep.": ("Preposition", "🧭", 0x06B6D4),
    "conj.": ("Conjunction", "🔗", 0x06B6D4),
    "pron.": ("Pronoun", "👤", 0xEC4899),
    "pers. pron.": ("Personal Pronoun", "👤", 0xEC4899),
    "poss. pron.": ("Possessive Pronoun", "👤", 0xEC4899),
    "refl. pron.": ("Reflexive Pronoun", "👤", 0xEC4899),
    "rel. pron.": ("Relative Pronoun", "👤", 0xEC4899),
    "interrog. pron.": ("Interrogative Pronoun", "👤", 0xEC4899),
    "dem. pron.": ("Demonstrative Pronoun", "👤", 0xEC4899),
    "indef. pron.": ("Indefinite Pronoun", "👤", 0xEC4899),
    "det.": ("Determiner", "📌", 0x06B6D4),
    "art.": ("Article", "📌", 0x06B6D4),
    "def. art.": ("Definite Article", "📌", 0x06B6D4),
    "indef. art.": ("Indefinite Article", "📌", 0x06B6D4),
    # Interjections / Exclamations
    "int.": ("Interjection / Exclamation", "💬", 0xEF4444),
    "interj.": ("Interjection / Exclamation", "💬", 0xEF4444),
    "excl.": ("Exclamation", "💬", 0xEF4444),
    # Word-building & Symbols
    "abbr.": ("Abbreviation", "🔤", 0xEAB308),
    "contr.": ("Contraction", "🔤", 0xEAB308),
    "symb.": ("Symbol", "🔣", 0xEAB308),
    "prefix": ("Prefix", "🧩", 0xEAB308),
    "suffix": ("Suffix", "🧩", 0xEAB308),
    "comb. form": ("Combining Form", "🧩", 0xEAB308),
    "comb.form": ("Combining Form", "🧩", 0xEAB308),
    "compar.": ("Comparative", "📈", 0x10B981),
    "superl.": ("Superlative", "📈", 0x10B981),
}

# Individual modifier/token fallback map for composite POS tags
POS_WORD_FALLBACK: dict[str, str] = {
    "n.": "Noun",
    "v.": "Verb",
    "adj.": "Adjective",
    "adv.": "Adverb",
    "prep.": "Preposition",
    "conj.": "Conjunction",
    "pron.": "Pronoun",
    "int.": "Interjection",
    "interj.": "Interjection",
    "abbr.": "Abbreviation",
    "prefix": "Prefix",
    "suffix": "Suffix",
    "symb.": "Symbol",
    "contr.": "Contraction",
    "det.": "Determiner",
    "art.": "Article",
    "predic.": "Predicative",
    "attrib.": "Attributive",
    "intr.": "Intransitive",
    "tr.": "Transitive",
    "aux.": "Auxiliary",
    "refl.": "Reflexive",
    "impers.": "Impersonal",
    "poss.": "Possessive",
    "rel.": "Relative",
    "interrog.": "Interrogative",
    "dem.": "Demonstrative",
    "indef.": "Indefinite",
    "pers.": "Personal",
    "pl.": "Plural",
    "sing.": "Singular",
    "past": "Past Tense",
    "part.": "Participle",
    "pres.": "Present",
    "compar.": "Comparative",
    "superl.": "Superlative",
}

# Regex pattern matching all valid POS headers in Oxford dictionary strings
_ATOMIC_POS_PATTERN = (
    r"(?:"
    r"past\s*&\s*past\s+part\.|"
    r"3rd\s+sing\.\s+pres\.|"
    r"(?:predic\.|attrib\.|poss\.|dem\.|interrog\.|rel\.|indef\.|pers\.|refl\.|compar\.|superl\.|def\.|indef\.|pl\.|sing\.|prop\.|sentence)\s+"
    r"(?:adj\.|adv\.|pron\.|art\.|n\.)|"
    r"n\.\s*pl\.|n\.\s*sing\.|"
    r"v\.\s*(?:intr\.|tr\.|aux\.|refl\.|impers\.)|"
    r"(?:intr\.|tr\.|aux\.|refl\.|impers\.)\s*v\.|"
    r"comb\.\s*form|"
    r"past\s+part\.|pres\s+part\.|"
    r"n\.|v\.|adj\.|adv\.|prep\.|conj\.|pron\.|int\.|interj\.|abbr\.|symb\.|contr\.|det\.|art\.|prefix|suffix|past|compar\.|superl\."
    r")"
)

# Matches single or compound POS (e.g. "n.", "n. & v.", "adj., n., & adv.", "predic. Adj.")
POS_FULL_REGEX = rf"{_ATOMIC_POS_PATTERN}(?:\s*(?:,|&|or)\s*{_ATOMIC_POS_PATTERN})*"


# ---------------------------------------------------------------------------
# 2. Inline Grammar, Usage, Register, & Etymology Abbreviation Expansions
# ---------------------------------------------------------------------------

INLINE_ABBR_EXPANSIONS: list[tuple[re.Pattern, str]] = [
    # Multi-word grammatical notes first
    (re.compile(r"\busu\.\s+foll\.\s+by\b", re.IGNORECASE), "usually followed by"),
    (re.compile(r"\busu\.\s+fol\.\s+by\b", re.IGNORECASE), "usually followed by"),
    (re.compile(r"\bfoll\.\s+by\b", re.IGNORECASE), "followed by"),
    (re.compile(r"\bfol\.\s+by\b", re.IGNORECASE), "followed by"),
    (re.compile(r"\bprec\.\s+by\b", re.IGNORECASE), "preceded by"),
    (re.compile(r"\boften\s+attrib\.", re.IGNORECASE), "often used before a noun"),
    (re.compile(r"\busu\.\s+attrib\.", re.IGNORECASE), "usually used before a noun"),
    (re.compile(r"\boften\s+predic\.", re.IGNORECASE), "often used after a verb"),
    (re.compile(r"\busu\.\s+predic\.", re.IGNORECASE), "usually used after a verb"),
    (re.compile(r"\bpast\s+&\s+past\s+part\.", re.IGNORECASE), "past & past participle:"),
    (re.compile(r"\bpast\s+part\.", re.IGNORECASE), "past participle:"),
    (re.compile(r"\bpres\.\s+part\.", re.IGNORECASE), "present participle:"),
    (re.compile(r"\b3rd\s+sing\.\s+pres\.", re.IGNORECASE), "3rd person singular present:"),
    # Single-word grammatical / inflectional abbreviations
    (re.compile(r"\battrib\.", re.IGNORECASE), "used before a noun"),
    (re.compile(r"\bpredic\.", re.IGNORECASE), "used after a verb"),
    (re.compile(r"\babsol\.", re.IGNORECASE), "used without an object"),
    (re.compile(r"\brefl\.", re.IGNORECASE), "reflexive"),
    (re.compile(r"\bintr\.", re.IGNORECASE), "intransitive"),
    (re.compile(r"\btrans\.", re.IGNORECASE), "transitive"),
    (re.compile(r"\bimpers\.", re.IGNORECASE), "impersonal"),
    (re.compile(r"\bpl\.", re.IGNORECASE), "plural:"),
    (re.compile(r"\bsing\.", re.IGNORECASE), "singular:"),
    (re.compile(r"\bcompar\.", re.IGNORECASE), "comparative:"),
    (re.compile(r"\bsuperl\.", re.IGNORECASE), "superlative:"),
    (re.compile(r"\bobj\.", re.IGNORECASE), "objective:"),
    (re.compile(r"\bposs\.", re.IGNORECASE), "possessive:"),
    (re.compile(r"\busu\.", re.IGNORECASE), "usually"),
    (re.compile(r"\besp\.", re.IGNORECASE), "especially"),
    (re.compile(r"\borig\.", re.IGNORECASE), "originally"),
    (re.compile(r"\bprob\.", re.IGNORECASE), "probably"),
    # Register / tone / region labels
    (re.compile(r"\bcolloq\.", re.IGNORECASE), "informal"),
    (re.compile(r"\bsl\.", re.IGNORECASE), "slang"),
    (re.compile(r"\bderog\.", re.IGNORECASE), "derogatory"),
    (re.compile(r"\bjoc\.", re.IGNORECASE), "humorous"),
    (re.compile(r"\barch\.", re.IGNORECASE), "archaic"),
    (re.compile(r"\bhist\.", re.IGNORECASE), "historical"),
    (re.compile(r"\bpoet\.", re.IGNORECASE), "poetic"),
    (re.compile(r"\bdial\.", re.IGNORECASE), "dialect"),
    (re.compile(r"\beuphem\.", re.IGNORECASE), "euphemistic"),
    (re.compile(r"\brhet\.", re.IGNORECASE), "rhetorical"),
    (re.compile(r"\bfig\.", re.IGNORECASE), "figurative"),
    (re.compile(r"\blit\.", re.IGNORECASE), "literal"),
    (re.compile(r"\bbrit\.", re.IGNORECASE), "British"),
    (re.compile(r"\baustral\.", re.IGNORECASE), "Australian"),
    (re.compile(r"\bscot\.", re.IGNORECASE), "Scottish"),
    (re.compile(r"\bn\.\s*amer\.", re.IGNORECASE), "North American"),
    # Domain labels
    (re.compile(r"\bnaut\.", re.IGNORECASE), "Nautical"),
    (re.compile(r"\bmil\.", re.IGNORECASE), "Military"),
    (re.compile(r"\bmed\.", re.IGNORECASE), "Medicine"),
    (re.compile(r"\bmus\.", re.IGNORECASE), "Music"),
    (re.compile(r"\bcomput\.", re.IGNORECASE), "Computing"),
    (re.compile(r"\bgram\.", re.IGNORECASE), "Grammar"),
    (re.compile(r"\bbiol\.", re.IGNORECASE), "Biology"),
    (re.compile(r"\bchem\.", re.IGNORECASE), "Chemistry"),
    (re.compile(r"\bphys\.", re.IGNORECASE), "Physics"),
    (re.compile(r"\bmath\.", re.IGNORECASE), "Mathematics"),
    (re.compile(r"\bpsychol\.", re.IGNORECASE), "Psychology"),
    (re.compile(r"\bphilos\.", re.IGNORECASE), "Philosophy"),
    (re.compile(r"\btheol\.", re.IGNORECASE), "Theology"),
    (re.compile(r"\beccl\.", re.IGNORECASE), "Ecclesiastical"),
    (re.compile(r"\barchit\.", re.IGNORECASE), "Architecture"),
    (re.compile(r"\bherald\.", re.IGNORECASE), "Heraldry"),
    (re.compile(r"\bastron\.", re.IGNORECASE), "Astronomy"),
    (re.compile(r"\bgeol\.", re.IGNORECASE), "Geology"),
    (re.compile(r"\bbot\.", re.IGNORECASE), "Botany"),
    (re.compile(r"\bzool\.", re.IGNORECASE), "Zoology"),
    (re.compile(r"\banat\.", re.IGNORECASE), "Anatomy"),
]

# Etymology-specific abbreviation expansions
ETYMOLOGY_EXPANSIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bOE\b"), "Old English"),
    (re.compile(r"\bME\b"), "Middle English"),
    (re.compile(r"\bOF\b"), "Old French"),
    (re.compile(r"\bON\b"), "Old Norse"),
    (re.compile(r"\bOHG\b"), "Old High German"),
    (re.compile(r"\bMHG\b"), "Middle High German"),
    (re.compile(r"\bMDu\.\b|\bMDu\b"), "Middle Dutch"),
    (re.compile(r"\bDu\.\b"), "Dutch"),
    (re.compile(r"\bGmc\b|\bGmc\."), "Germanic"),
    (re.compile(r"\bGk\b|\bGk\."), "Greek"),
    (re.compile(r"\bL\b|\blat\.", re.IGNORECASE), "Latin"),
    (re.compile(r"\bmed\.\s*L\b|\bmed\.\s*latin\b", re.IGNORECASE), "Medieval Latin"),
    (re.compile(r"\blate\s+L\b|\blate\s+latin\b", re.IGNORECASE), "Late Latin"),
    (re.compile(r"\bult\.", re.IGNORECASE), "ultimately"),
    (re.compile(r"\bprob\.", re.IGNORECASE), "probably"),
    (re.compile(r"\borig\.", re.IGNORECASE), "originally"),
    (re.compile(r"\brel\.\s+to\b", re.IGNORECASE), "related to"),
    (re.compile(r"\bassim\.", re.IGNORECASE), "assimilated"),
    (re.compile(r"\bdimin\.", re.IGNORECASE), "diminutive"),
    (re.compile(r"\bimit\.", re.IGNORECASE), "imitative"),
    (re.compile(r"\bvar\.", re.IGNORECASE), "variant"),
    (re.compile(r"\bcf\.", re.IGNORECASE), "compare"),
    (re.compile(r"\bfr\.", re.IGNORECASE), "from"),
]

SUPERSCRIPT_DIGITS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


@dataclass
class SenseItem:
    """Represents a single numbered sense (and optional lettered sub-senses)."""

    number: str | None = None
    main_text: str = ""
    subsenses: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class POSBlock:
    """Represents one Part-of-Speech section within an entry."""

    raw_pos: str
    expanded_pos: str
    icon: str
    color: int
    inflection_note: str | None = None
    senses: list[SenseItem] = field(default_factory=list)
    derivatives: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class ParsedDictionaryEntry:
    """Complete structured representation of a dictionary entry."""

    headword: str
    homograph_num: str | None = None
    intro_note: str | None = None
    pos_blocks: list[POSBlock] = field(default_factory=list)
    etymology: str | None = None


def expand_pos_tag(raw_pos: str) -> tuple[str, str, int]:
    """
    Expands any abbreviated POS string (e.g., 'n.', 'v.intr.', 'predic. Adj.',
    'n. & v.', 'adj., n., & adv.') into (Full English Label, Emoji Icon, Color).
    """
    cleaned = re.sub(r"\s+", " ", raw_pos.strip()).lower()
    if cleaned in POS_CANONICAL_MAP:
        return POS_CANONICAL_MAP[cleaned]

    # Handle composite POS tags connected by '&', 'or', or ','
    parts = [p.strip() for p in re.split(r"\s*(?:,|&|\bor\b)\s*", cleaned) if p.strip()]
    if len(parts) > 1:
        expanded_parts: list[str] = []
        primary_icon = "📘"
        primary_color = 0x5865F2
        for idx, part in enumerate(parts):
            label, icon, color = expand_pos_tag(part)
            short_label = re.sub(r"\s*\([^)]*\)", "", label)
            expanded_parts.append(short_label)
            if idx == 0:
                primary_icon = icon
                primary_color = color
        connector = " or " if " or " in cleaned else " & "
        if len(expanded_parts) > 2:
            combined = ", ".join(expanded_parts[:-1]) + f", {connector.strip()} " + expanded_parts[-1]
        else:
            combined = connector.join(expanded_parts)
        return combined, primary_icon, primary_color

    # Token-by-token fallback expansion
    tokens = cleaned.split(" ")
    expanded_tokens = [POS_WORD_FALLBACK.get(t, t.capitalize()) for t in tokens]
    label = " ".join(expanded_tokens)
    for key, (_, icon, color) in POS_CANONICAL_MAP.items():
        if key in cleaned:
            return label, icon, color
    return label, "📘", 0x5865F2


def expand_inline_abbreviations(text: str) -> str:
    """
    Expands grammatical, inflectional, and usage abbreviations inside text
    and formats *cross-references cleanly.
    """
    if not text:
        return ""

    result = text
    for pattern, replacement in INLINE_ABBR_EXPANSIONS:
        result = pattern.sub(replacement, result)

    # Fix false sentence-capitalizations that followed periods in the raw dataset
    # e.g., "(usu. In passive)" -> "(usually in passive)"
    result = re.sub(
        r"\b(usually|especially|originally|probably|followed by|preceded by|plural:|singular:|past:|past participle:|present participle:|objective:|possessive:)\s+([A-Z][a-z]+\b)",
        lambda m: f"{m.group(1)} {m.group(2).lower()}",
        result,
    )

    # Format *cross-reference words (e.g. *abide -> `🔗 abide`)
    result = re.sub(
        r"\*([A-Za-z0-9\-']+(?:\d+)?)",
        lambda m: f"`🔗 {m.group(1).rstrip('0123456789')}`",
        result,
    )

    # Italicize parenthetical usage/grammar notes cleanly
    def _style_parens(match: re.Match) -> str:
        inner = match.group(1).strip()
        return f"*({inner})*"

    result = re.sub(r"\(([^()]+)\)", _style_parens, result)

    # Clean up excess whitespace
    return re.sub(r"\s{2,}", " ", result).strip()


def _is_inflection_or_pos_grammar_note(raw_paren_inner: str) -> bool:
    """
    Determines whether a leading `(note)` right after the POS tag is a
    word-form/inflection/grammar header (e.g., `(-ting)`, `(pl. -ies)`,
    `(usu. in passive)`) rather than a sense-specific context note like `(of a door etc.)`.
    """
    lower = raw_paren_inner.strip().lower()
    if lower.startswith("of "):
        return False
    if "-" in lower:  # e.g. (-rr-), (-ting), (pl. -ies)
        return True
    grammar_markers = (
        "pl.",
        "sing.",
        "past",
        "pres.",
        "part.",
        "compar.",
        "superl.",
        "obj.",
        "poss.",
        "3rd",
        "usu.",
        "often",
        "also",
        "refl.",
        "intr.",
        "tr.",
        "attrib.",
        "predic.",
        "passive",
        "infin.",
        "imper.",
    )
    return any(m in lower for m in grammar_markers)


def format_inflection_note(raw_note: str) -> str:
    """Expands parenthetical inflection/grammar notes right after the POS tag."""
    inner = raw_note.strip()
    if inner.startswith("(") and inner.endswith(")"):
        inner = inner[1:-1].strip()
    expanded = expand_inline_abbreviations(inner).replace("*", "")
    grammar_keywords = (
        "plural",
        "singular",
        "past",
        "present",
        "comparative",
        "superlative",
        "objective",
        "possessive",
        "usually",
        "often",
        "also",
        "used",
        "reflexive",
    )
    if not any(lbl in expanded.lower() for lbl in grammar_keywords):
        return f"Forms: {expanded}"
    return expanded[0].upper() + expanded[1:] if expanded else expanded


def format_etymology(raw_etym: str) -> str:
    """Cleans and expands abbreviations inside the [etymology] block."""
    text = raw_etym.strip()
    for pattern, replacement in ETYMOLOGY_EXPANSIONS:
        text = pattern.sub(replacement, text)

    # Format *cross-references inside etymology (e.g., *horror -> 'horror')
    text = re.sub(
        r"\*([A-Za-z0-9\-']+)",
        lambda m: f"'{m.group(1).rstrip('0123456789')}'",
        text,
    )

    # Capitalize language names and the first character
    for lang in (
        "english",
        "french",
        "latin",
        "greek",
        "german",
        "germanic",
        "dutch",
        "italian",
        "spanish",
        "arabic",
        "sanskrit",
        "celtic",
        "scandinavian",
        "norse",
    ):
        text = re.sub(rf"\b{lang}\b", lang.capitalize(), text, flags=re.IGNORECASE)

    if text:
        text = text[0].upper() + text[1:]
    return text


def _extract_trailing_derivatives(body: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Detects and extracts trailing derivative word forms at the end of a POS block,
    e.g., '... some definition. Abandonment n. Abashedly adv.'
    """
    derivatives: list[tuple[str, str]] = []
    deriv_pattern = re.compile(rf"(?:^|(?<=[\.\?!])\s+)([A-Z][a-zA-Z\-']+(?:\s*\([^)]+\))?)\s+({_ATOMIC_POS_PATTERN})\s*$")
    remaining = body.strip()
    while True:
        match = deriv_pattern.search(remaining)
        if not match:
            break
        word_part = match.group(1).strip()
        pos_part = match.group(2).strip()
        if len(word_part.split()) > 2:
            break
        full_pos, _, _ = expand_pos_tag(pos_part)
        short_pos = re.sub(r"\s*\([^)]*\)", "", full_pos)
        derivatives.insert(0, (word_part, short_pos))
        remaining = remaining[: match.start()].strip()

    return remaining, derivatives


def _parse_senses(body: str) -> list[SenseItem]:
    """
    Splits a POS block body into numbered senses (1, 2, 3...) and lettered
    sub-senses (a, B, C... — noting uppercase B/C after periods in the dataset).
    """
    text = body.strip()
    if not text:
        return []

    num_matches = list(re.finditer(r"(?:^|(?<=\s))(\d{1,2})\s+(?=[a-zA-Z\(])", text))

    valid_matches: list[re.Match] = []
    expected_num = 1
    for m in num_matches:
        num_val = int(m.group(1))
        if num_val == expected_num or (expected_num == 1 and num_val in (1, 2)):
            valid_matches.append(m)
            expected_num = num_val + 1

    raw_senses: list[tuple[str | None, str]] = []
    if not valid_matches:
        raw_senses.append((None, text))
    else:
        prefix = text[: valid_matches[0].start()].strip()
        for idx, m in enumerate(valid_matches):
            sense_num = m.group(1)
            start_pos = m.end()
            end_pos = valid_matches[idx + 1].start() if idx + 1 < len(valid_matches) else len(text)
            chunk = text[start_pos:end_pos].strip()
            if idx == 0 and prefix:
                chunk = f"{prefix} {chunk}"
            raw_senses.append((sense_num, chunk))

    parsed_senses: list[SenseItem] = []
    for sense_num, chunk in raw_senses:
        sub_matches = list(re.finditer(r"(?:^|\s+)([a-zA-Z])\s+(?=[A-Z\(a-z])", chunk))
        valid_subs: list[re.Match] = []
        expected_ord = ord("a")
        for sm in sub_matches:
            letter = sm.group(1).lower()
            if ord(letter) == expected_ord:
                valid_subs.append(sm)
                expected_ord += 1

        if len(valid_subs) >= 2:
            lead_in = chunk[: valid_subs[0].start()].strip()
            subs: list[tuple[str, str]] = []
            for s_idx, sm in enumerate(valid_subs):
                sub_letter = sm.group(1).lower()
                s_start = sm.end()
                s_end = valid_subs[s_idx + 1].start() if s_idx + 1 < len(valid_subs) else len(chunk)
                sub_text = expand_inline_abbreviations(chunk[s_start:s_end].strip())
                subs.append((sub_letter, sub_text))
            parsed_senses.append(
                SenseItem(
                    number=sense_num,
                    main_text=expand_inline_abbreviations(lead_in),
                    subsenses=subs,
                )
            )
        else:
            parsed_senses.append(
                SenseItem(
                    number=sense_num,
                    main_text=expand_inline_abbreviations(chunk),
                )
            )

    return parsed_senses


def parse_dictionary_entry(raw_key: str, raw_value: str) -> ParsedDictionaryEntry:
    """
    Parses a raw (key, value) pair from `dictionary.json` into a structured
    `ParsedDictionaryEntry` with all POS tags and abbreviations expanded.
    """
    # 1. Extract headword & optional homograph trailing number (e.g. "Bank1" -> "Bank", "1")
    key_match = re.match(r"^([A-Za-z\-\s']+?)(\d+)?$", raw_key.strip())
    if key_match:
        headword = key_match.group(1).strip()
        homograph_num = key_match.group(2)
    else:
        headword = raw_key.strip()
        homograph_num = None

    working = raw_value.strip()

    # 2. Extract trailing etymology in square brackets [...]
    # Handles both normal "[latin: ...]" and truncated "[latin: ..." missing closing "]"
    etymology: str | None = None
    etym_match = re.search(r"\[([^\]]+?)(?:\]\.?|\.?)$", working)
    if etym_match:
        etymology = format_etymology(etym_match.group(1))
        working = working[: etym_match.start()].strip()

    # 3. Check for split compound headword before the first double-space "  "
    # e.g., Key: "Acid", Value: "test  n. Severe or conclusive test." -> Headword: "Acid test"
    compound_match = re.match(
        rf"^([a-zA-Z0-9\-'/,\s]+?)\s{{2,}}(?={POS_FULL_REGEX}(?:\s|\(|$))",
        working,
        flags=re.IGNORECASE,
    )
    if compound_match:
        prefix_part = compound_match.group(1).strip()
        if not re.fullmatch(POS_FULL_REGEX, prefix_part, flags=re.IGNORECASE):
            headword = f"{headword} {prefix_part}"
            working = working[compound_match.end() :].strip()

    # 4. Split into Part-of-Speech (POS) sections
    pos_boundary_regex = re.compile(
        rf"(?:^|(?:--+|—|\s{{2,}}))\s*({POS_FULL_REGEX})(?=\s+|\(|$)",
        flags=re.IGNORECASE,
    )
    pos_matches = list(pos_boundary_regex.finditer(working))

    intro_note: str | None = None
    pos_blocks: list[POSBlock] = []

    if not pos_matches:
        expanded_body = expand_inline_abbreviations(working)
        pos_blocks.append(
            POSBlock(
                raw_pos="",
                expanded_pos="Definition",
                icon="📖",
                color=0x5865F2,
                senses=[SenseItem(number=None, main_text=expanded_body)],
            )
        )
    else:
        if pos_matches[0].start() > 0:
            raw_intro = working[: pos_matches[0].start()].strip(" -—")
            if raw_intro:
                intro_note = expand_inline_abbreviations(raw_intro)

        for idx, pm in enumerate(pos_matches):
            raw_pos_str = pm.group(1).strip()
            expanded_pos, icon, color = expand_pos_tag(raw_pos_str)

            block_start = pm.end()
            block_end = pos_matches[idx + 1].start() if idx + 1 < len(pos_matches) else len(working)
            block_body = working[block_start:block_end].strip(" -—")

            # Extract optional inflection/form notes in parentheses right after the POS
            inflection_note: str | None = None
            infl_match = re.match(r"^\(([^)]+)\)\s*", block_body)
            if infl_match and _is_inflection_or_pos_grammar_note(infl_match.group(1)):
                candidate = infl_match.group(1).strip()
                block_body = block_body[infl_match.end() :].strip()
                inflection_note = format_inflection_note(candidate)

            # Extract trailing derivatives (e.g. "Abandonment n.")
            block_body, derivatives = _extract_trailing_derivatives(block_body)

            # Parse senses (1, 2, 3...) and sub-senses (a, b, c...)
            senses = _parse_senses(block_body)

            pos_blocks.append(
                POSBlock(
                    raw_pos=raw_pos_str,
                    expanded_pos=expanded_pos,
                    icon=icon,
                    color=color,
                    inflection_note=inflection_note,
                    senses=senses,
                    derivatives=derivatives,
                )
            )

    return ParsedDictionaryEntry(
        headword=headword,
        homograph_num=homograph_num,
        intro_note=intro_note,
        pos_blocks=pos_blocks,
        etymology=etymology,
    )


def _chunk_lines_for_embed_field(lines: list[str], max_len: int = 1024) -> list[str]:
    """
    Splits formatted sense lines into chunks guaranteed to be <= 1024 characters
    so `embed.add_field` never raises a Discord HTTPException.
    """
    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in lines:
        if len(line) > max_len:
            line = line[: max_len - 3] + "..."

        added_len = len(line) + (1 if current_lines else 0)
        if current_len + added_len > max_len and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = [line]
            current_len = len(line)
        else:
            current_lines.append(line)
            current_len += added_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks or ["—"]


def build_definition_embed(raw_key: str, raw_value: str) -> discord.Embed:
    """
    Converts a `(key, value)` pair from `dictionary.json` into a richly formatted
    `discord.Embed` with full part-of-speech labels, structured numbered senses,
    sub-senses, derived words, and word origin.
    """
    entry = parse_dictionary_entry(raw_key, raw_value)

    # 1. Title & Color
    superscript = entry.homograph_num.translate(SUPERSCRIPT_DIGITS) if entry.homograph_num else ""
    title_suffix = f" {superscript}" if superscript else ""
    title = f"📖 {entry.headword.capitalize()}{title_suffix}"

    primary_color = entry.pos_blocks[0].color if entry.pos_blocks else 0x5865F2

    # 2. Concise Overview Bar in `embed.description`
    pos_pills: list[str] = []
    for block in entry.pos_blocks:
        short_pos = re.sub(r"\s*\([^)]*\)", "", block.expanded_pos)
        pill = f"`{block.icon} {short_pos}`"
        if pill not in pos_pills:
            pos_pills.append(pill)

    desc_parts: list[str] = []
    if pos_pills:
        desc_parts.append("**Part of Speech:** " + "  •  ".join(pos_pills))
    if entry.intro_note:
        desc_parts.append(f"*{entry.intro_note}*")

    embed = discord.Embed(
        title=title,
        description="\n".join(desc_parts) if desc_parts else None,
        color=primary_color,
    )

    # 3. Add a Structured Field for Each Part of Speech
    all_derivatives: list[tuple[str, str]] = []

    for block in entry.pos_blocks:
        all_derivatives.extend(block.derivatives)

        field_lines: list[str] = []
        if block.inflection_note:
            field_lines.append(f"📝 *{block.inflection_note}*")

        for sense in block.senses:
            if sense.subsenses:
                header_prefix = f"**{sense.number}.**" if sense.number else "•"
                if sense.main_text:
                    field_lines.append(f"{header_prefix} {sense.main_text}")
                else:
                    field_lines.append(f"{header_prefix}")
                for sub_letter, sub_text in sense.subsenses:
                    field_lines.append(f"> **{sub_letter})** {sub_text}")
            elif sense.number:
                field_lines.append(f"**{sense.number}.** {sense.main_text}")
            elif sense.main_text:
                field_lines.append(f"• {sense.main_text}")

        chunks = _chunk_lines_for_embed_field(field_lines, max_len=1024)
        base_field_name = f"{block.icon} {block.expanded_pos}"

        for idx, chunk in enumerate(chunks):
            if len(embed.fields) >= 24:  # Leave 1 slot for derivatives if needed
                break
            field_name = base_field_name if idx == 0 else f"{block.icon} {block.expanded_pos} (Part {idx + 1})"
            embed.add_field(name=field_name[:256], value=chunk, inline=False)

    # 4. Derived Words & Phrases Field (if present)
    if all_derivatives and len(embed.fields) < 25:
        deriv_items = [f"**{word}** *({pos})*" for word, pos in all_derivatives]
        deriv_value = "  •  ".join(deriv_items)
        if len(deriv_value) > 1024:
            deriv_value = deriv_value[:1021] + "..."
        embed.add_field(
            name="🌿 Derived Words & Related Forms",
            value=deriv_value,
            inline=False,
        )

    # 5. Etymology Footer
    if entry.etymology:
        footer_text = f"🏛️ Word Origin: {entry.etymology}"
        embed.set_footer(text=footer_text[:2048])

    return embed
