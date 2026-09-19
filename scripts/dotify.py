#!/usr/bin/env python3
"""Create theme-aware portrait SVG frames (optional standalone asset)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

for theme, colors in {
    "dark": ("#0b1220", "#2dd4bf"),
    "light": ("#f8fafc", "#0f766e"),
}.items():
    bg, accent = colors
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="360" viewBox="0 0 360 360" role="img" aria-label="Portrait of Faris">
<rect width="360" height="360" rx="24" fill="{bg}"/>
<circle cx="180" cy="180" r="143" fill="none" stroke="{accent}" stroke-width="2" stroke-dasharray="3 8"/>
<clipPath id="portrait"><circle cx="180" cy="180" r="132"/></clipPath>
<image href="source/farisfyyy.png" x="65" y="24" width="230" height="300" preserveAspectRatio="xMidYMin slice" clip-path="url(#portrait)"/>
</svg>
'''
    (ASSETS / f"portrait-{theme}.svg").write_text(svg, encoding="utf-8")
    print(f"wrote portrait-{theme}.svg")
