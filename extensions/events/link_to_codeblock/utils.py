from __future__ import annotations

import html
import os
import re
from datetime import datetime

DISCORD_MESSAGE_LIMIT = 2000
CODE_PAGE_CHAR_LIMIT = 1750
CODE_PAGE_LINE_LIMIT = 35
ISSUE_PAGE_CHAR_LIMIT = 1800

GITHUB_RE = re.compile(
    r"https://github\.com/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/blob/"
    r"(?P<path>[^#>]+)(\?[^#>]+)?(#L(?P<start_line>\d+)(([-~:]|(\.\.))L(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

GITHUB_GIST_RE = re.compile(
    r"https://gist\.github\.com/([a-zA-Z0-9-]+)/(?P<gist_id>[a-zA-Z0-9]+)/*"
    r"(?P<revision>[a-zA-Z0-9]*)/*#file-(?P<file_path>[^#>]+?)(\?[^#>]+)?"
    r"(-L(?P<start_line>\d+)([-~:]L(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

GITLAB_RE = re.compile(
    r"https://gitlab\.com/(?P<repo>[\w.-]+/[\w.-]+)/\-/blob/(?P<path>[^#>]+)"
    r"(\?[^#>]+)?(#L(?P<start_line>\d+)(-(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

BITBUCKET_RE = re.compile(
    r"https://bitbucket\.org/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/src/(?P<ref>[0-9a-zA-Z]+)"
    r"/(?P<file_path>[^#>]+)(\?[^#>]+)?(#lines-(?P<start_line>\d+)(:(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

API = "https://api.github.com"
MAX_EMBEDS = 3
CACHE_TTL = 120.0
CACHE_SIZE = 256
SUPPRESS_ORIGINAL = True
VIEW_TIMEOUT = 900.0  # 15 minutes

GREEN, RED, PURPLE, GRAY, BLUE = 0x2DA44E, 0xCF222E, 0x8250DF, 0x6E7781, 0x1F6FEB
ORANGE, YELLOW, DARK_RED = 0xD97706, 0xCA8A04, 0x991B1B

_REPO = r"(?P<repo>[\w.-]+/[\w.-]+)"
ISSUE_RE = re.compile(
    rf"(?<!<)https://github\.com/{_REPO}/(?P<kind>issues|pull)/(?P<number>\d+)\b",
    re.IGNORECASE,
)
COMMIT_RE = re.compile(
    rf"(?<!<)https://github\.com/{_REPO}/commit/(?P<sha>[0-9a-f]{{7,40}})\b",
    re.IGNORECASE,
)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
SHODAN_CVEDB_URL = "https://cvedb.shodan.io"
MITRE_CVE_API_URL = "https://cveawg.mitre.org/api/cve"
CIRCL_CVE_API_URL = "https://cve.circl.lu/api"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

SECURITY_NEWS_FEEDS: dict[str, tuple[str, str]] = {
    "thehackernews": (
        "The Hacker News",
        "https://feeds.feedburner.com/TheHackersNews",
    ),
    "bleepingcomputer": (
        "BleepingComputer",
        "https://www.bleepingcomputer.com/feed/",
    ),
}

CVE_ID_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

Target = tuple[str, str, str]


def _get_github_raw_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3.raw"}
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    cleaned = _HTML_TAG_RE.sub("", html.unescape(raw))
    return re.sub(r"\s+", " ", cleaned).strip()


def _get_nvd_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    api_key = os.environ.get("NVD_API_KEY")
    if api_key:
        headers["apiKey"] = api_key
    return headers


def _trim(text: str | None, limit: int = 350) -> str:
    """Strip issue-template comments, collapse blank lines and shorten to ``limit``."""
    text = _HTML_COMMENT_RE.sub("", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    if text.count("```") % 2:
        text += "\n```"
    return text


def _paginate_markdown(text: str | None, limit: int = ISSUE_PAGE_CHAR_LIMIT) -> list[str]:
    """Split long markdown text into clean pages while keeping code fences balanced."""
    cleaned = _HTML_COMMENT_RE.sub("", text or "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned:
        return ["*No description provided.*"]

    pages: list[str] = []
    current_lines: list[str] = []
    current_len = 0
    in_fence = False
    fence_header = "```"

    for line in cleaned.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                fence_header = stripped
            else:
                in_fence = False

        line_len = len(line) + 1
        if current_lines and current_len + line_len > limit:
            chunk = "\n".join(current_lines)
            if in_fence:
                chunk += "\n```"
            pages.append(chunk)
            current_lines = [fence_header, line] if in_fence else [line]
            current_len = sum(len(x) + 1 for x in current_lines)
        else:
            current_lines.append(line)
            current_len += line_len

    if current_lines:
        chunk = "\n".join(current_lines)
        if chunk.count("```") % 2:
            chunk += "\n```"
        pages.append(chunk)

    return pages or ["*No description provided.*"]


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _cvss_Appearance(score: float | None, *, is_kev: bool = False) -> tuple[str, str, int]:  # noqa: PLR0911
    """Return (severity_label, tag, hex_colour) for a CVSS score and KEV status."""
    if is_kev and (score is None or score >= 7.0):
        return "CRITICAL (KEV)", "[KEV]", DARK_RED
    if score is None:
        return "UNKNOWN", "[?]", GRAY
    if score >= 9.0:
        return "CRITICAL", "[CRIT]", RED
    if score >= 7.0:
        return "HIGH", "[HIGH]", ORANGE
    if score >= 4.0:
        return "MEDIUM", "[MED]", YELLOW
    if score > 0.0:
        return "LOW", "[LOW]", GREEN
    return "NONE", "[NONE]", GRAY
