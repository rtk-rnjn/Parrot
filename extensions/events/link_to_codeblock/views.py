from __future__ import annotations

import contextlib

import discord

from .models import CodeSnippet, CVERecord, IssueOrCommitData, SecurityNewsItem
from .utils import BLUE, DARK_RED, DISCORD_MESSAGE_LIMIT, ISSUE_PAGE_CHAR_LIMIT, MAX_EMBEDS, VIEW_TIMEOUT, _cvss_Appearance, _paginate_markdown, _trim


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
                    label=(f"{idx + 1}. {s.short_name} (L{s.start_line}-L{s.end_line})"[:100]),
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
            self.mode_btn.label = f"Snippet Only (L{snippet.start_line}-L{snippet.end_line})"
            self.mode_btn.style = discord.ButtonStyle.primary
        else:
            self.mode_btn.label = f"Show Full File ({snippet.total_lines} lines)"
            self.mode_btn.style = discord.ButtonStyle.secondary

        self.lineno_btn.label = "Hide Line #" if self.line_numbers else "Show Line #"
        self.lineno_btn.style = discord.ButtonStyle.success if self.line_numbers else discord.ButtonStyle.secondary

        if self._SelectComponent is not None:
            for opt in self._SelectComponent.options:
                opt.default = opt.value == str(self.snippet_index)

    def current_content(self) -> str:
        header_parts: list[str] = []
        if len(self.snippets) > 1:
            header_parts.append(f"**File {self.snippet_index + 1}/{len(self.snippets)}**")
        header_parts.append(f"[Jump to Source](<{self.current_snippet.source_url}>)")
        prefix = " | ".join(header_parts)
        return f"-# {prefix}\n{self.pages[self.page_index]}"

    async def _on_select_snippet(self, interaction: discord.Interaction) -> None:
        if self._SelectComponent and self._SelectComponent.values:
            self.snippet_index = int(self._SelectComponent.values[0])
            self.page_index = 0
            self._rebuild_pages()
            await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="<<", style=discord.ButtonStyle.secondary, row=0)
    async def first_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = 0
        self._sync_components()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = max(0, self.page_index - 1)
        self._sync_components()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(
        label="Page 1/1",
        style=discord.ButtonStyle.secondary,
        disabled=True,
        row=0,
    )
    async def page_indicator(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer()

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary, row=0)
    async def next_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = min(len(self.pages) - 1, self.page_index + 1)
        self._sync_components()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary, row=0)
    async def last_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = len(self.pages) - 1
        self._sync_components()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="Show Full File", style=discord.ButtonStyle.secondary, row=1)
    async def mode_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.full_file = not self.full_file
        self.page_index = 0
        self._rebuild_pages()
        await interaction.response.edit_message(content=self.current_content(), view=self)

    @discord.ui.button(label="Show Line #", style=discord.ButtonStyle.secondary, row=1)
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
            self.paginate_btn.label = f"Browse All Code ({len(snippets)} file{'s' if len(snippets) > 1 else ''}, {total_snippet_pages} pages)"
            self.paginate_btn.style = discord.ButtonStyle.primary
        else:
            self.paginate_btn.label = "Interactive Viewer"
            self.paginate_btn.style = discord.ButtonStyle.secondary

        first_total_lines = snippets[0].total_lines
        self.full_file_btn.label = f"Full File ({first_total_lines} lines)"

        self.add_item(
            discord.ui.Button(
                label="Source",
                style=discord.ButtonStyle.link,
                url=snippets[0].source_url,
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
        note_text = f"-# *Snippet truncated ({', '.join(notes)}) - click **Browse All Code** below to page through everything.*"
        return f"{first_page}\n{note_text}"

    @discord.ui.button(label="Browse All Code", style=discord.ButtonStyle.primary)
    async def paginate_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        paginator = EphemeralCodePaginator(self.snippets, full_file=False, line_numbers=False)
        await interaction.response.send_message(
            content=paginator.current_content(),
            view=paginator,
            ephemeral=True,
        )

    @discord.ui.button(label="Full File", style=discord.ButtonStyle.secondary)
    async def full_file_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        paginator = EphemeralCodePaginator(self.snippets, full_file=True, line_numbers=True)
        await interaction.response.send_message(
            content=paginator.current_content(),
            view=paginator,
            ephemeral=True,
        )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
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
    state_prefix = f"{item.state_emoji} " if item.state_emoji else ""
    header_md = (
        f"### {state_prefix}[{item.display_title}]({item.url})\n"
        f"-# By {author_md} in [**{item.repo}**](https://github.com/{item.repo})"
        f" | <t:{unix_ts}:R>"
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
        stats_parts.append(f"**Comments:** `{item.comments}`")
    if item.additions is not None and item.deletions is not None:
        files_count = item.changed_files or 0
        stats_parts.append(f"**Changes:** `+{item.additions} -{item.deletions}` (`{files_count}` files)")
    if page_label:
        stats_parts.append(f"**Page:** `{page_label}`")

    meta_lines = ["  |  ".join(stats_parts)]
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
            label="<<",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index <= 0),
        )
        first_btn.callback = self._on_first

        prev_btn = discord.ui.Button(
            label="<",
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
            label=">",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index >= total_pages - 1),
        )
        next_btn.callback = self._on_next

        last_btn = discord.ui.Button(
            label=">>",
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
                label="Full Details / Paginate",
                style=discord.ButtonStyle.secondary,
            )
            read_btn.callback = self._make_open_ephemeral_callback(idx)
            action_row.add_item(read_btn)

            action_row.add_item(
                discord.ui.Button(
                    label="View on GitHub",
                    style=discord.ButtonStyle.link,
                    url=item.url,
                )
            )

            # Put the delete button on the last visible card's action row to keep the layout compact
            if idx == len(visible_items) - 1:
                if len(self.items) > MAX_EMBEDS:
                    more_btn = discord.ui.Button(
                        label=f"+{len(self.items) - MAX_EMBEDS} More Linked",
                        style=discord.ButtonStyle.primary,
                    )
                    more_btn.callback = self._make_open_ephemeral_callback(MAX_EMBEDS)
                    action_row.add_item(more_btn)

                delete_btn = discord.ui.Button(
                    label="Delete",
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


def _build_cve_container(
    record: CVERecord,
    *,
    body_text: str | None = None,
    page_label: str | None = None,
) -> discord.ui.Container:
    """Build a styled Components V2 Container for a CVERecord."""
    sev_label, sev_tag, colour = _cvss_Appearance(record.cvss, is_kev=record.is_kev)
    container = discord.ui.Container(accent_colour=discord.Colour(colour))

    pub_str = f" | Published <t:{int(record.published.timestamp())}:R>" if record.published else ""
    assigner_str = f" | CNA: `{record.assigner}`" if record.assigner else ""
    sources_str = f" | Sources: `{', '.join(record.sources_used)}`" if record.sources_used else ""

    badges: list[str] = [f"`{sev_label}`"]
    if record.is_kev:
        badges.append("`CISA KEV (Actively Exploited)`")
    if record.ransomware_campaign and record.ransomware_campaign.lower() not in (
        "unknown",
        "none",
    ):
        badges.append(f"`Ransomware: {record.ransomware_campaign}`")
    if record.state and record.state.upper() != "PUBLISHED":
        badges.append(f"`State: {record.state.upper()}`")

    tag_prefix = f"{sev_tag} " if sev_tag else ""
    header_md = (
        f"### {tag_prefix}[{record.cve_id}]({record.nvd_url}) -"
        f" {' '.join(badges)}\n-# [NVD]({record.nvd_url}) |"
        f" [MITRE]({record.mitre_url}) | [Shodan CVEDB]({record.shodan_url})"
        f"{assigner_str}{pub_str}{sources_str}"
    )

    section = discord.ui.Section(
        discord.ui.TextDisplay(header_md),
        accessory=discord.ui.Button(
            label="NVD Advisory",
            style=discord.ButtonStyle.link,
            url=record.nvd_url,
        ),
    )
    container.add_item(section)
    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    display_body = body_text if body_text is not None else (_trim(record.summary, limit=420) or "*No description available.*")
    container.add_item(discord.ui.TextDisplay(display_body))
    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    # Metrics bar (CVSS, EPSS, CWE, CPE count)
    metrics: list[str] = []
    if record.cvss is not None:
        ver = f" ({record.cvss_version})" if record.cvss_version else ""
        metrics.append(f"**CVSS{ver}:** `{record.cvss:.1f}/10.0`")
    else:
        metrics.append("**CVSS:** `N/A`")

    if record.epss is not None:
        pct = f" (top {(1.0 - record.ranking_epss) * 100:.1f}%)" if record.ranking_epss is not None else ""
        metrics.append(f"**EPSS (30d):** `{record.epss * 100:.2f}%`{pct}")

    if record.cwe_ids:
        metrics.append(f"**CWE:** {', '.join(f'`{c}`' for c in record.cwe_ids[:4])}")

    if record.cpes:
        metrics.append(f"**Affected CPEs:** `{len(record.cpes)}`")

    if page_label:
        metrics.append(f"**Page:** `{page_label}`")

    container.add_item(discord.ui.TextDisplay("-# " + "  |  ".join(metrics)))
    return container


class EphemeralCVEPaginator(discord.ui.LayoutView):
    """Ephemeral Components V2 LayoutView for paging through CVE records and their full technical details."""

    def __init__(self, records: list[CVERecord], *, initial_index: int = 0) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.records = records
        self.record_index = initial_index
        self.page_index = 0
        self.detail_pages: list[str] = []
        self._rebuild_layout()

    @property
    def current_record(self) -> CVERecord:
        return self.records[self.record_index]

    def _rebuild_layout(self) -> None:
        self.clear_items()
        rec = self.current_record
        self.detail_pages = rec.build_full_pages()
        self.page_index = max(0, min(self.page_index, len(self.detail_pages) - 1))
        total_pages = len(self.detail_pages)

        container = _build_cve_container(
            rec,
            body_text=self.detail_pages[self.page_index],
            page_label=(f"{self.page_index + 1}/{total_pages} (CVE {self.record_index + 1}/{len(self.records)})"),
        )

        # Page navigation row (for long CVE descriptions, CPEs, and references)
        nav_row = discord.ui.ActionRow()

        first_btn = discord.ui.Button(
            label="<<",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index <= 0),
        )
        first_btn.callback = self._on_first

        prev_btn = discord.ui.Button(
            label="<",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index <= 0),
        )
        prev_btn.callback = self._on_prev

        page_btn = discord.ui.Button(
            label=f"Detail Page {self.page_index + 1}/{total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )

        next_btn = discord.ui.Button(
            label=">",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index >= total_pages - 1),
        )
        next_btn.callback = self._on_next

        last_btn = discord.ui.Button(
            label=">>",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page_index >= total_pages - 1),
        )
        last_btn.callback = self._on_last

        for btn in (first_btn, prev_btn, page_btn, next_btn, last_btn):
            nav_row.add_item(btn)
        container.add_item(nav_row)

        # Dropdown selector when multiple CVEs are loaded (e.g., from /cve search or /cve latest)
        if len(self.records) > 1:
            select_row = discord.ui.ActionRow()
            options: list[discord.SelectOption] = []
            for idx, r in enumerate(self.records[:25]):
                sev_label, _, _ = _cvss_Appearance(r.cvss, is_kev=r.is_kev)
                score_txt = f"CVSS {r.cvss:.1f}" if r.cvss is not None else sev_label
                epss_txt = f" | EPSS {r.epss * 100:.1f}%" if r.epss is not None else ""
                options.append(
                    discord.SelectOption(
                        label=f"{idx + 1}. {r.cve_id} ({score_txt}{epss_txt})"[:100],
                        description=(r.summary or "No summary")[:100],
                        value=str(idx),
                        default=(idx == self.record_index),
                    )
                )
            select: discord.ui.Select = discord.ui.Select(
                placeholder=(f"Switch CVE ({self.record_index + 1}/{min(len(self.records), 25)})..."),
                options=options,
            )
            select.callback = self._on_select_cve
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
        self.page_index = min(len(self.detail_pages) - 1, self.page_index + 1)
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_last(self, interaction: discord.Interaction) -> None:
        self.page_index = len(self.detail_pages) - 1
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_select_cve(self, interaction: discord.Interaction) -> None:
        values = interaction.data.get("values") if interaction.data else None
        if values:
            self.record_index = int(values[0])
            self.page_index = 0
            self._rebuild_layout()
            await interaction.response.edit_message(view=self)


