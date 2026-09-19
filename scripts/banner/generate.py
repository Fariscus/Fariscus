#!/usr/bin/env python3
"""Generate Faris's animated profile banners.

Loop (two states only):
  portrait (farisfyyy.png)  →  </>  (dev)  →  portrait

Run from repo root:
    python scripts/banner/generate.py
"""

from __future__ import annotations

import html
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/source/farisfyyy.png"
ASSETS = ROOT / "assets"
LOGOS = Path(__file__).resolve().parent / "logos"
DATA = Path(__file__).resolve().parent / "data"

W, H = 1180, 610
LOOP_SECONDS = 10.0
INTRO_SECONDS = 2.6
TRAVELLER_COUNT = 900
MAX_PORTRAIT_POINTS = 18000
SEED = 20260319
FONT = "ui-monospace,SFMono-Regular,Consolas,monospace"

ROWS = [
    ("Subject", "Faris / Kris"),
    ("Role", "CS Student · Aspiring SWE"),
    ("Origin", "Cambodia"),
    ("Education", "Paragon IU · CS"),
    ("Status", "Building + Learning + Shipping"),
    ("ToolChain", "Cursor · Git · Docker"),
    ("Core.Lang", "Java · Python · C++ · TS"),
    ("Core.Frontend", "React · JavaScript"),
    ("Core.Backend", "Spring Boot · Laravel"),
    ("Core.Database", "MySQL · PostgreSQL"),
    ("Core.Infra", "Docker · GitHub · Linux"),
    ("Grid.Mail", "—"),
    ("Grid.LinkedIn", "/in/faris-fy"),
    ("Grid.GitHub", "Fariscus"),
    ("Grid.X", "—"),
]

