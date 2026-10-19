from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Annotated, Any, Literal
from urllib.parse import quote

import aiohttp
import arrow
import discord
from discord.ext import commands

from core.utils import BaseLayoutView, NoticeLayout, truncate

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from core import Bot

GITHUB_API_URL = "https://api.github.com"
GITHUB_URL = "https://github.com"
API_VERSION = "2022-11-28"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

DOT = " \N{MIDDLE DOT} "
MINUS = "\N{MINUS SIGN}"

# A components v2 message may hold at most 4000 characters of text in total, so every block is budgeted.
BODY_LIMIT = 1400
RELEASE_BODY_LIMIT = 1900
COMMITS_PER_PAGE = 8
MAX_RELEASES = 10
MAX_GIST_FILES = 10
CONTRIBUTORS_SHOWN = 15

GITHUB_COLOUR = discord.Colour.og_blurple()
OPEN_COLOUR = discord.Colour(0x238636)
MERGED_COLOUR = discord.Colour(0x8957E5)
CLOSED_COLOUR = discord.Colour(0xDA3633)
DRAFT_COLOUR = discord.Colour(0x6E7681)

USERNAME_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
REPO_PATTERN = re.compile(
    r"(?:https?://(?:www\.)?github\.com/)?"
    r"(?P<owner>[A-Za-z0-9][A-Za-z0-9-]{0,38})/"
    r"(?P<name>[A-Za-z0-9._-]{1,100}?)"
    r"(?:\.git)?(?:[/?#].*)?"
)
GIST_PATTERN = re.compile(r"[0-9A-Za-z]{1,64}")

HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HTML_TAG = re.compile(
    r"</?(?:details|summary|p|br|hr|img|div|span|picture|source|h[1-6]|sub|sup|center|table|thead|tbody|tr|td|th|kbd|ul|ol|li)\b[^>]*>",
    re.IGNORECASE,
)
MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
MARKDOWN_HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", re.MULTILINE)
BLANK_LINES = re.compile(r"\n{3,}")


class GitHubError(Exception):
    """A problem that should be shown to the user as-is."""


@dataclass(frozen=True, slots=True)
class RepoRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def path(self) -> str:
        return f"{quote(self.owner, safe='')}/{quote(self.name, safe='')}"

    @property
    def url(self) -> str:
        return f"{GITHUB_URL}/{self.full_name}"


def parse_repo(raw: str) -> RepoRef | None:
    """Accept ``owner/name`` or any github.com URL that starts with it."""
    match = REPO_PATTERN.fullmatch(raw.strip().strip("<>"))
    return RepoRef(match["owner"], match["name"]) if match else None


class RepoConverter(commands.Converter[RepoRef]):
    async def convert(self, ctx: commands.Context[Bot], argument: str) -> RepoRef:
        ref = parse_repo(argument)
        if ref is None:
            msg = "The repository should look like `owner/name` or be a link to one."
            raise commands.BadArgument(msg)
        return ref


class NumberConverter(commands.Converter[int]):
    async def convert(self, ctx: commands.Context[Bot], argument: str) -> int:
        cleaned = argument.strip().lstrip("#")
        if not cleaned.isdecimal() or not 0 < int(cleaned) < 10**9:
            msg = "Give a positive number, like `1234` or `#1234`."
            raise commands.BadArgument(msg)
        return int(cleaned)


class GistConverter(commands.Converter[str]):
    async def convert(self, ctx: commands.Context[Bot], argument: str) -> str:
        candidate = argument.strip().strip("<>").split("#", 1)[0].split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
        if not GIST_PATTERN.fullmatch(candidate):
            msg = "That does not look like a gist ID or a gist link."
            raise commands.BadArgument(msg)
        return candidate


def safe(text: str | None, limit: int = 200) -> str:
    """One escaped, mention-free line of user-provided text."""
    flat = " ".join((text or "").split())
    return truncate(discord.utils.escape_markdown(discord.utils.escape_mentions(flat)), limit)


def code(text: str, limit: int = 60) -> str:
    return f"`{truncate(text.replace('`', chr(39)), limit)}`"


def clean_markdown(text: str | None, limit: int) -> str:
    """Turn a GitHub-flavoured markdown body into something that renders well in Discord and fits ``limit``."""
    if not text:
        return ""
    text = HTML_COMMENT.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = MARKDOWN_IMAGE.sub(lambda match: f"[{match[1] or 'image'}]", text)
    text = HTML_TAG.sub("", text)
    text = MARKDOWN_HEADING.sub(r"**\1**", text)
    text = BLANK_LINES.sub("\n\n", text).strip()
    text = discord.utils.escape_mentions(text)
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"
    if text.count("```") % 2:
        text += "\n```"
    return text


def compact(number: int) -> str:
    for threshold, suffix in ((1_000_000, "M"), (1_000, "k")):
        if number >= threshold:
            return f"{number / threshold:.1f}".rstrip("0").rstrip(".") + suffix
    return str(number)


