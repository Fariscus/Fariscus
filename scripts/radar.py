#!/usr/bin/env python3
"""Render spider / radar charts as dark + light SVGs. Standard library only.

Usage:
  python scripts/radar.py --data data/skills.json -o assets/radar
  python scripts/radar.py --data data/langmix.json -o assets/radar-langs --values
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# Faris theme: teal / green (student backend identity), not Emmi's purple.
THEMES = {
    "dark": {
        "grid": "#30363d",
        "spoke": "#21262d",
        "label": "#c9d1d9",
        "value": "#8b949e",
        "title": "#e6edf3",
        "fill": "#2dd4bf",
        "stroke": "#14b8a6",
        "vertex": "#5eead4",
        "bg": "none",
    },
    "light": {
        "grid": "#d0d7de",
        "spoke": "#e6eaef",
        "label": "#1f2328",
        "value": "#57606a",
        "title": "#1f2328",
        "fill": "#2da44e",
        "stroke": "#1a7f37",
        "vertex": "#116329",
        "bg": "none",
    },
}

FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"
LBL, VAL, TTL = 13, 11, 15


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def estimate_width(text: str, size: float) -> float:
    return len(text) * size * 0.62


def polygon(radius: float, count: int, start: float = -math.pi / 2):
    return [
        (
            radius * math.cos(start + i * 2 * math.pi / count),
            radius * math.sin(start + i * 2 * math.pi / count),
        )
        for i in range(count)
    ]


def load_axes(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    axes = [(item["label"], float(item["value"])) for item in payload["axes"]]
    return payload.get("title", "Skill Radar"), axes


def render(
    title: str,
    axes: list[tuple[str, float]],
    theme: str,
    size: int,
    rings: int,
    show_values: bool,
    animate: bool,
) -> str:
    colors = THEMES[theme]
    count = len(axes)
    radius = size / 2 - 8
    gap = 20
    values = [max(0.0, min(100.0, value)) for _, value in axes]
    outer = polygon(radius, count)

    labels = []
    for index, (label, _) in enumerate(axes):
        angle = -math.pi / 2 + index * 2 * math.pi / count
        cos_v, sin_v = math.cos(angle), math.sin(angle)
        lx, ly = (radius + gap) * cos_v, (radius + gap) * sin_v
        anchor = "middle" if abs(cos_v) < 0.25 else ("start" if cos_v > 0 else "end")
        dy = 4 if abs(sin_v) < 0.25 else (14 if sin_v > 0 else -5)
        labels.append((lx, ly + dy, anchor, label, values[index]))

    min_x = min_y = -radius
    max_x = max_y = radius
    for lx, ly, anchor, label, value in labels:
        width = max(
            estimate_width(label, LBL),
            estimate_width(f"{value:g}", VAL) if show_values else 0.0,
        )
        if anchor == "start":
            x0, x1 = lx, lx + width
        elif anchor == "end":
            x0, x1 = lx - width, lx
        else:
            x0, x1 = lx - width / 2, lx + width / 2
        y0 = ly - LBL
        y1 = ly + 4 + (VAL + 4 if show_values else 0)
        min_x, max_x = min(min_x, x0), max(max_x, x1)
        min_y, max_y = min(min_y, y0), max(max_y, y1)

    pad = 10
    title_h = TTL + 14 if title else 0
    width = round((max_x - min_x) + 2 * pad)
    height = round((max_y - min_y) + 2 * pad + title_h)
    origin_x, origin_y = -min_x + pad, -min_y + pad + title_h

    if title:
        needed = round(estimate_width(title, TTL) + 2 * pad)
        if needed > width:
            origin_x += (needed - width) / 2
            width = needed

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'aria-label="{esc(title) or "radar chart"}" font-family="{FONT}">'
    ]
    if colors["bg"] != "none":
        parts.append(f'<rect width="100%" height="100%" fill="{colors["bg"]}"/>')
    if title:
        parts.append(
            f'<text x="{width / 2:.1f}" y="{pad + TTL}" text-anchor="middle" '
            f'font-size="{TTL}" font-weight="700" fill="{colors["title"]}">'
            f"{esc(title)}</text>"
        )
    parts.append(f'<g transform="translate({origin_x:.1f},{origin_y:.1f})">')

    for level in range(rings, 0, -1):
        points = " ".join(
            f"{x:.1f},{y:.1f}" for x, y in polygon(radius * level / rings, count)
        )
        opacity = 0.35 + 0.5 * level / rings
        parts.append(
            f'<polygon points="{points}" fill="none" stroke="{colors["grid"]}" '
            f'stroke-width="1" opacity="{opacity:.2f}"/>'
        )

    for x, y in outer:
        parts.append(
            f'<line x1="0" y1="0" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{colors["spoke"]}" stroke-width="1"/>'
        )

    shape = [
        (px * value / 100, py * value / 100)
        for (px, py), value in zip(outer, values)
    ]
    shape_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in shape)
    parts.append("<g>")
    if animate:
        parts.append(
            '<animateTransform attributeName="transform" type="scale" '
            'values="0.04;1" dur="1.1s" calcMode="spline" keyTimes="0;1" '
            'keySplines="0.22 1 0.36 1" fill="freeze"/>'
        )
    parts.append(
        f'<polygon points="{shape_points}" fill="{colors["fill"]}" fill-opacity="0.22" '
        f'stroke="{colors["stroke"]}" stroke-width="2.5" stroke-linejoin="round"/>'
    )
    for x, y in shape:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{colors["vertex"]}" '
            f'stroke="{colors["stroke"]}" stroke-width="1.2"/>'
        )
    parts.append("</g>")

    for lx, ly, anchor, label, value in labels:
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-size="{LBL}" font-weight="600" fill="{colors["label"]}">'
            f"{esc(label)}</text>"
        )
        if show_values:
            parts.append(
                f'<text x="{lx:.1f}" y="{ly + VAL + 4:.1f}" text-anchor="{anchor}" '
                f'font-size="{VAL}" fill="{colors["value"]}">{value:g}</text>'
            )

    parts.append("</g></svg>")
    return "".join(parts)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("-o", "--out", type=Path, required=True, help="prefix without extension")
    parser.add_argument("--size", type=int, default=440)
    parser.add_argument("--rings", type=int, default=4)
    parser.add_argument("--values", action="store_true")
    parser.add_argument("--no-animate", dest="animate", action="store_false")
    args = parser.parse_args(argv)

    if not args.data.exists():
        sys.exit(f"missing data file: {args.data}")

    title, axes = load_axes(args.data)
    if len(axes) < 3:
        sys.exit("a radar chart needs at least 3 axes")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        svg = render(title, axes, theme, args.size, args.rings, args.values, args.animate)
        dest = args.out.with_name(f"{args.out.name}-{theme}.svg")
        dest.write_text(svg, encoding="utf-8")
        print(f"wrote {dest}")


if __name__ == "__main__":
    main()