THEMES = {
    "dark": {
        "bg": "#0A101F",
        "panel": "#0D1628",
        "panel2": "#101B30",
        "line": "#25344C",
        "muted": "#8291A8",
        "text": "#DDE7F5",
        "portrait": "#AA9BEF",
        "chrome": "#22D3EE",
        "accent": "#10B981",
        "shadow": "#02050B",
    },
    "light": {
        "bg": "#F6F8FA",
        "panel": "#FFFFFF",
        "panel2": "#EDF3F7",
        "line": "#CBD7E1",
        "muted": "#64748B",
        "text": "#172033",
        "portrait": "#4A3D7A",
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
    """Only the </> developer mark."""
    LOGOS.mkdir(parents=True, exist_ok=True)
    size = 400
    code = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(code)
    stroke = 44
    draw.line([(154, 95), (66, 200), (154, 305)], fill="black", width=stroke, joint="curve")
    draw.line([(246, 95), (334, 200), (246, 305)], fill="black", width=stroke, joint="curve")
    draw.line([(225, 72), (174, 328)], fill="black", width=stroke)
    code.save(LOGOS / "code.png", optimize=True)
    cloud = LOGOS / "cloud.png"
    if cloud.exists():
        cloud.unlink()
    return {"code": code}


def floyd_steinberg(gray: np.ndarray) -> np.ndarray:
    """Serpentine 1-bit Floyd-Steinberg diffusion; True means a lit pixel."""
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


def subject_crop() -> Image.Image:
    """Full head-and-shoulders cutout, centered in the 300×340 VISUAL.MAP lattice."""
    source = Image.open(SOURCE).convert("RGBA")
    alpha = np.asarray(source.getchannel("A"))
    ys, xs = np.where(alpha > 20)
    if len(xs) == 0:
        raise SystemExit(f"No opaque pixels in {SOURCE}")
    pad = 4
    x0 = max(0, int(xs.min()) - pad)
    y0 = max(0, int(ys.min()) - pad)
    x1 = min(source.size[0], int(xs.max()) + pad)
    y1 = min(source.size[1], int(ys.max()) + pad)
    # Use the full subject (hair → shoulders/chest), not a tight face crop.
    head = source.crop((x0, y0, x1, y1))

    tw, th = 300, 340
    hw, hh = head.size
    # Fill the VISUAL.MAP frame — small padding only.
    scale = min(tw / hw, th / hh) * 0.99
    nw, nh = max(1, int(round(hw * scale))), max(1, int(round(hh * scale)))
    resized = head.resize((nw, nh), Image.Resampling.LANCZOS)

    a = np.asarray(resized.getchannel("A"))
    ys, xs = np.where(a > 20)
    if len(xs):
        cx = (xs.min() + xs.max()) / 2.0
        cy = (ys.min() + ys.max()) / 2.0
        ox = int(round(tw / 2 - cx))
        oy = int(round(th / 2 - cy))
    else:
        ox, oy = (tw - nw) // 2, (th - nh) // 2

    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    canvas.paste(resized, (ox, oy), resized)
    return canvas


def portrait_points(theme: str, rng: np.random.Generator) -> np.ndarray:
    """Return sampled x/y banner coordinates from a 300x340 dither grid."""
    crop = subject_crop()
    alpha = np.asarray(crop.getchannel("A"), dtype=np.float32) / 255.0

    if theme == "dark":
        lum = np.asarray(ImageOps.grayscale(crop.convert("RGB")), dtype=np.float32)
        # Lift shadows so the jawline stays visible (dark chin was vanishing).
        lifted = np.clip(255.0 * np.power(np.clip(lum / 255.0, 0, 1), 0.78), 0, 255)
        prepared = Image.fromarray(np.uint8(np.clip(lifted * alpha, 0, 255)))
        mask = Image.fromarray(np.uint8((alpha > 0.08) * 255))
        prepared = ImageOps.equalize(prepared, mask=mask)
        prepared = ImageEnhance.Contrast(prepared).enhance(1.28)
        prepared = prepared.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=1))
        select_lit = True
    else:
        # Same light-theme pipeline as the sample: white paper + autocontrast + FS.
        # (Earlier ink-crush made a solid blob; this keeps face detail like Emmi.)
        white = Image.new("RGBA", crop.size, "white")
        white.alpha_composite(crop)
        gray = np.asarray(ImageOps.grayscale(white.convert("RGB")), dtype=np.float32)
        mask = alpha > 0.08
        # Soften pale gray shirt so clothing still prints dots without crushing face.
        rgb = np.asarray(crop.convert("RGB"), dtype=np.float32)
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        max_c = np.maximum(np.maximum(r, g), b)
        min_c = np.minimum(np.minimum(r, g), b)
        sat = (max_c - min_c) / np.maximum(max_c, 1.0)
        shirt = mask & (sat < 0.14) & (gray > 120)
        gray = gray.copy()
        gray[shirt] *= 0.72
        gray = np.where(mask, gray, 255.0)
        prepared = Image.fromarray(np.uint8(np.clip(gray, 0, 255)))
        prepared = ImageOps.autocontrast(prepared, cutoff=1)
        prepared = ImageEnhance.Contrast(prepared).enhance(1.45)
        prepared = prepared.filter(ImageFilter.UnsharpMask(radius=2, percent=185, threshold=1))
        arr = np.asarray(prepared).astype(np.float32)
        prepared = Image.fromarray(np.uint8(np.where(mask, arr, 255.0)))
        select_lit = False
    bits = floyd_steinberg(np.asarray(prepared))
    active = bits if select_lit else ~bits
    if theme == "dark":
        active &= alpha > 0.08
    else:
        # Keep light-theme dots on the subject only (transparent → no ink).
        active &= alpha > 0.08

    ys, xs = np.where(active)
    if len(xs) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    points = np.column_stack((74 + xs, 154 + ys)).astype(np.float32)
    # Nudge so the silhouette bbox sits in the middle of VISUAL.MAP.
    cell_cx, cell_cy = 74 + 150.0, 154 + 170.0
    bx = (points[:, 0].min() + points[:, 0].max()) / 2.0
    by = (points[:, 1].min() + points[:, 1].max()) / 2.0
    points = points + np.array([cell_cx - bx, cell_cy - by], dtype=np.float32)
    if len(points) > MAX_PORTRAIT_POINTS:
        points = points[rng.choice(len(points), MAX_PORTRAIT_POINTS, replace=False)]
    return points