class CVEPublicLayoutView(discord.ui.LayoutView):
    """Public Components V2 LayoutView showing 1-3 CVE cards with ephemeral full-detail / multi-CVE paging."""

    def __init__(
        self,
        records: list[CVERecord],
        author_id: int,
        *,
        heading: str | None = None,
    ) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.records = records
        self.author_id = author_id
        self.heading = heading
        self._build_cards()

    def _build_cards(self) -> None:
        self.clear_items()
        if self.heading:
            self.add_item(discord.ui.TextDisplay(self.heading))

        visible = self.records[:MAX_EMBEDS]
        for idx, rec in enumerate(visible):
            container = _build_cve_container(rec)

            action_row = discord.ui.ActionRow()
            inspect_btn = discord.ui.Button(
                label=(f"Inspect & Page All ({len(self.records)} CVEs)" if len(self.records) > 1 else "Full Advisory, CPEs & Refs"),
                style=(discord.ButtonStyle.primary if idx == 0 else discord.ButtonStyle.secondary),
            )
            inspect_btn.callback = self._make_inspect_callback(idx)
            action_row.add_item(inspect_btn)

            action_row.add_item(
                discord.ui.Button(
                    label="MITRE",
                    style=discord.ButtonStyle.link,
                    url=rec.mitre_url,
                )
            )
            action_row.add_item(
                discord.ui.Button(
                    label="Shodan CVEDB",
                    style=discord.ButtonStyle.link,
                    url=rec.shodan_url,
                )
            )

            if idx == len(visible) - 1:
                delete_btn = discord.ui.Button(
                    label="Delete",
                    style=discord.ButtonStyle.danger,
                )
                delete_btn.callback = self._on_delete
                action_row.add_item(delete_btn)

            container.add_item(action_row)
            self.add_item(container)

    def _make_inspect_callback(self, index: int):
        async def _callback(interaction: discord.Interaction) -> None:
            paginator = EphemeralCVEPaginator(self.records, initial_index=index)
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
                "Only the command user or a moderator can dismiss this CVE card.",
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        if interaction.message:
            with contextlib.suppress(discord.HTTPException):
                await interaction.message.delete()


