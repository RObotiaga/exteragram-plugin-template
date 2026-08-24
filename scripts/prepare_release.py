#!/usr/bin/env python3
"""Stamp the release version into Python, Elyx metadata and pyproject.toml."""

import argparse
import re
from pathlib import Path


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def replace_one(text: str, pattern: str, replacement: str, description: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Failed to update {description}")
    return updated


def update_plugin_file(plugin_path: Path, version: str) -> None:
    text = plugin_path.read_text(encoding="utf-8")
    text = replace_one(
        text,
        r'^__version__ = ".*"$',
        f'__version__ = "{version}"',
        "__version__",
    )
    plugin_path.write_text(text, encoding="utf-8")


def update_metainfo_file(metainfo_path: Path, version: str) -> None:
    text = metainfo_path.read_text(encoding="utf-8")
    text = replace_one(
        text,
        r'^version:\s*["\']?.*?["\']?\s*$',
        f'version: "{version}"',
        "Elyx metainfo version",
    )
    metainfo_path.write_text(text, encoding="utf-8")


def update_pyproject_file(pyproject_path: Path, version: str) -> None:
    text = pyproject_path.read_text(encoding="utf-8")
    text = replace_one(
        text,
        r'^version = ".*"$',
        f'version = "{version}"',
        "pyproject version",
    )
    pyproject_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--plugin-file", required=True, type=Path)
    parser.add_argument("--metainfo-file", required=True, type=Path)
    parser.add_argument("--pyproject-file", required=True, type=Path)
    args = parser.parse_args()

    if VERSION_RE.fullmatch(args.version) is None:
        raise SystemExit("Version must match x.x.x")

    for label, path in (
        ("Plugin file", args.plugin_file),
        ("Elyx metainfo", args.metainfo_file),
        ("pyproject file", args.pyproject_file),
    ):
        if not path.is_file():
            raise SystemExit(f"{label} not found: {path}")

    update_plugin_file(args.plugin_file, args.version)
    update_metainfo_file(args.metainfo_file, args.version)
    update_pyproject_file(args.pyproject_file, args.version)

    print(f"version={args.version}")


if __name__ == "__main__":
    main()