def sample_logo_points(image: Image.Image, rng: np.random.Generator, count: int) -> np.ndarray:
    alpha = np.asarray(image.getchannel("A"))
    ys, xs = np.where(alpha > 127)
    chosen = rng.choice(len(xs), count, replace=len(xs) < count)
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
    # Match sample layout: labels left, values right, leaders fill the gap.
    value_right = 1127.0
    label_x = 491.0
    row_y = 153.0
    row_step = 23.0
    parts: list[str] = []
    for label, value in ROWS:
        max_value = value_right - label_x - text_width(label, 14) - 40
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
        row_y += row_step
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

    # Two states: portrait → </> → portrait
    times = [0, 3.0, 4.2, 7.0, 8.2, 10.0]
    key_times = ";".join(num(v / LOOP_SECONDS) for v in times)
    frames = [source, source, code, code, source, source]
    opacity_values = "0;0;1;1;0;0"
    band_opacity = ".94;.94;0;0;.94;.94"

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        'role="img" aria-label="Faris animated profile dashboard">',
        "<style>@keyframes blink{50%{opacity:.35}} .live{animation:blink 1.6s ease-in-out infinite}</style>",
        "<defs>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{colors["shadow"]}" flood-opacity=".28"/>'
        "</filter>",
        '<filter id="glow" x="-100%" y="-100%" width="300%" height="300%">'
        f'<feGaussianBlur stdDeviation="3" result="b"/><feFlood flood-color="{colors["chrome"]}" '
        'flood-opacity=".35"/><feComposite in2="b" operator="in"/>'
        '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
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
        f'font-family="{FONT}" font-size="13" letter-spacing=".4">profile.sh --live</text>',
        f'<rect x="35" y="88" width="418" height="472" rx="6" fill="{colors["panel2"]}" stroke="{colors["line"]}"/>',
        f'<path d="M35 124H453" stroke="{colors["line"]}"/>',
        f'<text x="49" y="111" fill="{colors["chrome"]}" font-family="{FONT}" font-size="13" '
        'font-weight="700" letter-spacing="1.2">VISUAL.MAP</text>',
        f'<text x="438" y="111" text-anchor="end" fill="{colors["muted"]}" font-family="{FONT}" '
        'font-size="11">300×340 / 1-BIT</text>',
        f'<path d="M49 141h12M49 141v12M439 141h-12M439 141v12M49 539h12M49 539v-12'
        f'M439 539h-12M439 539v-12" fill="none" stroke="{colors["chrome"]}" opacity=".55"/>',
        '<g clip-path="url(#visualClip)" shape-rendering="crispEdges">',
        '<g opacity="1">',
    ]

    code_centroid = code.mean(axis=0)
    band_ids = rng.integers(0, 94, size=len(portrait))
    noise = rng.normal(0, 3.5, size=(94, 2))
    for band in range(94):
        pts = portrait[band_ids == band]
        if not len(pts):
            continue
        centroid = pts.mean(axis=0)
        delta = (code_centroid - centroid) * 0.14 + noise[band]
        d = point_path(pts)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{colors["portrait"]}" stroke-width="1" opacity=".94">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="0 0;0 0;{num(delta[0])} {num(delta[1])};'
            f'{num(delta[0])} {num(delta[1])};0 0;0 0"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" keyTimes="{key_times}" '
            f'values="{band_opacity}"/></path>'
        )

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

    intro_ids = rng.integers(0, 60, size=len(portrait))
    order = rng.permutation(60)
    starts = np.empty(60)
    starts[order] = np.linspace(0.05, 1.15, 60)
    for group in range(60):
        pts = portrait[intro_ids == group]
        if not len(pts):
            continue
        parts.append(
            f'<path d="{point_path(pts)}" fill="none" stroke="{colors["portrait"]}" '
            'stroke-width="1" opacity="0">'
            f'<animate attributeName="opacity" begin="{num(starts[group])}s" dur=".75s" '
            'values="0;1" fill="freeze"/>'
            f'<animate attributeName="opacity" begin="{num(INTRO_SECONDS - 0.12)}s" dur=".12s" '
            'values="1;0" fill="freeze"/>'
            "</path>"
        )

    parts.extend(
        [
            "</g>",
            f'<text x="58" y="551" fill="{colors["muted"]}" font-family="{FONT}" font-size="10">'
            f"PTS {len(portrait):05d} · FS/SERPENTINE</text>",
            f'<rect x="474" y="88" width="672" height="472" rx="6" fill="{colors["panel2"]}" '
            f'stroke="{colors["line"]}"/>',
            f'<path d="M474 124H1146" stroke="{colors["line"]}"/>',
            f'<text x="490" y="111" fill="{colors["chrome"]}" font-family="{FONT}" font-size="13" '
            'font-weight="700" letter-spacing="1.2">SYSTEM.INFO</text>',
            '<g filter="url(#glow)"><circle class="live" cx="915" cy="106" r="4" fill="#FF4D5A"/></g>',
            f'<text x="927" y="111" fill="#FF4D5A" font-family="{FONT}" font-size="12" '
            'font-weight="700">LIVE</text>',
            f'<rect x="982" y="94" width="146" height="24" rx="12" fill="{colors["chrome"]}" '
            f'opacity=".16" stroke="{colors["chrome"]}"/>',
            f'<text x="1055" y="111" text-anchor="middle" fill="{colors["chrome"]}" '
            f'font-family="{FONT}" font-size="14" font-weight="700">@Fariscus</text>',
            render_info_rows(colors),
            f'<path d="M490 530H1130" stroke="{colors["line"]}"/>',
            f'<text x="491" y="548" fill="{colors["accent"]}" font-family="{FONT}" font-size="11">'
            "● ALL SYSTEMS NOMINAL</text>",
            f'<text x="1128" y="548" text-anchor="end" fill="{colors["muted"]}" '
            f'font-family="{FONT}" font-size="11">UTC+7 · CAMBODIA NODE</text>',
            "</svg>",
        ]
    )
    return "".join(parts)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source portrait: {SOURCE}")

    print(f"using portrait: {SOURCE.relative_to(ROOT)}")
    ASSETS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    logos = make_logos()

    for leftover in DATA.glob("cloud-*.npy"):
        leftover.unlink()

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
        print(f"wrote {output.relative_to(ROOT)} ({output.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
