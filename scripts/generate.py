#!/usr/bin/env python3
"""Run all local profile generators in order."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    python = sys.executable
    run([python, "scripts/banner/generate.py"])
    run([python, "scripts/dotify.py"])
    run([python, "scripts/radar.py", "--data", "data/skills.json", "-o", "assets/radar"])
    run([python, "scripts/radar.py", "--data", "data/langmix.json", "-o", "assets/radar-langs", "--values"])
    run([python, "scripts/cards.py", "--user", "Fariscus", "--projects", "data/projects.json", "--out", "assets"])
    print("all generators finished")


if __name__ == "__main__":
    main()