def file_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def when(iso: str | None, style: Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"] = "R") -> str | None:
    return discord.utils.format_dt(arrow.get(iso).datetime, style) if iso else None


def dated(iso: str | None) -> str | None:
    return f"{when(iso, 'D')} ({when(iso)})" if iso else None


def valid_url(url: str | None) -> bool:
    return bool(url) and url.startswith(("http://", "https://")) and len(url) <= 512


def user_link(user: dict[str, Any] | None) -> str:
    if not user:
        return "*ghost*"
    return f"[{user['login']}]({user['html_url']})"


def text(content: str) -> discord.ui.TextDisplay:
    return discord.ui.TextDisplay(content)


def facts(*pairs: tuple[str, str | None]) -> discord.ui.TextDisplay | None:
    lines = [f"**{label}**: {value}" for label, value in pairs if value]
    return text("\n".join(lines)) if lines else None


def header(title: str, subtitle: str | None = None, *extra: str, thumbnail: str | None = None) -> discord.ui.Item:
    """Title block, with an optional thumbnail on the right."""
    parts = [text(f"## {title}" + (f"\n-# {subtitle}" if subtitle else ""))]
    parts.extend(text(line) for line in extra if line)
    if thumbnail:
        return discord.ui.Section(*parts, accessory=discord.ui.Thumbnail(thumbnail))
    return _stack(parts)


def _stack(parts: list[discord.ui.TextDisplay]) -> discord.ui.TextDisplay:
    return text("\n".join(part.content for part in parts))


def collect(*items: discord.ui.Item | None) -> list[discord.ui.Item]:
    return [item for item in items if item is not None]


def commit_line(entry: dict[str, Any]) -> str:
    commit = entry["commit"]
    message = commit["message"].split("\n", 1)[0]
    author = entry.get("author")
    name = user_link(author) if author else safe(commit["author"]["name"], 30)
    stamp = when(commit["author"]["date"])
    return f"[`{entry['sha'][:7]}`]({entry['html_url']}) {safe(message, 80)}\n-# {name}{DOT}{stamp}"


@dataclass(slots=True)
class Page:
    """One screen of a :class:`GitHubView`. ``body`` is called on every render so items are always fresh."""

    body: Callable[[], list[discord.ui.Item]]
    url: str | None = None
    label: str = "Open on GitHub"
    colour: discord.Colour = GITHUB_COLOUR
    links: list[tuple[str, str]] = field(default_factory=list)


class GitHubView(BaseLayoutView):
    """A single container with the page content, optional Previous/Next buttons and link buttons."""

    def __init__(self, author: discord.User | discord.Member, pages: Sequence[Page], *, timeout: float = 180) -> None:
        super().__init__(author, timeout=timeout)
        self.pages = list(pages)
        self.index = 0
        self.container = discord.ui.Container(accent_colour=self.pages[0].colour)
        self.add_item(self.container)
        self.render()

    def render(self) -> None:
        page = self.pages[self.index]
        self.container.clear_items()
        self.container.accent_colour = page.colour
        for item in page.body():
            self.container.add_item(item)

        rows: list[discord.ui.ActionRow] = []
        if len(self.pages) > 1:
            rows.append(
                discord.ui.ActionRow(
                    self._nav_button("Previous", -1, "\N{BLACK LEFT-POINTING TRIANGLE}", disabled=self.index == 0),
                    discord.ui.Button(label=f"{self.index + 1} / {len(self.pages)}", disabled=True),
                    self._nav_button("Next", 1, "\N{BLACK RIGHT-POINTING TRIANGLE}", disabled=self.index >= len(self.pages) - 1),
                )
            )

        links = ([(page.label, page.url)] if page.url else []) + page.links
        buttons = [discord.ui.Button(label=label[:80], url=url) for label, url in links if valid_url(url)][:5]
        if buttons:
            rows.append(discord.ui.ActionRow(*buttons))

        if rows:
            self.container.add_item(discord.ui.Separator())
            for row in rows:
                self.container.add_item(row)

    def _nav_button(self, label: str, step: int, emoji: str, *, disabled: bool) -> discord.ui.Button:
        button = discord.ui.Button(label=label, emoji=emoji, disabled=disabled)

        async def callback(interaction: discord.Interaction) -> None:
            self.index = max(0, min(len(self.pages) - 1, self.index + step))
            self.render()
            await interaction.response.edit_message(view=self)

        button.callback = callback
        return button


def repository_items(data: dict[str, Any], languages: dict[str, int]) -> list[discord.ui.Item]:
    owner = data["owner"]
    badges = []
    if data.get("archived"):
        badges.append("\N{PACKAGE} Archived")
    if data.get("fork"):
        badges.append("\N{OCR FORK} Fork")
    if data.get("is_template"):
        badges.append("Template")
    if data.get("private"):
        badges.append("\N{LOCK} Private")

    description = safe(data.get("description"), 500) if data.get("description") else "*No description provided.*"
    if parent := data.get("parent"):
        description += f"\nForked from [{parent['full_name']}]({parent['html_url']})"

    title = f"[{data['full_name']}]({data['html_url']})"
    subtitle = DOT.join(["Repository", *badges])
    top = header(title, subtitle, description, thumbnail=owner["avatar_url"])

    watchers = data.get("subscribers_count", data.get("watchers_count", 0))
    stats = text(
        DOT.join(
            [
                f"\N{WHITE MEDIUM STAR} **{compact(data['stargazers_count'])}** stars",
                f"\N{OCR FORK} **{compact(data['forks_count'])}** forks",
                f"\N{EYES} **{compact(watchers)}** watching",
                f"\N{BUG} **{compact(data['open_issues_count'])}** open issues & PRs",
            ]
        )
    )

    license_info = data.get("license") or {}
    license_name = license_info.get("spdx_id") if license_info.get("spdx_id") not in {None, "NOASSERTION"} else license_info.get("name")

    breakdown = None
    total = sum(languages.values())
    if total:
        top_languages = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:5]
        breakdown = DOT.join(f"`{name}` {size / total * 100:.1f}%" for name, size in top_languages if size / total >= 0.001)

    homepage = data.get("homepage") or ""
    if homepage and not homepage.startswith("http"):
        homepage = f"https://{homepage}"

    details = facts(
        ("Languages", breakdown) if breakdown else ("Language", data.get("language")),
        ("License", license_name),
        ("Default branch", f"`{data['default_branch']}`"),
        ("Size", file_size(data.get("size", 0) * 1024)),
        ("Created", dated(data["created_at"])),
        ("Last push", when(data.get("pushed_at"))),
        ("Homepage", homepage if valid_url(homepage) else None),
    )

    topics = data.get("topics") or []
    topic_line = None
    if topics:
        topic_line = text(" ".join(f"`{topic}`" for topic in topics[:10]) + (f" +{len(topics) - 10} more" if len(topics) > 10 else ""))

    return collect(top, discord.ui.Separator(), stats, details, topic_line)


