from __future__ import annotations

import math
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Literal

from PIL import Image, ImageChops, ImageDraw, ImageFont

from .parser import LogoList
from .utils import LogoRuntimeError, get_max_fills, get_max_gif_frames, get_max_pen_width, get_max_segments, get_max_turtles, get_max_word_length

MAX_COORD = 10_000.0

# Standard 16-color MSWLogo palette (indices 0..15)
PALETTE: dict[int, tuple[int, int, int]] = {
    0: (0, 0, 0),  # Black
    1: (0, 0, 255),  # Blue
    2: (0, 255, 0),  # Green (Lime)
    3: (0, 255, 255),  # Cyan (Aqua)
    4: (255, 0, 0),  # Red
    5: (255, 0, 255),  # Magenta
    6: (255, 255, 0),  # Yellow
    7: (255, 255, 255),  # White
    8: (155, 96, 59),  # Brown
    9: (197, 136, 18),  # Tan
    10: (100, 162, 64),  # Forest
    11: (120, 187, 187),  # Aqua
    12: (255, 149, 119),  # Salmon
    13: (144, 113, 208),  # Purple
    14: (255, 163, 0),  # Orange
    15: (183, 183, 183),  # Grey
}

COLORS: dict[str, tuple[int, int, int]] = {
    "BLACK": (0, 0, 0),
    "WHITE": (255, 255, 255),
    "RED": (255, 0, 0),
    "GREEN": (0, 128, 0),
    "LIME": (0, 255, 0),
    "BLUE": (0, 0, 255),
    "YELLOW": (255, 255, 0),
    "CYAN": (0, 255, 255),
    "AQUA": (0, 255, 255),
    "MAGENTA": (255, 0, 255),
    "FUSCHIA": (255, 0, 255),
    "ORANGE": (255, 165, 0),
    "PURPLE": (128, 0, 128),
    "VIOLET": (238, 130, 238),
    "PINK": (255, 192, 203),
    "BROWN": (165, 42, 42),
    "TAN": (210, 180, 140),
    "FOREST": (34, 139, 34),
    "SALMON": (250, 128, 114),
    "GRAY": (128, 128, 128),
    "GREY": (128, 128, 128),
    "SILVER": (192, 192, 192),
    "DARKGRAY": (64, 64, 64),
    "DARKGREY": (64, 64, 64),
    "LIGHTGRAY": (211, 211, 211),
    "LIGHTGREY": (211, 211, 211),
    "NAVY": (0, 0, 128),
    "TEAL": (0, 128, 128),
    "MAROON": (128, 0, 0),
    "OLIVE": (128, 128, 0),
    "GOLD": (255, 215, 0),
    "INDIGO": (75, 0, 130),
    "CORAL": (255, 127, 80),
    "TURQUOISE": (64, 224, 208),
    "SKYBLUE": (135, 206, 235),
}

