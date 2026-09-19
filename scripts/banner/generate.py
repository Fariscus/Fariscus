#!/usr/bin/env python3
"""Generate Faris's animated profile banners.

Portrait (FarisFy5.png) ↔ code </> silhouette loop in VISUAL.MAP.
Layout matches the terminal dashboard structure; identity is Faris-only.

Run from repo root:
    python scripts/banner/generate.py
"""

from __future__ import annotations

import html
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/source/FarisFy5.png"
ASSETS = ROOT / "assets"
LOGOS = Path(__file__).resolve().parent / "logos"
DATA = Path(__file__).resolve().parent / "data"

W, H = 1180, 610
LOOP_SECONDS = 12.0
INTRO_SECONDS = 2.8
TRAVELLER_COUNT = 850
SEED = 20260319
FONT = "ui-monospace,SFMono-Regular,Consolas,monospace"

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

THEMES = {
    "dark": {
        "bg": "#07111f",
        "panel": "#0c1a2d",
        "panel2": "#0f2239",
        "line": "#29445e",
        "muted": "#8ba6be",
        "text": "#e4effa",
        "portrait": "#58d8c7",
        "chrome": "#4aa8ff",
        "accent": "#22c55e",
        "shadow": "#02050B",
    },
    "light": {
        "bg": "#F6F8FA",
        "panel": "#FFFFFF",
        "panel2": "#EDF3F7",
        "line": "#CBD7E1",
        "muted": "#64748B",
        "text": "#172033",
        "portrait": "#0f766e",
        "chrome": "#0891B2",
        "accent": "#10B981",
        "shadow": "#AAB7C4",
    },
}


def num(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def text_width(text: str, font_size: float) -> float:
    return len(text) * font_size * 0.605


def dotted_leader(x1: float, x2: float, y: float) -> str:
    if x2 <= x1 + 4:
        return ""
    return "".join(f"M{x:.0f} {y:.0f}h1" for x in range(int(x1), int(x2), 5))


def fit_value(value: str, max_width: float, font_size: float = 14) -> str:
    if text_width(value, font_size) <= max_width:
        return value
    trimmed = value
    while trimmed and text_width(trimmed + "…", font_size) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed.rstrip() + "…") if trimmed else "…"


def make_logos() -> dict[str, Image.Image]:
    """Create Faris-themed silhouettes (code + cloud) — not Emmi's logos."""
    LOGOS.mkdir(parents=True, exist_ok=True)
    size = 400
    logos: dict[str, Image.Image] = {}

    # </> developer mark
    code = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(code)
    stroke = 42
    draw.line([(154, 95), (66, 200), (154, 305)], fill="black", width=stroke, joint="curve")
    draw.line([(246, 95), (334, 200), (246, 305)], fill="black", width=stroke, joint="curve")
    draw.line([(225, 72), (174, 328)], fill="black", width=stroke)
    logos["code"] = code

    # Simple cloud (cloud-engineering interest)
    cloud = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(cloud)
    draw.ellipse((70, 150, 210, 290), fill="black")
    draw.ellipse((140, 110, 300, 270), fill="black")
    draw.ellipse((220, 155, 350, 285), fill="black")
    draw.rectangle((90, 210, 330, 300), fill="black")
    logos["cloud"] = cloud

    for name, image in logos.items():
        image.save(LOGOS / f"{name}.png", optimize=True)
    return logos


def floyd_steinberg(gray: np.ndarray) -> np.ndarray:
    """Serpentine 1-bit dither; True = lit pixel."""
    work = gray.astype(np.float32) / 255.0
    out = np.zeros_like(work, dtype=bool)
    height, width = work.shape
    for y in range(height):
        left_to_right = y % 2 == 0
        xs = range(width) if left_to_right else range(width - 1, -1, -1)
        direction = 1 if left_to_right else -1
        for x in xs:
            old = work[y, x]
            new = 1.0 if old >= 0.5 else 0.0
            out[y, x] = bool(new)
            err = old - new
            nx = x + direction
            if 0 <= nx < width:
                work[y, nx] += err * 7 / 16
            if y + 1 < height:
                if 0 <= x - direction < width:
                    work[y + 1, x - direction] += err * 3 / 16
                work[y + 1, x] += err * 5 / 16
                if 0 <= nx < width:
                    work[y + 1, nx] += err * 1 / 16
    return out