def user_items(data: dict[str, Any], repos: list[dict[str, Any]]) -> list[discord.ui.Item]:
    kind = data.get("type", "User")
    name = data.get("name") or data["login"]
    top = header(
        f"[{safe(name, 100)}]({data['html_url']})",
        f"@{data['login']}{DOT}{kind}",
        safe(data.get("bio"), 300) if data.get("bio") else "",
        thumbnail=data["avatar_url"],
    )

    parts = []
    if kind == "User":
        parts += [f"\N{BUSTS IN SILHOUETTE} **{compact(data['followers'])}** followers", f"**{compact(data['following'])}** following"]
    else:
        parts.append(f"\N{BUSTS IN SILHOUETTE} **{compact(data['followers'])}** followers")
    parts += [f"\N{PACKAGE} **{data['public_repos']}** repos", f"\N{MEMO} **{data['public_gists']}** gists"]
    stats = text(DOT.join(parts))

    blog = data.get("blog") or ""
    if blog and not blog.startswith("http"):
        blog = f"https://{blog}"
    twitter = data.get("twitter_username")

    details = facts(
        ("Company", safe(data.get("company"), 80) if data.get("company") else None),
        ("Location", safe(data.get("location"), 80) if data.get("location") else None),
        ("Website", blog if valid_url(blog) else None),
        ("X / Twitter", f"[@{twitter}](https://x.com/{quote(twitter, safe='')})" if twitter else None),
        ("Email", data.get("email")),
        ("Joined", dated(data["created_at"])),
    )

    popular = sorted((repo for repo in repos if not repo.get("fork")), key=lambda repo: repo["stargazers_count"], reverse=True)[:3]
    popular = [repo for repo in popular if repo["stargazers_count"] > 0]
    top_repos = None
    if popular:
        lines = []
        for repo in popular:
            language = f"{DOT}{repo['language']}" if repo.get("language") else ""
            lines.append(f"[{repo['name']}]({repo['html_url']}) \N{WHITE MEDIUM STAR} {compact(repo['stargazers_count'])}{language}")
        top_repos = text("**Popular repositories**\n" + "\n".join(lines))

    return collect(top, discord.ui.Separator(), stats, details, top_repos)


def issue_state(data: dict[str, Any]) -> tuple[str, discord.Colour, str]:
    if data["state"] == "open":
        return "Open", OPEN_COLOUR, "\N{LARGE GREEN CIRCLE}"
    reason = data.get("state_reason")
    if reason == "not_planned":
        return "Closed as not planned", DRAFT_COLOUR, "\N{MEDIUM WHITE CIRCLE}"
    if reason == "completed":
        return "Closed as completed", MERGED_COLOUR, "\N{LARGE PURPLE CIRCLE}"
    return "Closed", CLOSED_COLOUR, "\N{LARGE RED CIRCLE}"


def pr_state(data: dict[str, Any]) -> tuple[str, discord.Colour, str]:
    if data.get("merged"):
        return "Merged", MERGED_COLOUR, "\N{LARGE PURPLE CIRCLE}"
    if data["state"] == "closed":
        return "Closed", CLOSED_COLOUR, "\N{LARGE RED CIRCLE}"
    if data.get("draft"):
        return "Draft", DRAFT_COLOUR, "\N{MEDIUM WHITE CIRCLE}"
    return "Open", OPEN_COLOUR, "\N{LARGE GREEN CIRCLE}"


def label_names(data: dict[str, Any]) -> str | None:
    names = [label["name"] if isinstance(label, dict) else label for label in data.get("labels") or []]
    if not names:
        return None
    shown = " ".join(f"`{name}`" for name in names[:10])
    return shown + (f" +{len(names) - 10} more" if len(names) > 10 else "")


def title_block(repo: RepoRef, data: dict[str, Any], number: int, state: tuple[str, discord.Colour, str]) -> discord.ui.Item:
    label, _, emoji = state
    user = data.get("user") or {}
    return header(safe(data["title"], 220), f"{repo.full_name} #{number}{DOT}{emoji} {label}", thumbnail=user.get("avatar_url"))


def issue_items(repo: RepoRef, data: dict[str, Any]) -> list[discord.ui.Item]:
    body = clean_markdown(data.get("body"), BODY_LIMIT) or "*No description provided.*"
    assignees = ", ".join(user_link(user) for user in data.get("assignees") or []) or None
    milestone = data.get("milestone")
    reactions = (data.get("reactions") or {}).get("total_count", 0)

    details = facts(
        ("Author", user_link(data.get("user"))),
        ("Labels", label_names(data)),
        ("Assignees", assignees),
        ("Milestone", safe(milestone["title"], 60) if milestone else None),
        ("Comments", str(data["comments"]) if data.get("comments") else None),
        ("Reactions", str(reactions) if reactions else None),
        ("Locked", "Yes" if data.get("locked") else None),
        ("Opened", dated(data["created_at"])),
        ("Closed", when(data.get("closed_at"))),
    )
    return collect(title_block(repo, data, data["number"], issue_state(data)), discord.ui.Separator(), text(body), discord.ui.Separator(), details)


