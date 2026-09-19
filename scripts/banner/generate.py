#!/usr/bin/env python3
"""Render Faris's terminal-style profile banner (dark + light SVG).

Layout inspired by Emmi's profile.sh structure (two panels + key/value rows),
but with Faris's identity, teal palette, and a simpler deterministic portrait.
No numpy/scipy — Pillow only.
"""

from __future__ import annotations

import html
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
SOURCE = ASSETS / "source" / "profile.png"

W, H = 1180, 610
FONT = "ui-monospace,SFMono-Regular,Consolas,monospace"

# Faris teal identity (not purple).
THEMES = {
    "dark": {
        "bg": "#07111f",
        "panel": "#0c1a2d",
        "panel2": "#0f2239",
        "line": "#29445e",
        "muted": "#8ba6be",
        "text": "#e4effa",
        "chrome": "#4aa8ff",
        "accent": "#22c55e",
        "dot": "#58d8c7",
        "shadow": "#02050B",
    },
    "light": {
        "bg": "#F6F8FA",
        "panel": "#FFFFFF",
        "panel2": "#EDF3F7",
        "line": "#CBD7E1",
        "muted": "#64748B",
        "text": "#172033",
        "chrome": "#0891B2",
        "accent": "#10B981",
        "dot": "#0f766e",
        "shadow": "#AAB7C4",
    },
}

# Keep values short enough for the right panel (monospace ~0.60em).
ROWS = [
    ("Subject", "Faris / Kris"),
    ("Level", "Third-year CS student"),
    ("Campus", "Paragon IU"),
    ("Goal", "Aspiring Software Engineer"),
    ("Focus", "Backend · Cloud · AI agents"),
    ("Status", "Building + Learning + Shipping"),
    ("ToolChain", "Cursor · Git · Docker"),
    ("Core.Lang", "Java · Python · C++ · TS"),
    ("Core.Backend", "Spring Boot · Laravel"),
    ("Core.Frontend", "React · JavaScript"),
    ("Core.Database", "MySQL · PostgreSQL"),
    ("Core.Infra", "Docker · GitHub"),
    ("Grid.GitHub", "Fariscus"),
]


def text_width(text: str, font_size: float) -> float:
    """Stable monospace estimate used for leader gaps."""
    return len(text) * font_size * 0.605


def dotted_leader(x1: float, x2: float, y: float) -> str:
    if x2 <= x1 + 4:
        return ""
    return "".join(f"M{x:.0f} {y:.0f}h1" for x in range(int(x1), int(x2), 5))


def fit_value(value: str, max_width: float, font_size: float = 14) -> str:
    """Truncate with an ellipsis if a value would collide with the label."""
    if text_width(value, font_size) <= max_width:
        return value
    trimmed = value
    while trimmed and text_width(trimmed + "…", font_size) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed.rstrip() + "…") if trimmed else "…"