def portrait_points(theme: str, rng: np.random.Generator) -> np.ndarray:
    """Sample dithered portrait points into the VISUAL.MAP frame."""
    source = Image.open(SOURCE).convert("RGBA")
    # Head + torso crop for FarisFy5 (1033×1522, subject centered with halo).
    w, h = source.size
    crop = source.crop((int(w * 0.12), int(h * 0.02), int(w * 0.88), int(h * 0.72)))
    crop = crop.resize((300, 340), Image.Resampling.LANCZOS)
    rgb = crop.convert("RGB")
    alpha = np.asarray(crop.getchannel("A"), dtype=np.float32) / 255.0
    # Also treat near-black studio backdrop as empty.
    lum_raw = np.asarray(ImageOps.grayscale(rgb), dtype=np.float32)
    alpha = np.maximum(alpha, (lum_raw > 18).astype(np.float32))

    if theme == "dark":
        prepared = Image.fromarray(np.uint8(np.clip(lum_raw * alpha, 0, 255)), "L")
        select_lit = True
        mask = Image.fromarray(np.uint8((alpha > 0.08) * 255), "L")
        prepared = ImageOps.equalize(prepared, mask=mask)
    else:
        white = Image.new("RGBA", crop.size, "white")
        white.alpha_composite(crop)
        prepared = ImageOps.grayscale(white.convert("RGB"))
        select_lit = False
        prepared = ImageOps.autocontrast(prepared, cutoff=1)

    prepared = ImageEnhance.Contrast(prepared).enhance(1.4)
    prepared = prepared.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=1))
    bits = floyd_steinberg(np.asarray(prepared))
    active = bits if select_lit else ~bits
    active &= alpha > 0.08

    ys, xs = np.where(active)
    if len(xs) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    points = np.column_stack((74 + xs, 154 + ys)).astype(np.float32)
    if len(points) > 16000:
        points = points[rng.choice(len(points), 16000, replace=False)]
    return points


def sample_logo_points(image: Image.Image, rng: np.random.Generator, count: int) -> np.ndarray:
    alpha = np.asarray(image.getchannel("A"))
    ys, xs = np.where(alpha > 127)
    chosen = rng.choice(len(xs), count, replace=len(xs) < count)
    # Centered ~270×270 square inside VISUAL.MAP.
    return np.column_stack((89 + xs[chosen] * 0.675, 188 + ys[chosen] * 0.675)).astype(np.float32)


