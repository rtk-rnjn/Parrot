from __future__ import annotations

import contextlib
import logging
import os
import random as randomlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

if TYPE_CHECKING:
    from core import Bot

log = logging.getLogger(__name__)
load_dotenv()

PURPLE, GREEN, RED, GOLD, BLUE = 0x8E44AD, 0x2ECC71, 0xE74C3C, 0xF1C40F, 0x3498DB
VIEW_TIMEOUT = 300

API_BASE = "https://api.imgflip.com"
FONTS: list[tuple[str, str, str]] = [
    ("impact", "Impact (Classic)", "Classic bold meme font"),
    ("arial", "Arial", "Clean sans-serif font"),
    ("comic-sans-ms", "Comic Sans MS", "Playful casual font"),
    ("helvetica", "Helvetica", "Modern neutral sans-serif"),
    ("times-new-roman", "Times New Roman", "Classic serif font"),
    ("montserrat", "Montserrat", "Geometric modern sans-serif"),
    ("roboto", "Roboto", "Crisp UI sans-serif"),
    ("oswald", "Oswald", "Tall condensed headline font"),
    ("anton", "Anton", "Heavy display headline font"),
    ("bebas-neue", "Bebas Neue", "All-caps clean display font"),
]
COLOR_PRESETS: list[tuple[str, str, str, str]] = [
    ("classic", "Classic White / Black outline", "#ffffff", "#000000"),
    ("black", "Pure Black / White outline", "#000000", "#ffffff"),
    ("yellow", "Yellow / Black outline", "#ffff00", "#000000"),
    ("red", "Red / Black outline", "#ff3b30", "#000000"),
    ("cyan", "Cyan / Black outline", "#00ffff", "#000000"),
    ("green", "Lime Green / Black outline", "#34c759", "#000000"),
]
WATERMARK_POSITIONS: list[tuple[str, str]] = [
    ("bottom-left", "Bottom Left (Default)"),
    ("bottom-right", "Bottom Right"),
    ("top-left", "Top Left"),
    ("top-right", "Top Right"),
]

DISCLAIMER = "-# Powered by the free Imgflip Meme Generator API (imgflip.com/api)."


class MemeError(Exception):
    """User-facing error raised by the Meme cog."""


def esc(s: Any) -> str:
    return discord.utils.escape_mentions(discord.utils.escape_markdown(str(s)))


def clip(s: Any, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"


def split_captions(raw: str) -> list[str]:
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|")]
    elif ";" in raw:
        parts = [p.strip() for p in raw.split(";")]
    elif "\n" in raw:
        parts = [p.strip() for p in raw.splitlines()]
    else:
        parts = [raw.strip()]
    return [p for p in parts if p] or [""]


def parse_quick_args(raw: str) -> tuple[str | None, list[str]]:
    if not raw.strip():
        return None, []
    if "|" in raw:
        chunks = [c.strip() for c in raw.split("|")]
        return chunks[0] or None, [c for c in chunks[1:] if c]
    if ";" in raw:
        chunks = [c.strip() for c in raw.split(";")]
        return chunks[0] or None, [c for c in chunks[1:] if c]
    return raw.strip(), []


def sep(visible: bool = True) -> discord.ui.Separator:
    return discord.ui.Separator(visible=visible, spacing=discord.SeparatorSpacing.small)


def text(s: str) -> discord.ui.TextDisplay:
    return discord.ui.TextDisplay(clip(s, 3900))


def head(s: str, thumb: str | None = None) -> discord.ui.Item:
    if thumb:
        return discord.ui.Section(text(s), accessory=discord.ui.Thumbnail(thumb))
    return text(s)


def gallery(*urls: str | None) -> discord.ui.MediaGallery | None:
    items = [discord.MediaGalleryItem(u) for u in urls if u]
    return discord.ui.MediaGallery(*items) if items else None


def button(
    label: str | None,
    on_click: Callable[[discord.Interaction], Awaitable[None]] | None = None,
    *,
    url: str | None = None,
    emoji: str | None = None,
    style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    disabled: bool = False,
) -> discord.ui.Button:
    if url:
        return discord.ui.Button(label=label, url=url, emoji=emoji)
    b = discord.ui.Button(label=label, emoji=emoji, disabled=disabled, style=style)
    if on_click:
        b.callback = on_click  # type: ignore[assignment]
    return b


def select(
    options: list[discord.SelectOption],
    on_select: Callable[[discord.Interaction, str], Awaitable[None]],
    placeholder: str,
) -> discord.ui.Select:
    sel = discord.ui.Select(placeholder=clip(placeholder, 150), options=options[:25])

    async def cb(interaction: discord.Interaction) -> None:
        await on_select(interaction, sel.values[0])

    sel.callback = cb
    return sel


def opt(
    label: str,
    value: str,
    *,
    desc: str | None = None,
    emoji: str | None = None,
    default: bool = False,
) -> discord.SelectOption:
    return discord.SelectOption(
        label=clip(label, 100),
        value=clip(value, 100),
        emoji=emoji,
        default=default,
        description=clip(desc, 100) if desc else None,
    )


@dataclass
class MemeTemplate:
    id: str
    name: str
    url: str
    width: int = 500
    height: int = 500
    box_count: int = 2
    captions: int = 0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemeTemplate:
        return cls(
            id=str(d["id"]),
            name=str(d.get("name", f"Template #{d['id']}")),
            url=str(d.get("url", "")),
            width=int(d.get("width", 500)),
            height=int(d.get("height", 500)),
            box_count=max(1, int(d.get("box_count", 2))),
            captions=int(d.get("captions", 0)),
        )


@dataclass
class GeneratedMeme:
    url: str
    page_url: str
    template: MemeTemplate
    boxes: list[str] = field(default_factory=list)


class QueryModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        title: str,
        label: str,
        placeholder: str,
        on_query: Callable[[discord.Interaction, str], Awaitable[None]],
        default: str | None = None,
        max_length: int = 120,
    ) -> None:
        super().__init__(title=clip(title, 45), timeout=VIEW_TIMEOUT)
        self.field = discord.ui.TextInput(
            label=clip(label, 45),
            placeholder=clip(placeholder, 100),
            default=default,
            max_length=max_length,
            required=True,
        )
        self.add_item(discord.ui.Label(text=clip(label, 45), component=self.field))
        self._on_query = on_query

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._on_query(interaction, self.field.value.strip())


class UploadTemplateModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        on_upload: Callable[[discord.Interaction, str, str, str], Awaitable[None]],
    ) -> None:
        super().__init__(title="Upload Public Template", timeout=VIEW_TIMEOUT)
        self.name_input = discord.ui.TextInput(
            label="Template Name",
            placeholder="Surprised Cat",
            max_length=64,
            required=True,
        )
        self.url_input = discord.ui.TextInput(
            label="Direct Image URL (https://...)",
            placeholder="https://example.com/my-template.png",
            max_length=400,
            required=True,
        )
        self.alt_input = discord.ui.TextInput(
            label="Alternate Names (optional, comma-separated)",
            placeholder="shocked cat, wide eyed cat",
            max_length=200,
            required=False,
        )
        self.add_item(discord.ui.Label(text="Template Name", component=self.name_input))
        self.add_item(discord.ui.Label(text="Direct Image URL", component=self.url_input))
        self.add_item(discord.ui.Label(text="Alternate Names", component=self.alt_input))
        self._on_upload = on_upload

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._on_upload(
            interaction,
            self.name_input.value.strip(),
            self.url_input.value.strip(),
            self.alt_input.value.strip(),
        )


class CaptionModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        template: MemeTemplate,
        current_boxes: list[str],
        start_index: int,
        on_save: Callable[[discord.Interaction, list[str], bool], Awaitable[None]],
        auto_generate: bool = True,
    ) -> None:
        end_idx = min(template.box_count, start_index + 5)
        title_suffix = f" ({start_index + 1}-{end_idx})" if template.box_count > 5 else ""
        super().__init__(
            title=clip(f"Caption: {template.name}{title_suffix}", 45),
            timeout=VIEW_TIMEOUT,
        )
        self.template = template
        self.current_boxes = list(current_boxes)
        self.start_index = start_index
        self.auto_generate = auto_generate
        self._on_save = on_save
        self.inputs: list[tuple[int, discord.ui.TextInput]] = []

        count = min(5, max(1, template.box_count - start_index))
        for offset in range(count):
            idx = start_index + offset
            default_val = self.current_boxes[idx] if idx < len(self.current_boxes) else ""
            if template.box_count == 2 and idx == 0:
                text_label = "Top Text (Box 1)"
            elif template.box_count == 2 and idx == 1:
                text_label = "Bottom Text (Box 2)"
            else:
                text_label = f"Box #{idx + 1} Text"
            text_input_field = discord.ui.TextInput(
                label=clip(text_label, 45),
                placeholder=f"Enter caption for box #{idx + 1}...",
                default=default_val,
                max_length=200,
                required=(idx == 0 and start_index == 0),
                style=discord.TextStyle.short,
            )
            self.inputs.append((idx, text_input_field))
            self.add_item(text_input_field)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        updated = list(self.current_boxes)
        while len(updated) < self.template.box_count:
            updated.append("")
        for idx, inp in self.inputs:
            updated[idx] = inp.value.strip()
        await self._on_save(interaction, updated, self.auto_generate)


class BaseView(discord.ui.LayoutView):
    """Owner-locked Components V2 view."""

    def __init__(self, cog: Meme, user_id: int) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.cog, self.user_id = cog, user_id
        self.message: discord.Message | None = None

    def render(self) -> None:
        raise NotImplementedError

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message(
            "These controls belong to whoever ran the command. Run it yourself!",
            ephemeral=True,
        )
        return False

    async def run(
        self,
        interaction: discord.Interaction,
        fn: Callable[..., Awaitable[Any]] | None = None,
        *a: Any,
        **kw: Any,
    ) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer()
        try:
            if fn:
                await fn(*a, **kw)
        except MemeError as e:
            await interaction.followup.send(f"\N{CROSS MARK} {e}", ephemeral=True)
            return
        self.render()
        await interaction.edit_original_response(view=self)

    def modal_button(
        self,
        label: str,
        emoji: str,
        /,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        **modal_kw: Any,
    ) -> discord.ui.Button:
        async def click(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(QueryModal(**modal_kw))

        return button(label, click, emoji=emoji, style=style)

    async def on_timeout(self) -> None:
        for item in self.walk_children():
            if isinstance(item, (discord.ui.Button, discord.ui.Select)) and not getattr(item, "url", None):
                item.disabled = True
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)


