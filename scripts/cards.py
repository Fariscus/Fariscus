#!/usr/bin/env python3
"""Build local GitHub statistics, language, and featured-repository SVG cards."""

import argparse
import html
import json
import os
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

THEMES = {
    "dark": {"bg": "#111c2e", "ink": "#e6edf7", "muted": "#9fb3c8", "line": "#263b55", "accent": "#2dd4bf"},
    "light": {"bg": "#ffffff", "ink": "#102a43", "muted": "#627d98", "line": "#d9e2ec", "accent": "#0f766e"},
}


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "faris-profile-cards"}
    if token := os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"Skipped {path}: {error}")
        return None


def write(path, body, width, height, title):
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">{body}</svg>\n', encoding="utf-8")


def stat_card(out, rows):
    for mode, c in THEMES.items():
        height = 146 + len(rows) * 40
        entries = "".join(f'<text x="30" y="{105 + i * 40}" fill="{c["muted"]}" font-family="system-ui" font-size="15">{html.escape(label)}</text><text x="350" y="{105 + i * 40}" text-anchor="end" fill="{c["ink"]}" font-family="ui-monospace, monospace" font-size="17" font-weight="700">{html.escape(value)}</text><line x1="30" y1="{119 + i * 40}" x2="350" y2="{119 + i * 40}" stroke="{c["line"]}"/>' for i, (label, value) in enumerate(rows))
        write(out / f"card-stats-{mode}.svg", f'<rect width="380" height="{height}" rx="20" fill="{c["bg"]}"/><rect x="1" y="1" width="378" height="{height - 2}" rx="19" fill="none" stroke="{c["line"]}"/><text x="30" y="43" fill="{c["ink"]}" font-family="system-ui" font-size="19" font-weight="800">GitHub snapshot</text><text x="30" y="65" fill="{c["muted"]}" font-family="system-ui" font-size="12">public API data · no estimates</text>{entries}', 380, height, "GitHub statistics")


def language_card(out, languages):
    c = THEMES["light"]
    top, total = languages.most_common(6), sum(languages.values())
    height = max(190, 100 + len(top) * 32)
    rows = "".join(f'<text x="25" y="{95 + i * 32}" fill="{c["ink"]}" font-family="system-ui" font-size="13" font-weight="650">{html.escape(name)}</text><rect x="130" y="{83 + i * 32}" width="190" height="10" rx="5" fill="{c["line"]}"/><rect x="130" y="{83 + i * 32}" width="{190 * value / total:.1f}" height="10" rx="5" fill="{c["accent"]}"/><text x="352" y="{95 + i * 32}" text-anchor="end" fill="{c["muted"]}" font-family="ui-monospace" font-size="12">{value / total * 100:.1f}%</text>' for i, (name, value) in enumerate(top)) if total else '<text x="25" y="100" fill="#627d98" font-family="system-ui" font-size="14">Language data unavailable</text>'
    write(out / "metrics.languages.svg", f'<rect width="380" height="{height}" rx="20" fill="{c["bg"]}"/><rect x="1" y="1" width="378" height="{height - 2}" rx="19" fill="none" stroke="{c["line"]}"/><text x="24" y="39" fill="{c["ink"]}" font-family="system-ui" font-size="18" font-weight="800">Most-used languages</text><text x="24" y="60" fill="{c["muted"]}" font-family="system-ui" font-size="11">bytes across public non-fork repositories</text>{rows}', 380, height, "Most used programming languages")


def project_card(out, project, repo):
    name = project["repo"]
    description = project.get("description") or repo.get("description") or "Public GitHub repository"
    language = repo.get("language") or "Language not reported"
    for mode, c in THEMES.items():
        body = f'<rect width="380" height="180" rx="20" fill="{c["bg"]}"/><rect x="1" y="1" width="378" height="178" rx="19" fill="none" stroke="{c["line"]}"/><text x="25" y="40" fill="{c["accent"]}" font-family="ui-monospace" font-size="12">FEATURED REPOSITORY</text><text x="25" y="73" fill="{c["ink"]}" font-family="system-ui" font-size="18" font-weight="800">{html.escape(name[:32])}</text><text x="25" y="103" fill="{c["muted"]}" font-family="system-ui" font-size="12">{html.escape(description[:58])}</text><text x="25" y="128" fill="{c["muted"]}" font-family="system-ui" font-size="12">{html.escape(description[58:116])}</text><text x="25" y="158" fill="{c["ink"]}" font-family="ui-monospace" font-size="12">{html.escape(language)} · ★ {repo.get("stargazers_count", 0)} · fork {repo.get("forks_count", 0)}</text>'
        safe = name.replace("/", "-")
        write(out / f"card-{safe}-{mode}.svg", body, 380, 180, name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--projects", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True)
    user = api(f"/users/{quote(args.user)}")
    repos = api(f"/users/{quote(args.user)}/repos?per_page=100&type=owner&sort=updated")
    if not isinstance(user, dict) or not isinstance(repos, list):
        print("GitHub data unavailable; keeping existing cards.")
        return
    active = [repo for repo in repos if not repo.get("fork") and not repo.get("archived")]
    pr = api(f"/search/issues?q={quote('author:' + args.user + ' type:pr')}&per_page=1")
    rows = [("Public repositories", str(user.get("public_repos", 0))), ("Total stars received", str(sum(repo.get("stargazers_count", 0) for repo in active))), ("Followers", str(user.get("followers", 0))), ("Following", str(user.get("following", 0)))]
    if isinstance(pr, dict) and isinstance(pr.get("total_count"), int): rows.append(("Pull requests authored", str(pr["total_count"])))
    languages = Counter()
    for repo in active:
        if result := api(f'/repos/{quote(repo["full_name"], safe="/")}/languages'):
            languages.update({key: value for key, value in result.items() if isinstance(value, int)})
    stat_card(args.out, rows); language_card(args.out, languages)
    lookup = {repo["name"]: repo for repo in repos}
    for project in json.loads(args.projects.read_text(encoding="utf-8"))["projects"]:
        if repo := lookup.get(project["repo"]): project_card(args.out, project, repo)


if __name__ == "__main__": main()