MERGE_STATES = {
    "clean": "\N{WHITE HEAVY CHECK MARK} Ready to merge",
    "dirty": "\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Has merge conflicts",
    "blocked": "\N{NO ENTRY SIGN} Blocked (reviews or checks required)",
    "behind": "Behind the base branch",
    "unstable": "\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Some checks are failing",
}


def ci_summary(payload: dict[str, Any] | None) -> str | None:
    runs = (payload or {}).get("check_runs") or []
    if not runs:
        return None
    passed = failed = pending = 0
    for run in runs:
        if run.get("status") != "completed":
            pending += 1
        elif run.get("conclusion") in {"success", "neutral", "skipped"}:
            passed += 1
        else:
            failed += 1
    parts = []
    if passed:
        parts.append(f"\N{WHITE HEAVY CHECK MARK} {passed} passed")
    if failed:
        parts.append(f"\N{CROSS MARK} {failed} failed")
    if pending:
        parts.append(f"\N{HOURGLASS WITH FLOWING SAND} {pending} running")
    return DOT.join(parts)


def pull_request_items(repo: RepoRef, data: dict[str, Any], checks: dict[str, Any] | None) -> list[discord.ui.Item]:
    body = clean_markdown(data.get("body"), BODY_LIMIT) or "*No description provided.*"
    assignees = ", ".join(user_link(user) for user in data.get("assignees") or []) or None
    reviewers = [user_link(user) for user in data.get("requested_reviewers") or []]
    reviewers += [f"`{team['slug']}`" for team in data.get("requested_teams") or []]

    head, base = data["head"], data["base"]
    branches = f"`{truncate(head['label'], 50)}` \N{RIGHTWARDS ARROW} `{truncate(base['label'], 50)}`"
    changes = (
        f"**+{data['additions']:,}** **{MINUS}{data['deletions']:,}** in {data['changed_files']} file{'' if data['changed_files'] == 1 else 's'}"
    )
    mergeable = MERGE_STATES.get(data.get("mergeable_state") or "") if data["state"] == "open" and not data.get("draft") else None
    merged_by = data.get("merged_by")

    details = facts(
        ("Author", user_link(data.get("user"))),
        ("Branches", branches),
        ("Changes", f"{changes}{DOT}{data['commits']} commit{'' if data['commits'] == 1 else 's'}"),
        ("Checks", ci_summary(checks)),
        ("Status", mergeable),
        ("Labels", label_names(data)),
        ("Assignees", assignees),
        ("Reviewers requested", ", ".join(reviewers) or None),
        ("Comments", str(data["comments"] + data["review_comments"]) if data["comments"] + data["review_comments"] else None),
        ("Opened", dated(data["created_at"])),
        ("Merged", f"{when(data['merged_at'])} by {user_link(merged_by)}" if data.get("merged") and merged_by else None),
        ("Closed", when(data.get("closed_at")) if not data.get("merged") else None),
    )
    return collect(title_block(repo, data, data["number"], pr_state(data)), discord.ui.Separator(), text(body), discord.ui.Separator(), details)


def commits_items(repo: RepoRef, chunk: list[dict[str, Any]], branch: str | None) -> list[discord.ui.Item]:
    subtitle = repo.full_name + (f"{DOT}{code(branch, 40)}" if branch else "")
    return [header("Recent commits", subtitle), discord.ui.Separator(), text("\n\n".join(commit_line(entry) for entry in chunk))]


def release_items(repo: RepoRef, release: dict[str, Any], *, latest: bool) -> list[discord.ui.Item]:
    badges = []
    if latest:
        badges.append("\N{WHITE HEAVY CHECK MARK} Latest")
    if release.get("prerelease"):
        badges.append("\N{CONSTRUCTION SIGN} Pre-release")
    if release.get("draft"):
        badges.append("Draft")

    title = safe(release.get("name") or release["tag_name"], 200)
    author = release.get("author")
    byline = f"{repo.full_name}{DOT}`{truncate(release['tag_name'], 40)}`"
    if release.get("published_at"):
        byline += f"{DOT}{when(release['published_at'])}"
    if author:
        byline += f" by {author['login']}"

    body = clean_markdown(release.get("body"), RELEASE_BODY_LIMIT) or "*No release notes.*"

    assets = release.get("assets") or []
    asset_block = None
    if assets:
        lines = [
            f"[{truncate(asset['name'], 45)}]({asset['browser_download_url']}) - {file_size(asset['size'])}{DOT}{asset['download_count']:,} downloads"
            for asset in assets[:5]
        ]
        if len(assets) > 5:
            lines.append(f"-# and {len(assets) - 5} more asset{'' if len(assets) == 6 else 's'}")
        asset_block = text("**Assets**\n" + "\n".join(lines))

    return collect(
        header(title, byline, DOT.join(badges), thumbnail=(author or {}).get("avatar_url")),
        discord.ui.Separator(),
        text(body),
        discord.ui.Separator() if asset_block else None,
        asset_block,
    )


FILE_STATUS = {"added": "A", "removed": "D", "modified": "M", "renamed": "R", "copied": "C", "changed": "M"}


