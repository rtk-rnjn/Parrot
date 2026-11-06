from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from datetime import datetime

from .utils import CODE_PAGE_CHAR_LIMIT, CODE_PAGE_LINE_LIMIT, ISSUE_PAGE_CHAR_LIMIT, _paginate_markdown


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
            safe_line = raw_line.replace("`", "`\u200b")
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
        mode_tag = f" (Full File | {self.total_lines} lines)" if full_file else ""
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


@dataclass(slots=True)
class CVERecord:
    cve_id: str
    summary: str
    published: datetime | None = None
    cvss: float | None = None
    cvss_version: str | None = None
    epss: float | None = None
    ranking_epss: float | None = None
    is_kev: bool = False
    ransomware_campaign: str | None = None
    proposed_action: str | None = None
    cwe_ids: list[str] = field(default_factory=list)
    cpes: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    assigner: str | None = None
    state: str = "PUBLISHED"
    credits: list[str] = field(default_factory=list)
    affected_products: list[str] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)

    @property
    def nvd_url(self) -> str:
        return f"https://nvd.nist.gov/vuln/detail/{self.cve_id}"

    @property
    def mitre_url(self) -> str:
        return f"https://www.cve.org/CVERecord?id={self.cve_id}"

    @property
    def shodan_url(self) -> str:
        return f"https://cvedb.shodan.io/cve/{self.cve_id}"

    def build_full_pages(self) -> list[str]:
        """Build detailed markdown pages for the ephemeral CVE inspector."""
        sections: list[str] = [f"**Description**\n{self.summary or '*No summary available.*'}"]

        if self.proposed_action:
            sections.append(f"**Recommended Mitigation / CISA Action**\n{self.proposed_action}")

        if self.affected_products:
            prod_lines = "\n".join(f"- `{p}`" for p in self.affected_products[:25])
            sections.append(f"**Affected Vendor / Product Versions**\n{prod_lines}")

        if self.cpes:
            cpe_lines = "\n".join(f"- `{c}`" for c in self.cpes[:25])
            extra = f"\n-# *...and {len(self.cpes) - 25} more CPEs*" if len(self.cpes) > 25 else ""
            sections.append(f"**Affected CPE 2.3 Identifiers ({len(self.cpes)})**\n{cpe_lines}{extra}")

        if self.credits:
            credit_lines = ", ".join(f"`{c}`" for c in self.credits[:10])
            sections.append(f"**Discovery / Advisory Credits**\n{credit_lines}")

        if self.references:
            ref_lines = "\n".join(f"- <{ref}>" for ref in self.references[:20])
            extra = f"\n-# *...and {len(self.references) - 20} more references*" if len(self.references) > 20 else ""
            sections.append(f"**References & Advisories ({len(self.references)})**\n{ref_lines}{extra}")

        return _paginate_markdown("\n\n".join(sections), limit=ISSUE_PAGE_CHAR_LIMIT)


@dataclass(slots=True)
class SecurityNewsItem:
    title: str
    url: str
    summary: str
    source_name: str
    published: datetime | None = None
    cve_ids: list[str] = field(default_factory=list)
    is_kev_alert: bool = False
    vendor_product: str | None = None
    due_date: str | None = None
    ransomware_use: str | None = None