class MemeStudioView(BaseView):
    TABS = [  # noqa: RUF012
        ("studio", "Studio", "\N{ARTIST PALETTE}"),
        ("style", "Font & Style", "\N{LOWER LEFT FOUNTAIN PEN}\N{VARIATION SELECTOR-16}"),
        ("browse", "Templates", "\N{CARD INDEX DIVIDERS}\N{VARIATION SELECTOR-16}"),
    ]

    def __init__(
        self,
        cog: Meme,
        user_id: int,
        templates: list[MemeTemplate],
        selected: MemeTemplate,
        *,
        boxes: list[str] | None = None,
        generated: GeneratedMeme | None = None,
        query: str | None = None,
    ) -> None:
        super().__init__(cog, user_id)
        self.templates = templates
        self.template = selected
        self.boxes: list[str] = list(boxes) if boxes else [""] * selected.box_count
        self._sync_boxes()
        self.generated = generated
        self.query = query
        self.tab = "studio"
        self.page = 0
        self.font = "impact"
        self.color_preset = "classic"
        self.watermark_position = "bottom-left"
        self.max_font_size = 50
        self.uppercase = False

    def _sync_boxes(self) -> None:
        if len(self.boxes) < self.template.box_count:
            self.boxes.extend([""] * (self.template.box_count - len(self.boxes)))
        elif len(self.boxes) > self.template.box_count:
            self.boxes = self.boxes[: self.template.box_count]

    @property
    def has_captions(self) -> bool:
        return any(b.strip() for b in self.boxes)

    def _active_color_pair(self) -> tuple[str, str]:
        for key, _, fg, outline in COLOR_PRESETS:
            if key == self.color_preset:
                return fg, outline
        return "#ffffff", "#000000"

    async def select_template(self, template_id: str) -> None:
        found = next((t for t in self.templates if t.id == template_id), None)
        if not found:
            all_t = await self.cog.get_memes()
            found = next((t for t in all_t if t.id == template_id), None)
        if not found:
            msg = f"Template `{esc(template_id)}` not found."
            raise MemeError(msg)
        self.template = found
        self._sync_boxes()
        self.generated = None
        self.tab = "studio"

    async def pick_random(self) -> None:
        pool = self.templates or await self.cog.get_memes()
        self.template = randomlib.choice(pool)
        self.boxes = [""] * self.template.box_count
        self.generated = None
        self.tab = "studio"

    async def search_templates(self, query: str) -> None:
        matches = await self.cog.search_templates(query)
        if not matches:
            msg = f"No meme templates found matching \N{LEFT DOUBLE QUOTATION MARK}{esc(query)}\N{RIGHT DOUBLE QUOTATION MARK} in the top 100 templates (or pass a numeric Imgflip template ID)."
            raise MemeError(msg)
        self.templates = matches
        self.template = matches[0]
        self.boxes = [""] * self.template.box_count
        self.generated = None
        self.query = query
        self.page = 0
        self.tab = "studio"

    async def reset_trending(self) -> None:
        self.templates = await self.cog.get_memes()
        self.query = None
        self.page = 0
        self.template = self.templates[0]
        self._sync_boxes()

    async def turn_page(self, delta: int) -> None:
        max_page = max(0, (len(self.templates) - 1) // 25)
        self.page = max(0, min(max_page, self.page + delta))

    async def set_font(self, font: str) -> None:
        self.font = font
        if self.has_captions:
            await self.render_meme()

    async def set_color(self, preset: str) -> None:
        self.color_preset = preset
        if self.has_captions:
            await self.render_meme()

    async def set_watermark_pos(self, pos: str) -> None:
        self.watermark_position = pos
        if self.has_captions:
            await self.render_meme()

    async def toggle_caps(self) -> None:
        self.uppercase = not self.uppercase
        if self.has_captions:
            await self.render_meme()

    async def clear_captions(self) -> None:
        self.boxes = [""] * self.template.box_count
        self.generated = None

    async def render_meme(self) -> None:
        if not self.has_captions:
            msg = "Add at least one caption box before generating the meme!"
            raise MemeError(msg)
        fg, outline = self._active_color_pair()
        texts = [b.upper() if self.uppercase else b for b in self.boxes]
        self.generated = await self.cog.caption_image(
            self.template,
            texts,
            font=self.font,
            max_font_size=self.max_font_size,
            color=fg,
            outline_color=outline,
            watermark_position=self.watermark_position,
        )
        self.tab = "studio"

    async def _on_caption_saved(self, interaction: discord.Interaction, updated: list[str], auto_gen: bool) -> None:
        self.boxes = updated
        if auto_gen and any(b.strip() for b in self.boxes):
            await self.run(interaction, self.render_meme)
        else:
            await self.run(interaction)

    async def _on_template_uploaded(self, interaction: discord.Interaction, name: str, image_url: str, alt_names: str) -> None:
        async def do_upload() -> None:
            tpl = await self.cog.upload_template(name=name, image_url=image_url, alt_names=alt_names or None)
            self.templates = [tpl] + [t for t in self.templates if t.id != tpl.id]
            self.template = tpl
            self.boxes = [""] * tpl.box_count
            self.generated = None
            self.page = 0
            self.tab = "studio"

        await self.run(interaction, do_upload)

    def _open_caption_modal(self, start_index: int = 0) -> Callable[[discord.Interaction], Awaitable[None]]:
        async def callback(interaction: discord.Interaction) -> None:
            modal = CaptionModal(
                template=self.template,
                current_boxes=self.boxes,
                start_index=start_index,
                on_save=self._on_caption_saved,
                auto_generate=True,
            )
            await interaction.response.send_modal(modal)

        return callback

    def _open_upload_modal(self) -> Callable[[discord.Interaction], Awaitable[None]]:
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(UploadTemplateModal(on_upload=self._on_template_uploaded))

        return callback

    async def _set_tab(self, tab: str) -> None:
        self.tab = tab

    def _studio_body(self) -> str:
        t = self.template
        lines = [
            f"**Template ID** `{t.id}` \N{MIDDLE DOT} **Size** {t.width}\N{MULTIPLICATION SIGN}{t.height}px \N{MIDDLE DOT} **Text Boxes** {t.box_count}",
        ]
        if t.captions:
            lines.append(f"**All-time uses** ~{t.captions:,}+ captions on Imgflip")
        lines.append("")
        lines.append("### \N{MEMO} Captions")
        for i in range(t.box_count):
            val = self.boxes[i].strip() if i < len(self.boxes) else ""
            shown = f"`{esc(clip(val, 90))}`" if val else "*(empty \N{EM DASH} click Edit Text)*"
            lines.append(f"**Box #{i + 1}:** {shown}")
        if self.generated:
            lines.append(
                f"\n\N{SPARKLES} **Rendered Meme Ready!** [Direct Image]({self.generated.url}) \N{MIDDLE DOT} [Imgflip Page]({self.generated.page_url})"
            )
        else:
            lines.append("\n-# Tip: Click **Edit Text** below to type your captions and render the meme automatically.")
        return "\n".join(lines)

    def _style_body(self) -> str:
        font_label = next((lbl for k, lbl, _ in FONTS if k == self.font), self.font)
        color_label = next((lbl for k, lbl, _, _ in COLOR_PRESETS if k == self.color_preset), self.color_preset)
        wm_label = next((lbl for k, lbl in WATERMARK_POSITIONS if k == self.watermark_position), self.watermark_position)
        return "\n".join(
            [
                "### \N{LOWER LEFT FOUNTAIN PEN}\N{VARIATION SELECTOR-16} Typography & Box Styling",
                f"**Active Font** `{esc(font_label)}` (`{self.font}`)",
                f"**Color Theme** {esc(color_label)}",
                f"**Watermark Position** {esc(wm_label)}",
                f"**Max Font Size** `{self.max_font_size}px`",
                f"**Force ALL CAPS** `{'Enabled' if self.uppercase else 'Disabled'}`",
                "",
                "-# Changing a font, color, or watermark position automatically re-renders your meme if you have already entered captions.",
            ]
        )

    def _browse_body(self) -> str:
        start = self.page * 25
        chunk = self.templates[start : start + 25]
        header = (
            f"### \N{RIGHT-POINTING MAGNIFYING GLASS} Filter results for \N{LEFT DOUBLE QUOTATION MARK}{esc(self.query)}\N{RIGHT DOUBLE QUOTATION MARK}"
            if self.query
            else "### \N{FIRE} Trending Top 100 Meme Templates"
        )
        lines = [
            header,
            f"-# Showing {start + 1}\N{EN DASH}{start + len(chunk)} of {len(self.templates)} templates (Page {self.page + 1}/{max(1, (len(self.templates) - 1) // 25 + 1)})",
            "",
        ]
        for idx, t in enumerate(chunk[:12], start + 1):
            marker = "\N{SMALL ORANGE DIAMOND}" if t.id == self.template.id else "\N{BULLET}"
            lines.append(f"{marker} **{idx}. {esc(t.name)}** (`#{t.id}`) \N{EM DASH} {t.box_count} boxes")
        if len(chunk) > 12:
            lines.append(f"-# \N{HORIZONTAL ELLIPSIS} and {len(chunk) - 12} more in the dropdown menu below.")
        return "\n".join(lines)

    def render(self) -> None:
        self.clear_items()
        t = self.template
        accent = GREEN if self.generated else PURPLE
        c = discord.ui.Container(accent_colour=accent)

        status_tag = "Rendered Meme" if self.generated else "Template Preview"
        c.add_item(
            head(
                f"## \N{FRAME WITH PICTURE}\N{VARIATION SELECTOR-16} {esc(t.name)}\n"
                f"-# Meme Studio \N{MIDDLE DOT} {status_tag} \N{MIDDLE DOT} {t.box_count} text boxes",
                t.url if self.generated and t.url else None,
            )
        )
        c.add_item(sep())

        body_fn = {
            "studio": self._studio_body,
            "style": self._style_body,
            "browse": self._browse_body,
        }[self.tab]
        c.add_item(text(body_fn()))

        img_url = self.generated.url if self.generated else t.url
        if g := gallery(img_url):
            c.add_item(g)

        c.add_item(sep())

        start = self.page * 25
        chunk = self.templates[start : start + 25]
        if chunk:
            opts = [
                opt(
                    item.name,
                    item.id,
                    desc=f"#{item.id} | {item.box_count} boxes | {item.width}x{item.height}",
                    emoji="\N{FRAME WITH PICTURE}\N{VARIATION SELECTOR-16}",
                    default=item.id == t.id,
                )
                for item in chunk
            ]
            c.add_item(
                discord.ui.ActionRow(
                    select(
                        opts,
                        lambda i, v: self.run(i, self.select_template, v),
                        f"Switch template ({start + 1}-{start + len(chunk)} of {len(self.templates)})\N{HORIZONTAL ELLIPSIS}",
                    )
                )
            )

        if self.tab == "style":
            c.add_item(
                discord.ui.ActionRow(
                    select(
                        [
                            opt(
                                lbl,
                                val,
                                desc=desc,
                                emoji="\N{LOWER LEFT FOUNTAIN PEN}\N{VARIATION SELECTOR-16}",
                                default=val == self.font,
                            )
                            for val, lbl, desc in FONTS
                        ],
                        lambda i, v: self.run(i, self.set_font, v),
                        "Choose font family\N{HORIZONTAL ELLIPSIS}",
                    )
                )
            )
            c.add_item(
                discord.ui.ActionRow(
                    select(
                        [
                            opt(
                                lbl,
                                key,
                                desc=f"Text {fg} / Outline {out}",
                                emoji="\N{ARTIST PALETTE}",
                                default=key == self.color_preset,
                            )
                            for key, lbl, fg, out in COLOR_PRESETS
                        ],
                        lambda i, v: self.run(i, self.set_color, v),
                        "Choose text color preset\N{HORIZONTAL ELLIPSIS}",
                    )
                )
            )
            c.add_item(
                discord.ui.ActionRow(
                    select(
                        [
                            opt(
                                lbl,
                                pos,
                                emoji="\N{ROUND PUSHPIN}",
                                default=pos == self.watermark_position,
                            )
                            for pos, lbl in WATERMARK_POSITIONS
                        ],
                        lambda i, v: self.run(i, self.set_watermark_pos, v),
                        "Watermark position\N{HORIZONTAL ELLIPSIS}",
                    )
                )
            )

        tab_buttons = [
            button(
                lbl,
                lambda i, key=key: self.run(i, self._set_tab, key),
                emoji=em,
                style=discord.ButtonStyle.primary if self.tab == key else discord.ButtonStyle.secondary,
            )
            for key, lbl, em in self.TABS
        ]
        c.add_item(discord.ui.ActionRow(*tab_buttons))

        action_row: list[discord.ui.Button] = [
            button(
                "Edit Text" if t.box_count <= 5 else "Edit Boxes 1-5",
                self._open_caption_modal(0),
                emoji="\N{MEMO}",
                style=discord.ButtonStyle.success,
            )
        ]
        if t.box_count > 5:
            action_row.append(
                button(
                    f"Edit Boxes 6-{min(10, t.box_count)}",
                    self._open_caption_modal(5),
                    emoji="\N{MEMO}",
                    style=discord.ButtonStyle.success,
                )
            )
        action_row.append(
            button(
                "Render Meme",
                lambda i: self.run(i, self.render_meme),
                emoji="\N{HIGH VOLTAGE SIGN}",
                style=discord.ButtonStyle.primary,
                disabled=not self.has_captions,
            )
        )
        action_row.append(
            self.modal_button(
                "Filter / ID",
                "\N{LEFT-POINTING MAGNIFYING GLASS}",
                title="Filter Top 100 or Enter ID",
                label="Template keyword or custom ID",
                placeholder="drake, two buttons, or 181913649",
                on_query=lambda i, q: self.run(i, self.search_templates, q),
            )
        )
        action_row.append(
            button(
                "Random",
                lambda i: self.run(i, self.pick_random),
                emoji="\N{GAME DIE}",
            )
        )
        c.add_item(discord.ui.ActionRow(*action_row[:5]))

        util_row: list[discord.ui.Button] = []
        if len(self.templates) > 25:
            max_page = max(0, (len(self.templates) - 1) // 25)
            util_row.append(
                button(
                    "Prev Page",
                    lambda i: self.run(i, self.turn_page, -1),
                    emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
                    disabled=self.page == 0,
                )
            )
            util_row.append(
                button(
                    "Next Page",
                    lambda i: self.run(i, self.turn_page, 1),
                    emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
                    disabled=self.page >= max_page,
                )
            )
        if self.tab == "style":
            util_row.append(
                button(
                    f"ALL CAPS: {'ON' if self.uppercase else 'OFF'}",
                    lambda i: self.run(i, self.toggle_caps),
                    emoji="\N{INPUT SYMBOL FOR LATIN CAPITAL LETTERS}",
                    style=discord.ButtonStyle.primary if self.uppercase else discord.ButtonStyle.secondary,
                )
            )
        if self.tab == "browse":
            util_row.append(
                button(
                    "Upload Template",
                    self._open_upload_modal(),
                    emoji="\N{UPWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
                )
            )
        if self.has_captions:
            util_row.append(
                button(
                    "Clear Text",
                    lambda i: self.run(i, self.clear_captions),
                    emoji="\N{WASTEBASKET}\N{VARIATION SELECTOR-16}",
                    style=discord.ButtonStyle.danger,
                )
            )
        if self.query:
            util_row.append(
                button(
                    "All Top 100",
                    lambda i: self.run(i, self.reset_trending),
                    emoji="\N{FIRE}",
                )
            )
        if self.generated:
            util_row.append(
                button(
                    "Image Link",
                    url=self.generated.url,
                    emoji="\N{GLOBE WITH MERIDIANS}",
                )
            )
        if util_row:
            c.add_item(discord.ui.ActionRow(*util_row[:5]))

        c.add_item(text(DISCLAIMER))
        self.add_item(c)


class TTLCache:
    def __init__(self, maxsize: int = 256) -> None:
        self._d: dict[Any, tuple[float, Any]] = {}
        self._max = maxsize

    def get(self, k: Any) -> Any:
        v = self._d.get(k)
        if v and v[0] > time.monotonic():
            return v[1]
        self._d.pop(k, None)
        return None

    def set(self, k: Any, val: Any, ttl: float) -> None:
        if len(self._d) >= self._max:
            now = time.monotonic()
            self._d = {a: b for a, b in self._d.items() if b[0] > now}
            if len(self._d) >= self._max:
                self._d.pop(next(iter(self._d)))
        self._d[k] = (time.monotonic() + ttl, val)


class Meme(commands.Cog, command_attrs={"hidden": True}):
    """Interactive Meme Studio and generator powered by the free Imgflip API."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.session: aiohttp.ClientSession = self.bot.http_session
        self.cache = TTLCache()

    @property
    def api_key(self) -> str | None:
        key = os.getenv("IMAGE_FLIP_KEY")
        return key.strip() if key else None

    def _require_key(self) -> str:
        key = self.api_key
        if not key:
            msg = (
                "Missing `IMAGE_FLIP_KEY` API key in environment. "
                "Create a free Bearer API key at <https://imgflip.com/api> and set `IMAGE_FLIP_KEY` in your environment."
            )
            raise MemeError(msg)
        return key

    async def send(self, ctx: commands.Context[Any], view: BaseView) -> None:
        view.render()
        view.message = await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    async def cog_command_error(self, ctx: commands.Context[Any], error: commands.CommandError) -> None:
        err = getattr(error, "original", error)
        if isinstance(err, commands.CommandOnCooldown):
            msg = f"\N{HOURGLASS WITH FLOWING SAND} Slow down! Try again in {err.retry_after:.0f}s."
        elif isinstance(err, (commands.UserInputError, MemeError)):
            msg = f"\N{CROSS MARK} {err}"
        else:
            log.error("meme cog error", exc_info=err)
            msg = "\N{CROSS MARK} Something went wrong while talking to Imgflip. Try again later."
        await ctx.send(msg, allowed_mentions=discord.AllowedMentions.none())

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        form: list[tuple[str, str]] | dict[str, str] | None = None,
        auth: bool = False,
    ) -> dict[str, Any]:
        assert self.session
        headers: dict[str, str] = {}
        if auth:
            headers["Authorization"] = f"Bearer {self._require_key()}"
        url = f"{API_BASE}{endpoint}"
        try:
            async with self.session.request(method, url, params=params, data=form, headers=headers) as r:
                if r.status == 429:
                    msg = "Imgflip API is rate-limiting requests right now. Try again in a moment."
                    raise MemeError(msg)
                payload = await r.json(content_type=None)
        except TimeoutError:
            msg = "Imgflip API timed out. Try again in a moment."
            raise MemeError(msg) from None
        except aiohttp.ClientError as e:
            msg = f"Couldn't reach Imgflip API ({type(e).__name__})."
            raise MemeError(msg) from None

        if not isinstance(payload, dict):
            msg = "Unexpected response from Imgflip API."
            raise MemeError(msg)
        if not payload.get("success"):
            err_msg = payload.get("error_message") or "Unknown Imgflip API error."
            raise MemeError(str(err_msg))
        return payload.get("data") or {}

    async def get_memes(self, *, fresh: bool = False) -> list[MemeTemplate]:
        if not fresh and (cached := self.cache.get("trending_memes")) is not None:
            return cached
        data = await self._request("GET", "/get_memes")
        raw_list = data.get("memes") or []
        templates = [MemeTemplate.from_dict(m) for m in raw_list if isinstance(m, dict) and m.get("id")]
        if not templates:
            msg = "Imgflip returned an empty template list."
            raise MemeError(msg)
        self.cache.set("trending_memes", templates, ttl=1800)
        return templates

    async def search_templates(self, query: str) -> list[MemeTemplate]:
        q = query.strip()
        if not q:
            return await self.get_memes()

        trending = await self.get_memes()
        ql = q.lower()

        scored: list[tuple[int, int, MemeTemplate]] = []
        for idx, t in enumerate(trending):
            nl = t.name.lower()
            if t.id == q or nl == ql:
                scored.append((0, idx, t))
            elif nl.startswith(ql):
                scored.append((1, idx, t))
            elif ql in nl or all(tok in nl for tok in ql.split()):
                scored.append((2, idx, t))
        scored.sort(key=lambda item: (item[0], item[1]))
        hits = [item[2] for item in scored]

        if not hits and q.isdigit():
            custom = MemeTemplate(
                id=q,
                name=f"Custom Template #{q}",
                url="",
                box_count=2,
            )
            return [custom, *trending[:24]]
        return hits

    async def resolve_template(self, query: str | None) -> tuple[MemeTemplate, list[MemeTemplate]]:
        trending = await self.get_memes()
        if not query or not query.strip():
            return trending[0], trending
        hits = await self.search_templates(query)
        if hits:
            return hits[0], hits
        msg = f"No template matching \N{LEFT DOUBLE QUOTATION MARK}{esc(query)}\N{RIGHT DOUBLE QUOTATION MARK} in the top 100 templates (you can also pass any numeric Imgflip template ID)."
        raise MemeError(msg)

    async def caption_image(
        self,
        template: MemeTemplate,
        boxes: list[str],
        *,
        font: str = "impact",
        max_font_size: int = 50,
        color: str = "#ffffff",
        outline_color: str = "#000000",
        watermark_position: str = "bottom-left",
    ) -> GeneratedMeme:
        form: list[tuple[str, str]] = [
            ("template_id", template.id),
            ("font", font),
            ("max_font_size", str(max_font_size)),
            ("watermark_position", watermark_position),
        ]
        for idx, val in enumerate(boxes[:20]):
            form.append((f"boxes[{idx}][text]", val))
            if color != "#ffffff" or outline_color != "#000000":
                form.append((f"boxes[{idx}][color]", color))
                form.append((f"boxes[{idx}][outline_color]", outline_color))

        data = await self._request("POST", "/caption_image", form=form, auth=True)
        url = str(data.get("url") or "")
        page_url = str(data.get("page_url") or url)
        if not url:
            msg = "Imgflip did not return an image URL."
            raise MemeError(msg)
        return GeneratedMeme(url=url, page_url=page_url, template=template, boxes=list(boxes))

    async def upload_template(
        self,
        *,
        name: str,
        image_url: str,
        alt_names: str | None = None,
    ) -> MemeTemplate:
        form: dict[str, str] = {
            "name": name[:64],
            "image_url": image_url,
        }
        if alt_names:
            form["alt_names"] = alt_names[:255]
        data = await self._request("POST", "/upload_template", form=form, auth=True)
        tpl_id = str(data.get("template_id") or "")
        if not tpl_id:
            msg = "Imgflip did not return a template_id for the uploaded image."
            raise MemeError(msg)
        return MemeTemplate(id=tpl_id, name=name[:64], url=image_url, box_count=2)

    async def template_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        try:
            templates = await self.get_memes()
        except MemeError:
            return []
        c = current.lower().strip()
        matches = [t for t in templates if not c or c in t.name.lower() or c in t.id][:25]
        return [app_commands.Choice(name=clip(f"{t.name} ({t.box_count} boxes)", 100), value=t.id) for t in matches]

    async def font_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        c = current.lower().strip()
        return [app_commands.Choice(name=lbl, value=val) for val, lbl, _ in FONTS if not c or c in val or c in lbl.lower()][:25]

    @commands.group(name="meme", aliases=["memes", "imgflip"], invoke_without_command=True)
    @commands.cooldown(2, 8.0, commands.BucketType.user)
    async def meme(
        self,
        ctx: commands.Context[Any],
        *,
        query: str | None = commands.parameter(
            default=None,
            description="Optional template name/ID, or `template | top text | bottom text`",
        ),
    ) -> None:
        """Open the interactive Meme Studio, or pass `template | text1 | text2` to render immediately."""
        async with ctx.typing():
            if query and ("|" in query or ";" in query):
                tpl_query, captions = parse_quick_args(query)
                tpl, pool = await self.resolve_template(tpl_query)
                gen = None
                if any(c.strip() for c in captions):
                    gen = await self.caption_image(tpl, captions)
                view = MemeStudioView(
                    self,
                    ctx.author.id,
                    pool,
                    tpl,
                    boxes=captions or None,
                    generated=gen,
                    query=tpl_query,
                )
            else:
                tpl, pool = await self.resolve_template(query)
                view = MemeStudioView(self, ctx.author.id, pool, tpl, query=query)
        await self.send(ctx, view)

    @meme.command(name="studio")
    @commands.cooldown(2, 8.0, commands.BucketType.user)
    async def studio(
        self,
        ctx: commands.Context[Any],
        *,
        template: str | None = commands.parameter(
            default=None,
            description="Initial template name or ID to load in the studio",
        ),
    ) -> None:
        """Launch the interactive Meme Studio with template selector, font styling, and caption modals."""
        async with ctx.typing():
            tpl, pool = await self.resolve_template(template)
            view = MemeStudioView(self, ctx.author.id, pool, tpl, query=template)
        await self.send(ctx, view)

    @meme.command(name="make", aliases=["create", "caption"])
    @commands.cooldown(3, 10.0, commands.BucketType.user)
    async def make(
        self,
        ctx: commands.Context[Any],
        template: str = commands.parameter(description="Template name or Imgflip ID (quote if multi-word)"),
        *,
        captions: str = commands.parameter(
            description="Captions separated by `|` or `;` (e.g. `Top text | Bottom text`)",
        ),
    ) -> None:
        """Generate a meme directly from a template and pipe-separated captions (`|`)."""
        async with ctx.typing():
            tpl, pool = await self.resolve_template(template)
            boxes = split_captions(captions)
            gen = await self.caption_image(tpl, boxes)
            view = MemeStudioView(
                self,
                ctx.author.id,
                pool,
                tpl,
                boxes=boxes,
                generated=gen,
                query=template,
            )
        await self.send(ctx, view)

    @meme.command(name="search", aliases=["find", "filter"])
    @commands.cooldown(3, 8.0, commands.BucketType.user)
    async def search(
        self,
        ctx: commands.Context[Any],
        *,
        query: str = commands.parameter(description="Search keywords or template ID"),
    ) -> None:
        """Filter the top 100 meme templates by keyword (or load a custom numeric template ID)."""
        async with ctx.typing():
            hits = await self.search_templates(query)
            if not hits:
                msg = f"No meme templates found matching \N{LEFT DOUBLE QUOTATION MARK}{esc(query)}\N{RIGHT DOUBLE QUOTATION MARK}."
                raise MemeError(msg)
            view = MemeStudioView(self, ctx.author.id, hits, hits[0], query=query)
            view.tab = "browse"
        await self.send(ctx, view)

    @meme.command(name="trending", aliases=["top", "templates"])
    @commands.cooldown(2, 8.0, commands.BucketType.user)
    async def trending(self, ctx: commands.Context[Any]) -> None:
        """Browse the top 100 trending meme templates on Imgflip."""
        async with ctx.typing():
            templates = await self.get_memes()
            view = MemeStudioView(self, ctx.author.id, templates, templates[0])
            view.tab = "browse"
        await self.send(ctx, view)

    @meme.command(name="random", aliases=["rand"])
    @commands.cooldown(3, 8.0, commands.BucketType.user)
    async def random_cmd(self, ctx: commands.Context[Any]) -> None:
        """Pick a random trending meme template and open it in the Meme Studio."""
        async with ctx.typing():
            templates = await self.get_memes()
            picked = randomlib.choice(templates)
            view = MemeStudioView(self, ctx.author.id, templates, picked)
        await self.send(ctx, view)

    @meme.command(name="upload")
    @commands.cooldown(1, 20.0, commands.BucketType.user)
    async def upload(
        self,
        ctx: commands.Context[Any],
        name: str = commands.parameter(description="Public name for the new template (quote if multi-word)"),
        image_url: str | None = commands.parameter(
            default=None,
            description="Direct image URL (or attach an image to the message)",
        ),
    ) -> None:
        """Upload a custom public meme template to Imgflip and open it in the Meme Studio."""
        url = image_url
        if not url and ctx.message.attachments:
            url = ctx.message.attachments[0].url
        if not url:
            msg = "Provide an `image_url` or attach an image to your command message."
            raise MemeError(msg)
        async with ctx.typing():
            tpl = await self.upload_template(name=name, image_url=url)
            trending = await self.get_memes()
            pool = [tpl] + [t for t in trending if t.id != tpl.id]
            view = MemeStudioView(self, ctx.author.id, pool, tpl)
        await self.send(ctx, view)

    @meme.command(name="about")
    async def about(self, ctx: commands.Context[Any]) -> None:
        """API details, environment setup, and quick-start guide for the Meme Studio."""
        has_key = "\N{LARGE GREEN CIRCLE} Configured" if self.api_key else "\N{LARGE RED CIRCLE} Missing (`IMAGE_FLIP`)"
        c = discord.ui.Container(accent_colour=PURPLE)
        c.add_item(
            text(
                "## \N{ARTIST PALETTE} Meme Studio \N{EM DASH} Guide & Info\n"
                f"**API Key Status:** {has_key} *(Free Tier)*\n\n"
                "### \N{HIGH VOLTAGE SIGN} Quick Usage\n"
                "\N{BULLET} `meme` \N{EM DASH} Open the interactive Meme Studio\n"
                "\N{BULLET} `meme drake | writing slash commands | using prefix + Components V2` \N{EM DASH} Instant render\n"
                "\N{BULLET} `meme make 'two buttons' sleep early | code at 2am` \N{EM DASH} Render by template & captions\n"
                "\N{BULLET} `meme search distracted` \N{EM DASH} Filter the top 100 templates or load a custom ID\n"
                "\N{BULLET} `meme trending` / `meme random` \N{EM DASH} Browse top 100 or roll a random template\n"
                "\N{BULLET} `meme upload 'My Template' [url]` \N{EM DASH} Upload a new template from URL or attachment\n\n" + DISCLAIMER
            )
        )
        v = discord.ui.LayoutView(timeout=None)
        v.add_item(c)
        await ctx.send(view=v, allowed_mentions=discord.AllowedMentions.none())


async def setup(bot: Bot) -> None:
    await bot.add_cog(Meme(bot))
