#!/usr/bin/env python3
"""Build GitHub statistics, language breakdown, and featured repo SVG cards.

Uses only the Python standard library + GitHub REST/GraphQL APIs.
Fails softly: one bad request does not crash the whole run.

  python scripts/cards.py --user Fariscus --projects data/projects.json --out assets
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

USERNAME_DEFAULT = "Fariscus"

UA = {"User-Agent": "faris-fy-profile-cards"}

# Teal dark / green light — Faris identity (not purple branding).
THEMES = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "title": "#2dd4bf",
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "value": "#e6edf3",
        "accent": "#2dd4bf",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "title": "#1a7f37",
        "text": "#1f2328",
        "muted": "#57606a",
        "value": "#1f2328",
        "accent": "#1a7f37",
    },
}

LANG_COLOR = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "PHP": "#4F5D95",
    "Makefile": "#427819",
    "Dockerfile": "#384d54",
}

FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"

ICON_STAR = (
    "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 "
    "2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 "
    "01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"
)
ICON_FORK = (
    "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75v-.878a2.25 2.25 0 "
    "111.5 0v.878a2.25 2.25 0 01-2.25 2.25h-1.5v2.128a2.251 2.251 0 11-1.5 "
    "0V8.5h-1.5A2.25 2.25 0 013.5 6.25v-.878a2.25 2.25 0 111.5 0zM5 3.25a.75.75 0 "
    "10-1.5 0 .75.75 0 001.5 0zm6.75.75a.75.75 0 100-1.5.75.75 0 000 1.5zm-3 "
    "8.75a.75.75 0 100-1.5.75.75 0 000 1.5z"
)
ICON_REPO = (
    "M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 "
    "0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 "
    "012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 "
    "12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 "
    "00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"
)

CONTRIB_QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}
"""


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text_width(text: str, size: float) -> float:
    return len(text) * size * 0.53


def wrap(text: str, size: float, max_w: float, max_lines: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if text_width(trial, size) <= max_w or not current:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and words:
        used = len(" ".join(lines).split())
        if used < len(words):
            while lines and text_width(lines[-1] + "…", size) > max_w:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] += "…"
    return lines


def icon(path: str, x: float, y: float, size: float, fill: str) -> str:
    scale = size / 16
    return (
        f'<path transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})" '
        f'fill="{fill}" d="{path}"/>'
    )