def transport(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    rows, cols = linear_sum_assignment(cdist(source, target, metric="sqeuclidean"))
    ordered = np.empty_like(target)
    ordered[rows] = target[cols]
    return ordered


def point_path(points: np.ndarray) -> str:
    if not len(points):
        return ""
    integer = np.rint(points).astype(int)
    unique = sorted({(int(x), int(y)) for x, y in integer}, key=lambda p: (p[1], p[0]))
    chunks: list[str] = []
    i = 0
    while i < len(unique):
        x0, y = unique[i]
        x1 = x0
        i += 1
        while i < len(unique) and unique[i][1] == y and unique[i][0] <= x1 + 1:
            x1 = unique[i][0]
            i += 1
        chunks.append(f"M{x0} {y}h{x1 - x0 + 1}")
    return "".join(chunks)


def animate_values(points: list[np.ndarray], index: int) -> str:
    return ";".join(f"{num(p[index, 0])} {num(p[index, 1])}" for p in points)


def render_info_rows(colors: dict[str, str]) -> str:
    value_right = 1127.0
    label_x = 491.0
    row_y = 153.0
    parts: list[str] = []
    for label, value in ROWS:
        max_value = value_right - label_x - text_width(label, 14) - 36
        value = fit_value(value, max_value)
        label_len = text_width(label, 14)
        value_len = text_width(value, 14)
        leader_start = label_x + label_len + 12
        leader_end = value_right - value_len - 12
        parts.append(
            f'<text x="{label_x:.0f}" y="{row_y:.0f}" fill="{colors["muted"]}" '
            f'font-family="{FONT}" font-size="14">{html.escape(label)}</text>'
            f'<path d="{dotted_leader(leader_start, leader_end, row_y - 4)}" '
            f'fill="none" stroke="{colors["line"]}" stroke-width="1" shape-rendering="crispEdges"/>'
            f'<text x="{value_right:.0f}" y="{row_y:.0f}" text-anchor="end" fill="{colors["text"]}" '
            f'font-family="{FONT}" font-size="14" textLength="{value_len:.1f}" '
            f'lengthAdjust="spacingAndGlyphs">{html.escape(value)}</text>'
        )
        row_y += 23.0
    return "".join(parts)


def render_svg(
    theme_name: str,
    portrait: np.ndarray,
    logo_points: dict[str, np.ndarray],
    rng: np.random.Generator,
) -> str:
    colors = THEMES[theme_name]
    n = min(TRAVELLER_COUNT, len(portrait))
    source = portrait[rng.choice(len(portrait), n, replace=False)]
    code = transport(source, logo_points["code"][:n])
    cloud = transport(code, logo_points["cloud"][:n])

    # portrait → code (dev) → cloud → portrait
    # hold / morph / hold / morph / hold / morph / hold
    times = [0, 2.8, 4.0, 6.2, 7.4, 9.6, 10.8, 12.0]
    key_times = ";".join(num(v / LOOP_SECONDS) for v in times)
    frames = [source, source, code, code, cloud, cloud, source, source]
    opacity_values = "0;0;1;1;1;1;1;0"

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        'role="img" aria-label="Faris animated profile dashboard">',
        "<style>@keyframes blink{50%{opacity:.35}} .live{animation:blink 1.6s ease-in-out infinite}</style>",
        "<defs>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{colors["shadow"]}" flood-opacity=".28"/>'
        "</filter>",
        '<clipPath id="visualClip"><rect x="49" y="124" width="390" height="414" rx="3"/></clipPath>',
        "</defs>",
        f'<rect width="{W}" height="{H}" rx="18" fill="{colors["bg"]}"/>',
        f'<rect x="13" y="13" width="1154" height="584" rx="13" fill="{colors["panel"]}" '
        f'stroke="{colors["line"]}" filter="url(#shadow)"/>',
        f'<path d="M13 62H1167" stroke="{colors["line"]}"/>',
        '<circle cx="38" cy="38" r="6" fill="#FF5F57"/>'
        '<circle cx="59" cy="38" r="6" fill="#FEBC2E"/>'
        '<circle cx="80" cy="38" r="6" fill="#28C840"/>',
        f'<text x="590" y="43" text-anchor="middle" fill="{colors["muted"]}" '
        f'font-family="{FONT}" font-size="13" letter-spacing=".4">faris.profile — learning mode</text>',
        # Left panel
        f'<rect x="35" y="88" width="418" height="472" rx="6" fill="{colors["panel2"]}" stroke="{colors["line"]}"/>',
        f'<path d="M35 124H453" stroke="{colors["line"]}"/>',
        f'<text x="49" y="111" fill="{colors["chrome"]}" font-family="{FONT}" font-size="13" '
        'font-weight="700" letter-spacing="1.2">VISUAL.MAP</text>',
        f'<text x="438" y="111" text-anchor="end" fill="{colors["muted"]}" font-family="{FONT}" '
        'font-size="11">300×340 / 1-BIT</text>',
        f'<path d="M49 141h12M49 141v12M439 141h-12M439 141v12M49 521h12M49 521v-12'
        f'M439 521h-12M439 521v-12" fill="none" stroke="{colors["chrome"]}" opacity=".55"/>',
        '<g clip-path="url(#visualClip)" shape-rendering="crispEdges">',
        '<g opacity="1">',
    ]

    # Portrait drift bands (visible at rest; fade while travellers take over).
    code_centroid = code.mean(axis=0)
    band_ids = rng.integers(0, 80, size=len(portrait))
    noise = rng.normal(0, 4, size=(80, 2))
    for band in range(80):
        pts = portrait[band_ids == band]
        if not len(pts):
            continue
        centroid = pts.mean(axis=0)
        delta = (code_centroid - centroid) * 0.16 + noise[band]
        d = point_path(pts)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{colors["portrait"]}" stroke-width="1" opacity=".94">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="0 0;0 0;{num(delta[0])} {num(delta[1])};'
            f'{num(delta[0])} {num(delta[1])};0 0;0 0;0 0;0 0"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" keyTimes="{key_times}" '
            'values=".94;.94;0;0;0;0;.94;.94"/></path>'
        )

    # Travellers: portrait → </> → cloud → portrait
    for i in range(n):
        positions = animate_values(frames, i)
        parts.append(
            f'<path d="M-.65-.65h1.3v1.3h-1.3z" fill="{colors["portrait"]}">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="{positions}"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" calcMode="linear" keyTimes="{key_times}" '
            f'values="{opacity_values}"/></path>'
        )
    parts.append("</g>")

    # Intro shimmer: face appears in scattered groups once.
    intro_ids = rng.integers(0, 50, size=len(portrait))
    order = rng.permutation(50)
    starts = np.empty(50)
    starts[order] = np.linspace(0.05, 1.1, 50)
    for group in range(50):
        pts = portrait[intro_ids == group]
        if not len(pts):
            continue
        parts.append(
            f'<path d="{point_path(pts)}" fill="none" stroke="{colors["portrait"]}" '
            'stroke-width="1" opacity="0">'
            f'<animate attributeName="opacity" begin="{num(starts[group])}s" dur=".7s" '
            'values="0;1" fill="freeze"/>'
            f'<animate attributeName="opacity" begin="{num(INTRO_SECONDS - 0.12)}s" dur=".12s" '
            'values="1;0" fill="freeze"/>'
            "</path>"
        )

    parts.extend(
        [
            "</g>",
            f'<text x="49" y="551" fill="{colors["muted"]}" font-family="{FONT}" font-size="10">'
            f"PTS {len(portrait):05d} · PIC→DEV→CLOUD→PIC</text>",
            # Right panel
            f'<rect x="474" y="88" width="672" height="472" rx="6" fill="{colors["panel2"]}" '
            f'stroke="{colors["line"]}"/>',
            f'<path d="M474 124H1146" stroke="{colors["line"]}"/>',
            f'<text x="490" y="111" fill="{colors["chrome"]}" font-family="{FONT}" font-size="13" '
            'font-weight="700" letter-spacing="1.2">SYSTEM.INFO</text>',
            '<circle class="live" cx="915" cy="106" r="4" fill="#FF4D5A"/>',
            f'<text x="927" y="111" fill="#FF4D5A" font-family="{FONT}" font-size="12" '
            'font-weight="700">LIVE</text>',
            f'<rect x="982" y="94" width="146" height="24" rx="12" fill="{colors["chrome"]}" '
            f'opacity=".16" stroke="{colors["chrome"]}"/>',
            f'<text x="1055" y="111" text-anchor="middle" fill="{colors["chrome"]}" '
            f'font-family="{FONT}" font-size="14" font-weight="700">@Fariscus</text>',
            render_info_rows(colors),
            f'<path d="M490 530H1130" stroke="{colors["line"]}"/>',
            f'<text x="491" y="548" fill="{colors["accent"]}" font-family="{FONT}" font-size="11">'
            "● SYSTEM READY TO LEARN</text>",
            f'<text x="1128" y="548" text-anchor="end" fill="{colors["muted"]}" '
            f'font-family="{FONT}" font-size="11">UTC+7 · CAMBODIA NODE</text>',
            "</svg>",
        ]
    )
    return "".join(parts)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing portrait: {SOURCE}")

    ASSETS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    logos = make_logos()

    portraits: dict[str, np.ndarray] = {}
    for index, theme in enumerate(THEMES):
        rng = np.random.default_rng(SEED + index)
        points = portrait_points(theme, rng)
        portraits[theme] = points
        np.save(DATA / f"portrait-{theme}.npy", points)
        print(f"portrait-{theme}: {len(points):,} points")

    for index, theme in enumerate(THEMES):
        rng = np.random.default_rng(SEED + 100 + index)
        sampled = {
            name: sample_logo_points(image, rng, TRAVELLER_COUNT)
            for name, image in logos.items()
        }
        for name, points in sampled.items():
            np.save(DATA / f"{name}-{theme}.npy", points)
        svg = render_svg(theme, portraits[theme], sampled, rng)
        output = ASSETS / f"banner-{theme}.svg"
        output.write_text(svg, encoding="utf-8")
        print(
            f"wrote {output.relative_to(ROOT)} "
            f"({output.stat().st_size / 1024:.1f} KiB)"
        )


if __name__ == "__main__":
    main()
