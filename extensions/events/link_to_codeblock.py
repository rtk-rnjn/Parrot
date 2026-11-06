from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import textwrap
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

import discord
from aiohttp import ClientResponseError
from discord.ext import commands

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

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

Target = tuple[str, str, str]


def _get_github_raw_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3.raw"}
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _trim(text: str | None, limit: int = 350) -> str:
    """Strip issue-template comments, collapse blank lines and shorten to ``limit``."""
    text = _HTML_COMMENT_RE.sub("", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"
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


@dataclass(slots=True)
class CodeSnippet:
    file_path: str
    language: str
    source_url: str
    all_lines: list[str]
    start_line: int
    end_line: int

    @property
    def short_name(self) -> str:
        return self.file_path.rsplit("/", maxsplit=1)[-1]

    @property
    def total_lines(self) -> int:
        return len(self.all_lines)

    def build_pages(
        self,
        *,
        full_file: bool = False,
        line_numbers: bool = False,
        max_chars: int = CODE_PAGE_CHAR_LIMIT,
        max_lines: int = CODE_PAGE_LINE_LIMIT,
    ) -> list[str]:
        """Build paginated codeblock strings for either the requested snippet or the full file."""
        if full_file:
            start = 1
            end = len(self.all_lines)
            raw_slice = self.all_lines
        else:
            start = self.start_line
            end = self.end_line
            raw_slice = self.all_lines[start - 1 : end]

        if not raw_slice:
            header = f"`{self.file_path}` line {start}\n"
            return [f"{header}``` ```"]

        dedented = textwrap.dedent("\n".join(raw_slice)).rstrip().splitlines()
        if not dedented:
            header = f"`{self.file_path}` line {start}\n" if start == end else f"`{self.file_path}` lines {start} to {end}\n"
            return [f"{header}``` ```"]

        width = len(str(end))
        pages: list[str] = []
        chunk: list[str] = []
        chunk_start_line = start
        current_chars = 0

        for idx, raw_line in enumerate(dedented):
            line_no = start + idx
            safe_line = raw_line.replace("`", "`\N{ZERO WIDTH SPACE}")
            formatted_line = f"{line_no:>{width}} | {safe_line}" if line_numbers else safe_line

            # Truncate single extremely long lines (e.g. minified files) so a page never overflows
            if len(formatted_line) > max_chars - 100:
                formatted_line = formatted_line[: max_chars - 103] + "..."

            line_cost = len(formatted_line) + 1
            if chunk and (current_chars + line_cost > max_chars or len(chunk) >= max_lines):
                chunk_end_line = line_no - 1
                pages.append(self._format_page(chunk, chunk_start_line, chunk_end_line, full_file=full_file))
                chunk = [formatted_line]
                chunk_start_line = line_no
                current_chars = line_cost
            else:
                chunk.append(formatted_line)
                current_chars += line_cost

        if chunk:
            chunk_end_line = start + len(dedented) - 1
            pages.append(self._format_page(chunk, chunk_start_line, chunk_end_line, full_file=full_file))

        return pages

    def _format_page(self, lines: list[str], start: int, end: int, *, full_file: bool) -> str:
        mode_tag = f" (Full File • {self.total_lines} lines)" if full_file else ""
        header = f"`{self.file_path}` line {start}{mode_tag}\n" if start == end else f"`{self.file_path}` lines {start}-{end}{mode_tag}\n"
        body = "\n".join(lines)
        return f"{header}```{self.language}\n{body}\n```"


@dataclass(slots=True)
class IssueOrCommitData:
    kind: str  # "issues", "pull", or "commit"
    repo: str
    ident: str
    title: str
    url: str
    body: str
    state_label: str
    state_emoji: str
    colour: int
    created_at: datetime
    author_name: str
    author_url: str | None = None
    author_avatar: str | None = None
    comments: int = 0
    additions: int | None = None
    deletions: int | None = None
    changed_files: int | None = None
    labels: list[str] = field(default_factory=list)

    @property
    def display_title(self) -> str:
        if self.kind == "commit":
            return f"Commit `{self.ident[:7]}`: {self.title}"[:256]
        prefix = "PR" if self.kind == "pull" else "Issue"
        return f"{prefix} #{self.ident}: {self.title}"[:256]

    @property
    def short_label(self) -> str:
        if self.kind == "commit":
            return f"{self.repo}@{self.ident[:7]}"
        prefix = "PR" if self.kind == "pull" else "Issue"
        return f"{prefix} #{self.ident} ({self.repo})"


class EphemeralCodePaginator(discord.ui.View):
    """Interactive ephemeral paginator for browsing code snippets and full files."""

    def __init__(
        self,
        snippets: list[CodeSnippet],
        *,
        initial_index: int = 0,
        full_file: bool = False,
        line_numbers: bool = False,
    ) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.snippets = snippets
        self.snippet_index = initial_index
        self.full_file = full_file
        self.line_numbers = line_numbers
        self.page_index = 0
        self.pages: list[str] = []

        self._SelectComponent: discord.ui.Select | None = None
        if len(self.snippets) > 1:
            options = [
                discord.SelectOption(
                    label=f"{idx + 1}. {s.short_name} (L{s.start_line}-L{s.end_line})"[:100],
                    description=s.file_path[:100],
                    value=str(idx),
                    default=(idx == self.snippet_index),
                )
                for idx, s in enumerate(self.snippets[:25])
            ]
            select: discord.ui.Select = discord.ui.Select(
                placeholder="Switch code snippet...",
                options=options,
                row=2,
            )
            select.callback = self._on_select_snippet
            self._SelectComponent = select
            self.add_item(select)

        self._rebuild_pages()

    @property
    def current_snippet(self) -> CodeSnippet:
        return self.snippets[self.snippet_index]

    def _rebuild_pages(self) -> None:
        self.pages = self.current_snippet.build_pages(
            full_file=self.full_file,
            line_numbers=self.line_numbers,
        )
        self.page_index = max(0, min(self.page_index, len(self.pages) - 1))
        self._sync_components()

    def _sync_components(self) -> None:
        total = len(self.pages)
        at_start = self.page_index <= 0
        at_end = self.page_index >= total - 1

        self.first_btn.disabled = at_start
        self.prev_btn.disabled = at_start
        self.page_indicator.label = f"Page {self.page_index + 1}/{total}"
        self.next_btn.disabled = at_end
        self.last_btn.disabled = at_end

        snippet = self.current_snippet
        if self.full_file:
            self.mode_btn.label = f"\N{DIRECT HIT} Snippet Only (L{snippet.start_line}-L{snippet.end_line})"
            self.mode_btn.style = discord.ButtonStyle.primary
        else:
            self.mode_btn.label = f"\N{PAGE FACING UP} Show Full File ({snippet.total_lines} lines)"
            self.mode_btn.style = discord.ButtonStyle.secondary

        self.lineno_btn.label = "\N{INPUT SYMBOL FOR NUMBERS} Hide Line #" if self.line_numbers else "\N{INPUT SYMBOL FOR NUMBERS} Show Line #"
        self.lineno_btn.style = discord.ButtonStyle.success if self.line_numbers else discord.ButtonStyle.secondary

        if self._SelectComponent is not None:
            for opt in self._SelectComponent.options:
                opt.default = opt.value == str(self.snippet_index)

    def current_content(self) -> str:
        header_parts: list[str] = []
        if len(self.snippets) > 1:
            header_parts.append(f"**File {self.snippet_index + 1}/{len(self.snippets)}**")
        header_parts.append(f"[Jump to Source](<{self.current_snippet.source_url}>)")
        prefix = " • ".join(header_parts)
        return f"-# {prefix}\n{self.pages[self.page_index]}"

    async def _on_select_snippet(self, interaction: discord.Interaction) -> None:
        if self._SelectComponent and self._SelectComponent.values:
            self.snippet_index = int(self._SelectComponent.values[0])
            self.page_index = 0
            self._rebuild_pages()
            await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", style=discord.ButtonStyle.secondary, row=0)
    async def first_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = 0
        self._sync_components()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="\N{BLACK LEFT-POINTING TRIANGLE}", style=discord.ButtonStyle.secondary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = max(0, self.page_index - 1)
        self._sync_components()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, disabled=True, row=0)
    async def page_indicator(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer()

    @discord.ui.button(label="\N{BLACK RIGHT-POINTING TRIANGLE}", style=discord.ButtonStyle.secondary, row=0)
    async def next_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = min(len(self.pages) - 1, self.page_index + 1)
        self._sync_components()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", style=discord.ButtonStyle.secondary, row=0)
    async def last_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = len(self.pages) - 1
        self._sync_components()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="\N{PAGE FACING UP} Show Full File", style=discord.ButtonStyle.secondary, row=1)
    async def mode_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.full_file = not self.full_file
        self.page_index = 0
        self._rebuild_pages()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="\N{INPUT SYMBOL FOR NUMBERS} Show Line #", style=discord.ButtonStyle.secondary, row=1)
    async def lineno_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.line_numbers = not self.line_numbers
        self._rebuild_pages()
        await interaction.response.edit_message(content=self.current_content(), view=self)