def compare_items(repo: RepoRef, base: str, head: str, data: dict[str, Any]) -> list[discord.ui.Item]:
    ahead, behind = data.get("ahead_by", 0), data.get("behind_by", 0)
    summary = {
        "identical": "Both refs point to the same code.",
        "ahead": f"{code(head)} is **{ahead}** commit{'' if ahead == 1 else 's'} ahead of {code(base)}.",
        "behind": f"{code(head)} is **{behind}** commit{'' if behind == 1 else 's'} behind {code(base)}.",
        "diverged": f"{code(head)} is **{ahead}** ahead and **{behind}** behind {code(base)}.",
    }.get(data.get("status", ""), "")

    files = data.get("files") or []
    additions = sum(file.get("additions", 0) for file in files)
    deletions = sum(file.get("deletions", 0) for file in files)
    capped = "+" if len(files) >= 300 else ""
    stats = text(
        f"{summary}\n"
        f"**{data.get('total_commits', 0)}** commit{'' if data.get('total_commits') == 1 else 's'}{DOT}"
        f"**{len(files)}{capped}** file{'' if len(files) == 1 else 's'} changed{DOT}**+{additions:,}** **{MINUS}{deletions:,}**"
    )

    commit_block = None
    if commits := data.get("commits"):
        newest = commits[-5:][::-1]
        commit_block = text("**Latest commits**\n" + "\n".join(commit_line(entry).split("\n", 1)[0] for entry in newest))

    file_block = None
    if files:
        busiest = sorted(files, key=lambda file: file.get("changes", 0), reverse=True)[:8]
        lines = [
            f"`{FILE_STATUS.get(file['status'], '?')}` `{truncate(file['filename'], 55)}` **+{file['additions']}** **{MINUS}{file['deletions']}**"
            for file in busiest
        ]
        if len(files) > len(busiest):
            lines.append(f"-# and {len(files) - len(busiest)} more file{'' if len(files) - len(busiest) == 1 else 's'}")
        file_block = text("**Biggest changes**\n" + "\n".join(lines))

    return collect(
        header("Comparing refs", repo.full_name, f"{code(base)} \N{RIGHTWARDS ARROW} {code(head)}"),
        discord.ui.Separator(),
        stats,
        commit_block,
        file_block,
    )


def topics_items(repo: RepoRef, data: dict[str, Any]) -> list[discord.ui.Item]:
    topics = data.get("topics") or []
    description = safe(data.get("description"), 300) if data.get("description") else ""
    if topics:
        body = " ".join(f"[`{topic}`]({GITHUB_URL}/topics/{quote(topic, safe='')})" for topic in topics)
        footer = f"-# {len(topics)} topic{'' if len(topics) == 1 else 's'}{DOT}select one to explore it on GitHub"
    else:
        body = "*This repository has no topics.*"
        footer = "-# Maintainers can add topics from the gear icon next to **About** on the repository page."
    return [
        header(f"Topics of {data['name']}", repo.full_name, description, thumbnail=data["owner"]["avatar_url"]),
        discord.ui.Separator(),
        text(body),
        text(footer),
    ]


def contributors_items(repo: RepoRef, rows: list[dict[str, Any]]) -> list[discord.ui.Item]:
    shown = rows[:CONTRIBUTORS_SHOWN]
    biggest = max(row["contributions"] for row in shown)
    medals = {1: "\N{FIRST PLACE MEDAL}", 2: "\N{SECOND PLACE MEDAL}", 3: "\N{THIRD PLACE MEDAL}"}

    lines = []
    for rank, row in enumerate(shown, start=1):
        bar = "\N{FULL BLOCK}" * max(1, round(10 * row["contributions"] / biggest))
        bot = " \N{ROBOT FACE}" if row.get("type") == "Bot" else ""
        marker = medals.get(rank, f"`{rank:>2}.`")
        lines.append(f"{marker} [{row['login']}]({row['html_url']}){bot}{DOT}**{row['contributions']:,}** commits `{bar}`")

    total = sum(row["contributions"] for row in shown)
    subtitle = f"{repo.full_name}{DOT}top {len(shown)}"
    return [
        header("Top contributors", subtitle, thumbnail=shown[0]["avatar_url"]),
        discord.ui.Separator(),
        text("\n".join(lines)),
        text(f"-# {total:,} commits across the contributors shown"),
    ]


def gist_items(data: dict[str, Any], file: dict[str, Any]) -> list[discord.ui.Item]:
    owner = data.get("owner")
    filename = file["filename"]
    visibility = "public" if data.get("public") else "secret"
    top = header(
        safe(data.get("description") or filename, 200),
        f"gist `{data['id'][:12]}`{DOT}{visibility}",
        thumbnail=owner["avatar_url"] if owner else None,
    )

    files = data.get("files") or {}
    details = facts(
        ("Owner", user_link(owner) if owner else "*anonymous*"),
        ("Files", str(len(files))),
        ("Comments", str(data["comments"]) if data.get("comments") else None),
        ("Forks", str(len(data["forks"])) if data.get("forks") else None),
        ("Revisions", str(len(data["history"])) if data.get("history") else None),
        ("Created", dated(data["created_at"])),
        ("Updated", when(data.get("updated_at"))),
    )

    language = file.get("language")
    meta = DOT.join(part for part in (f"**{safe(filename, 80)}**", language, file_size(file.get("size", 0))) if part)
    content = file.get("content")
    if content is None:
        preview = f"*Preview unavailable. [Open the raw file]({file['raw_url']}).*" if valid_url(file.get("raw_url")) else "*Preview unavailable.*"
    else:
        lines = content.replace("\r\n", "\n").split("\n")
        snippet = "\n".join(lines[:18])
        cut = len(lines) > 18
        if len(snippet) > 1200:
            snippet, cut = snippet[:1200], True
        extension = PurePosixPath(filename).suffix.lstrip(".").lower()
        fence = re.sub(r"[^a-z0-9+#-]", "", extension or (language or "").lower())
        snippet = snippet.replace("```", "`\u200b``")
        preview = f"```{fence}\n{snippet}\n```" + ("\n-# Preview shortened" if cut or file.get("truncated") else "")

    return collect(top, discord.ui.Separator(), details, discord.ui.Separator(), text(meta), text(preview))


