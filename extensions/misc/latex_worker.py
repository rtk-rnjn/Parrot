"""Isolated LaTeX renderer. Reads LaTeX on stdin, writes PNG bytes to stdout."""

import contextlib
import io
import sys

MAX_W, MAX_H = 3000, 1500
DPI = 200


def _limit_resources() -> None:
    try:
        import resource  # noqa: PLC0415
    except ImportError:
        return
    for name, value in (
        ("RLIMIT_CPU", 8),
        ("RLIMIT_AS", 1024 * 1024**2),
        ("RLIMIT_FSIZE", 0),
    ):
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(getattr(resource, name), (value, value))


def main() -> int:
    # 1. Heavy imports + font cache warm-up BEFORE limits
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    matplotlib.rcParams["text.usetex"] = False
    from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: PLC0415
    from matplotlib.figure import Figure  # noqa: PLC0415

    warm = Figure(dpi=50)
    FigureCanvasAgg(warm)
    warm.text(0, 0, r"$x^2$")
    warm.savefig(io.BytesIO(), format="png")

    # 2. Lock down, then touch untrusted input
    _limit_resources()
    latex = sys.stdin.read()

    try:
        fig = Figure(dpi=DPI)
        FigureCanvasAgg(fig)
        text = fig.text(0, 0, f"${latex}$", fontsize=20)

        bbox = text.get_window_extent(fig.canvas.get_renderer())  # pyright: ignore[reportAttributeAccessIssue]
        if bbox.width > MAX_W or bbox.height > MAX_H:
            return 3

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=DPI, transparent=False, bbox_inches="tight", pad_inches=0.1)
    except Exception:
        return 2

    sys.stdout.buffer.write(buf.getvalue())
    return 0


if __name__ == "__main__":
    sys.exit(main())
