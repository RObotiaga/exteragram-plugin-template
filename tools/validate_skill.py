#!/usr/bin/env python3
"""Validate the repository-local exteraGram template skill package."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "exteragram-eaf-template"
SKILL_FILE = SKILL_ROOT / "SKILL.md"

REQUIRED_REFERENCES = {
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

REFERENCE_RE = re.compile(r"`references/([A-Za-z0-9_.-]+\.md)`")


def fail(message: str) -> None:
    raise SystemExit(f"skill validation failed: {message}")


def validate_frontmatter(text: str) -> None:
    if not text.startswith("---\n"):
        fail("SKILL.md must start with YAML frontmatter")
    try:
        _, frontmatter, _ = text.split("---", 2)
    except ValueError:
        fail("SKILL.md frontmatter is not closed")
    if not re.search(r"(?m)^name:\s*\S+", frontmatter):
        fail("SKILL.md frontmatter is missing name")
    if not re.search(r"(?m)^description:\s*(?:>|\S)", frontmatter):
        fail("SKILL.md frontmatter is missing description")


def main() -> int:
    if not SKILL_FILE.is_file():
        fail(f"missing {SKILL_FILE.relative_to(ROOT)}")

    references_dir = SKILL_ROOT / "references"
    if not references_dir.is_dir():
        fail("missing references directory")

    text = SKILL_FILE.read_text(encoding="utf-8")
    validate_frontmatter(text)

    if SKILL_FILE.stat().st_size > 16_000:
        fail("SKILL.md is too large; keep it as a router and move detail to references")

    present = {path.name for path in references_dir.glob("*.md")}
    missing = sorted(REQUIRED_REFERENCES - present)
    unexpected = sorted(present - REQUIRED_REFERENCES)
    if missing:
        fail("missing reference files: " + ", ".join(missing))
    if unexpected:
        fail("unrouted reference files: " + ", ".join(unexpected))

    routed = set(REFERENCE_RE.findall(text))
    missing_routes = sorted((REQUIRED_REFERENCES - {"SOURCES.md"}) - routed)
    if missing_routes:
        fail("SKILL.md does not route to: " + ", ".join(missing_routes))

    for filename in sorted(REQUIRED_REFERENCES):
        path = references_dir / filename
        body = path.read_text(encoding="utf-8")
        if not body.strip():
            fail(f"empty reference: {filename}")
        if path.stat().st_size > 30_000:
            fail(f"{filename} exceeds 30 KB; split it by topic")
        if not body.startswith("# "):
            fail(f"{filename} must start with one H1 heading")

    normalized: dict[str, str] = {}
    for filename in sorted(REQUIRED_REFERENCES):
        body = (references_dir / filename).read_text(encoding="utf-8").strip()
        if body in normalized:
            fail(f"duplicate reference contents: {normalized[body]} and {filename}")
        normalized[body] = filename

    print(
        f"validated {SKILL_FILE.relative_to(ROOT)} with "
        f"{len(REQUIRED_REFERENCES)} topical references"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