def _build_news_container(
    item: SecurityNewsItem,
    *,
    full_text: bool = False,
    page_label: str | None = None,
) -> discord.ui.Container:
    """Build a Components V2 Container for a cybersecurity news article or CISA KEV alert."""
    colour = DARK_RED if item.is_kev_alert else BLUE
    badge_tag = "[KEV]" if item.is_kev_alert else "[NEWS]"
    container = discord.ui.Container(accent_colour=discord.Colour(colour))

    pub_str = f" | <t:{int(item.published.timestamp())}:R>" if item.published else ""
    header_md = f"### {badge_tag} [{item.title[:220]}]({item.url})\n-# **{item.source_name}**{pub_str}"

    section = discord.ui.Section(
        discord.ui.TextDisplay(header_md),
        accessory=discord.ui.Button(
            label="Read Source",
            style=discord.ButtonStyle.link,
            url=item.url,
        ),
    )
    container.add_item(section)
    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    body = item.summary if full_text else _trim(item.summary, limit=380)
    container.add_item(discord.ui.TextDisplay(body or "*No summary available.*"))

    meta_tags: list[str] = []
    if item.vendor_product:
        meta_tags.append(f"**Target:** `{item.vendor_product}`")
    if item.due_date:
        meta_tags.append(f"**CISA Due Date:** `{item.due_date}`")
    if item.ransomware_use:
        meta_tags.append(f"**Ransomware:** `{item.ransomware_use}`")
    if item.cve_ids:
        linked_cves = ", ".join(f"[`{c}`](https://nvd.nist.gov/vuln/detail/{c})" for c in item.cve_ids[:5])
        meta_tags.append(f"**Mentioned CVEs:** {linked_cves}")
    if page_label:
        meta_tags.append(f"**Item:** `{page_label}`")

    if meta_tags:
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay("-# " + "  |  ".join(meta_tags)))

    return container