def portrait_dots(color: str) -> str:
    """Deterministic stipple portrait inside the VISUAL.MAP frame."""
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing portrait: {SOURCE}")

    image = Image.open(SOURCE).convert("RGB")
    side = min(image.width, image.height)
    left = (image.width - side) // 2
    top = max(0, (image.height - side) // 2 - 40)
    crop = image.crop((left, top, left + side, top + side))
    # Slightly denser grid than before for a cleaner Emmi-like stipple.
    size = 140
    gray = ImageEnhance.Contrast(
        ImageOps.grayscale(crop.resize((size, size), Image.Resampling.LANCZOS))
    ).enhance(1.55)
    pixels = gray.load()

    # Portrait area inside left panel clip: x~55–420, y~145–530
    origin_x, origin_y = 62.0, 148.0
    step = 358.0 / size
    dots: list[str] = []
    for y in range(size):
        for x in range(size):
            value = pixels[x, y] / 255.0
            # Darker pixels → larger dots (face reads clearly).
            radius = 1.35 * (1.0 - value) ** 1.35
            if radius < 0.28:
                continue
            opacity = 0.22 + (1.0 - value) * 0.75
            dots.append(
                f'<circle cx="{origin_x + x * step:.2f}" cy="{origin_y + y * step:.2f}" '
                f'r="{radius:.2f}" fill="{color}" opacity="{opacity:.2f}"/>'
            )
    return "".join(dots)


def render(colors: dict[str, str], dots: str) -> str:
    value_right = 1127.0
    label_x = 491.0
    row_y = 153.0
    info_rows: list[str] = []

    for label, value in ROWS:
        # Leave room for label + gaps; truncate if needed.
        max_value = value_right - label_x - text_width(label, 14) - 36
        value = fit_value(value, max_value)
        label_len = text_width(label, 14)
        value_len = text_width(value, 14)
        leader_start = label_x + label_len + 12
        leader_end = value_right - value_len - 12
        info_rows.append(
            f'<text x="{label_x:.0f}" y="{row_y:.0f}" fill="{colors["muted"]}" '
            f'font-family="{FONT}" font-size="14">{html.escape(label)}</text>'
            f'<path d="{dotted_leader(leader_start, leader_end, row_y - 4)}" '
            f'fill="none" stroke="{colors["line"]}" stroke-width="1" shape-rendering="crispEdges"/>'
            f'<text x="{value_right:.0f}" y="{row_y:.0f}" text-anchor="end" fill="{colors["text"]}" '
            f'font-family="{FONT}" font-size="14" textLength="{value_len:.1f}" '
            f'lengthAdjust="spacingAndGlyphs">{html.escape(value)}</text>'
        )
        row_y += 23.0

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Faris profile dashboard">
<style>@keyframes blink{{50%{{opacity:.35}}}} .live{{animation:blink 1.6s ease-in-out infinite}}</style>
<defs>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{colors["shadow"]}" flood-opacity=".28"/>
  </filter>
  <clipPath id="visualClip"><rect x="49" y="124" width="390" height="414" rx="3"/></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="18" fill="{colors["bg"]}"/>
<rect x="13" y="13" width="1154" height="584" rx="13" fill="{colors["panel"]}" stroke="{colors["line"]}" filter="url(#shadow)"/>
<path d="M13 62H1167" stroke="{colors["line"]}"/>
<circle cx="38" cy="38" r="6" fill="#FF5F57"/>
<circle cx="59" cy="38" r="6" fill="#FEBC2E"/>
<circle cx="80" cy="38" r="6" fill="#28C840"/>
<text x="590" y="43" text-anchor="middle" fill="{colors["muted"]}" font-family="{FONT}" font-size="13" letter-spacing=".4">faris.profile — learning mode</text>

<!-- Left: VISUAL.MAP -->
<rect x="35" y="88" width="418" height="472" rx="6" fill="{colors["panel2"]}" stroke="{colors["line"]}"/>
<path d="M35 124H453" stroke="{colors["line"]}"/>
<text x="49" y="111" fill="{colors["chrome"]}" font-family="{FONT}" font-size="13" font-weight="700" letter-spacing="1.2">VISUAL.MAP</text>
<text x="438" y="111" text-anchor="end" fill="{colors["muted"]}" font-family="{FONT}" font-size="11">140×140 / DOT-MAP</text>
<path d="M49 141h12M49 141v12M439 141h-12M439 141v12M49 521h12M49 521v-12M439 521h-12M439 521v-12" fill="none" stroke="{colors["chrome"]}" opacity=".55"/>
<g clip-path="url(#visualClip)" shape-rendering="geometricPrecision">{dots}</g>
<text x="49" y="551" fill="{colors["muted"]}" font-family="{FONT}" font-size="10">PTS {len(dots.split("<circle")) - 1:05d} · FS/LEARNING</text>

<!-- Right: SYSTEM.INFO -->
<rect x="474" y="88" width="672" height="472" rx="6" fill="{colors["panel2"]}" stroke="{colors["line"]}"/>
<path d="M474 124H1146" stroke="{colors["line"]}"/>
<text x="490" y="111" fill="{colors["chrome"]}" font-family="{FONT}" font-size="13" font-weight="700" letter-spacing="1.2">SYSTEM.INFO</text>
<circle class="live" cx="915" cy="106" r="4" fill="#FF4D5A"/>
<text x="927" y="111" fill="#FF4D5A" font-family="{FONT}" font-size="12" font-weight="700">LIVE</text>
<rect x="982" y="94" width="146" height="24" rx="12" fill="{colors["chrome"]}" opacity=".16" stroke="{colors["chrome"]}"/>
<text x="1055" y="111" text-anchor="middle" fill="{colors["chrome"]}" font-family="{FONT}" font-size="14" font-weight="700">@Fariscus</text>
{"".join(info_rows)}
<path d="M490 530H1130" stroke="{colors["line"]}"/>
<text x="491" y="548" fill="{colors["accent"]}" font-family="{FONT}" font-size="11">● SYSTEM READY TO LEARN</text>
<text x="1128" y="548" text-anchor="end" fill="{colors["muted"]}" font-family="{FONT}" font-size="11">UTC+7 · CAMBODIA NODE</text>
</svg>
'''


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, colors in THEMES.items():
        svg = render(colors, portrait_dots(colors["dot"]))
        dest = ASSETS / f"banner-{name}.svg"
        dest.write_text(svg, encoding="utf-8")
        print(f"wrote {dest} ({dest.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