# Require explicit '#' or '0x' prefix for hex colors so words like "ACE" or "BED" never match
_HEX_COLOR_RE = re.compile(r"^(?:#|0[xX])([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _clamp_coord(value: float) -> float:
    if not math.isfinite(value):
        msg = "Coordinate must be a finite number."
        raise LogoRuntimeError(msg)
    return max(-MAX_COORD, min(MAX_COORD, value))


def _require_finite(value: float, name: str = "Value") -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        msg = f"{name} must be a finite number."
        raise LogoRuntimeError(msg)
    return float(value)


def parse_color(value: Any) -> tuple[int, int, int]:  # noqa: PLR0912, PLR0915
    """
    Parses a Logo color specification:
    - RGB list/tuple of 3 integers in 0..255: `[255 0 128]`
    - MSWLogo palette index 0..15 (int or float or numeric word)
    - Named color word: `"RED`, `"BLUE`, etc.
    - Explicit hex color word: `"#FF0000`, `"#F00`, `"0xFF0000`
    Raises `LogoRuntimeError` for any unknown or invalid color.
    """
    if isinstance(value, LogoList):
        items = value.values
    elif isinstance(value, (list, tuple)):
        items = tuple(value)
    else:
        items = None

    if items is not None:
        if len(items) != 3:
            msg = f"RGB color list must have exactly 3 numbers, got {len(items)}."
            raise LogoRuntimeError(msg)
        rgb: list[int] = []
        for comp in items:
            try:
                fcomp = float(comp)
            except (TypeError, ValueError) as exc:
                msg = f"Invalid RGB component: {comp!r}."
                raise LogoRuntimeError(msg) from exc
            if not math.isfinite(fcomp) or not fcomp.is_integer():
                msg = f"RGB component must be an integer between 0 and 255, got {comp!r}."
                raise LogoRuntimeError(msg)
            icomp = int(fcomp)
            if icomp < 0 or icomp > 255:
                msg = f"RGB component must be between 0 and 255, got {icomp}."
                raise LogoRuntimeError(msg)
            rgb.append(icomp)
        return (rgb[0], rgb[1], rgb[2])

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        fval = float(value)
        if not math.isfinite(fval) or not fval.is_integer():
            msg = f"Color palette index must be an integer between 0 and 15, got {value!r}."
            raise LogoRuntimeError(msg)
        idx = int(fval)
        if idx in PALETTE:
            return PALETTE[idx]
        msg = f"Color palette index must be between 0 and 15, got {idx}."
        raise LogoRuntimeError(msg)

    if isinstance(value, str):
        cleaned = value.strip()
        cleaned = cleaned.removeprefix('"')
        upper = cleaned.upper()
        if upper in COLORS:
            return COLORS[upper]

        # Check integer palette index passed as string (e.g. "4)
        if re.fullmatch(r"[+-]?\d+", cleaned):
            idx = int(cleaned)
            if idx in PALETTE:
                return PALETTE[idx]
            msg = f"Color palette index must be between 0 and 15, got {idx}."
            raise LogoRuntimeError(msg)

        hex_match = _HEX_COLOR_RE.fullmatch(cleaned)
        if hex_match:
            hex_value = hex_match.group(1)
            if len(hex_value) == 3:
                r = int(hex_value[0] * 2, 16)
                g = int(hex_value[1] * 2, 16)
                b = int(hex_value[2] * 2, 16)
            else:
                r = int(hex_value[0:2], 16)
                g = int(hex_value[2:4], 16)
                b = int(hex_value[4:6], 16)
            return (r, g, b)

    msg = f"Unknown or invalid color: {value!r}."
    raise LogoRuntimeError(msg)


PenMode = Literal["PAINT", "ERASE", "REVERSE"]


@dataclass
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float
    color: tuple[int, int, int]
    width: int
    mode: PenMode = "PAINT"


@dataclass
class DotOp:
    x: float
    y: float
    color: tuple[int, int, int]
    size: int
    mode: PenMode = "PAINT"


@dataclass
class FillOp:
    x: float
    y: float
    color: tuple[int, int, int]


@dataclass
class PolygonFillOp:
    points: tuple[tuple[float, float], ...]
    fill_color: tuple[int, int, int]


@dataclass
class LabelOp:
    x: float
    y: float
    text: str
    color: tuple[int, int, int]
    height: int
    heading: float = 0.0


DrawOp = Segment | DotOp | FillOp | PolygonFillOp | LabelOp


@dataclass
class TurtleState:
    x: float
    y: float
    heading: float = 0.0
    pen_down: bool = True
    pen_mode: PenMode = "PAINT"
    pen_color: tuple[int, int, int] = (0, 0, 0)
    flood_color: tuple[int, int, int] | None = None
    pen_width: int = 2
    visible: bool = False
    label_height: int = 14
    poly_path: list[tuple[float, float]] | None = None


class Turtle:
    def __init__(self, width: int = 1000, height: int = 800) -> None:
        if width < 16 or width > 4096 or height < 16 or height > 4096:
            msg = "Canvas dimensions must be between 16 and 4096 pixels."
            raise LogoRuntimeError(msg)
        self.width = width
        self.height = height
        self.bg_color: tuple[int, int, int] = (255, 255, 255)

        self._turtles: dict[int, TurtleState] = {0: TurtleState(x=width / 2, y=height / 2)}
        self._active_ids: tuple[int, ...] = (0,)

        self.segments: list[Segment] = []
        self.ops: list[DrawOp] = []
        self._fill_count = 0

    @property
    def _primary(self) -> TurtleState:
        return self._turtles[self._active_ids[0]]

    def _iter_active(self) -> list[TurtleState]:
        return [self._turtles[tid] for tid in self._active_ids]

    # Backward-compatible state properties for the primary active turtle
    @property
    def x(self) -> float:
        return self._primary.x

    @x.setter
    def x(self, value: float) -> None:
        self._primary.x = _clamp_coord(value)

    @property
    def y(self) -> float:
        return self._primary.y

    @y.setter
    def y(self, value: float) -> None:
        self._primary.y = _clamp_coord(value)

    @property
    def heading(self) -> float:
        return self._primary.heading

    @heading.setter
    def heading(self, value: float) -> None:
        self._primary.heading = _require_finite(value, "Heading") % 360.0

    @property
    def pen_down(self) -> bool:
        return self._primary.pen_down

    @pen_down.setter
    def pen_down(self, value: bool) -> None:
        for t in self._iter_active():
            t.pen_down = bool(value)

    @property
    def pen_mode(self) -> PenMode:
        return self._primary.pen_mode

    @property
    def pen_color(self) -> tuple[int, int, int]:
        return self._primary.pen_color

    @pen_color.setter
    def pen_color(self, value: tuple[int, int, int]) -> None:
        for t in self._iter_active():
            t.pen_color = value

    @property
    def pen_width(self) -> int:
        return self._primary.pen_width

    @pen_width.setter
    def pen_width(self, value: int) -> None:
        self.set_width(value)

    @property
    def visible(self) -> bool:
        return self._primary.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        for t in self._iter_active():
            t.visible = bool(value)

    # Multi-turtle management (Tier 2 with hard cap)
    def _ensure_turtle(self, tid: int) -> TurtleState:
        max_turtles = get_max_turtles()
        if tid < 0 or tid >= max_turtles:
            msg = f"Turtle index must be between 0 and {max_turtles - 1}, got {tid}."
            raise LogoRuntimeError(msg)
        if tid not in self._turtles:
            self._turtles[tid] = TurtleState(x=self.width / 2, y=self.height / 2)
        return self._turtles[tid]

    def set_turtle(self, tid: int) -> None:
        self._ensure_turtle(tid)
        self._active_ids = (tid,)

    def tell(self, tids: list[int] | tuple[int, ...]) -> None:
        if not tids:
            msg = "TELL requires at least one turtle index."
            raise LogoRuntimeError(msg)
        unique_ids: list[int] = []
        for tid in tids:
            self._ensure_turtle(tid)
            if tid not in unique_ids:
                unique_ids.append(tid)
        self._active_ids = tuple(unique_ids)

    def who(self) -> int | tuple[int, ...]:
        if len(self._active_ids) == 1:
            return self._active_ids[0]
        return self._active_ids

    def max_turtle_id(self) -> int:
        return max(self._turtles.keys())

    # Internal op budget check
    def _record_segment(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[int, int, int],
        width: int,
        mode: PenMode = "PAINT",
    ) -> None:
        max_segments = get_max_segments()
        if len(self.ops) >= max_segments:
            msg = f"Maximum drawing segment limit ({max_segments}) exceeded."
            raise LogoRuntimeError(msg)
        seg = Segment(
            _clamp_coord(x1),
            _clamp_coord(y1),
            _clamp_coord(x2),
            _clamp_coord(y2),
            color,
            width,
            mode,
        )
        self.segments.append(seg)
        self.ops.append(seg)

    def _record_op(self, op: DrawOp) -> None:
        max_segments = get_max_segments()
        if len(self.ops) >= max_segments:
            msg = f"Maximum drawing segment limit ({max_segments}) exceeded."
            raise LogoRuntimeError(msg)
        self.ops.append(op)

    def _move_state_to(self, state: TurtleState, new_x: float, new_y: float) -> None:
        clamped_x = _clamp_coord(new_x)
        clamped_y = _clamp_coord(new_y)
        if state.pen_down:
            draw_color = self.bg_color if state.pen_mode == "ERASE" else state.pen_color
            self._record_segment(
                state.x,
                state.y,
                clamped_x,
                clamped_y,
                draw_color,
                state.pen_width,
                state.pen_mode,
            )
        state.x = clamped_x
        state.y = clamped_y
        if state.poly_path is not None:
            max_segments = get_max_segments()
            if len(state.poly_path) < max_segments:
                state.poly_path.append((clamped_x, clamped_y))

    # Movement
    def forward(self, distance: float) -> None:
        dist = _require_finite(distance, "Distance")
        for state in self._iter_active():
            radians = math.radians(state.heading)
            new_x = state.x + math.sin(radians) * dist
            new_y = state.y - math.cos(radians) * dist
            self._move_state_to(state, new_x, new_y)

    def backward(self, distance: float) -> None:
        dist = _require_finite(distance, "Distance")
        self.forward(-dist)

    def right(self, degrees: float) -> None:
        deg = _require_finite(degrees, "Angle")
        for state in self._iter_active():
            state.heading = (state.heading + deg) % 360.0

    def left(self, degrees: float) -> None:
        deg = _require_finite(degrees, "Angle")
        for state in self._iter_active():
            state.heading = (state.heading - deg) % 360.0

    # Pen
    def pen_up(self) -> None:
        for state in self._iter_active():
            state.pen_down = False

    def pen_down_mode(self) -> None:
        for state in self._iter_active():
            state.pen_down = True
            state.pen_mode = "PAINT"

    def pen_paint(self) -> None:
        self.pen_down_mode()

    def pen_erase(self) -> None:
        for state in self._iter_active():
            state.pen_down = True
            state.pen_mode = "ERASE"

    def pen_reverse(self) -> None:
        for state in self._iter_active():
            state.pen_down = True
            state.pen_mode = "REVERSE"

    def show_turtle(self) -> None:
        for state in self._iter_active():
            state.visible = True

    def hide_turtle(self) -> None:
        for state in self._iter_active():
            state.visible = False

    def set_color(self, color: tuple[int, int, int]) -> None:
        for state in self._iter_active():
            state.pen_color = color

    def set_flood_color(self, color: tuple[int, int, int]) -> None:
        for state in self._iter_active():
            state.flood_color = color

    def set_bg_color(self, color: tuple[int, int, int]) -> None:
        self.bg_color = color

    def set_width(self, width: int) -> None:
        max_pen_width = get_max_pen_width()
        if not isinstance(width, int) or isinstance(width, bool):
            msg = f"Pen width must be an integer between 1 and {max_pen_width}."
            raise LogoRuntimeError(msg)
        if width < 1 or width > max_pen_width:
            msg = f"Pen width must be between 1 and {max_pen_width}, got {width}."
            raise LogoRuntimeError(msg)
        for state in self._iter_active():
            state.pen_width = width

    def set_label_height(self, height: int) -> None:
        if height < 4 or height > 100:
            msg = f"Label height must be between 4 and 100, got {height}."
            raise LogoRuntimeError(msg)
        for state in self._iter_active():
            state.label_height = height

    # Position & Coordinate reporters
    def get_xcor(self) -> float:
        val = self._primary.x - self.width / 2
        return 0.0 if abs(val) < 1e-9 else round(val, 6)

    def get_ycor(self) -> float:
        val = self.height / 2 - self._primary.y
        return 0.0 if abs(val) < 1e-9 else round(val, 6)

    def get_pos(self) -> tuple[float, float]:
        return (self.get_xcor(), self.get_ycor())

    def get_heading(self) -> float:
        val = self._primary.heading % 360.0
        return 0.0 if abs(val) < 1e-9 or abs(val - 360.0) < 1e-9 else round(val, 6)

    def towards(self, x: float, y: float) -> float:
        tx = _require_finite(x, "X coordinate")
        ty = _require_finite(y, "Y coordinate")
        dx = tx - self.get_xcor()
        dy = ty - self.get_ycor()
        if abs(dx) < 1e-12 and abs(dy) < 1e-12:
            return 0.0
        angle = math.degrees(math.atan2(dx, dy)) % 360.0
        return 0.0 if abs(angle) < 1e-9 else round(angle, 6)

    def home(self) -> None:
        self.set_xy(0.0, 0.0)
        self.set_heading(0.0)

    def set_heading(self, heading: float) -> None:
        deg = _require_finite(heading, "Heading")
        for state in self._iter_active():
            state.heading = deg % 360.0

    def set_xy(self, x: float, y: float) -> None:
        lx = _require_finite(x, "X coordinate")
        ly = _require_finite(y, "Y coordinate")
        new_x = self.width / 2 + lx
        new_y = self.height / 2 - ly
        for state in self._iter_active():
            self._move_state_to(state, new_x, new_y)

    def set_x(self, x: float) -> None:
        lx = _require_finite(x, "X coordinate")
        new_x = self.width / 2 + lx
        for state in self._iter_active():
            self._move_state_to(state, new_x, state.y)

    def set_y(self, y: float) -> None:
        ly = _require_finite(y, "Y coordinate")
        new_y = self.height / 2 - ly
        for state in self._iter_active():
            self._move_state_to(state, state.x, new_y)

    def clean(self) -> None:
        """CLEAN: clears all drawn trails without moving or rotating the turtle."""
        self.segments.clear()
        self.ops.clear()
        self._fill_count = 0

    def clear_screen(self) -> None:
        """CS / CLEARSCREEN: clears the screen AND resets active turtle(s) to (0, 0) heading 0."""
        self.clean()
        for state in self._iter_active():
            state.x = self.width / 2
            state.y = self.height / 2
            state.heading = 0.0

    def clear(self) -> None:
        """Alias for clear_screen() so CS resets both trails and turtle home."""
        self.clear_screen()

    # Shapes, Fills, and Labels
    def arc(self, angle: float, radius: float) -> None:
        ang = _require_finite(angle, "Arc angle")
        rad = _require_finite(radius, "Arc radius")
        if rad == 0.0 or ang == 0.0:
            return
        abs_rad = min(abs(rad), MAX_COORD)
        sweep = max(-360.0, min(360.0, ang))
        steps = max(8, min(120, int(abs(sweep) / 3) + 1))

        for state in self._iter_active():
            if not state.pen_down:
                continue
            draw_color = self.bg_color if state.pen_mode == "ERASE" else state.pen_color
            start_deg = state.heading
            prev_x: float | None = None
            prev_y: float | None = None
            for step in range(steps + 1):
                theta = math.radians(start_deg + (sweep * step / steps))
                px = _clamp_coord(state.x + math.sin(theta) * abs_rad)
                py = _clamp_coord(state.y - math.cos(theta) * abs_rad)
                if prev_x is not None and prev_y is not None:
                    self._record_segment(
                        prev_x,
                        prev_y,
                        px,
                        py,
                        draw_color,
                        state.pen_width,
                        state.pen_mode,
                    )
                prev_x, prev_y = px, py

    def ellipse(self, radius_x: float, radius_y: float) -> None:
        rx = _require_finite(radius_x, "Ellipse X radius")
        ry = _require_finite(radius_y, "Ellipse Y radius")
        if rx == 0.0 and ry == 0.0:
            return
        abs_rx = min(abs(rx), MAX_COORD)
        abs_ry = min(abs(ry), MAX_COORD)
        steps = 72

        for state in self._iter_active():
            if not state.pen_down:
                continue
            draw_color = self.bg_color if state.pen_mode == "ERASE" else state.pen_color
            rot = math.radians(state.heading)
            cos_r = math.cos(rot)
            sin_r = math.sin(rot)
            prev_x: float | None = None
            prev_y: float | None = None
            for step in range(steps + 1):
                t = 2.0 * math.pi * step / steps
                ex = abs_rx * math.cos(t)
                ey = abs_ry * math.sin(t)
                px = _clamp_coord(state.x + ex * cos_r - ey * sin_r)
                py = _clamp_coord(state.y + ex * sin_r + ey * cos_r)
                if prev_x is not None and prev_y is not None:
                    self._record_segment(
                        prev_x,
                        prev_y,
                        px,
                        py,
                        draw_color,
                        state.pen_width,
                        state.pen_mode,
                    )
                prev_x, prev_y = px, py

    def dot(self, pos: tuple[float, float] | None = None) -> None:
        for state in self._iter_active():
            if pos is not None:
                dx = _clamp_coord(self.width / 2 + _require_finite(pos[0], "Dot X"))
                dy = _clamp_coord(self.height / 2 - _require_finite(pos[1], "Dot Y"))
            else:
                dx, dy = state.x, state.y
            draw_color = self.bg_color if state.pen_mode == "ERASE" else state.pen_color
            self._record_op(
                DotOp(
                    x=dx,
                    y=dy,
                    color=draw_color,
                    size=max(state.pen_width, 2),
                    mode=state.pen_mode,
                )
            )

    def fill(self) -> None:
        max_fills = get_max_fills()
        for state in self._iter_active():
            if self._fill_count >= max_fills:
                msg = f"Maximum FILL operation limit ({max_fills}) exceeded."
                raise LogoRuntimeError(msg)
            self._fill_count += 1
            color = state.flood_color if state.flood_color is not None else state.pen_color
            self._record_op(FillOp(x=state.x, y=state.y, color=color))

    def begin_polygon(self) -> None:
        for state in self._iter_active():
            state.poly_path = [(state.x, state.y)]

    def end_polygon(self, fill_color: tuple[int, int, int]) -> None:
        for state in self._iter_active():
            pts = state.poly_path
            state.poly_path = None
            if pts and len(pts) >= 3:
                self._record_op(PolygonFillOp(points=tuple(pts), fill_color=fill_color))

    def label(self, text: str) -> None:
        max_word = get_max_word_length()
        clean_text = "".join(ch if ch.isprintable() else " " for ch in str(text))
        if len(clean_text) > max_word:
            clean_text = clean_text[:max_word]
        for state in self._iter_active():
            draw_color = self.bg_color if state.pen_mode == "ERASE" else state.pen_color
            self._record_op(
                LabelOp(
                    x=state.x,
                    y=state.y,
                    text=clean_text,
                    color=draw_color,
                    height=state.label_height,
                    heading=state.heading,
                )
            )

    # Rendering helpers
    @staticmethod
    def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
        try:
            return ImageFont.load_default(size=max(6, min(100, size)))
        except TypeError:
            return ImageFont.load_default()

    def _render_ops_onto(self, image: Image.Image, ops_slice: list[DrawOp]) -> None:
        draw = ImageDraw.Draw(image)
        for op in ops_slice:
            if isinstance(op, Segment):
                if op.mode == "REVERSE":
                    mask = Image.new("L", (self.width, self.height), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.line((op.x1, op.y1, op.x2, op.y2), fill=255, width=op.width)
                    inverted = ImageChops.invert(image)
                    image.paste(inverted, (0, 0), mask)
                    draw = ImageDraw.Draw(image)
                else:
                    draw.line(
                        (op.x1, op.y1, op.x2, op.y2),
                        fill=op.color,
                        width=op.width,
                    )
            elif isinstance(op, DotOp):
                r = op.size / 2.0
                bbox = (op.x - r, op.y - r, op.x + r, op.y + r)
                if op.mode == "REVERSE":
                    mask = Image.new("L", (self.width, self.height), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse(bbox, fill=255)
                    inverted = ImageChops.invert(image)
                    image.paste(inverted, (0, 0), mask)
                    draw = ImageDraw.Draw(image)
                else:
                    draw.ellipse(bbox, fill=op.color)
            elif isinstance(op, PolygonFillOp):
                if len(op.points) >= 3:
                    draw.polygon(list(op.points), fill=op.fill_color)
            elif isinstance(op, FillOp):
                ix = round(op.x)
                iy = round(op.y)
                if 0 <= ix < self.width and 0 <= iy < self.height:
                    ImageDraw.floodfill(image, (ix, iy), op.color)
                    draw = ImageDraw.Draw(image)
            elif isinstance(op, LabelOp) and op.text:
                font = self._load_font(op.height)
                draw.text((op.x, op.y - op.height), op.text, fill=op.color, font=font)

    def _draw_visible_turtles(self, image: Image.Image) -> None:
        draw = ImageDraw.Draw(image)
        for state in self._turtles.values():
            if not state.visible:
                continue
            rad = math.radians(state.heading)
            tip_x = state.x + math.sin(rad) * 12.0
            tip_y = state.y - math.cos(rad) * 12.0
            left_rad = math.radians(state.heading - 140.0)
            left_x = state.x + math.sin(left_rad) * 9.0
            left_y = state.y - math.cos(left_rad) * 9.0
            right_rad = math.radians(state.heading + 140.0)
            right_x = state.x + math.sin(right_rad) * 9.0
            right_y = state.y - math.cos(right_rad) * 9.0
            draw.polygon(
                [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)],
                outline=state.pen_color,
            )

    def render_image(self) -> Image.Image:
        image = Image.new("RGB", (self.width, self.height), self.bg_color)
        # If external callers appended directly to self.segments without self.ops, honor both
        ops_to_draw: list[DrawOp] = self.ops if self.ops else list(self.segments)
        self._render_ops_onto(image, ops_to_draw)
        self._draw_visible_turtles(image)
        return image

    def render(self) -> BytesIO:
        """Renders the canvas to a PNG BytesIO buffer (without slow optimize=True)."""
        image = self.render_image()
        output = BytesIO()
        image.save(output, format="PNG", optimize=False)
        output.seek(0)
        return output

    def render_gif(
        self,
        max_frames: int | None = None,
        duration_ms: int = 50,
        scale: float = 0.5,
    ) -> BytesIO:
        """
        Tier 2 feature: Renders an animated GIF showing the drawing progression.
        Enforces hard caps on frame count (`MAX_GIF_FRAMES`), frame duration, and pixel count.
        """
        frame_cap = min(max_frames or get_max_gif_frames(), get_max_gif_frames())
        frame_cap = max(2, frame_cap)
        duration_ms = max(20, min(500, int(duration_ms)))
        scale = max(0.2, min(1.0, float(scale)))

        target_w = max(64, min(800, int(self.width * scale)))
        target_h = max(64, min(600, int(self.height * scale)))

        ops_to_draw: list[DrawOp] = self.ops if self.ops else list(self.segments)
        total_ops = len(ops_to_draw)

        frames: list[Image.Image] = []
        if total_ops == 0:
            base = self.render_image()
            if (target_w, target_h) != (self.width, self.height):
                base = base.resize((target_w, target_h), Image.Resampling.BILINEAR)
            frames.append(base)
        else:
            num_steps = min(total_ops, frame_cap - 1)
            image = Image.new("RGB", (self.width, self.height), self.bg_color)
            last_idx = 0
            for step in range(1, num_steps + 1):
                next_idx = round(step * total_ops / num_steps)
                if next_idx > last_idx:
                    self._render_ops_onto(image, ops_to_draw[last_idx:next_idx])
                    last_idx = next_idx
                frame = image.copy()
                if (target_w, target_h) != (self.width, self.height):
                    frame = frame.resize((target_w, target_h), Image.Resampling.BILINEAR)
                frames.append(frame)

        output = BytesIO()
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=False,
        )
        output.seek(0)
        return output