class CodeblockPublicView(discord.ui.View):
    """Public view attached to the channel codeblock reply; spawns ephemeral paginators on click."""

    def __init__(self, snippets: list[CodeSnippet], author_id: int) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.snippets = snippets
        self.author_id = author_id

        total_snippet_pages = sum(len(s.build_pages(full_file=False)) for s in snippets)
        if len(snippets) > 1 or total_snippet_pages > 1:
            self.paginate_btn.label = (
                f"\N{OPEN BOOK} Browse All Code ({len(snippets)} file{'s' if len(snippets) > 1 else ''}, {total_snippet_pages} pages)"
            )
            self.paginate_btn.style = discord.ButtonStyle.primary
        else:
            self.paginate_btn.label = "\N{OPEN BOOK} Interactive Viewer"
            self.paginate_btn.style = discord.ButtonStyle.secondary

        first_total_lines = snippets[0].total_lines
        self.full_file_btn.label = f"\N{PAGE FACING UP} Full File ({first_total_lines} lines)"

        self.add_item(
            discord.ui.Button(
                label="Source",
                style=discord.ButtonStyle.link,
                url=snippets[0].source_url,
                emoji="\N{LINK SYMBOL}",
            )
        )

    def build_initial_message(self) -> str:
        """Render as many snippets as fit cleanly in the initial public message, or the first page."""
        rendered_blocks = [s.build_pages(full_file=False)[0] for s in self.snippets]
        combined = "\n".join(rendered_blocks)

        has_more_pages = any(len(s.build_pages(full_file=False)) > 1 for s in self.snippets)
        if len(combined) < DISCORD_MESSAGE_LIMIT - 80 and not has_more_pages:
            return combined

        first_page = rendered_blocks[0]
        extra_files = len(self.snippets) - 1
        first_pages_count = len(self.snippets[0].build_pages(full_file=False))
        notes: list[str] = []
        if first_pages_count > 1:
            notes.append(f"showing page 1/{first_pages_count}")
        if extra_files > 0:
            notes.append(f"+{extra_files} more file{'s' if extra_files > 1 else ''}")
        note_text = (
            f"-# \N{ELECTRIC LIGHT BULB} *Snippet truncated ({', '.join(notes)}) — click **Browse All Code** below to page through everything.*"
        )
        return f"{first_page}\n{note_text}"

    @discord.ui.button(label="\N{OPEN BOOK} Browse All Code", style=discord.ButtonStyle.primary)
    async def paginate_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        paginator = EphemeralCodePaginator(self.snippets, full_file=False, line_numbers=False)
        await interaction.response.send_message(
            content=paginator.current_content(),
            view=paginator,
            ephemeral=True,
        )

    @discord.ui.button(label="\N{PAGE FACING UP} Full File", style=discord.ButtonStyle.secondary)
    async def full_file_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        paginator = EphemeralCodePaginator(self.snippets, full_file=True, line_numbers=True)
        await interaction.response.send_message(
            content=paginator.current_content(),
            view=paginator,
            ephemeral=True,
        )

    @discord.ui.button(emoji="\N{WASTEBASKET}", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        is_author = interaction.user.id == self.author_id
        can_manage = (
            isinstance(interaction.user, discord.Member)
            and interaction.channel is not None
            and interaction.channel.permissions_for(interaction.user).manage_messages
        )
        if not (is_author or can_manage):
            await interaction.response.send_message(
                "Only the message author or a moderator can delete this snippet.",
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        if interaction.message:
            with contextlib.suppress(discord.HTTPException):
                await interaction.message.delete()


def _build_issue_container(
    item: IssueOrCommitData,
    *,
    body_text: str,
    page_label: str | None = None,
) -> discord.ui.Container:
    """Build a styled Components V2 Container for a GitHub Issue, PR, or Commit."""
    container = discord.ui.Container(accent_colour=discord.Colour(item.colour))

    author_md = f"[**{item.author_name}**]({item.author_url})" if item.author_url else f"**{item.author_name}**"
    unix_ts = int(item.created_at.timestamp())
    header_md = (
        f"### {item.state_emoji} [{item.display_title}]({item.url})\n"
        f"-# \N{BUST IN SILHOUETTE} {author_md} in [**{item.repo}**](https://github.com/{item.repo}) • <t:{unix_ts}:R>"
    )

    if item.author_avatar:
        section = discord.ui.Section(
            discord.ui.TextDisplay(header_md),
            accessory=discord.ui.Thumbnail(media=item.author_avatar),
        )
        container.add_item(section)
    else:
        section = discord.ui.Section(
            discord.ui.TextDisplay(header_md),
            accessory=discord.ui.Button(
                label="Open",
                style=discord.ButtonStyle.link,
                url=item.url,
            ),
        )
        container.add_item(section)

    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    if body_text:
        container.add_item(discord.ui.TextDisplay(body_text))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    # Build compact metadata badges
    stats_parts = [f"**State:** `{item.state_label}`"]
    if item.kind != "commit":
        stats_parts.append(f"**Comments:** \N{SPEECH BALLOON} `{item.comments}`")
    if item.additions is not None and item.deletions is not None:
        files_count = item.changed_files or 0
        stats_parts.append(f"**Changes:** `+{item.additions} \N{MINUS SIGN}{item.deletions}` (`{files_count}` files)")
    if page_label:
        stats_parts.append(f"**Page:** `{page_label}`")

    meta_lines = ["  •  ".join(stats_parts)]
    if item.labels:
        formatted_labels = " ".join(f"`{lbl}`" for lbl in item.labels[:6])
        meta_lines.append(f"**Labels:** {formatted_labels}")

    container.add_item(discord.ui.TextDisplay("-# " + "\n-# ".join(meta_lines)))
    return container


class EphemeralIssuePaginator(discord.ui.LayoutView):
    """Ephemeral Components V2 LayoutView for paging through full Issue/PR/Commit bodies and multiple targets."""

    def __init__(self, items: list[IssueOrCommitData], *, initial_item_index: int = 0) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.items = items
        self.item_index = initial_item_index
        self.page_index = 0
        self.body_pages: list[str] = []
        self._rebuild_layout()

    @property
    def current_item(self) -> IssueOrCommitData:
        return self.items[self.item_index]

    def _rebuild_layout(self) -> None:
        self.clear_items()
        item = self.current_item
        self.body_pages = _paginate_markdown(item.body, limit=ISSUE_PAGE_CHAR_LIMIT)
        self.page_index = max(0, min(self.page_index, len(self.body_pages) - 1))
        total_pages = len(self.body_pages)

        container = _build_issue_container(
            item,
            body_text=self.body_pages[self.page_index],
            page_label=f"{self.page_index + 1}/{total_pages}",
        )

        # Navigation row inside the container
        nav_row = discord.ui.ActionRow()

        first_btn = discord.ui.Button(
            label="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index <= 0),
        )
        first_btn.callback = self._on_first

        prev_btn = discord.ui.Button(
            label="\N{BLACK LEFT-POINTING TRIANGLE}",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index <= 0),
        )
        prev_btn.callback = self._on_prev

        page_btn = discord.ui.Button(
            label=f"Page {self.page_index + 1}/{total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )

        next_btn = discord.ui.Button(
            label="\N{BLACK RIGHT-POINTING TRIANGLE}",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index >= total_pages - 1),
        )
        next_btn.callback = self._on_next

        last_btn = discord.ui.Button(
            label="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index >= total_pages - 1),
        )
        last_btn.callback = self._on_last

        for btn in (first_btn, prev_btn, page_btn, next_btn, last_btn):
            nav_row.add_item(btn)
        container.add_item(nav_row)

        # If multiple issues/PRs/commits were linked, add a selector dropdown
        if len(self.items) > 1:
            select_row = discord.ui.ActionRow()
            options = [
                discord.SelectOption(
                    label=f"{idx + 1}. {it.short_label}"[:100],
                    description=it.title[:100],
                    value=str(idx),
                    emoji=it.state_emoji,
                    default=(idx == self.item_index),
                )
                for idx, it in enumerate(self.items[:25])
            ]
            select: discord.ui.Select = discord.ui.Select(
                placeholder="Switch Issue / PR / Commit...",
                options=options,
            )
            select.callback = self._on_select_item
            select_row.add_item(select)
            container.add_item(select_row)

        self.add_item(container)

    async def _on_first(self, interaction: discord.Interaction) -> None:
        self.page_index = 0
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_prev(self, interaction: discord.Interaction) -> None:
        self.page_index = max(0, self.page_index - 1)
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_next(self, interaction: discord.Interaction) -> None:
        self.page_index = min(len(self.body_pages) - 1, self.page_index + 1)
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_last(self, interaction: discord.Interaction) -> None:
        self.page_index = len(self.body_pages) - 1
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_select_item(self, interaction: discord.Interaction) -> None:
        values = interaction.data.get("values") if interaction.data else None
        if values:
            self.item_index = int(values[0])
            self.page_index = 0
            self._rebuild_layout()
            await interaction.response.edit_message(view=self)


class IssuePublicLayoutView(discord.ui.LayoutView):
    """Public Components V2 LayoutView displaying GitHub Issue/PR/Commit cards with ephemeral detail paging."""

    def __init__(self, items: list[IssueOrCommitData], author_id: int) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.items = items
        self.author_id = author_id
        self._build_public_cards()

    def _build_public_cards(self) -> None:
        self.clear_items()
        visible_items = self.items[:MAX_EMBEDS]

        for idx, item in enumerate(visible_items):
            trimmed_body = _trim(item.body, limit=350) or "*No description provided.*"
            container = _build_issue_container(item, body_text=trimmed_body)

            action_row = discord.ui.ActionRow()
            read_btn = discord.ui.Button(
                label="\N{OPEN BOOK} Full Details / Paginate",
                style=discord.ButtonStyle.secondary,
            )
            read_btn.callback = self._make_open_ephemeral_callback(idx)
            action_row.add_item(read_btn)

            action_row.add_item(
                discord.ui.Button(
                    label="View on GitHub",
                    style=discord.ButtonStyle.link,
                    url=item.url,
                    emoji="\N{LINK SYMBOL}",
                )
            )

            # Put the delete button on the last visible card's action row to keep the layout compact
            if idx == len(visible_items) - 1:
                if len(self.items) > MAX_EMBEDS:
                    more_btn = discord.ui.Button(
                        label=f"\N{HEAVY PLUS SIGN} +{len(self.items) - MAX_EMBEDS} More Linked",
                        style=discord.ButtonStyle.primary,
                    )
                    more_btn.callback = self._make_open_ephemeral_callback(MAX_EMBEDS)
                    action_row.add_item(more_btn)

                delete_btn = discord.ui.Button(
                    emoji="\N{WASTEBASKET}",
                    style=discord.ButtonStyle.danger,
                )
                delete_btn.callback = self._on_delete
                action_row.add_item(delete_btn)

            container.add_item(action_row)
            self.add_item(container)

    def _make_open_ephemeral_callback(self, index: int):
        async def _callback(interaction: discord.Interaction) -> None:
            paginator = EphemeralIssuePaginator(self.items, initial_item_index=index)
            await interaction.response.send_message(view=paginator, ephemeral=True)

        return _callback

    async def _on_delete(self, interaction: discord.Interaction) -> None:
        is_author = interaction.user.id == self.author_id
        can_manage = (
            isinstance(interaction.user, discord.Member)
            and interaction.channel is not None
            and interaction.channel.permissions_for(interaction.user).manage_messages
        )
        if not (is_author or can_manage):
            await interaction.response.send_message(
                "Only the message author or a moderator can dismiss this preview.",
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        if interaction.message:
            with contextlib.suppress(discord.HTTPException):
                await interaction.message.delete()


class LinkToCodeblock(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.pattern_handlers: list[tuple[re.Pattern[str], Callable[..., Any]]] = [
            (GITHUB_RE, self._fetch_github_snippet),
            (GITHUB_GIST_RE, self._fetch_github_gist_snippet),
            (GITLAB_RE, self._fetch_gitlab_snippet),
            (BITBUCKET_RE, self._fetch_bitbucket_snippet),
        ]

        self.api_request_headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token:
            self.api_request_headers["Authorization"] = f"Bearer {token}"

        self._cache: dict[Target, tuple[float, IssueOrCommitData]] = {}
        self._replies: dict[int, list[discord.Message]] = {}

        _log.debug("Cog loaded: %s", self.__class__.__name__)

    def _track_reply(self, trigger_id: int, reply: discord.Message) -> None:
        self._replies.setdefault(trigger_id, []).append(reply)
        while len(self._replies) > 200:
            self._replies.pop(next(iter(self._replies)))

    async def _fetch_response(self, url: str, response_format: str, **kwargs: Any) -> Any:
        """Makes http requests using aiohttp."""
        async with self.bot.http_session.get(url, raise_for_status=True, **kwargs) as response:
            if response_format == "text":
                return await response.text()
            if response_format == "json":
                return await response.json()
        return None

    def _find_ref(self, path: str, refs: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> tuple[str, str]:
        """Loops through all branches and tags to find the required ref."""
        ref, file_path = path.split("/", 1)
        for possible_ref in refs:
            if path.startswith(possible_ref["name"] + "/"):
                ref = possible_ref["name"]
                file_path = path[len(ref) + 1 :]
                break
        return ref, file_path

    async def _fetch_github_snippet(
        self,
        source_url: str,
        repo: str,
        path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        """Fetches a snippet from a GitHub repo."""
        headers = dict(self.bot.http_session.headers)
        headers.update(_get_github_raw_headers())

        branches = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/branches",
            "json",
            headers=headers,
        )
        tags = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/tags",
            "json",
            headers=headers,
        )
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)

        file_contents = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}",
            "text",
            headers=headers,
        )
        return self._build_code_snippet(file_contents, file_path, source_url, start_line, end_line)

    async def _fetch_github_gist_snippet(
        self,
        source_url: str,
        gist_id: str,
        revision: str,
        file_path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        """Fetches a snippet from a GitHub gist."""
        headers = dict(self.bot.http_session.headers)
        headers.update(_get_github_raw_headers())

        gist_json: dict[str, Any] | None = await self._fetch_response(
            f"https://api.github.com/gists/{gist_id}{f'/{revision}' if revision != '' else ''}",
            "json",
            headers=headers,
        )
        if gist_json is None:
            return None

        for gist_file in gist_json["files"]:
            if file_path == gist_file.lower().replace(".", "-"):
                file_contents = await self._fetch_response(
                    gist_json["files"][gist_file]["raw_url"],
                    "text",
                )
                return self._build_code_snippet(file_contents, gist_file, source_url, start_line, end_line)
        return None

    async def _fetch_gitlab_snippet(
        self,
        source_url: str,
        repo: str,
        path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        """Fetches a snippet from a GitLab repo."""
        enc_repo = quote_plus(repo)

        branches = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/branches",
            "json",
        )
        tags = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/tags",
            "json",
        )
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)
        enc_ref = quote_plus(ref)
        enc_file_path = quote_plus(file_path)

        file_contents = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/files/{enc_file_path}/raw?ref={enc_ref}",
            "text",
        )
        return self._build_code_snippet(file_contents, file_path, source_url, start_line, end_line)

    async def _fetch_bitbucket_snippet(
        self,
        source_url: str,
        repo: str,
        ref: str,
        file_path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        """Fetches a snippet from a BitBucket repo."""
        file_contents = await self._fetch_response(
            f"https://bitbucket.org/{quote_plus(repo)}/raw/{quote_plus(ref)}/{quote_plus(file_path)}",
            "text",
        )
        return self._build_code_snippet(file_contents, file_path, source_url, start_line, end_line)

    def _build_code_snippet(
        self,
        file_contents: str | None,
        file_path: str,
        source_url: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        if not file_contents:
            return None

        if end_line is None:
            start = end = int(start_line or 0)
        else:
            start = int(start_line or 0)
            end = int(end_line)

        split_file_contents = file_contents.splitlines()
        if not split_file_contents:
            return None

        if start > end:
            start, end = end, start
        if start > len(split_file_contents) or end < 1:
            return None

        start = max(1, start)
        end = min(len(split_file_contents), end)

        language = file_path.rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[-1]
        trimmed_language = language.replace("-", "").replace("+", "").replace("_", "")
        if not trimmed_language.isalnum():
            language = ""

        return CodeSnippet(
            file_path=file_path,
            language=language,
            source_url=source_url,
            all_lines=split_file_contents,
            start_line=start,
            end_line=end,
        )

    async def _parse_snippets(self, content: str) -> list[CodeSnippet]:
        """Parse message content and return a sorted list of CodeSnippet objects."""
        all_snippets: list[tuple[int, CodeSnippet]] = []

        for pattern, handler in self.pattern_handlers:
            for match in pattern.finditer(content):
                try:
                    snippet = await handler(source_url=match.group(0), **match.groupdict())
                    if snippet is not None:
                        all_snippets.append((match.start(), snippet))
                except ClientResponseError:
                    pass

        all_snippets.sort(key=lambda pair: pair[0])
        return [pair[1] for pair in all_snippets]

    @commands.Cog.listener("on_message")
    async def on_message_codeblock(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        perms = message.channel.permissions_for(message.guild.me)
        if not perms.send_messages:
            return

        snippets = await self._parse_snippets(message.content)
        if not snippets:
            return

        view = CodeblockPublicView(snippets, author_id=message.author.id)
        content_to_send = view.build_initial_message()

        try:
            reply = await message.reply(
                content_to_send,
                view=view,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            return

        self._track_reply(message.id, reply)
        if SUPPRESS_ORIGINAL and perms.manage_messages:
            with contextlib.suppress(discord.HTTPException):
                await message.edit(suppress=True)

    async def _get(self, path: str) -> dict[str, Any]:
        async with self.bot.http_session.get(
            f"{API}{path}",
            headers=self.api_request_headers,
            raise_for_status=True,
        ) as resp:
            return await resp.json()

    async def _fetch_issue_data(self, repo: str, kind: str, number: int) -> IssueOrCommitData:
        if kind == "pull":
            data = await self._get(f"/repos/{repo}/pulls/{number}")
        else:
            data = await self._get(f"/repos/{repo}/issues/{number}")
            if "pull_request" in data:  # an /issues/N link that is really a PR
                data = await self._get(f"/repos/{repo}/pulls/{number}")
                kind = "pull"
        is_pr = kind == "pull"

        if data.get("merged"):
            state_label, state_emoji, colour = "Merged", "\N{LARGE PURPLE CIRCLE}", PURPLE
        elif data.get("draft"):
            state_label, state_emoji, colour = "Draft", "\N{MEDIUM WHITE CIRCLE}", GRAY
        elif data["state"] == "closed":
            state_label, state_emoji, colour = "Closed", "\N{LARGE RED CIRCLE}", RED
        else:
            state_label, state_emoji, colour = "Open", "\N{LARGE GREEN CIRCLE}", GREEN

        user = data.get("user") or {}
        labels = [lbl["name"] for lbl in data.get("labels", [])[:8]]

        return IssueOrCommitData(
            kind=kind,
            repo=repo,
            ident=str(number),
            title=data["title"],
            url=data["html_url"],
            body=data.get("body") or "",
            state_label=state_label,
            state_emoji=state_emoji,
            colour=colour,
            created_at=_ts(data["created_at"]),
            author_name=user.get("login", "unknown"),
            author_url=user.get("html_url"),
            author_avatar=user.get("avatar_url"),
            comments=data.get("comments", 0),
            additions=data.get("additions") if is_pr else None,
            deletions=data.get("deletions") if is_pr else None,
            changed_files=data.get("changed_files") if is_pr else None,
            labels=labels,
        )

    async def _fetch_commit_data(self, repo: str, sha: str) -> IssueOrCommitData:
        data = await self._get(f"/repos/{repo}/commits/{sha}")
        title, _, body = data["commit"]["message"].partition("\n")
        stats = data.get("stats") or {}
        gh_user = data.get("author") or {}

        return IssueOrCommitData(
            kind="commit",
            repo=repo,
            ident=data["sha"],
            title=title,
            url=data["html_url"],
            body=body,
            state_label="Commit",
            state_emoji="\N{HAMMER}",
            colour=BLUE,
            created_at=_ts(data["commit"]["author"]["date"]),
            author_name=gh_user.get("login") or data["commit"]["author"]["name"],
            author_url=gh_user.get("html_url"),
            author_avatar=gh_user.get("avatar_url"),
            additions=stats.get("additions", 0),
            deletions=stats.get("deletions", 0),
            changed_files=len(data.get("files", [])),
        )

    async def _data_for(self, target: Target) -> IssueOrCommitData | None:
        now = time.monotonic()
        hit = self._cache.get(target)
        if hit and now - hit[0] < CACHE_TTL:
            return hit[1]

        kind, repo, ident = target
        try:
            if kind == "commit":
                item = await self._fetch_commit_data(repo, ident)
            else:
                item = await self._fetch_issue_data(repo, kind, int(ident))
        except ClientResponseError as exc:
            if exc.status in (403, 429):
                _log.warning("GitHub rate limit hit while fetching %s", target)
            return None

        self._cache[target] = (now, item)
        while len(self._cache) > CACHE_SIZE:
            self._cache.pop(next(iter(self._cache)))
        return item

    @staticmethod
    def _find_targets(content: str) -> list[Target]:
        found: dict[Target, int] = {}
        for m in ISSUE_RE.finditer(content):
            found.setdefault((m["kind"].lower(), m["repo"].lower(), m["number"]), m.start())
        for m in COMMIT_RE.finditer(content):
            found.setdefault(("commit", m["repo"].lower(), m["sha"].lower()), m.start())
        return sorted(found, key=found.__getitem__)

    @commands.Cog.listener("on_message")
    async def on_message_issue(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        targets = self._find_targets(message.content)
        if not targets:
            return

        perms = message.channel.permissions_for(message.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return

        # Fetch up to 10 targets so the user can page through all of them ephemerally,
        # while rendering the first MAX_EMBEDS (3) cards directly in the public LayoutView.
        results = await asyncio.gather(*(self._data_for(t) for t in targets[:10]))
        items = [item for item in results if item is not None]
        if not items:
            return

        layout_view = IssuePublicLayoutView(items, author_id=message.author.id)

        try:
            reply = await message.reply(
                view=layout_view,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            return

        self._track_reply(message.id, reply)
        if SUPPRESS_ORIGINAL and perms.manage_messages:
            with contextlib.suppress(discord.HTTPException):
                await message.edit(suppress=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """If the user deletes their message, delete our codeblock/issue replies too."""
        replies = self._replies.pop(message.id, None)
        if replies:
            for reply in replies:
                with contextlib.suppress(discord.HTTPException):
                    await reply.delete()
