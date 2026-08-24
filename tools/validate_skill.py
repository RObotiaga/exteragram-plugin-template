#!/usr/bin/env python3
"""Validate the repository-local exteraGram template skill package."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "exteragram-eaf-template"
SKILL_FILE = SKILL_DIR / "SKILL.md"
REF_DIR = SKILL_DIR / "references"

EXPECTED_REFERENCES = {
    "00-source-priority.md",
    "01-template-architecture.md",
    "02-elyx-eaf.md",
    "03-python-baseplugin.md",
    "04-kotlin-dex.md",
    "05-hooks-reflection.md",
    "06-telegram-internals.md",
    "07-ui-settings.md",
    "08-lifecycle-concurrency.md",
    "09-debugging-testing.md",
    "10-build-ci-release.md",
    "11-recipes.md",
    "12-pitfalls-compatibility.md",
    "SOURCES.md",
}

MAX_SKILL_BYTES = 12_000
MAX_REFERENCE_BYTES = 20_000


def fail(message: str) -> None:
    raise SystemExit(f"skill validation failed: {message}")


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        fail(f"not valid UTF-8: {path.relative_to(ROOT)} ({exc})")


def validate_frontmatter(text: str) -> None:
    if not text.startswith("---\n"):
        fail("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        fail("SKILL.md frontmatter is not closed")

    frontmatter = text[4:end]
    if not re.search(r"(?m)^name:\s*\S.+$", frontmatter):
        fail("SKILL.md frontmatter is missing a non-empty name")
    if not re.search(r"(?m)^description:\s*(?:>[-+]?\s*)?\S", frontmatter):
        # Multiline YAML descriptions may put text on following indented lines.
        if not re.search(r"(?m)^description:\s*>[-+]?\s*$", frontmatter):
            fail("SKILL.md frontmatter is missing a description")


def validate_markdown(path: Path, text: str, max_bytes: int) -> None:
    size = len(text.encode("utf-8"))
    if size > max_bytes:
        fail(
            f"{path.relative_to(ROOT)} is {size} bytes; split it below {max_bytes} bytes"
        )
    if not re.search(r"(?m)^#\s+\S", text):
        fail(f"{path.relative_to(ROOT)} has no H1 heading")


def main() -> int:
    skill_text = read_text(SKILL_FILE)
    validate_frontmatter(skill_text)
    validate_markdown(SKILL_FILE, skill_text, MAX_SKILL_BYTES)

    actual_refs = {
        path.name
        for path in REF_DIR.glob("*.md")
        if path.is_file()
    }
    missing = EXPECTED_REFERENCES - actual_refs
    extra = actual_refs - EXPECTED_REFERENCES
    if missing:
        fail(f"missing reference files: {sorted(missing)}")
    if extra:
        fail(f"unregistered reference files: {sorted(extra)}")

    for name in sorted(EXPECTED_REFERENCES):
        route = f"references/{name}"
        if route not in skill_text:
            fail(f"SKILL.md does not route to {route}")

    hashes: dict[str, str] = {}
    for name in sorted(EXPECTED_REFERENCES):
        path = REF_DIR / name
        text = read_text(path)
        validate_markdown(path, text, MAX_REFERENCE_BYTES)

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in hashes:
            fail(
                f"duplicate reference content: {name} and {hashes[digest]}"
            )
        hashes[digest] = name

    print(
        f"validated {SKILL_FILE.relative_to(ROOT)} and "
        f"{len(EXPECTED_REFERENCES)} topical references"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