def api_get(path: str, token: str | None):
    request = urllib.request.Request(
        "https://api.github.com" + path,
        headers={**UA, "Accept": "application/vnd.github+json"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"  skip {path}: {error}", file=sys.stderr)
        return None


def graphql(query: str, variables: dict, token: str):
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={**UA, "Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"  graphql unavailable: {error}", file=sys.stderr)
        return None


def fetch_contributions(user: str, token: str | None):
    """Return (total, current_streak, longest_streak) when GraphQL works."""
    if not token:
        return None
    payload = graphql(CONTRIB_QUERY, {"login": user}, token)
    if not payload or payload.get("errors"):
        if payload and payload.get("errors"):
            print(f"  contributions: {payload['errors'][0].get('message')}", file=sys.stderr)
        return None
    try:
        calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except (TypeError, KeyError):
        return None

    days = [
        (dt.date.fromisoformat(day["date"]), day["contributionCount"])
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    ]
    days.sort()

    longest = run = 0
    for _, count in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)

    current = 0
    for date, count in reversed(days):
        if count > 0:
            current += 1
        elif date != days[-1][0]:
            break
    return calendar["totalContributions"], current, longest


def frame(width: int, height: int, colors: dict, body: str, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{esc(label)}" '
        f'font-family="{FONT}">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" '
        f'fill="{colors["bg"]}" stroke="{colors["border"]}"/>'
        f"{body}</svg>"
    )


def render_stats(user: str, tiles: list[tuple[str, str]], theme: str) -> str:
    colors = THEMES[theme]
    pad = 22
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    row_h, width = 46, 480
    height = pad + 52 + (rows - 1) * row_h + 17 + pad
    col_w = (width - 2 * pad) / cols

    parts = [
        f'<text x="{pad}" y="{pad + 14}" font-size="15" font-weight="700" '
        f'fill="{colors["title"]}">{esc(user)}</text>',
        f'<text x="{width - pad}" y="{pad + 14}" font-size="11" text-anchor="end" '
        f'fill="{colors["muted"]}">at a glance</text>',
        f'<line x1="{pad}" y1="{pad + 26}" x2="{width - pad}" y2="{pad + 26}" '
        f'stroke="{colors["border"]}"/>',
    ]
    top = pad + 52
    for index, (label, value) in enumerate(tiles):
        x = pad + (index % cols) * col_w
        y = top + (index // cols) * row_h
        parts.append(
            f'<text x="{x:.0f}" y="{y:.0f}" font-size="23" font-weight="700" '
            f'fill="{colors["value"]}">{esc(value)}</text>'
        )
        parts.append(
            f'<text x="{x:.0f}" y="{y + 17:.0f}" font-size="10.5" '
            f'fill="{colors["muted"]}">{esc(label)}</text>'
        )
    return frame(width, height, colors, "".join(parts), f"{user} GitHub statistics")


def render_repo(repo: dict, theme: str) -> str:
    colors = THEMES[theme]
    width, height, pad = 420, 132, 18
    parts = [
        icon(ICON_REPO, pad, pad, 15, colors["muted"]),
        f'<text x="{pad + 22}" y="{pad + 12}" font-size="14.5" font-weight="700" '
        f'fill="{colors["title"]}">{esc(repo["name"])}</text>',
    ]
    description = repo.get("description") or "No description yet."
    for index, line in enumerate(wrap(description, 11.5, width - 2 * pad, 3)):
        parts.append(
            f'<text x="{pad}" y="{pad + 36 + index * 16}" font-size="11.5" '
            f'fill="{colors["text"]}">{esc(line)}</text>'
        )

    footer_y = height - pad - 2
    x = pad
    if repo.get("language"):
        color = LANG_COLOR.get(repo["language"], colors["muted"])
        parts.append(f'<circle cx="{x + 5}" cy="{footer_y - 4}" r="5" fill="{color}"/>')
        parts.append(
            f'<text x="{x + 15}" y="{footer_y}" font-size="11" fill="{colors["muted"]}">'
            f'{esc(repo["language"])}</text>'
        )
        x += 15 + text_width(repo["language"], 11) + 18

    for path, count in ((ICON_STAR, repo.get("stars", 0)), (ICON_FORK, repo.get("forks", 0))):
        parts.append(icon(path, x, footer_y - 11, 12, colors["muted"]))
        parts.append(
            f'<text x="{x + 17}" y="{footer_y}" font-size="11" fill="{colors["muted"]}">'
            f"{count}</text>"
        )
        x += 17 + text_width(str(count), 11) + 18

    return frame(width, height, colors, "".join(parts), f'{repo["name"]} repository card')


def render_languages(languages: Counter, theme: str = "light") -> str:
    """Horizontal bar + two-column legend, similar layout to common metrics cards."""
    colors = THEMES[theme]
    top = languages.most_common(8)
    total = sum(languages.values()) or 1
    width, bar_w, pad = 480, 436, 22
    legend_rows = (len(top) + 1) // 2
    height = 88 + legend_rows * 22 + 18

    parts = [
        f'<text x="{pad}" y="28" font-size="15" font-weight="700" fill="#0969da">'
        f'{len(languages)} Languages</text>',
        f'<text x="{width / 2}" y="52" text-anchor="middle" font-size="13" fill="#0969da">'
        f"Most used languages</text>",
    ]

    x = pad
    y = 64
    for name, bytes_count in top:
        segment = bar_w * bytes_count / total
        fill = LANG_COLOR.get(name, "#8b949e")
        parts.append(
            f'<rect x="{x:.2f}" y="{y}" width="{segment:.2f}" height="8" fill="{fill}"/>'
        )
        x += segment
    # rounded mask look via outer stroke frame
    parts.append(
        f'<rect x="{pad}" y="{y}" width="{bar_w}" height="8" rx="4" fill="none" '
        f'stroke="{colors["border"]}"/>'
    )

    for index, (name, bytes_count) in enumerate(top):
        col = index % 2
        row = index // 2
        lx = pad + col * 220
        ly = 96 + row * 22
        fill = LANG_COLOR.get(name, "#8b949e")
        pct = bytes_count / total * 100
        size_mb = bytes_count / (1024 * 1024)
        size_label = f"{size_mb:.2f} MB" if size_mb >= 0.01 else f"{bytes_count / 1024:.1f} KB"
        parts.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="4" fill="{fill}"/>')
        parts.append(
            f'<text x="{lx + 14}" y="{ly}" font-size="12" fill="{colors["text"]}">'
            f"{esc(name)}</text>"
        )
        parts.append(
            f'<text x="{lx + 200}" y="{ly}" text-anchor="end" font-size="11" '
            f'fill="{colors["muted"]}">{size_label} · {pct:.2f}%</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="Most used languages" '
        f'font-family="{FONT}">'
        f'<rect width="{width}" height="{height}" fill="{colors["bg"]}"/>'
        f"{''.join(parts)}</svg>"
    )


def list_repos(user: str, token: str | None) -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        batch = api_get(
            f"/users/{user}/repos?per_page=100&page={page}&type=owner&sort=updated",
            token,
        )
        if not isinstance(batch, list):
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default=USERNAME_DEFAULT)
    parser.add_argument("--projects", type=Path, default=Path("data/projects.json"))
    parser.add_argument("--out", type=Path, default=Path("assets"))
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    args.out.mkdir(parents=True, exist_ok=True)

    user = api_get(f"/users/{args.user}", token)
    repos = list_repos(args.user, token)
    if not isinstance(user, dict) or not repos:
        print("GitHub data unavailable; keeping existing generated cards.", file=sys.stderr)
        return

    owned = [repo for repo in repos if not repo.get("fork")]
    stars = sum(repo.get("stargazers_count", 0) for repo in owned)
    tiles = [
        ("Total stars", f"{stars:,}"),
        ("Public repos", f"{user.get('public_repos', 0):,}"),
        ("Followers", f"{user.get('followers', 0):,}"),
    ]

    contributions = fetch_contributions(args.user, token)
    if contributions:
        total, current, longest = contributions
        tiles += [
            ("Contributions (1y)", f"{total:,}"),
            ("Current streak", f"{current:,}"),
            ("Longest streak", f"{longest:,}"),
        ]
    else:
        print("  note: contribution tiles skipped (token/GraphQL unavailable)", file=sys.stderr)

    for theme in THEMES:
        path = args.out / f"card-stats-{theme}.svg"
        path.write_text(render_stats(args.user, tiles, theme), encoding="utf-8")
    print(f"wrote card-stats-*.svg ({len(tiles)} tiles)")

    languages: Counter = Counter()
    for repo in owned:
        if repo.get("archived"):
            continue
        full_name = repo.get("full_name")
        if not full_name:
            continue
        result = api_get(f"/repos/{full_name}/languages", token)
        if isinstance(result, dict):
            languages.update(
                {name: count for name, count in result.items() if isinstance(count, int)}
            )

    if languages:
        (args.out / "metrics.languages.svg").write_text(
            render_languages(languages, "light"), encoding="utf-8"
        )
        print(f"wrote metrics.languages.svg ({len(languages)} languages)")
    else:
        print("  language metrics unavailable", file=sys.stderr)

    if not args.projects.exists():
        print(f"no {args.projects}; skipping project cards")
        return

    wanted = json.loads(args.projects.read_text(encoding="utf-8")).get("projects", [])
    by_name = {repo["name"].lower(): repo for repo in repos}
    for entry in wanted:
        source = by_name.get(entry["repo"].lower())
        if not source:
            print(f"  !! {entry['repo']} not found — skipped", file=sys.stderr)
            continue
        card = {
            "name": source["name"],
            "description": entry.get("description") or source.get("description"),
            "language": entry.get("language") or source.get("language"),
            "stars": source.get("stargazers_count", 0),
            "forks": source.get("forks_count", 0),
        }
        for theme in THEMES:
            dest = args.out / f"card-{source['name']}-{theme}.svg"
            dest.write_text(render_repo(card, theme), encoding="utf-8")
        print(f"wrote card-{source['name']}-*.svg")


if __name__ == "__main__":
    main()
