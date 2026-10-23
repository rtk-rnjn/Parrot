from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import logging
import re
import time
import uuid as uuidlib
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Literal
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .wiki_scrapper import WIKI_LANGS, SearchPage, WikiArticle, WikiClient, WikiError, WikiTable, paginate

if TYPE_CHECKING:
    from core import Bot

log = logging.getLogger(__name__)

UA = "MinecraftCog/1.0 (discord.py; +https://github.com/YOUR/REPO)"
GREEN, RED, GOLD, BLUE, GREY = 0x5B8731, 0xB02E26, 0xFCA800, 0x3C8DBC, 0x6B6B6B
VIEW_TIMEOUT = 300

MCSRV = "https://api.mcsrvstat.us"
MOJANG_NAME = "https://api.mojang.com/users/profiles/minecraft/"
MOJANG_PROFILE = "https://sessionserver.mojang.com/session/minecraft/profile/"
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
DATA_RAW = "https://raw.githubusercontent.com/PrismarineJS/minecraft-data/master/data"
ASSETS_RAW = "https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data"
HEADS = "https://mc-heads.net"

RELEASE_RE = re.compile(r"^\d+(\.\d+)+$")
NAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$")
ADDR_RE = re.compile(r"^(?:[A-Za-z0-9._-]+|\[[0-9a-fA-F:]+\])(?::\d{1,5})?$")

LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/3.0/"
DISCLAIMER = "-# Not an official Minecraft product. Not approved by or associated with Mojang or Microsoft."


class MCError(Exception):
    """User-facing error."""


def esc(s: Any) -> str:
    return discord.utils.escape_mentions(discord.utils.escape_markdown(str(s)))


