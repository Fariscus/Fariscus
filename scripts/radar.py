#!/usr/bin/env python3
"""Render a JSON-configured radar chart to dark and light SVG files."""

import argparse
import html
import json
import math
from pathlib import Path

THEMES = {
    "dark": {"bg": "#0b1220", "panel": "#111c2e", "ink": "#e6edf7", "muted": "#9fb3c8", "line": "#263b55", "accent": "#2dd4bf"},
    "light": {"bg": "#f8fafc", "panel": "#ffffff", "ink": "#102a43", "muted": "#627d98", "line": "#d9e2ec", "accent": "#0f766e"},
}


def point(angle, radius):
    return 210 + math.cos(angle) * radius, 210 + math.sin(angle) * radius


def render(data, theme):
    labels = [axis["label"] for axis in data["axes"]]
    values = [max(0, min(100, float(axis["value"]))) for axis in data["axes"]]
    style = THEMES[theme]
    count = len(labels)
    if count < 3:
        raise ValueError("A radar chart needs at least three axes.")
    angle = lambda i: -math.pi / 2 + i * math.tau / count
    points = lambda values, radius: " ".join(f"{x:.1f},{y:.1f}" for i, value in enumerate(values) for x, y in [point(angle(i), radius * value / 100)])
    rings = "".join(f'<polygon points="{points([level] * count, 145)}" fill="none" stroke="{style["line"]}"/>' for level in (20, 40, 60, 80, 100))
    spokes = "".join(f'<line x1="210" y1="210" x2="{point(angle(i), 145)[0]:.1f}" y2="{point(angle(i), 145)[1]:.1f}" stroke="{style["line"]}"/>' for i in range(count))
    labels_svg = []
    for index, label in enumerate(labels):
        x, y = point(angle(index), 178)
        anchor = "end" if x > 275 else "start" if x < 145 else "middle"
        labels_svg.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle" fill="{style["ink"]}" font-size="13" font-weight="650">{html.escape(label)}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="420" viewBox="0 0 420 420" role="img" aria-label="{html.escape(data.get("title", "Radar chart"))}">
<rect width="420" height="420" rx="20" fill="{style['panel']}"/><rect x="1" y="1" width="418" height="418" rx="19" fill="none" stroke="{style['line']}"/>
<text x="25" y="37" fill="{style['ink']}" font-family="system-ui, sans-serif" font-size="18" font-weight="800">{html.escape(data.get('title', 'Radar chart'))}</text>
<text x="25" y="59" fill="{style['muted']}" font-family="system-ui, sans-serif" font-size="11">self-assessed learning level</text>
<g font-family="system-ui, sans-serif">{rings}{spokes}<polygon points="{points(values, 145)}" fill="{style['accent']}" fill-opacity=".24" stroke="{style['accent']}" stroke-width="3"/>{''.join(labels_svg)}</g></svg>\n'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output prefix, e.g. assets/radar")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    for theme in THEMES:
        args.output.with_name(f"{args.output.name}-{theme}.svg").write_text(render(data, theme), encoding="utf-8")


if __name__ == "__main__":
    main()