class GitHub(commands.Cog):
    """Look up users, repositories, issues, pull requests, releases and more on GitHub."""

    help_emoji = "\N{OCTOPUS}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        # Optional. Raises the API limit from 60 to 5000 requests per hour.
        self.token = os.environ.get("GITHUB_TOKEN")

    async def request(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        missing: str = "GitHub could not find that.",
    ) -> Any:
        """GET a GitHub API path and return the decoded JSON, or raise :class:`GitHubError` with a friendly message."""
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with self.bot.http_session.get(f"{GITHUB_API_URL}{path}", params=params, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                if response.status < 400:
                    return await response.json()

                status = response.status
                remaining = response.headers.get("X-RateLimit-Remaining")
                reset = response.headers.get("X-RateLimit-Reset")
                try:
                    body = await response.json(content_type=None)
                except aiohttp.ContentTypeError, ValueError:
                    body = None
        except (TimeoutError, aiohttp.ClientError) as error:
            msg = "Could not reach GitHub right now. Try again in a moment."
            raise GitHubError(msg) from error

        message = body.get("message", "") if isinstance(body, dict) else ""
        if status == 404:
            raise GitHubError(missing)
        if status == 429 or (status == 403 and (remaining == "0" or "rate limit" in message.lower())):
            retry = ""
            if reset and reset.isdigit():
                retry = f" Try again {discord.utils.format_dt(datetime.fromtimestamp(int(reset), tz=UTC), 'R')}."
            msg = f"GitHub's API rate limit has been reached.{retry}"
            raise GitHubError(msg)
        if status == 451:
            msg = "GitHub cannot show this because it was blocked for legal reasons."
            raise GitHubError(msg)
        detail = f": {truncate(message, 200)}" if message else "."
        msg = f"GitHub returned an error ({status}){detail}"
        raise GitHubError(msg)

    async def optional(self, path: str, **kwargs: Any) -> Any:
        """Like :meth:`request`, but a failure yields ``None`` because the data is only nice to have."""
        try:
            return await self.request(path, **kwargs)
        except GitHubError:
            return None

    async def deliver(self, ctx: commands.Context[Bot], producer: Awaitable[GitHubView]) -> discord.Message:
        """Await the view, then send it. Any :class:`GitHubError` becomes an error notice instead."""
        none = discord.AllowedMentions.none()
        async with ctx.typing():
            try:
                view = await producer
            except GitHubError as error:
                return await ctx.reply(view=NoticeLayout.error(str(error), title="GitHub"), allowed_mentions=none)

        message = await ctx.reply(view=view, allowed_mentions=none)
        view.message = message
        return message

    @staticmethod
    def single(ctx: commands.Context[Bot], page: Page) -> GitHubView:
        return GitHubView(ctx.author, [page])

    @commands.group(name="github", aliases=["gh"])  # Thanks `will.#0021` (211756205721255947)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def github_group(self, ctx: commands.Context[Bot]) -> discord.Message | None:
        """Commands for finding information related to GitHub."""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)
        return None

    @github_group.command(name="user", aliases=["userinfo", "u"], extras={"examples": ["github user torvalds"]})  # Thanks `will.#0021`
    async def github_user_info(
        self,
        ctx: commands.Context[Bot],
        username: str = commands.parameter(description="The GitHub username to fetch information for."),
    ) -> discord.Message:
        """Fetches a user's or organisation's GitHub profile."""
        return await self.deliver(ctx, self.user_view(ctx, username))

    async def user_view(self, ctx: commands.Context[Bot], username: str) -> GitHubView:
        username = username.strip().lstrip("@")
        if not USERNAME_PATTERN.fullmatch(username):
            msg = f"`{discord.utils.escape_markdown(truncate(username, 40))}` is not a valid GitHub username."
            raise GitHubError(msg)

        quoted = quote(username, safe="")
        data, repos = await asyncio.gather(
            self.request(f"/users/{quoted}", missing=f"The profile for `{username}` was not found."),
            self.optional(f"/users/{quoted}/repos", params={"per_page": 100, "sort": "pushed"}),
            return_exceptions=True,
        )
        if isinstance(data, BaseException):
            raise data
        repos = repos if isinstance(repos, list) else []

        links = [("Repositories", f"{data['html_url']}?tab=repositories")]
        if data.get("public_gists"):
            links.append(("Gists", f"https://gist.github.com/{quoted}"))
        return self.single(ctx, Page(partial(user_items, data, repos), url=data["html_url"], label="Open profile", links=links))

    @github_group.command(
        name="repository",
        aliases=["repo", "r"],
        extras={"examples": ["github repo python/cpython", "github repo python cpython"]},  # Thanks ``willdn`` (will.#0021 - 211756205721255947)
    )
    async def github_repo_info(self, ctx: commands.Context[Bot], *repository: str) -> discord.Message:
        """Fetches a repositories' GitHub information.
        The repository should look like `user/reponame` or `user reponame`.
        """
        return await self.deliver(ctx, self.repository_view(ctx, repository))

    async def repository_view(self, ctx: commands.Context[Bot], repository: tuple[str, ...]) -> GitHubView:
        repo = parse_repo("/".join(repository))
        if repo is None:
            msg = "The repository should look like `user/reponame` or `user reponame`."
            raise GitHubError(msg)

        data, languages = await asyncio.gather(
            self.request(f"/repos/{repo.path}", missing=f"The repository `{repo.full_name}` was not found."),
            self.optional(f"/repos/{repo.path}/languages"),
            return_exceptions=True,
        )
        if isinstance(data, BaseException):
            raise data
        languages = languages if isinstance(languages, dict) else {}

        links = [("Issues", f"{data['html_url']}/issues"), ("Pull requests", f"{data['html_url']}/pulls")]
        homepage = data.get("homepage") or ""
        if homepage:
            links.append(("Homepage", homepage if homepage.startswith("http") else f"https://{homepage}"))
        return self.single(ctx, Page(partial(repository_items, data, languages), url=data["html_url"], label="Open repository", links=links))

    @github_group.command(name="issue", aliases=["issues", "i"], extras={"examples": ["github issue python/cpython 1234"]})
    async def github_issue(
        self,
        ctx: commands.Context[Bot],
        repo: Annotated[RepoRef, RepoConverter] = commands.parameter(  # noqa: B008
            converter=RepoConverter, description="The repository, as `owner/name` or a link."
        ),
        number: int = commands.parameter(converter=NumberConverter, description="The issue number."),
    ) -> discord.Message:
        """Shows the details of an issue."""
        return await self.deliver(ctx, self.issue_view(ctx, repo, number))

    async def issue_view(self, ctx: commands.Context[Bot], repo: RepoRef, number: int) -> GitHubView:
        data = await self.request(f"/repos/{repo.path}/issues/{number}", missing=f"Issue #{number} was not found in `{repo.full_name}`.")
        if "pull_request" in data:  # the issues endpoint also returns pull requests
            return await self.pull_request_view(ctx, repo, number)

        _, colour, _ = issue_state(data)
        return self.single(
            ctx, Page(partial(issue_items, repo, data), url=data["html_url"], label="Open issue", colour=colour, links=[("Repository", repo.url)])
        )

    @github_group.command(name="pr", aliases=["pull", "pullrequest"], extras={"examples": ["github pr python/cpython 1234"]})
    async def github_pull_request(
        self,
        ctx: commands.Context[Bot],
        repo: Annotated[RepoRef, RepoConverter] = commands.parameter(  # noqa: B008
            converter=RepoConverter, description="The repository, as `owner/name` or a link."
        ),
        number: int = commands.parameter(converter=NumberConverter, description="The pull request number."),
    ) -> discord.Message:
        """Shows the details of a pull request."""
        return await self.deliver(ctx, self.pull_request_view(ctx, repo, number))

    async def pull_request_view(self, ctx: commands.Context[Bot], repo: RepoRef, number: int) -> GitHubView:
        data = await self.request(f"/repos/{repo.path}/pulls/{number}", missing=f"Pull request #{number} was not found in `{repo.full_name}`.")
        checks = await self.optional(f"/repos/{repo.path}/commits/{data['head']['sha']}/check-runs", params={"per_page": 100})

        _, colour, _ = pr_state(data)
        return self.single(
            ctx,
            Page(
                partial(pull_request_items, repo, data, checks),
                url=data["html_url"],
                label="Open pull request",
                colour=colour,
                links=[("Files changed", f"{data['html_url']}/files"), ("Repository", repo.url)],
            ),
        )

    @github_group.command(
        name="commits",
        aliases=["commit", "log"],
        extras={"examples": ["github commits python/cpython", "github commits python/cpython 3.12"]},
    )
    async def github_commits(
        self,
        ctx: commands.Context[Bot],
        repo: Annotated[RepoRef, RepoConverter] = commands.parameter(  # noqa: B008
            converter=RepoConverter, description="The repository, as `owner/name` or a link."
        ),
        branch: str | None = commands.parameter(default=None, description="A branch, tag or commit to start from. Defaults to the default branch."),
    ) -> discord.Message:
        """Displays the most recent commits of a repository."""
        return await self.deliver(ctx, self.commits_view(ctx, repo, branch))

    async def commits_view(self, ctx: commands.Context[Bot], repo: RepoRef, branch: str | None) -> GitHubView:
        params: dict[str, Any] = {"per_page": COMMITS_PER_PAGE * 4}
        if branch:
            params["sha"] = branch
        missing = f"No commits were found: `{repo.full_name}` or the ref {code(branch or '')} does not exist."
        commits = await self.request(f"/repos/{repo.path}/commits", params=params, missing=missing)
        if not commits:
            msg = f"`{repo.full_name}` has no commits yet."
            raise GitHubError(msg)

        url = f"{repo.url}/commits" + (f"/{quote(branch, safe='/')}" if branch else "")
        pages = [
            Page(partial(commits_items, repo, commits[start : start + COMMITS_PER_PAGE], branch), url=url, label="All commits")
            for start in range(0, len(commits), COMMITS_PER_PAGE)
        ]
        return GitHubView(ctx.author, pages)

    @github_group.command(name="releases", aliases=["release", "rel"], extras={"examples": ["github releases python/cpython"]})
    async def github_releases(
        self,
        ctx: commands.Context[Bot],
        repo: Annotated[RepoRef, RepoConverter] = commands.parameter(  # noqa: B008
            converter=RepoConverter, description="The repository, as `owner/name` or a link."
        ),
    ) -> discord.Message:
        """Shows the most recent releases, with their notes and downloads."""
        return await self.deliver(ctx, self.releases_view(ctx, repo))

    async def releases_view(self, ctx: commands.Context[Bot], repo: RepoRef) -> GitHubView:
        releases = await self.request(
            f"/repos/{repo.path}/releases", params={"per_page": MAX_RELEASES}, missing=f"The repository `{repo.full_name}` was not found."
        )
        if not releases:
            msg = f"`{repo.full_name}` has no releases. It may only use [tags]({repo.url}/tags)."
            raise GitHubError(msg)

        latest = next((release for release in releases if not release.get("prerelease") and not release.get("draft")), None)
        pages = [
            Page(
                partial(release_items, repo, release, latest=release is latest),
                url=release.get("html_url"),
                label="Open release",
                colour=DRAFT_COLOUR if release.get("prerelease") else OPEN_COLOUR if release is latest else GITHUB_COLOUR,
                links=[("All releases", f"{repo.url}/releases")],
            )
            for release in releases
        ]
        return GitHubView(ctx.author, pages)

    @github_group.command(name="compare", aliases=["diff", "cmp"], extras={"examples": ["github compare python/cpython 3.11 3.12"]})
    async def github_compare(
        self,
        ctx: commands.Context[Bot],
        repo: Annotated[RepoRef, RepoConverter] = commands.parameter(  # noqa: B008
            converter=RepoConverter, description="The repository, as `owner/name` or a link."
        ),
        base: str = commands.parameter(description="The base branch, tag or commit. Quote it if it has spaces."),
        head: str = commands.parameter(description="The branch, tag or commit to compare against the base. Use `user:branch` for forks."),
    ) -> discord.Message:
        """Compares two branches, tags or commits."""
        return await self.deliver(ctx, self.compare_view(ctx, repo, base, head))

    async def compare_view(self, ctx: commands.Context[Bot], repo: RepoRef, base: str, head: str) -> GitHubView:
        data = await self.request(
            f"/repos/{repo.path}/compare/{quote(base, safe='/:')}...{quote(head, safe='/:')}",
            missing=f"`{repo.full_name}`, {code(base)} or {code(head)} was not found.",
        )
        if data.get("status") == "identical":
            colour = DRAFT_COLOUR
        elif data.get("status") == "behind":
            colour = CLOSED_COLOUR
        else:
            colour = OPEN_COLOUR
        return self.single(ctx, Page(partial(compare_items, repo, base, head, data), url=data["html_url"], label="Open comparison", colour=colour))

    @github_group.command(name="topics", aliases=["topic"], extras={"examples": ["github topics python/cpython"]})
    async def github_topics(
        self,
        ctx: commands.Context[Bot],
        repo: RepoRef = commands.parameter(converter=RepoConverter, description="The repository, as `owner/name` or a link."),  # noqa: B008
    ) -> discord.Message:
        """Shows the topics of a repository."""
        return await self.deliver(ctx, self.topics_view(ctx, repo))

    async def topics_view(self, ctx: commands.Context[Bot], repo: RepoRef) -> GitHubView:
        data = await self.request(f"/repos/{repo.path}", missing=f"The repository `{repo.full_name}` was not found.")
        return self.single(ctx, Page(partial(topics_items, repo, data), url=data["html_url"], label="Open repository"))

    @github_group.command(name="contributors", aliases=["contributor", "contrib"], extras={"examples": ["github contributors python/cpython"]})
    async def github_contributors(
        self,
        ctx: commands.Context[Bot],
        repo: RepoRef = commands.parameter(converter=RepoConverter, description="The repository, as `owner/name` or a link."),  # noqa: B008
    ) -> discord.Message:
        """Lists the top contributors of a repository."""
        return await self.deliver(ctx, self.contributors_view(ctx, repo))

    async def contributors_view(self, ctx: commands.Context[Bot], repo: RepoRef) -> GitHubView:
        rows = await self.request(
            f"/repos/{repo.path}/contributors",
            params={"per_page": CONTRIBUTORS_SHOWN},
            missing=f"The repository `{repo.full_name}` was not found.",
        )
        if not rows:
            msg = f"`{repo.full_name}` has no contributors yet."
            raise GitHubError(msg)
        return self.single(ctx, Page(partial(contributors_items, repo, rows), url=f"{repo.url}/graphs/contributors", label="Open contributors"))

    @github_group.command(name="gist", aliases=["g"], extras={"examples": ["github gist 0123456789abcdef0123456789abcdef"]})
    async def github_gist(
        self,
        ctx: commands.Context[Bot],
        gist: str = commands.parameter(converter=GistConverter, description="The gist ID, or a link to the gist."),
    ) -> discord.Message:
        """Displays a public gist and a preview of each of its files."""
        return await self.deliver(ctx, self.gist_view(ctx, gist))

    async def gist_view(self, ctx: commands.Context[Bot], gist: str) -> GitHubView:
        data = await self.request(f"/gists/{quote(gist, safe='')}", missing="That gist was not found. It may have been deleted.")
        files = list((data.get("files") or {}).values())[:MAX_GIST_FILES]
        if not files:
            msg = "That gist has no files."
            raise GitHubError(msg)

        pages = [
            Page(
                partial(gist_items, data, file),
                url=data["html_url"],
                label="Open gist",
                links=[("Raw file", file["raw_url"])] if file.get("raw_url") else [],
            )
            for file in files
        ]
        return GitHubView(ctx.author, pages)


async def setup(bot: Bot) -> None:
    await bot.add_cog(GitHub(bot))
