from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def set_korean_font() -> None:
    from matplotlib import font_manager
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("NanumGothic", "Malgun Gothic", "AppleGothic"):
        if name in installed:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def _bar(spec, ax):
    d = spec["data"]
    ax.bar(d["labels"], d["values"])
    ax.set_title(spec.get("title", ""))


def _line(spec, ax):
    d = spec["data"]
    ax.plot(d["labels"], d["values"], marker="o")
    ax.set_title(spec.get("title", ""))


def _donut(spec, ax):
    d = spec["data"]
    ax.pie(d["values"], labels=d["labels"], wedgeprops={"width": 0.4})
    ax.set_title(spec.get("title", ""))


def _flowchart_mpl(spec, ax):
    nodes = spec["data"]["nodes"]
    edges = spec["data"].get("edges", [])
    ax.axis("off")
    ax.set_title(spec.get("title", ""))

    # Map node names to y positions (index i -> y = len(nodes) - i)
    node_positions = {}
    for i, node in enumerate(nodes):
        y = len(nodes) - i
        node_positions[node] = (0.5, y)
        ax.text(0.5, y, node, ha="center", va="center",
                bbox={"boxstyle": "round", "fc": "#e8f0fe", "ec": "#4a6fd0"})

    # Draw edges (skip if node not in positions)
    for src, dst in edges:
        if src in node_positions and dst in node_positions:
            src_pos = node_positions[src]
            dst_pos = node_positions[dst]
            ax.annotate("", xy=dst_pos, xytext=src_pos,
                        arrowprops={"arrowstyle": "->"})

    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(nodes) + 1)


def render_chart(spec: dict, out_dir: Path) -> Path | None:
    ctype = spec["type"]
    if ctype == "table":
        return None
    set_korean_font()
    out = Path(out_dir) / f"{spec['id']}.png"
    fig, ax = plt.subplots(figsize=(6, 4))
    try:
        if ctype == "bar":
            _bar(spec, ax)
        elif ctype == "line":
            _line(spec, ax)
        elif ctype == "donut":
            _donut(spec, ax)
        elif ctype == "flowchart":
            _flowchart_mpl(spec, ax)  # graphviz fallback: Phase 1 uses matplotlib boxes
        else:
            raise ValueError(f"unknown chart type: {ctype}")
        fig.tight_layout()
        fig.savefig(out, dpi=150)
    finally:
        plt.close(fig)
    return out