def clip(s: Any, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"


def bar(cur: int, mx: int, w: int = 10) -> str:
    if not mx:
        return ""
    f = round(w * min(cur, mx) / mx)
    return "\N{BLACK PARALLELOGRAM}" * f + "\N{WHITE PARALLELOGRAM}" * (w - f)


def epoch(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def size(n: int | float | None) -> str:
    if not n:
        return "?"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def snake(s: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower().replace(" ", "_")


def uuid_int_array(u: uuidlib.UUID) -> str:
    n = u.int
    parts = [(n >> s) & 0xFFFFFFFF for s in (96, 64, 32, 0)]
    return "[I; " + ", ".join(str(p - (1 << 32) if p >= 1 << 31 else p) for p in parts) + "]"


def offline_uuid(name: str) -> uuidlib.UUID:
    """UUID a cracked / offline-mode server assigns (Java's UUID.nameUUIDFromBytes)."""
    h = bytearray(hashlib.md5(f"OfflinePlayer:{name}".encode()).digest())  # noqa: S324
    h[6] = (h[6] & 0x0F) | 0x30
    h[8] = (h[8] & 0x3F) | 0x80
    return uuidlib.UUID(bytes=bytes(h))


def clean_address(raw: str) -> str:
    a = re.sub(r"^\w+://", "", raw.strip()).split("/")[0].strip()
    if not a or len(a) > 253 or not ADDR_RE.match(a):
        msg = "That doesn't look like a server address. Try `play.example.com` or `host:port`."
        raise MCError(msg)
    return a


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
    primary: bool = False,
    disabled: bool = False,
) -> discord.ui.Button:
    if url:
        return discord.ui.Button(label=label, url=url, emoji=emoji)
    b = discord.ui.Button(
        label=label,
        emoji=emoji,
        disabled=disabled,
        style=discord.ButtonStyle.primary if primary else discord.ButtonStyle.secondary,
    )
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


class QueryModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        title: str,
        label: str,
        placeholder: str,
        on_query: Callable[[discord.Interaction, str], Awaitable[None]],
        default: str | None = None,
        max_length: int = 100,
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


class BaseView(discord.ui.LayoutView):
    """Owner-locked Components V2 view. Subclasses implement render()."""

    def __init__(self, cog: Minecraft, user_id: int) -> None:
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
        except (MCError, WikiError) as e:
            await interaction.followup.send(f"\N{CROSS MARK} {e}", ephemeral=True)
            return
        self.render()
        await interaction.edit_original_response(view=self)

    def modal_button(self, label: str, emoji: str, /, **modal_kw: Any) -> discord.ui.Button:
        async def click(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(QueryModal(**modal_kw))

        return button(label, click, emoji=emoji)

    async def on_timeout(self) -> None:
        for item in self.walk_children():
            if isinstance(item, (discord.ui.Button, discord.ui.Select)) and not getattr(item, "url", None):
                item.disabled = True
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)


class ServerView(BaseView):
    TABS: ClassVar = [
        ("overview", "Overview", "\N{CLIPBOARD}"),
        ("players", "Players", "\N{BUSTS IN SILHOUETTE}"),
        ("plugins", "Plugins & mods", "\N{JIGSAW PUZZLE PIECE}"),
        ("tech", "Technical", "\N{HAMMER AND WRENCH}\N{VARIATION SELECTOR-16}"),
    ]

    def __init__(
        self,
        cog: Minecraft,
        user_id: int,
        address: str,
        requested: str,
        edition: str,
        data: dict,
        mapped: str | None,
    ) -> None:
        super().__init__(cog, user_id)
        self.address, self.requested, self.edition, self.data, self.mapped = (
            address,
            requested,
            edition,
            data,
            mapped,
        )
        self.tab = "overview"

    async def reload(self) -> None:
        self.edition, self.data = await self.cog.fetch_server(self.address, self.requested, fresh=True)
        self.mapped = await self.cog.protocol_names(self.edition, (self.data.get("protocol") or {}).get("version"))

    async def switch(self, address: str) -> None:
        self.address = clean_address(address)
        self.requested = "auto"
        self.tab = "overview"
        await self.reload()

    def _overview(self) -> str:
        data_dict, java = self.data, self.edition == "java"
        motd = "\n".join(f"> {esc(line)}" if line.strip() else "> " for line in (data_dict.get("motd") or {}).get("clean", [])) or "> *(no MOTD)*"
        pl = data_dict.get("players") or {}
        on, mx = int(pl.get("online", 0)), int(pl.get("max", 0))
        lines = [motd, "", f"\N{BUSTS IN SILHOUETTE} **Players** {on:,} / {mx:,}  {bar(on, mx)}"]
        ver = data_dict.get("version")
        if ver or data_dict.get("software"):
            lines.append(
                f"\N{LABEL}\N{VARIATION SELECTOR-16} **Version** {esc(ver or '?')}"
                + (f" \N{MIDDLE DOT} {esc(data_dict['software'])}" if data_dict.get("software") else "")
            )
        proto = data_dict.get("protocol") or {}
        if proto.get("version") is not None:
            lines.append(f"\N{ELECTRIC PLUG} **Protocol** {proto['version']}" + (f" \N{RIGHTWARDS ARROW} {self.mapped}" if self.mapped else ""))
        if data_dict.get("gamemode"):
            lines.append(f"\N{VIDEO GAME} **Gamemode** {esc(data_dict['gamemode'])}")
        if (data_dict.get("map") or {}).get("clean"):
            lines.append(f"\N{WORLD MAP}\N{VARIATION SELECTOR-16} **Map** {esc(data_dict['map']['clean'])}")
        host, port = data_dict.get("hostname") or self.address, data_dict.get("port")
        join = f"`{host}`" if java and port in (None, 25565) else f"`{host}` port `{port}`"
        lines.append(f"\N{ROUND PUSHPIN} **Join** {join}")
        cached = (data_dict.get("debug") or {}).get("cachetime")
        lines.append("-# via mcsrvstat.us" + (f" \N{MIDDLE DOT} checked <t:{int(cached)}:R>" if cached else ""))
        return "\n".join(lines)

    def _players(self) -> str:
        player_data = self.data.get("players") or {}
        names = [p.get("name", "?") if isinstance(p, dict) else str(p) for p in player_data.get("list", [])]
        out = f"## \N{BUSTS IN SILHOUETTE} {int(player_data.get('online', 0)):,} / {int(player_data.get('max', 0)):,} online\n"
        if names:
            out += ", ".join(f"`{n}`" for n in names[:60])
            if len(names) > 60:
                out += f"\n\N{HORIZONTAL ELLIPSIS} +{len(names) - 60} more"
        else:
            out += "The server doesn't publish a player list (normal for big networks, or query is disabled)."
        return out

    def _plugins(self) -> str:
        def fmt(xs):
            return ", ".join(f"`{esc(x.get('name', '?'))}`" + (f" {esc(x['version'])}" if x.get("version") else "") for x in xs)

        parts = []
        if self.data.get("plugins"):
            parts.append(f"## \N{JIGSAW PUZZLE PIECE} Plugins ({len(self.data['plugins'])})\n{clip(fmt(self.data['plugins']), 1700)}")
        if self.data.get("mods"):
            parts.append(f"## \N{WRENCH} Mods ({len(self.data['mods'])})\n{clip(fmt(self.data['mods']), 1700)}")
        return "\n\n".join(parts) or "No plugins or mods exposed."

    def _tech(self) -> str:
        server_data, debug_info = self.data, self.data.get("debug") or {}

        def yn(v):
            return "\N{WHITE HEAVY CHECK MARK}" if v else "\N{CROSS MARK}"

        rows = [
            ("Resolved IP", server_data.get("ip")),
            ("Port", server_data.get("port")),
            ("Hostname", server_data.get("hostname")),
            ("Server ID", server_data.get("serverid")),
            ("Software", server_data.get("software")),
            ("Protocol name", (server_data.get("protocol") or {}).get("name")),
            ("EULA blocked", yn(server_data.get("eula_blocked"))),
            ("SRV record used", yn(debug_info.get("srv"))),
            ("Query enabled", yn(debug_info.get("query"))),
            ("Ping answered", yn(debug_info.get("ping"))),
            ("Icon", yn(bool(server_data.get("icon")))),
        ]
        body = "\n".join(f"**{k}:** `{esc(v)}`" for k, v in rows if v not in (None, "", "None"))
        if debug_info.get("cacheexpire"):
            body += f"\n**Cache expires:** <t:{int(debug_info['cacheexpire'])}:R>"
        info = (server_data.get("info") or {}).get("clean")
        if info:
            body += "\n\n**Extra info**\n" + clip("\n".join(esc(line) for line in info), 800)
        return "## \N{HAMMER AND WRENCH}\N{VARIATION SELECTOR-16} Technical\n" + body

    def _offline(self) -> str:
        tried = "Java and Bedrock" if self.requested == "auto" else ("Java" if self.edition == "java" else "Bedrock")
        return (
            f"No response from `{esc(self.address)}` ({tried} checked).\n\n"
            "\N{BULLET} Double-check spelling and the **port** (Java 25565, Bedrock 19132)\n"
            "\N{BULLET} Wrong edition? Specify `java` or `bedrock` in the `server` command\n"
            "\N{BULLET} Some hosts block status pings or the server is just starting\n"
            "-# via mcsrvstat.us"
        )

    def render(self) -> None:
        self.clear_items()
        d, online, java = self.data, bool(self.data.get("online")), self.edition == "java"
        host = d.get("hostname") or d.get("ip") or self.address
        icon = f"{MCSRV}/icon/{quote(self.address, safe=':')}" if online and d.get("icon") else None
        container = discord.ui.Container(accent_colour=GREEN if online else RED)
        status_dot = "\N{LARGE GREEN CIRCLE}" if online else "\N{LARGE RED CIRCLE}"
        container.add_item(
            head(
                f"## {status_dot} {esc(host)}\n-# {'Java' if java else 'Bedrock'} Edition \N{MIDDLE DOT} {'Online' if online else 'Offline'}",
                icon,
            )
        )
        container.add_item(sep())
        body = (
            {
                "overview": self._overview,
                "players": self._players,
                "plugins": self._plugins,
                "tech": self._tech,
            }[self.tab]()
            if online
            else self._offline()
        )
        container.add_item(text(body))
        container.add_item(sep())
        if online:
            row = []
            for key, label, emoji in self.TABS:
                dis = key == "plugins" and not (d.get("plugins") or d.get("mods"))
                b = button(
                    label,
                    lambda i, k=key: self.run(i, self._set_tab, k),
                    emoji=emoji,
                    primary=self.tab == key,
                    disabled=dis,
                )
                row.append(b)
            container.add_item(discord.ui.ActionRow(*row))
        container.add_item(
            discord.ui.ActionRow(
                button(
                    "Refresh",
                    lambda i: self.run(i, self.reload),
                    emoji="\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}",
                ),
                self.modal_button(
                    "Another server",
                    "\N{RIGHT-POINTING MAGNIFYING GLASS}",
                    title="Check a server",
                    label="Server address",
                    placeholder="play.example.com",
                    on_query=lambda i, q: self.run(i, self.switch, q),
                ),
                button(
                    "Web status",
                    url=f"https://mcsrvstat.us/{'bedrock/' if not java else ''}server/{quote(self.address, safe=':')}",
                    emoji="\N{GLOBE WITH MERIDIANS}",
                ),
            )
        )
        container.add_item(text(DISCLAIMER))
        self.add_item(container)

    async def _set_tab(self, tab: str) -> None:
        self.tab = tab


@dataclass
class Profile:
    uuid: uuidlib.UUID
    name: str
    skin_url: str | None = None
    model: str = "classic"
    cape_url: str | None = None
    timestamp: int | None = None
    legacy: bool = False


class PlayerView(BaseView):
    TABS: ClassVar = [
        ("overview", "Overview", "\N{STANDING PERSON}"),
        ("skin", "Skin texture", "\N{ARTIST PALETTE}"),
        ("head", "Head", "\N{MOYAI}"),
        ("cape", "Cape", "\N{SCARF}"),
    ]

    def __init__(self, cog: Minecraft, user_id: int, profile: Profile, tab: str = "overview") -> None:
        super().__init__(cog, user_id)
        self.p, self.tab = profile, tab

    async def lookup(self, query: str) -> None:
        self.p = await self.cog.get_profile(query)
        self.tab = "overview"

    def render(self) -> None:
        self.clear_items()
        p, uid = self.p, self.p.uuid.hex
        info_container = discord.ui.Container(accent_colour=GREEN)
        info = [
            f"**Username** `{esc(p.name)}`",
            f"**UUID** `{p.uuid}`",
            f"**Undashed** `{uid}`",
            f"**NBT int-array** `{uuid_int_array(p.uuid)}`",
            f"**Offline-mode UUID** `{offline_uuid(p.name)}`",
            (
                f"**Skin model** {'Slim (Alex-style, 3px arms)' if p.model == 'slim' else 'Classic (Steve-style, 4px arms)'}"
                if p.skin_url
                else "**Skin** default (no custom skin set)"
            ),
        ]
        if p.skin_url:
            info.append(f"**Skin hash** `{clip(p.skin_url.rsplit('/', 1)[-1], 24)}`")
        info.append(f"**Cape** {'yes' if p.cape_url else 'none'}")
        if p.legacy:
            info.append("**Legacy** account")
        info_container.add_item(
            head(
                f"## {esc(p.name)}\n-# Java Edition profile \N{MIDDLE DOT} Mojang session server",
                f"{HEADS}/avatar/{uid}/128",
            )
        )
        info_container.add_item(sep())
        if self.tab == "overview":
            info_container.add_item(text("\n".join(info)))
            if g := gallery(f"{HEADS}/player/{uid}/400"):
                info_container.add_item(g)
        elif self.tab == "skin":
            info_container.add_item(
                text(
                    "## \N{ARTIST PALETTE} Skin\nRaw 64\N{MULTIPLICATION SIGN}64 texture, then the flat front view.\n"
                    + (f"[Texture URL]({p.skin_url})" if p.skin_url else "Default skin.")
                )
            )
            if g := gallery(p.skin_url or f"{HEADS}/skin/{uid}", f"{HEADS}/body/{uid}/300"):
                info_container.add_item(g)
        elif self.tab == "head":
            info_container.add_item(text("## \N{MOYAI} Head\n3D head and flat avatar."))
            if g := gallery(f"{HEADS}/head/{uid}/300", f"{HEADS}/avatar/{uid}/300"):
                info_container.add_item(g)
        elif p.cape_url:
            info_container.add_item(text("## \N{SCARF} Cape\nRaw cape texture atlas (the part facing you is the front-left panel)."))
            info_container.add_item(gallery(p.cape_url))  # type: ignore[arg-type]
        else:
            info_container.add_item(
                text("## \N{SCARF} Cape\nThis account has no cape equipped (or it is an OptiFine/mod cape, which Mojang doesn't know about).")
            )
        info_container.add_item(sep())
        info_container.add_item(
            discord.ui.ActionRow(
                select(
                    [opt(option_label, tab_key, emoji=emoji_icon, default=tab_key == self.tab) for tab_key, option_label, emoji_icon in self.TABS],
                    lambda i, v: self.run(i, self._set_tab, v),
                    "View\N{HORIZONTAL ELLIPSIS}",
                )
            )
        )
        info_container.add_item(
            discord.ui.ActionRow(
                self.modal_button(
                    "Another player",
                    "\N{RIGHT-POINTING MAGNIFYING GLASS}",
                    title="Look up a player",
                    label="Username or UUID",
                    placeholder="Notch",
                    on_query=lambda i, q: self.run(i, self.lookup, q),
                    max_length=36,
                ),
                button(
                    "Download skin",
                    url=f"{HEADS}/download/{uid}",
                    emoji="\N{DOWNWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
                ),
                button("NameMC", url=f"https://namemc.com/profile/{uid}", emoji="\N{GLOBE WITH MERIDIANS}"),
            )
        )
        info_container.add_item(
            text("-# Renders by mc-heads.net \N{MIDDLE DOT} skin data from Mojang \N{MIDDLE DOT} Java Edition only\n" + DISCLAIMER)
        )
        self.add_item(info_container)

    async def _set_tab(self, tab: str) -> None:
        self.tab = tab


class WikiView(BaseView):
    def __init__(self, cog: Minecraft, user_id: int, lang: str = "en") -> None:
        super().__init__(cog, user_id)
        self.lang = lang
        self.mode = "results"
        self.results: SearchPage | None = None
        self.article: WikiArticle | None = None
        self.trail: list[str] = []
        self.entries: list[tuple[str, str, str]] = []
        self.key = "intro"
        self.pages: list[str] = [""]
        self.pi = 0

    @property
    def client(self) -> WikiClient:
        return self.cog.wiki(self.lang)

    async def do_search(self, query: str) -> None:
        page = await self.client.search(query, limit=10)
        if not page.hits:
            hint = f" Did you mean **{esc(page.suggestion)}**?" if page.suggestion else ""
            msg = f"No wiki results for \N{LEFT DOUBLE QUOTATION MARK}{esc(query)}\N{RIGHT DOUBLE QUOTATION MARK}.{hint}"
            raise MCError(msg)
        self.results, self.mode = page, "results"
        if page.hits[0].title.lower() == query.lower() or len(page.hits) == 1:
            await self.open(page.hits[0].title, push=False)

    async def open(self, title: str, *, push: bool = True) -> None:
        if push and self.article:
            self.trail.append(self.article.title)
        self.article = await self.client.get_article(title)
        self.mode = "page"
        self._build_entries()
        await self._show("intro")

    async def back(self) -> None:
        if self.trail:
            self.article = await self.client.get_article(self.trail.pop())
            self.mode = "page"
            self._build_entries()
            await self._show("intro")
        elif self.results:
            self.mode = "results"

    async def to_results(self) -> None:
        self.mode = "results"

    async def random(self) -> None:
        await self.open(await self.client.random_title())

    async def lang_switch(self, lang: str) -> None:
        self.lang = lang
        if self.article:
            await self.open(self.article.title, push=False)

    def _build_entries(self) -> None:
        article_instance = self.article
        assert article_instance
        ents: list[tuple[str, str, str]] = [("intro", "Introduction", "\N{OPEN BOOK}")]
        if article_instance.infobox:
            ents.append(("infobox", "Infobox", "\N{PACKAGE}"))
        n_tab = min(len(article_instance.tables), 5)
        for i, s in enumerate(article_instance.flat_sections()):
            if len(ents) >= 25 - n_tab:
                break
            ents.append(
                (
                    f"s:{i}",
                    ("\N{DOWNWARDS ARROW WITH TIP RIGHTWARDS} " if s.level > 2 else "") + s.heading,
                    "\N{PAGE FACING UP}" if s.level <= 2 else "\N{WHITE SMALL SQUARE}\N{VARIATION SELECTOR-16}",
                )
            )
        for i, t in enumerate(article_instance.tables[:n_tab]):
            ents.append((f"t:{i}", f"Table: {t.caption}", "\N{BAR CHART}"))
        self.entries = ents

    async def _show(self, key: str) -> None:
        article_instance = self.article
        assert article_instance
        self.key, self.pi = key, 0
        if key == "intro":
            self.pages = paginate(article_instance.summary or "*(This page has no introduction.)*", 1700)
        elif key == "infobox":
            lines = []
            for infobox_key, infobox_value in article_instance.infobox.items():
                if infobox_key == "_title":
                    continue
                v = ", ".join(infobox_value) if isinstance(infobox_value, list) else infobox_value
                lines.append(f"**{esc(infobox_key)}** \N{EM DASH} {esc(clip(v, 220))}")
            self.pages = paginate("\n".join(lines), 1700) or ["*Empty infobox.*"]
        elif key.startswith("s:"):
            sec = article_instance.flat_sections()[int(key[2:])]
            self.pages = paginate(sec.text or "*(Nothing here directly; see its subsections.)*", 1700)
        elif key.startswith("t:"):
            t = article_instance.tables[int(key[2:])]
            slices = [t.rows[i : i + 12] for i in range(0, len(t.rows), 12)] or [[]]
            self.pages = [WikiTable(t.caption, t.headers, r).to_text(max_rows=12) for r in slices]
        self.pages = self.pages or [""]

    async def _jump(self, key: str) -> None:
        await self._show(key)

    async def _page(self, delta: int) -> None:
        self.pi = max(0, min(len(self.pages) - 1, self.pi + delta))

    def _footer(self) -> str:
        base = self.client.base_url
        article_instance = self.article
        hist = f" \N{MIDDLE DOT} [History & authors]({article_instance.history_url})" if article_instance and self.mode == "page" else ""
        return (
            f"-# Text from the [Minecraft Wiki]({base}) under [CC BY-NC-SA 3.0]({LICENSE_URL}){hist}. "
            "Changes may have been made; images/names remain property of their owners.\n" + DISCLAIMER
        )

    def render(self) -> None:
        self.clear_items()
        container = discord.ui.Container(accent_colour=BLUE)
        if self.mode == "results" and self.results:
            results_response = self.results
            lines = [
                f"## \N{RIGHT-POINTING MAGNIFYING GLASS} Wiki results for \N{LEFT DOUBLE QUOTATION MARK}{esc(clip(results_response.query, 60))}\N{RIGHT DOUBLE QUOTATION MARK}",
                f"-# {results_response.total:,} matches \N{MIDDLE DOT} {WIKI_LANGS.get(self.lang, self.lang)} edition",
            ]
            for n, h in enumerate(results_response.hits, 1):
                lines.append(
                    f"**{n}. {esc(h.title)}**"
                    + (f" -# \N{RIGHTWARDS ARROW WITH HOOK} {esc(h.redirect_from)}" if h.redirect_from else "")
                    + f"\n{esc(clip(h.snippet, 150))}"
                )
            container.add_item(text("\n".join(lines)))
            container.add_item(sep())
            container.add_item(
                discord.ui.ActionRow(
                    select(
                        [opt(h.title, h.title, desc=h.snippet or None, emoji="\N{OPEN BOOK}") for h in results_response.hits],
                        lambda i, v: self.run(i, self.open, v),
                        "Open an article\N{HORIZONTAL ELLIPSIS}",
                    )
                )
            )
            container.add_item(
                discord.ui.ActionRow(
                    self.modal_button(
                        "New search",
                        "\N{LEFT-POINTING MAGNIFYING GLASS}",
                        title="Search the wiki",
                        label="Search",
                        placeholder="redstone comparator",
                        on_query=lambda i, q: self.run(i, self.do_search, q),
                    ),
                    button(
                        "Search on wiki",
                        url=self.client.search_url(results_response.query),
                        emoji="\N{GLOBE WITH MERIDIANS}",
                    ),
                    *(
                        [
                            button(
                                "Back",
                                lambda i: self.run(i, self.back),
                                emoji="\N{LEFTWARDS ARROW WITH HOOK}\N{VARIATION SELECTOR-16}",
                            )
                        ]
                        if self.article
                        else []
                    ),
                )
            )
        elif self.article:
            article_instance = self.article
            label = next((label_text for entry_key, label_text, _ in self.entries if entry_key == self.key), "")
            meta = [f"{WIKI_LANGS.get(article_instance.lang, article_instance.lang)} edition"]
            if article_instance.last_modified and (t := epoch(article_instance.last_modified)):
                meta.append(f"edited <t:{t}:R>" + (f" by {esc(article_instance.last_editor)}" if article_instance.last_editor else ""))
            sep_dot = " \N{MIDDLE DOT} "
            container.add_item(
                head(
                    f"# {esc(article_instance.title)}\n-# {sep_dot.join(meta)}\n-# {esc(clip(label, 60))}"
                    + (f" \N{MIDDLE DOT} page {self.pi + 1}/{len(self.pages)}" if len(self.pages) > 1 else ""),
                    article_instance.thumbnail,
                )
            )
            container.add_item(sep())
            container.add_item(text(self.pages[self.pi]))
            container.add_item(sep())
            container.add_item(
                discord.ui.ActionRow(
                    select(
                        [opt(label, key, emoji=emoji_icon, default=key == self.key) for key, label, emoji_icon in self.entries],
                        lambda i, v: self.run(i, self._jump, v),
                        "Jump to section\N{HORIZONTAL ELLIPSIS}",
                    )
                )
            )
            if article_instance.related:
                container.add_item(
                    discord.ui.ActionRow(
                        select(
                            [opt(t, t, emoji="\N{LINK SYMBOL}") for t in article_instance.related[:25]],
                            lambda i, v: self.run(i, self.open, v),
                            "Related articles\N{HORIZONTAL ELLIPSIS}",
                        )
                    )
                )
            container.add_item(
                discord.ui.ActionRow(
                    button(
                        "Prev",
                        lambda i: self.run(i, self._page, -1),
                        emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
                        disabled=self.pi == 0,
                    ),
                    button(
                        "Next",
                        lambda i: self.run(i, self._page, 1),
                        emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
                        disabled=self.pi >= len(self.pages) - 1,
                    ),
                    button(
                        "Back",
                        lambda i: self.run(i, self.back),
                        emoji="\N{LEFTWARDS ARROW WITH HOOK}\N{VARIATION SELECTOR-16}",
                        disabled=not (self.trail or self.results),
                    ),
                    self.modal_button(
                        "Search",
                        "\N{LEFT-POINTING MAGNIFYING GLASS}",
                        title="Search the wiki",
                        label="Search",
                        placeholder="enchanting table",
                        on_query=lambda i, q: self.run(i, self.do_search, q),
                    ),
                    button("Random", lambda i: self.run(i, self.random), emoji="\N{GAME DIE}"),
                )
            )
            container.add_item(
                discord.ui.ActionRow(
                    button("Open on wiki", url=article_instance.url, emoji="\N{GLOBE WITH MERIDIANS}"),
                    button("History & authors", url=article_instance.history_url, emoji="\N{SCROLL}"),
                    button(
                        "CC BY-NC-SA 3.0",
                        url=LICENSE_URL,
                        emoji="\N{SCALES}\N{VARIATION SELECTOR-16}",
                    ),
                )
            )
        container.add_item(text(self._footer()))
        self.add_item(container)


@dataclass
class Described:
    title: str
    subtitle: str
    lines: list[str]
    wiki_title: str
    texture: str | None = None


class DataView(BaseView):
    COLOR: ClassVar = {"item": GOLD, "mob": RED, "enchant": 0x8E44AD, "effect": 0x1ABC9C, "biome": GREEN}
    thumb: str | None = None

    def __init__(
        self,
        cog: Minecraft,
        user_id: int,
        kind: str,
        version: str,
        name: str,
        versions: list[str],
    ) -> None:
        super().__init__(cog, user_id)
        self.kind, self.version, self.name, self.versions = kind, version, name, versions
        self.d: Described | None = None

    async def load(self, version: str | None = None) -> None:
        version = version or self.version
        d = await self.cog.describe(self.kind, version, self.name)
        if d is None:
            msg = f"`{self.name}` doesn't exist in **{version}**."
            raise MCError(msg)
        self.version, self.d = version, d

    def render(self) -> None:
        self.clear_items()
        game_data = self.d
        assert game_data
        ui_container = discord.ui.Container(accent_colour=self.COLOR.get(self.kind, GREEN))
        thumb = game_data.texture or self.thumb
        ui_container.add_item(
            head(
                f"## {esc(game_data.title)}\n-# {game_data.subtitle} \N{MIDDLE DOT} data for **{self.version}**",
                thumb,
            )
        )
        ui_container.add_item(sep())
        ui_container.add_item(text("\n".join(game_data.lines)))
        ui_container.add_item(sep())
        opts = [opt(v, v, default=v == self.version, desc="newest" if i == 0 else None) for i, v in enumerate(self.versions[:25])]
        ui_container.add_item(
            discord.ui.ActionRow(
                select(
                    opts,
                    lambda i, v: self.run(i, self.load, v),
                    "Compare another game version\N{HORIZONTAL ELLIPSIS}",
                )
            )
        )
        wiki_url = f"https://minecraft.wiki/w/{quote(game_data.wiki_title.replace(' ', '_'))}"
        row = [
            button("Read wiki in Discord", self._open_wiki, emoji="\N{OPEN BOOK}"),
            button("Wiki page", url=wiki_url, emoji="\N{GLOBE WITH MERIDIANS}"),
        ]
        if game_data.texture:
            row.append(
                button(
                    "Texture PNG",
                    url=game_data.texture,
                    emoji="\N{FRAME WITH PICTURE}\N{VARIATION SELECTOR-16}",
                )
            )
        ui_container.add_item(discord.ui.ActionRow(*row))
        ui_container.add_item(
            text(
                "-# Game data: PrismarineJS/minecraft-data (MIT) \N{MIDDLE DOT} textures: PrismarineJS/minecraft-assets, art \N{COPYRIGHT SIGN} Mojang Studios\n"
                + DISCLAIMER
            )
        )
        self.add_item(ui_container)

    async def _open_wiki(self, interaction: discord.Interaction) -> None:
        assert self.d
        await interaction.response.defer()
        try:
            v = WikiView(self.cog, interaction.user.id)
            await v.open(self.d.wiki_title, push=False)
        except (WikiError, MCError) as e:
            await interaction.followup.send(f"\N{CROSS MARK} {e}", ephemeral=True)
            return
        v.render()
        v.message = await interaction.followup.send(view=v, allowed_mentions=discord.AllowedMentions.none(), wait=True)


class VersionView(BaseView):
    def __init__(
        self,
        cog: Minecraft,
        user_id: int,
        manifest: dict,
        entry: dict,
        detail: dict | None,
        protocol: dict | None,
    ) -> None:
        super().__init__(cog, user_id)
        self.manifest, self.entry, self.detail, self.proto = manifest, entry, detail, protocol
        self.kind = entry.get("type") if entry.get("type") in ("release", "snapshot") else "release"

    async def pick(self, vid: str) -> None:
        entry = next((v for v in self.manifest["versions"] if v["id"] == vid), None)
        if not entry:
            msg = f"Unknown version `{esc(vid)}`."
            raise MCError(msg)
        self.entry = entry
        self.detail, self.proto = await self.cog.version_detail(entry)

    async def search(self, q: str) -> None:
        vs = self.manifest["versions"]
        hit = next((v for v in vs if v["id"].lower() == q.lower()), None) or next((v for v in vs if q.lower() in v["id"].lower()), None)
        if not hit:
            msg = f"No version matching `{esc(q)}`."
            raise MCError(msg)
        await self.pick(hit["id"])

    async def toggle(self) -> None:
        self.kind = "snapshot" if self.kind == "release" else "release"

    def render(self) -> None:
        self.clear_items()
        m, entry_data, details, p = self.manifest, self.entry, self.detail or {}, self.proto
        latest = m["latest"]
        rel = epoch(entry_data.get("releaseTime"))
        lines = [f"**Type** `{entry_data.get('type')}`" + (f" \N{MIDDLE DOT} released <t:{rel}:D> (<t:{rel}:R>)" if rel else "")]
        if p:
            lines.append(
                f"**Protocol version** `{p.get('version')}`"
                + (f" (0x{int(p['version']):X})" if isinstance(p.get("version"), int) and p["version"] > 0 else "")
            )
            if p.get("dataVersion") not in (None, -1):
                lines.append(f"**Data version** `{p['dataVersion']}` *(world save version)*")
        if details.get("javaVersion"):
            lines.append(f"**Requires Java** {details['javaVersion'].get('majorVersion')} (`{details['javaVersion'].get('component')}`)")
        pack_version = details.get("pack_version")
        if pack_version is not None:
            lines.append(
                "**Pack format** "
                + (
                    f"resource `{pack_version.get('resource')}` \N{MIDDLE DOT} data `{pack_version.get('data')}`"
                    if isinstance(pack_version, dict)
                    else f"`{pack_version}`"
                )
            )
        if details.get("assetIndex"):
            lines.append(f"**Asset index** `{details['assetIndex'].get('id')}`")
        downloads = details.get("downloads") or {}
        for key, label in (
            ("client", "Client JAR"),
            ("server", "Server JAR"),
            ("client_mappings", "Client mappings"),
            ("server_mappings", "Server mappings"),
        ):
            if downloads.get(key):
                lines.append(f"**{label}** {size(downloads[key].get('size'))}")
        if details.get("minimumLauncherVersion"):
            lines.append(f"**Min. launcher** `{details['minimumLauncherVersion']}`")
        lines.append(f"\n**Latest release** `{latest['release']}` \N{MIDDLE DOT} **Latest snapshot** `{latest['snapshot']}`")
        version_container = discord.ui.Container(accent_colour=GREEN if entry_data.get("type") == "release" else GOLD)
        version_container.add_item(
            head(
                f"## \N{PACKAGE} Java Edition {esc(entry_data['id'])}\n-# Mojang version manifest"
                + (" \N{MIDDLE DOT} MC data: PrismarineJS" if p else "")
            )
        )
        version_container.add_item(sep())
        version_container.add_item(text("\n".join(lines)))
        version_container.add_item(sep())
        pool = [v for v in m["versions"] if v.get("type") == self.kind][:25]
        if not any(v["id"] == entry_data["id"] for v in pool):
            pool = [entry_data, *pool[:24]]
        version_container.add_item(
            discord.ui.ActionRow(
                select(
                    [
                        opt(
                            v["id"],
                            v["id"],
                            default=v["id"] == entry_data["id"],
                            desc=(v.get("releaseTime") or "")[:10],
                        )
                        for v in pool
                    ],
                    lambda i, v: self.run(i, self.pick, v),
                    f"Browse {self.kind}s\N{HORIZONTAL ELLIPSIS}",
                )
            )
        )
        version_container.add_item(
            discord.ui.ActionRow(
                button(
                    "Latest release",
                    lambda i: self.run(i, self.pick, latest["release"]),
                    emoji="\N{LABEL}\N{VARIATION SELECTOR-16}",
                ),
                button(
                    "Latest snapshot",
                    lambda i: self.run(i, self.pick, latest["snapshot"]),
                    emoji="\N{TEST TUBE}",
                ),
                button(
                    "Show snapshots" if self.kind == "release" else "Show releases",
                    lambda i: self.run(i, self.toggle),
                    emoji="\N{TWISTED RIGHTWARDS ARROWS}",
                ),
                self.modal_button(
                    "Find",
                    "\N{LEFT-POINTING MAGNIFYING GLASS}",
                    title="Find a version",
                    label="Version id",
                    placeholder="26.1 or 25w37a",
                    on_query=lambda i, q: self.run(i, self.search, q),
                    max_length=40,
                ),
            )
        )
        links = [
            button(
                "Wiki page",
                url=f"https://minecraft.wiki/w/Java_Edition_{quote(entry_data['id'].replace(' ', '_'))}",
                emoji="\N{OPEN BOOK}",
            )
        ]
        if downloads.get("server"):
            links.append(
                button(
                    "Server JAR",
                    url=downloads["server"]["url"],
                    emoji="\N{DESKTOP COMPUTER}\N{VARIATION SELECTOR-16}",
                )
            )
        if downloads.get("client"):
            links.append(button("Client JAR", url=downloads["client"]["url"], emoji="\N{VIDEO GAME}"))
        if entry_data.get("url"):
            links.append(button("Version JSON", url=entry_data["url"], emoji="\N{RECEIPT}"))
        version_container.add_item(discord.ui.ActionRow(*links))
        version_container.add_item(
            text("-# Source: Mojang launcher metadata \N{MIDDLE DOT} protocol/data versions: PrismarineJS/minecraft-data\n" + DISCLAIMER)
        )
        self.add_item(version_container)


class TTLCache:
    def __init__(self, maxsize: int = 600) -> None:
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


class Minecraft(commands.Cog):
    """Everything Minecraft: servers, players, wiki, items, and versions."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.session = self.bot.http_session
        self.cache = TTLCache()
        self._wikis: dict[str, WikiClient] = {}
        self._idx: dict[tuple, dict] = {}

    def wiki(self, lang: str = "en") -> WikiClient:
        lang = lang if lang in WIKI_LANGS else "en"
        if lang not in self._wikis:
            self._wikis[lang] = WikiClient(self.bot, lang=lang)
        return self._wikis[lang]

    async def http(
        self,
        url: str,
        *,
        params: dict | None = None,
        ttl: float = 60,
        kind: str = "json",
        method: str = "GET",
        ok: tuple[int, ...] = (200,),
        fresh: bool = False,
    ) -> tuple[int, Any]:
        key = (method, url, tuple(sorted((params or {}).items())))
        if not fresh and (hit := self.cache.get(key)) is not None:
            return hit
        assert self.session
        try:
            async with self.session.request(method, url, params=params) as r:
                status, data = r.status, None
                if status in ok and kind == "json":
                    data = await r.json(content_type=None)
                elif status in ok and kind == "text":
                    data = await r.text()
        except TimeoutError:
            msg = "The upstream service timed out. Try again in a moment."
            raise MCError(msg) from None
        except aiohttp.ClientError as e:
            msg = f"Couldn't reach the upstream service ({type(e).__name__})."
            raise MCError(msg) from None
        res = (status, data)
        if status in ok or status in (204, 404):
            self.cache.set(key, res, ttl)
        return res

    async def send(self, ctx: commands.Context[Any], view: BaseView) -> None:
        view.render()
        view.message = await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.group(name="minecraft", aliases=["mc"], invoke_without_command=True)
    async def mc(self, ctx: commands.Context[Any]) -> None:
        """Everything Minecraft: servers, players, wiki, items, and versions."""
        await ctx.send_help(ctx.command)

    async def fetch_server(self, address: str, edition: str, fresh: bool = False) -> tuple[str, dict]:
        addr = clean_address(address)
        last: tuple[str, dict] | None = None
        for ed in ["java", "bedrock"] if edition == "auto" else [edition]:
            url = f"{MCSRV}/{'bedrock/' if ed == 'bedrock' else ''}3/{quote(addr, safe=':[]')}"
            status, data = await self.http(url, ttl=60, fresh=fresh)
            if status == 429:
                msg = "The status API is rate-limiting us. Try again in a minute."
                raise MCError(msg)
            if not isinstance(data, dict):
                msg = f"The status API returned HTTP {status}."
                raise MCError(msg)
            last = (ed, data)
            if data.get("online"):
                return last
        assert last
        return last

    async def protocol_names(self, edition: str, proto: int | None) -> str | None:
        if proto is None:
            return None
        path = "pc" if edition == "java" else "bedrock"
        try:
            _, data = await self.http(f"{DATA_RAW}/{path}/common/protocolVersions.json", ttl=21600)
        except MCError:
            return None
        names = [e["minecraftVersion"] for e in data or [] if e.get("version") == proto and RELEASE_RE.match(str(e.get("minecraftVersion", "")))]
        if not names:
            return None
        names.reverse()
        return names[0] if len(names) == 1 else f"{names[0]} \N{EN DASH} {names[-1]}"

    @mc.command(name="server")
    @commands.cooldown(2, 10.0, commands.BucketType.user)
    async def server(
        self,
        ctx: commands.Context[Any],
        address: str = commands.parameter(description="Hostname or host:port"),
        edition: Literal["auto", "java", "bedrock"] = commands.parameter(
            default="auto",
            description="Which edition (auto tries Java, then Bedrock)",
        ),
    ) -> None:
        """Java/Bedrock server status, players, plugins and technical info."""
        async with ctx.typing():
            ed, data = await self.fetch_server(address, edition)
            mapped = await self.protocol_names(ed, (data.get("protocol") or {}).get("version"))
        await self.send(
            ctx,
            ServerView(self, ctx.author.id, clean_address(address), edition, ed, data, mapped),
        )

    async def get_profile(self, query: str) -> Profile:
        trimmed_query = query.strip()
        if UUID_RE.match(trimmed_query):
            uid = trimmed_query.replace("-", "").lower()
        elif NAME_RE.match(trimmed_query):
            status_code, d = await self.http(MOJANG_NAME + trimmed_query, ttl=600)
            if status_code == 429:
                msg = "Mojang is rate-limiting lookups. Try again shortly."
                raise MCError(msg)
            if not d:
                msg = f"No Java Edition account named **{esc(trimmed_query)}**. (Bedrock gamertags aren't supported.)"
                raise MCError(msg)
            uid = d["id"]
        else:
            msg = "Enter a username (3-16 letters, numbers, `_`) or a UUID."
            raise MCError(msg)
        status_code, prof = await self.http(MOJANG_PROFILE + uid, ttl=600)
        if status_code == 429:
            msg = "Mojang is rate-limiting profile lookups (limited per UUID). Try again in a minute."
            raise MCError(msg)
        if not prof:
            msg = "No profile exists for that UUID."
            raise MCError(msg)
        profile = Profile(uuid=uuidlib.UUID(uid), name=prof.get("name", trimmed_query), legacy=bool(prof.get("legacy")))
        for prop in prof.get("properties", []):
            if prop.get("name") == "textures":
                try:
                    tex = json.loads(base64.b64decode(prop["value"]))
                except ValueError, KeyError:
                    break
                skin = tex.get("textures", {}).get("SKIN") or {}
                cape = tex.get("textures", {}).get("CAPE") or {}
                profile.skin_url = skin.get("url", "").replace("http://", "https://") or None
                profile.model = (skin.get("metadata") or {}).get("model", "classic")
                profile.cape_url = cape.get("url", "").replace("http://", "https://") or None
                if tex.get("timestamp"):
                    profile.timestamp = int(tex["timestamp"]) // 1000
        return profile

    @mc.command(name="player")
    @commands.cooldown(2, 10.0, commands.BucketType.user)
    async def player(
        self,
        ctx: commands.Context[Any],
        player: str = commands.parameter(description="Username or UUID"),
    ) -> None:
        """Look up a Java Edition player (UUIDs, skin model, cape, renders)."""
        async with ctx.typing():
            profile = await self.get_profile(player)
        await self.send(ctx, PlayerView(self, ctx.author.id, profile))

    @mc.command(name="skin")
    @commands.cooldown(2, 10.0, commands.BucketType.user)
    async def skin(
        self,
        ctx: commands.Context[Any],
        player: str = commands.parameter(description="Username or UUID"),
    ) -> None:
        """View a player's skin and cape."""
        async with ctx.typing():
            profile = await self.get_profile(player)
        await self.send(ctx, PlayerView(self, ctx.author.id, profile, tab="skin"))

    @mc.command(name="wiki")
    @commands.cooldown(2, 8.0, commands.BucketType.user)
    async def wiki_cmd(
        self,
        ctx: commands.Context[Any],
        *,
        query: str = commands.parameter(description="Article title or search terms"),
    ) -> None:
        """Search and read the Minecraft Wiki."""
        language = "en"
        if language not in WIKI_LANGS:
            valid = ", ".join(f"`{c}`" for c in WIKI_LANGS)
            msg = f"Unsupported language `{esc(language)}`. Available editions: {valid}."
            raise MCError(msg)
        async with ctx.typing():
            view = WikiView(self, ctx.author.id, language)
            await view.do_search(query)
        await self.send(ctx, view)

    async def wiki_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        lang = getattr(interaction.namespace, "language", None) or "en"
        try:
            titles = await self.wiki(lang).opensearch(current, 25)
        except WikiError:
            return []
        return [app_commands.Choice(name=clip(t, 100), value=clip(t, 100)) for t in titles]

    async def manifest(self) -> dict:
        _st, d = await self.http(MANIFEST, ttl=300)
        if not d:
            msg = "Couldn't load Mojang's version manifest."
            raise MCError(msg)
        return d

    async def version_detail(self, entry: dict) -> tuple[dict | None, dict | None]:
        detail = None
        with contextlib.suppress(MCError):
            _st, detail = await self.http(entry["url"], ttl=3600)
        proto = None
        try:
            _, plist = await self.http(f"{DATA_RAW}/pc/common/protocolVersions.json", ttl=21600)
            proto = next((p for p in plist or [] if p.get("minecraftVersion") == entry["id"]), None)
        except MCError:
            pass
        return detail, proto

    @mc.command(name="version")
    @commands.cooldown(2, 8.0, commands.BucketType.user)
    async def version(
        self,
        ctx: commands.Context[Any],
        version: str | None = commands.parameter(
            default=None,
            description="Version id (default: latest release)",
        ),
    ) -> None:
        """Browse Minecraft: Java Edition versions (protocol, data version, jars, Java)."""
        async with ctx.typing():
            m = await self.manifest()
            vid = version or m["latest"]["release"]
            entry = next((v for v in m["versions"] if v["id"].lower() == vid.lower()), None)
            if not entry:
                msg = f"Unknown version `{esc(vid)}`."
                raise MCError(msg)
            detail, proto = await self.version_detail(entry)
        await self.send(ctx, VersionView(self, ctx.author.id, m, entry, detail, proto))

    async def version_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        try:
            m = await self.manifest()
        except MCError:
            return []
        c = current.lower()
        out = [v for v in m["versions"] if c in v["id"].lower()][:25]
        return [app_commands.Choice(name=f"{v['id']} ({v['type']})", value=v["id"]) for v in out]

    async def mc_paths(self) -> dict:
        _, data_paths = await self.http(f"{DATA_RAW}/dataPaths.json", ttl=21600)
        if not data_paths:
            msg = "Couldn't load Minecraft game data (GitHub unreachable)."
            raise MCError(msg)
        return data_paths["pc"]

    async def mc_versions(self) -> list[str]:
        return [v for v in await self.mc_paths() if RELEASE_RE.match(v)][::-1]

    async def resolve_version(self, v: str | None) -> str:
        available_versions = await self.mc_versions()
        if not v:
            return available_versions[0]
        paths = await self.mc_paths()
        if v not in paths:
            msg = f"No game data for `{esc(v)}`."
            raise MCError(msg)
        return v

    async def mc_data(self, ver: str, kind: str) -> Any:
        paths = await self.mc_paths()
        data_path = (paths.get(ver) or {}).get(kind)
        if not data_path:
            msg = f"No `{kind}` data for {ver}."
            raise MCError(msg)
        _, d = await self.http(f"{DATA_RAW}/{data_path}/{kind}.json", ttl=21600)
        if d is None:
            msg = f"Couldn't load `{kind}` data for {ver}."
            raise MCError(msg)
        return d

    async def mc_index(self, ver: str, kind: str, key: str = "name") -> dict:
        k = (ver, kind, key)
        if k not in self._idx:
            if len(self._idx) > 60:
                self._idx.clear()
            data = await self.mc_data(ver, kind)
            self._idx[k] = {e[key]: e for e in data}
        return self._idx[k]

    async def mc_opt_index(self, ver: str, kind: str, key: str = "name") -> dict:
        try:
            return await self.mc_index(ver, kind, key)
        except MCError:
            return {}

    async def texture_url(self, ver: str, name: str, block_first: bool) -> str | None:
        folders = ["blocks", "items"] if block_first else ["items", "blocks"]
        cands = [f"{f}/{n}" for f in folders for n in (name, f"{name}_top", f"{name}_front")]
        versions = [ver]
        latest = (await self.mc_versions())[0]
        if latest != ver:
            versions.append(latest)
        for v in versions:
            urls = [f"{ASSETS_RAW}/{v}/{c}.png" for c in cands]
            res = await asyncio.gather(
                *(self.http(u, method="HEAD", kind="none", ttl=21600) for u in urls),
                return_exceptions=True,
            )
            for u, r in zip(urls, res, strict=False):
                if isinstance(r, tuple) and r[0] == 200:
                    return u
        return None

    async def wiki_thumb(self, title: str) -> str | None:
        try:
            return (await self.wiki("en").get_article(title)).thumbnail
        except WikiError:
            return None

    @staticmethod
    def _recipes_text(recipes: list[dict], id2name: dict[int, str]) -> str:
        out = []
        for r in recipes[:3]:
            if "inShape" in r:
                flat = [c for row in r["inShape"] for c in row]
                kind = f"shaped {max(len(x) for x in r['inShape'])}\N{MULTIPLICATION SIGN}{len(r['inShape'])}"
            else:
                flat, kind = r.get("ingredients", []), "shapeless"
            ids = [c["id"] if isinstance(c, dict) else c for c in flat if c not in (None, -1)]
            ing = ", ".join(f"{n}\N{MULTIPLICATION SIGN} {id2name.get(i, '?')}" for i, n in Counter(ids).items())
            out.append(f"\N{BULLET} *{kind}* \N{RIGHTWARDS ARROW} \N{MULTIPLICATION SIGN}{(r.get('result') or {}).get('count', 1)}: {ing}")
        return "\n".join(out)

    async def describe(self, kind: str, ver: str, name: str) -> Described | None:
        f = {
            "item": self._fetch_item_details,
            "mob": self._d_mob,
            "enchant": self._d_ench,
            "effect": self._d_effect,
            "biome": self._d_biome,
        }[kind]
        return await f(ver, name)

    async def _fetch_item_details(self, ver: str, name: str) -> Described | None:  # noqa: PLR0912
        items, blocks = await self.mc_opt_index(ver, "items"), await self.mc_opt_index(ver, "blocks")
        item, block = items.get(name), blocks.get(name)
        if not item and not block:
            return None
        base = item or block
        disp = base["displayName"]
        formatted_item_details = [f"**ID** `minecraft:{name}`"]
        if item:
            formatted_item_details.append(f"**Registry ID** `{item['id']}` *(changes between versions)*")
            formatted_item_details.append(f"**Stack size** {item['stackSize']}")
            if item.get("maxDurability"):
                formatted_item_details.append(f"**Durability** {item['maxDurability']:,}")
            id2 = {e["id"]: e["name"] for e in items.values()}
            if item.get("repairWith"):
                formatted_item_details.append("**Repair with** " + ", ".join(f"`{r}`" for r in item["repairWith"]))
            if item.get("enchantCategories"):
                formatted_item_details.append("**Enchant tags** " + ", ".join(f"`{c}`" for c in item["enchantCategories"][:8]))
        else:
            id2 = {e["id"]: e["name"] for e in items.values()}
            formatted_item_details.append("**Item form** none (block only)")
        if block:
            formatted_item_details.append("\n**\N{BRICK} Block**")
            formatted_item_details.append(f"**Hardness** {block['hardness']} \N{MIDDLE DOT} **Blast resistance** {block['resistance']}")
            formatted_item_details.append(
                f"**Light emitted** {block.get('emitLight', 0)} \N{MIDDLE DOT} **Light filtered** {block.get('filterLight', 0)}"
            )
            formatted_item_details.append(
                f"**Transparent** {'yes' if block.get('transparent') else 'no'} \N{MIDDLE DOT} **Diggable** {'yes' if block.get('diggable') else 'no'} \N{MIDDLE DOT} **Hitbox** `{block.get('boundingBox')}`"
            )
            if block.get("material"):
                formatted_item_details.append(f"**Mining tag** `{block['material']}`")
            if block.get("harvestTools"):
                formatted_item_details.append("**Harvest tools** " + ", ".join(f"`{id2.get(int(k), k)}`" for k in list(block["harvestTools"])[:10]))
            if block.get("drops"):
                formatted_item_details.append(
                    "**Drops** " + ", ".join(f"`{id2.get(d if isinstance(d, int) else d.get('drop'), '?')}`" for d in block["drops"][:8])
                )
            formatted_item_details.append(
                f"**State IDs** {block.get('minStateId')}\N{EN DASH}{block.get('maxStateId')} (default {block.get('defaultState')})"
            )
            for s in (block.get("states") or [])[:6]:
                vals = f": {', '.join(map(str, s['values'][:8]))}" if s.get("values") else f" ({s['num_values']} values)"
                formatted_item_details.append(f"\N{BULLET} state `{s['name']}` *{s['type']}*{vals}")
        foods = await self.mc_opt_index(ver, "foods")
        if fd := foods.get(name):
            formatted_item_details.append(
                f"\n**\N{MEAT ON BONE} Food** restores {fd['foodPoints']} hunger ({fd['foodPoints'] / 2:g} drumsticks) \N{MIDDLE DOT} saturation {fd['saturation']}"
            )
        if item:
            try:
                rec = (await self.mc_data(ver, "recipes")).get(str(item["id"]))
            except MCError:
                rec = None
            if rec:
                formatted_item_details.append("\n**\N{HAMMER} Crafting**\n" + self._recipes_text(rec, id2))
        formatted_item_details.append(
            f"\n**Commands** `/give @s minecraft:{name}`" + (f" \N{MIDDLE DOT} `/setblock ~ ~ ~ minecraft:{name}`" if block else "")
        )
        tex = await self.texture_url(ver, name, block_first=bool(block and not item))
        return Described(
            disp,
            "Item" + (" & Block" if item and block else "") if item else "Block",
            formatted_item_details,
            disp,
            tex,
        )

    async def _d_mob(self, ver: str, name: str) -> Described | None:
        entity_data = (await self.mc_index(ver, "entities")).get(name)
        if not entity_data:
            return None
        L = [
            f"**ID** `minecraft:{name}`",
            f"**Registry ID** `{entity_data['id']}`",
            f"**Type** {entity_data.get('type', '?')} \N{MIDDLE DOT} **Category** {entity_data.get('category', '?')}",
            f"**Hitbox** {entity_data.get('width')} wide \N{MULTIPLICATION SIGN} {entity_data.get('height')} tall (blocks)",
            f"**Summon** `/summon minecraft:{name}`",
        ]
        return Described(entity_data["displayName"], "Entity", L, entity_data["displayName"], await self.wiki_thumb(entity_data["displayName"]))

    async def _d_ench(self, ver: str, name: str) -> Described | None:
        enchantment_data = (await self.mc_index(ver, "enchantments")).get(name)
        if not enchantment_data:
            return None
        min_cost_data, max_cost = enchantment_data.get("minCost", {}), enchantment_data.get("maxCost", {})
        excl = ", ".join(f"`{x}`" for x in enchantment_data.get("exclude", [])) or "none"
        L = [
            f"**ID** `minecraft:{name}`",
            f"**Max level** {enchantment_data['maxLevel']} \N{MIDDLE DOT} **Category** `{enchantment_data.get('category')}`",
            f"**Weight** {enchantment_data.get('weight')} (higher = more common)",
            f"**Min cost** {min_cost_data.get('a', 0)}\N{MIDDLE DOT}lvl + {min_cost_data.get('b', 0)} \N{MIDDLE DOT} **Max cost** {max_cost.get('a', 0)}\N{MIDDLE DOT}lvl + {max_cost.get('b', 0)}",
            f"**Treasure only** {'yes' if enchantment_data.get('treasureOnly') else 'no'} \N{MIDDLE DOT} **Curse** {'yes' if enchantment_data.get('curse') else 'no'}",
            f"**Tradeable** {'yes' if enchantment_data.get('tradeable') else 'no'} \N{MIDDLE DOT} **Discoverable** {'yes' if enchantment_data.get('discoverable') else 'no'}",
            f"**Incompatible with** {excl}",
            f"**Command** `/enchant @s minecraft:{name} {enchantment_data['maxLevel']}`",
        ]
        return Described(
            enchantment_data["displayName"], "Enchantment", L, enchantment_data["displayName"], await self.wiki_thumb(enchantment_data["displayName"])
        )

    async def _d_effect(self, ver: str, name: str) -> Described | None:
        effect_data = (await self.mc_index(ver, "effects")).get(name)
        if not effect_data:
            return None
        rid = snake(effect_data["name"])
        L = [
            f"**ID** `minecraft:{rid}`",
            f"**Registry ID** `{effect_data['id']}`",
            f"**Kind** {effect_data.get('type', '?')}",
            f"**Command** `/effect give @s minecraft:{rid} 30 1`",
        ]
        return Described(
            effect_data["displayName"],
            "Status effect",
            L,
            effect_data["displayName"],
            await self.wiki_thumb(effect_data["displayName"]),
        )

    async def _d_biome(self, ver: str, name: str) -> Described | None:
        biome_data = (await self.mc_index(ver, "biomes")).get(name)
        if not biome_data:
            return None
        L = [
            f"**ID** `minecraft:{name}`",
            f"**Registry ID** `{biome_data['id']}`",
            f"**Category** {biome_data.get('category')} \N{MIDDLE DOT} **Dimension** {biome_data.get('dimension')}",
            f"**Temperature** {biome_data.get('temperature')} \N{MIDDLE DOT} **Precipitation** {'yes' if biome_data.get('has_precipitation') else 'no'}",
        ]
        if isinstance(biome_data.get("color"), int):
            L.append(f"**Map colour** `#{biome_data['color']:06X}`")
        L.append(f"**Locate** `/locate biome minecraft:{name}`")
        return Described(biome_data["displayName"], "Biome", L, biome_data["displayName"], await self.wiki_thumb(biome_data["displayName"]))

    async def _open_data(self, ctx: commands.Context[Any], kind: str, name: str, version: str | None) -> None:
        async with ctx.typing():
            ver = await self.resolve_version(version)
            versions = await self.mc_versions()
            if ver not in versions:
                versions = [ver, *versions[:24]]
            view = DataView(self, ctx.author.id, kind, ver, name, versions)
            await view.load()
        await self.send(ctx, view)

    async def _data_choices(self, interaction: discord.Interaction, current: str, files: list[str]) -> list[app_commands.Choice[str]]:
        try:
            ver = await self.resolve_version(getattr(interaction.namespace, "version", None))
            merged: dict[str, str] = {}
            for f in files:
                for n, e in (await self.mc_opt_index(ver, f)).items():
                    merged.setdefault(n, e.get("displayName", n))
        except MCError:
            return []
        current_input = current.lower().replace(" ", "_")
        scored = []
        for n, disp in merged.items():
            dl = disp.lower()
            if current_input in n or current_input in dl:
                scored.append(
                    (
                        0
                        if n == current_input or dl == current.lower()
                        else 1
                        if n.startswith(current_input) or dl.startswith(current.lower())
                        else 2,
                        len(n),
                        n,
                        disp,
                    )
                )
        scored.sort()
        return [app_commands.Choice(name=clip(d, 100), value=n) for _, _, n, d in scored[:25]]

    async def _version_choices(self, current: str) -> list[app_commands.Choice[str]]:
        try:
            vs = await self.mc_versions()
        except MCError:
            return []
        return [app_commands.Choice(name=v, value=v) for v in vs if current.lower() in v.lower()][:25]

    @mc.command(name="item")
    @commands.cooldown(3, 10.0, commands.BucketType.user)
    async def item(
        self,
        ctx: commands.Context[Any],
        name: str = commands.parameter(description="Item or block"),
        version: str | None = commands.parameter(
            default=None,
            description="Game version (default: latest release)",
        ),
    ) -> None:
        """Item/block data: IDs, stack size, hardness, drops, recipes, states, texture."""
        await self._open_data(ctx, "item", name.lower().replace(" ", "_").replace("minecraft:", ""), version)

    async def item_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._data_choices(interaction, current, ["items", "blocks"])

    async def item_vac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._version_choices(current)

    @mc.command(name="mob")
    @commands.cooldown(3, 10.0, commands.BucketType.user)
    async def mob(
        self,
        ctx: commands.Context[Any],
        name: str = commands.parameter(description="Mob / entity"),
        version: str | None = commands.parameter(
            default=None,
            description="Game version",
        ),
    ) -> None:
        """Entity data: ID, type, hitbox."""
        await self._open_data(ctx, "mob", name.lower().replace(" ", "_").replace("minecraft:", ""), version)

    async def mob_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._data_choices(interaction, current, ["entities"])

    async def mob_vac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._version_choices(current)

    @mc.command(name="enchant")
    @commands.cooldown(3, 10.0, commands.BucketType.user)
    async def enchant(
        self,
        ctx: commands.Context[Any],
        name: str = commands.parameter(description="Enchantment"),
        version: str | None = commands.parameter(
            default=None,
            description="Game version",
        ),
    ) -> None:
        """Enchantment data: levels, cost formula, exclusions."""
        await self._open_data(ctx, "enchant", name.lower().replace(" ", "_").replace("minecraft:", ""), version)

    async def enchant_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._data_choices(interaction, current, ["enchantments"])

    async def enchant_vac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._version_choices(current)

    @mc.command(name="effect")
    @commands.cooldown(3, 10.0, commands.BucketType.user)
    async def effect(
        self,
        ctx: commands.Context[Any],
        name: str = commands.parameter(description="Effect"),
        version: str | None = commands.parameter(
            default=None,
            description="Game version",
        ),
    ) -> None:
        """Status effect data."""
        await self._open_data(ctx, "effect", name, version)

    async def effect_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._data_choices(interaction, current, ["effects"])

    async def effect_vac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._version_choices(current)

    @mc.command(name="biome")
    @commands.cooldown(3, 10.0, commands.BucketType.user)
    async def biome(
        self,
        ctx: commands.Context[Any],
        name: str = commands.parameter(description="Biome"),
        version: str | None = commands.parameter(
            default=None,
            description="Game version",
        ),
    ) -> None:
        """Biome data: category, dimension, temperature."""
        await self._open_data(ctx, "biome", name.lower().replace(" ", "_").replace("minecraft:", ""), version)

    async def biome_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._data_choices(interaction, current, ["biomes"])

    async def biome_vac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._version_choices(current)

    @mc.command(name="about")
    async def about(self, ctx: commands.Context[Any]) -> None:
        """Data sources, licences and disclaimers for the Minecraft commands."""
        c = discord.ui.Container(accent_colour=GREEN)
        c.add_item(
            text(
                "## \N{PICK}\N{VARIATION SELECTOR-16} Minecraft commands: sources & licences\n"
                f"**Wiki text** \N{EM DASH} [Minecraft Wiki](https://minecraft.wiki), [CC BY-NC-SA 3.0]({LICENSE_URL}). Attribution, a history/authors link and the licence are shown on every article; "
                "text may be shortened or reformatted. Non-commercial use only; derivatives must stay under the same licence.\n"
                "**Server status** \N{EM DASH} [mcsrvstat.us](https://mcsrvstat.us)\n"
                "**Profiles, skins, versions** \N{EM DASH} Mojang public APIs; renders by [mc-heads.net](https://mc-heads.net)\n"
                "**Item/block/entity data** \N{EM DASH} [PrismarineJS/minecraft-data](https://github.com/PrismarineJS/minecraft-data) (MIT)\n"
                "**Textures** \N{EM DASH} [PrismarineJS/minecraft-assets](https://github.com/PrismarineJS/minecraft-assets); the artwork belongs to Mojang Studios.\n\n"
                "This bot is open source and free. " + DISCLAIMER.removeprefix("-# ")
            )
        )
        v = discord.ui.LayoutView(timeout=None)
        v.add_item(c)
        await ctx.send(view=v, allowed_mentions=discord.AllowedMentions.none())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Minecraft(bot))
