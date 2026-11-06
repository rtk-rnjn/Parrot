from __future__ import annotations

import re

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=15)
MAX_RESPONSE = 8 * 1024 * 1024
MAX_PACKUMENT = 30 * 1024 * 1024  # the full npm document of a package can be huge

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Parrot/1.0; +https://discord.com)",
    "Accept": "application/json, text/plain, */*",
}

DOT = " \N{MIDDLE DOT} "
VERSIONS_PER_PAGE = 12
MAX_VERSIONS = 120
SEARCH_LIMIT = 8
DEPENDENCY_BUDGET = 3000  # characters of dependency names across the whole message (the message limit is 4000)
GROUP_BUDGET = 1100
MAX_GROUPS = 8

EXTRA_MARKER = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")
VERSION_PATTERN = re.compile(r"[0-9A-Za-z.+_~^!*-]{1,64}")
REPO_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "codeberg.org", "sr.ht")

GO_MOD_DIRECTIVE = re.compile(r"^go\s+(\S+)", re.MULTILINE)
GO_REQUIRE_BLOCK = re.compile(r"require\s*\((.*?)\)", re.DOTALL)
GO_REQUIRE_SINGLE = re.compile(r"^require\s+([^\s(]\S*)\s+(\S+)(.*)$", re.MULTILINE)