class EphemeralNewsPaginator(discord.ui.LayoutView):
    """Ephemeral Components V2 paginator for browsing cybersecurity news and CISA KEV advisories."""

    def __init__(self, items: list[SecurityNewsItem], *, initial_index: int = 0) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.items = items
        self.index = initial_index
        self._rebuild_layout()

    def _rebuild_layout(self) -> None:
        self.clear_items()
        total = len(self.items)
        self.index = max(0, min(self.index, total - 1))
        current = self.items[self.index]

        container = _build_news_container(
            current,
            full_text=True,
            page_label=f"{self.index + 1}/{total}",
        )

        nav_row = discord.ui.ActionRow()
        first_btn = discord.ui.Button(
            label="<<",
            style=discord.ButtonStyle.secondary,
            disabled=(self.index <= 0),
        )
        first_btn.callback = self._on_first

        prev_btn = discord.ui.Button(
            label="<",
            style=discord.ButtonStyle.secondary,
            disabled=(self.index <= 0),
        )
        prev_btn.callback = self._on_prev

        page_btn = discord.ui.Button(
            label=f"Article {self.index + 1}/{total}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )

        next_btn = discord.ui.Button(
            label=">",
            style=discord.ButtonStyle.secondary,
            disabled=(self.index >= total - 1),
        )
        next_btn.callback = self._on_next

        last_btn = discord.ui.Button(
            label=">>",
            style=discord.ButtonStyle.secondary,
            disabled=(self.index >= total - 1),
        )
        last_btn.callback = self._on_last

        for btn in (first_btn, prev_btn, page_btn, next_btn, last_btn):
            nav_row.add_item(btn)
        container.add_item(nav_row)

        if len(self.items) > 1:
            select_row = discord.ui.ActionRow()
            options = [
                discord.SelectOption(
                    label=f"{idx + 1}. {it.title}"[:100],
                    description=f"{it.source_name}"[:100],
                    value=str(idx),
                    default=(idx == self.index),
                )
                for idx, it in enumerate(self.items[:25])
            ]
            select: discord.ui.Select = discord.ui.Select(
                placeholder="Jump to news article / KEV alert...",
                options=options,
            )
            select.callback = self._on_select
            select_row.add_item(select)
            container.add_item(select_row)

        self.add_item(container)

    async def _on_first(self, interaction: discord.Interaction) -> None:
        self.index = 0
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_prev(self, interaction: discord.Interaction) -> None:
        self.index = max(0, self.index - 1)
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_next(self, interaction: discord.Interaction) -> None:
        self.index = min(len(self.items) - 1, self.index + 1)
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_last(self, interaction: discord.Interaction) -> None:
        self.index = len(self.items) - 1
        self._rebuild_layout()
        await interaction.response.edit_message(view=self)

    async def _on_select(self, interaction: discord.Interaction) -> None:
        values = interaction.data.get("values") if interaction.data else None
        if values:
            self.index = int(values[0])
            self._rebuild_layout()
            await interaction.response.edit_message(view=self)


class NewsPublicLayoutView(discord.ui.LayoutView):
    """Public Components V2 LayoutView showing top security news & CISA KEV items with ephemeral paging."""

    def __init__(
        self,
        items: list[SecurityNewsItem],
        author_id: int,
        *,
        heading: str | None = None,
    ) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.items = items
        self.author_id = author_id
        self.heading = heading
        self._build_cards()

    def _build_cards(self) -> None:
        self.clear_items()
        if self.heading:
            self.add_item(discord.ui.TextDisplay(self.heading))

        visible = self.items[:MAX_EMBEDS]
        for idx, item in enumerate(visible):
            container = _build_news_container(item, full_text=False)
            action_row = discord.ui.ActionRow()

            browse_btn = discord.ui.Button(
                label=f"Browse All News ({len(self.items)} items)",
                style=(discord.ButtonStyle.primary if idx == 0 else discord.ButtonStyle.secondary),
            )
            browse_btn.callback = self._make_browse_callback(idx)
            action_row.add_item(browse_btn)

            if idx == len(visible) - 1:
                delete_btn = discord.ui.Button(label="Delete", style=discord.ButtonStyle.danger)
                delete_btn.callback = self._on_delete
                action_row.add_item(delete_btn)

            container.add_item(action_row)
            self.add_item(container)

    def _make_browse_callback(self, index: int):
        async def _callback(interaction: discord.Interaction) -> None:
            paginator = EphemeralNewsPaginator(self.items, initial_index=index)
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
                "Only the command user or a moderator can dismiss this news digest.",
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        if interaction.message:
            with contextlib.suppress(discord.HTTPException):
                await interaction.message.delete()
