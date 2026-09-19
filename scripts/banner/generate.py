#!/usr/bin/env python3
"""Render Faris's terminal-style profile banner (dark + light SVG).

Requires Pillow. Portrait source: assets/source/profile.png
Dot rendering is deterministic (same photo → same SVG).
"""

from __future__ import annotations

import html
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
SOURCE = ASSETS / "source" / "profile.png"

# Original Faris palette — teal signals, not purple.
THEMES = {
    "dark": {
        "bg": "#07111f",
        "shell": "#0c1a2d",
        "panel": "#0f2239",
        "line": "#29445e",
        "ink": "#e4effa",
        "muted": "#8ba6be",
        "signal": "#4aa8ff",
        "dot": "#58d8c7",
    },
    "light": {
        "bg": "#f4f8fc",
        "shell": "#ffffff",
        "panel": "#edf4f8",
        "line": "#bdd0dd",
        "ink": "#142438",
        "muted": "#5f7892",
        "signal": "#147ab9",
        "dot": "#197f8e",
    },
}


def portrait_dots(color: str) -> str:
    """Convert the supplied photo into a fixed circle mosaic."""
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing portrait: {SOURCE}")

    image = Image.open(SOURCE).convert("RGB")
    side = image.width
    top = max(0, (image.height - side) // 2 - 35)
    crop = image.crop((0, top, side, min(image.height, top + side)))
    gray = ImageEnhance.Contrast(
        ImageOps.grayscale(crop.resize((118, 118), Image.Resampling.LANCZOS))
    ).enhance(1.45)
    pixels = gray.load()
    dots = []
    for y in range(118):
        for x in range(118):
            value = pixels[x, y] / 255
            radius = 1.52 * value**1.65
            if radius >= 0.22:
                dots.append(
                    f'<circle cx="{93 + x * 2.47:.2f}" cy="{148 + y * 2.47:.2f}" '
                    f'r="{radius:.2f}" fill="{color}" opacity="{0.18 + value * 0.80:.2f}"/>'
                )
    return "".join(dots)


def render(colors: dict[str, str], dots: str) -> str:
    rows = [
        ("IDENTITY", "Faris / Kris"),
        ("LEVEL", "Third-year CS student"),
        ("CAMPUS", "Paragon International University"),
        ("PRIMARY", "Backend engineering"),
        ("EXPLORING", "Cloud systems · AI agents"),
        ("CORE.LANG", "Java · Python · C++"),
        ("CORE.BACKEND", "Spring Boot · Laravel"),
        ("DATA", "MySQL · PostgreSQL"),
        ("TOOLCHAIN", "Docker · Git · GitHub"),
    ]
    info = []
    for index, (label, value) in enumerate(rows):
        y = 153 + index * 38
        start = 760 if len(label) < 10 else 800
        info.append(
            f'<text x="620" y="{y}" fill="{colors["muted"]}" font-family="ui-monospace, monospace" '
            f'font-size="14">{html.escape(label)}</text>'
            f'<path d="M{start} {y - 5}H1080" stroke="{colors["line"]}" stroke-dasharray="1 5"/>'
            f'<text x="1100" y="{y}" text-anchor="end" fill="{colors["ink"]}" '
            f'font-family="ui-monospace, monospace" font-size="14">{html.escape(value)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="610" viewBox="0 0 1180 610" role="img" aria-label="Faris developer profile dashboard">
<style>@keyframes blink{{50%{{opacity:.25}}}} .live{{animation:blink 1.4s ease-in-out infinite}}</style>
<rect width="1180" height="610" rx="26" fill="{colors['bg']}"/>
<rect x="18" y="18" width="1144" height="574" rx="18" fill="{colors['shell']}" stroke="{colors['line']}"/>
<rect x="18" y="18" width="1144" height="52" rx="18" fill="{colors['shell']}"/>
<path d="M18 70H1162" stroke="{colors['line']}"/>
<circle cx="48" cy="44" r="7" fill="#ff665f"/><circle cx="72" cy="44" r="7" fill="#fbbf24"/><circle cx="96" cy="44" r="7" fill="#22c55e"/>
<text x="590" y="49" text-anchor="middle" fill="{colors['muted']}" font-family="ui-monospace, monospace" font-size="14">faris.profile — learning mode</text>
<rect x="42" y="96" width="495" height="448" rx="12" fill="{colors['panel']}" stroke="{colors['line']}"/>
<text x="64" y="126" fill="{colors['signal']}" font-family="ui-monospace, monospace" font-size="15" font-weight="700" letter-spacing="1">PORTRAIT.SIGNAL</text>
<text x="510" y="126" text-anchor="end" fill="{colors['muted']}" font-family="ui-monospace, monospace" font-size="12">118×118 / DOT-MAP</text>
<path d="M42 142H537" stroke="{colors['line']}"/>
<clipPath id="portrait"><rect x="58" y="156" width="463" height="345" rx="8"/></clipPath>
<g clip-path="url(#portrait)">{dots}</g>
<path d="M60 162h18m-18 0v18M519 162h-18m18 0v18M60 495h18m-18 0v-18M519 495h-18m18 0v-18" fill="none" stroke="{colors['signal']}"/>
<text x="64" y="525" fill="{colors['muted']}" font-family="ui-monospace, monospace" font-size="12">PHOTO / DETERMINISTIC DOT RENDER</text>
<rect x="560" y="96" width="578" height="448" rx="12" fill="{colors['panel']}" stroke="{colors['line']}"/>
<text x="582" y="126" fill="{colors['signal']}" font-family="ui-monospace, monospace" font-size="15" font-weight="700" letter-spacing="1">LEARNING.SYSTEM</text>
<circle class="live" cx="1004" cy="120" r="5" fill="#fb7185"/>
<text x="1017" y="126" fill="#fb7185" font-family="ui-monospace, monospace" font-size="13" font-weight="700">LIVE</text>
<rect x="1048" y="107" width="70" height="25" rx="13" fill="{colors['signal']}" opacity=".17"/>
<text x="1083" y="125" text-anchor="middle" fill="{colors['signal']}" font-family="ui-monospace, monospace" font-size="12" font-weight="700">Fariscus</text>
<path d="M560 142H1138" stroke="{colors['line']}"/>
{''.join(info)}
<path d="M560 502H1138" stroke="{colors['line']}"/>
<circle cx="586" cy="522" r="4" fill="#22c55e"/>
<text x="598" y="527" fill="#22c55e" font-family="ui-monospace, monospace" font-size="12">SYSTEM READY TO LEARN</text>
<text x="1115" y="527" text-anchor="end" fill="{colors['muted']}" font-family="ui-monospace, monospace" font-size="12">CAMBODIA / UTC+7</text>
</svg>
'''


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, colors in THEMES.items():
        svg = render(colors, portrait_dots(colors["dot"]))
        dest = ASSETS / f"banner-{name}.svg"
        dest.write_text(svg, encoding="utf-8")
        print(f"wrote {dest}")


if __name__ == "__main__":
    main()
