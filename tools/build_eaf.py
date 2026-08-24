#!/usr/bin/env python3
"""Build a structured Elyx/EAF archive from the template sources.

The canonical plugin entry point remains a normal Python source file in the
repository. During packaging we embed the release DEX into a temporary copy of
that source, store it as ``main.py`` in the archive, and add any extra Python
modules from ``plugin_src/`` as the ``src`` package.

The resulting file is a regular ZIP archive with an ``.eaf`` extension and
``refmap.yml`` at its root, as expected by Elyx.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from embed_dex import embed_source


DEFAULT_EXTRA_SOURCE_DIR = Path("plugin_src")


def _validated_python(path: Path, source: str) -> None:
    try:
        ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise RuntimeError(f"Invalid Python source: {path}: {exc}") from exc


def _iter_extra_sources(source_dir: Path):
    if not source_dir.exists():
        return

    for path in sorted(source_dir.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        yield path


def _writestr(zip_file: ZipFile, archive_path: str, data: bytes) -> None:
    info = ZipInfo(archive_path)
    # Fixed timestamp makes archives reproducible for identical inputs.
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    zip_file.writestr(info, data)


def build_eaf(
    *,
    dex_path: Path,
    plugin_path: Path,
    refmap_path: Path,
    metainfo_path: Path,
    extra_source_dir: Path,
    output_path: Path,
) -> None:
    required_files = (dex_path, plugin_path, refmap_path, metainfo_path)
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise RuntimeError("Missing required file(s): " + ", ".join(missing))

    dex = dex_path.read_bytes()
    if not dex:
        raise RuntimeError(f"DEX is empty: {dex_path}")

    plugin_source = plugin_path.read_text(encoding="utf-8")
    _validated_python(plugin_path, plugin_source)
    embedded_main = embed_source(plugin_source, dex)
    _validated_python(Path("main.py"), embedded_main)

    refmap = refmap_path.read_bytes()
    metainfo = metainfo_path.read_bytes()
    if not refmap.strip():
        raise RuntimeError(f"refmap is empty: {refmap_path}")
    if not metainfo.strip():
        raise RuntimeError(f"metainfo is empty: {metainfo_path}")

    extra_files: list[tuple[str, bytes]] = []
    for path in _iter_extra_sources(extra_source_dir) or ():
        relative = path.relative_to(extra_source_dir).as_posix()
        archive_path = f"src/{relative}"
        data = path.read_bytes()
        if path.suffix == ".py":
            _validated_python(path, data.decode("utf-8"))
        extra_files.append((archive_path, data))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.unlink(missing_ok=True)

    try:
        with ZipFile(tmp_path, "w") as archive:
            _writestr(archive, "refmap.yml", refmap)
            _writestr(archive, "metainfo.yml", metainfo)
            _writestr(archive, "main.py", embedded_main.encode("utf-8"))
            for archive_path, data in extra_files:
                _writestr(archive, archive_path, data)

        with ZipFile(tmp_path, "r") as archive:
            names = set(archive.namelist())
            required_entries = {"refmap.yml", "metainfo.yml", "main.py"}
            missing_entries = sorted(required_entries - names)
            if missing_entries:
                raise RuntimeError(
                    "Built EAF is missing required entries: " + ", ".join(missing_entries)
                )
            if any(name.startswith("/") for name in names):
                raise RuntimeError("Built EAF contains absolute archive paths")
            if archive.testzip() is not None:
                raise RuntimeError("Built EAF failed ZIP integrity validation")

        tmp_path.replace(output_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    print(
        f"built {output_path} with {len(dex)} DEX bytes and "
        f"{len(extra_files)} extra source file(s)"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dex", required=True, type=Path)
    parser.add_argument("--plugin-file", required=True, type=Path)
    parser.add_argument("--refmap", default=Path("refmap.yml"), type=Path)
    parser.add_argument("--metainfo", default=Path("metainfo.yml"), type=Path)
    parser.add_argument(
        "--extra-source-dir", default=DEFAULT_EXTRA_SOURCE_DIR, type=Path
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        build_eaf(
            dex_path=args.dex,
            plugin_path=args.plugin_file,
            refmap_path=args.refmap,
            metainfo_path=args.metainfo,
            extra_source_dir=args.extra_source_dir,
            output_path=args.output,
        )
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
