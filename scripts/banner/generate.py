#!/usr/bin/env python3
"""Generate Faris's animated terminal-inspired profile banners."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
THEMES = {
    "dark": {"bg": "#0b1220", "panel": "#111c2e", "text": "#e6edf7", "muted": "#9fb3c8", "line": "#263b55", "accent": "#2dd4bf", "blue": "#60a5fa"},
    "light": {"bg": "#f8fafc", "panel": "#ffffff", "text": "#102a43", "muted": "#627d98", "line": "#d9e2ec", "accent": "#0f766e", "blue": "#2563eb"},
}


def render(name, c):
    rows = [("ROLE", "Third-year Computer Science student"), ("FOCUS", "Backend engineering · Cloud · AI agents"), ("UNIVERSITY", "Paragon International University"), ("STATUS", "Learning through projects")]
    row_svg = "".join(f'<text x="620" y="{138 + i * 42}" fill="{c["accent"]}" font-family="ui-monospace, monospace" font-size="12">{label}</text><text x="770" y="{138 + i * 42}" fill="{c["text"]}" font-family="ui-monospace, monospace" font-size="13">{value}</text><line x1="610" y1="{151 + i * 42}" x2="1110" y2="{151 + i * 42}" stroke="{c["line"]}"/>' for i, (label, value) in enumerate(rows))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="430" viewBox="0 0 1180 430" role="img" aria-label="Faris profile terminal">
<style>@keyframes pulse{{50%{{opacity:.35}}}}.cursor{{animation:pulse 1.1s step-end infinite}}</style>
<rect width="1180" height="430" rx="22" fill="{c['bg']}"/><rect x="1" y="1" width="1178" height="428" rx="21" fill="none" stroke="{c['line']}"/>
<rect x="34" y="30" width="1112" height="42" rx="11" fill="{c['panel']}" stroke="{c['line']}"/><circle cx="61" cy="51" r="6" fill="#ef4444"/><circle cx="82" cy="51" r="6" fill="#f59e0b"/><circle cx="103" cy="51" r="6" fill="#22c55e"/><text x="590" y="56" text-anchor="middle" fill="{c['muted']}" font-family="ui-monospace, monospace" font-size="13">faris@profile: ~/build</text>
<text x="65" y="125" fill="{c['accent']}" font-family="ui-monospace, monospace" font-size="16">$ whoami</text><text x="65" y="178" fill="{c['text']}" font-family="system-ui, sans-serif" font-size="48" font-weight="800">FARIS / KRIS</text>
<text x="65" y="214" fill="{c['muted']}" font-family="ui-monospace, monospace" font-size="15">aspiring software engineer<span class="cursor">_</span></text>
<rect x="65" y="252" width="430" height="88" rx="14" fill="{c['panel']}" stroke="{c['line']}"/><text x="91" y="285" fill="{c['blue']}" font-family="ui-monospace, monospace" font-size="14">JAVA · SPRING BOOT · PYTHON</text><text x="91" y="315" fill="{c['accent']}" font-family="ui-monospace, monospace" font-size="14">POSTGRES · DOCKER · AWS ↗</text>
<rect x="580" y="95" width="550" height="235" rx="14" fill="{c['panel']}" stroke="{c['line']}"/>{row_svg}
<path d="M65 385H1110" stroke="{c['line']}"/><text x="65" y="403" fill="{c['muted']}" font-family="ui-monospace, monospace" font-size="12">building, learning, and shipping one project at a time.</text></svg>\n'''


for theme, colors in THEMES.items():
    (ASSETS / f"banner-{theme}.svg").write_text(render(theme, colors), encoding="utf-8")
