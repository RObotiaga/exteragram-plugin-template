#!/usr/bin/env python3
"""Build a structured Elyx/EAF archive from the template sources.

The canonical plugin entry point remains a normal Python source file in the
repository. During packaging it is stored unchanged as ``main.py``. The release
DEX is stored as a real binary asset at ``assets/classes.dex`` and additional
Python modules from ``plugin_src/`` are added as the ``src`` package.

The resulting file is a regular ZIP archive with an ``.eaf`` extension and
``refmap.yml`` at its root, as expected by Elyx.
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


DEFAULT_EXTRA_SOURCE_DIR = Path("plugin_src")
DEFAULT_ASSET_DIR = Path("assets")
DEX_ARCHIVE_PATH = "assets/classes.dex"
ELYX_ID_RE = re.compile(r"^[A-Za-z0-9_]{2,32}$")


def _validated_python(path: Path, source: str) -> None:
    try:
        ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise RuntimeError(f"Invalid Python source: {path}: {exc}") from exc


def _read_elyx_id(path: Path, data: bytes) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"metainfo is not valid UTF-8: {path}") from exc

    values: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.startswith("id:"):
            continue

        value = raw_line.partition(":")[2].strip()
        if " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values.append(value)

    if len(values) != 1:
        raise RuntimeError(
            f"metainfo must contain exactly one top-level id field: {path}"
        )

    plugin_id = values[0]
    if not ELYX_ID_RE.fullmatch(plugin_id):
        raise RuntimeError(
            "invalid Elyx plugin id "
            f"{plugin_id!r}: expected 2-32 ASCII letters, digits, or underscore"
        )

    return plugin_id


def _iter_project_files(source_dir: Path):
    if not source_dir.exists():
        return

    for path in sorted(source_dir.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        yield path


def _iter_asset_files(asset_dir: Path):
    if not asset_dir.exists():
        return

    for path in sorted(asset_dir.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        if path.name == ".DS_Store":
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
    asset_dir: Path,
    output_path: Path,
) -> None:
    required_files = (dex_path, plugin_path, refmap_path, metainfo_path)
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise RuntimeError("Missing required file(s): " + ", ".join(missing))

    dex = dex_path.read_bytes()
    if not dex:
        raise RuntimeError(f"DEX is empty: {dex_path}")
    if not dex.startswith(b"dex\n"):
        raise RuntimeError(f"DEX has an invalid magic header: {dex_path}")

    plugin_source = plugin_path.read_text(encoding="utf-8")
    _validated_python(plugin_path, plugin_source)

    refmap = refmap_path.read_bytes()
    metainfo = metainfo_path.read_bytes()
    if not refmap.strip():
        raise RuntimeError(f"refmap is empty: {refmap_path}")
    if not metainfo.strip():
        raise RuntimeError(f"metainfo is empty: {metainfo_path}")
    elyx_id = _read_elyx_id(metainfo_path, metainfo)

    source_files: list[tuple[str, bytes]] = []
    for path in _iter_project_files(extra_source_dir) or ():
        relative = path.relative_to(extra_source_dir).as_posix()
        archive_path = f"src/{relative}"
        data = path.read_bytes()
        if path.suffix == ".py":
            _validated_python(path, data.decode("utf-8"))
        source_files.append((archive_path, data))

    asset_files: list[tuple[str, bytes]] = []
    for path in _iter_asset_files(asset_dir) or ():
        relative = path.relative_to(asset_dir).as_posix()
        archive_path = f"assets/{relative}"
        if archive_path == DEX_ARCHIVE_PATH:
            raise RuntimeError(
                f"{asset_dir / 'classes.dex'} conflicts with generated {DEX_ARCHIVE_PATH}; "
                "the release DEX must come from --dex"
            )
        asset_files.append((archive_path, path.read_bytes()))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.unlink(missing_ok=True)

    try:
        with ZipFile(tmp_path, "w") as archive:
            _writestr(archive, "refmap.yml", refmap)
            _writestr(archive, "metainfo.yml", metainfo)
            _writestr(archive, "main.py", plugin_source.encode("utf-8"))
            for archive_path, data in source_files:
                _writestr(archive, archive_path, data)
            for archive_path, data in asset_files:
                _writestr(archive, archive_path, data)
            _writestr(archive, DEX_ARCHIVE_PATH, dex)

        with ZipFile(tmp_path, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise RuntimeError("Built EAF contains duplicate archive paths")

            required_entries = {
                "refmap.yml",
                "metainfo.yml",
                "main.py",
                DEX_ARCHIVE_PATH,
            }
            missing_entries = sorted(required_entries - set(names))
            if missing_entries:
                raise RuntimeError(
                    "Built EAF is missing required entries: " + ", ".join(missing_entries)
                )
            if any(name.startswith("/") or ".." in Path(name).parts for name in names):
                raise RuntimeError("Built EAF contains unsafe archive paths")
            if archive.read(DEX_ARCHIVE_PATH) != dex:
                raise RuntimeError("Packaged DEX does not match the release DEX")
            if archive.testzip() is not None:
                raise RuntimeError("Built EAF failed ZIP integrity validation")

        tmp_path.replace(output_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    print(
        f"built {output_path} for Elyx id {elyx_id!r} with binary "
        f"{DEX_ARCHIVE_PATH} ({len(dex)} bytes), {len(source_files)} extra source "
        f"file(s), and {len(asset_files)} extra asset(s)"
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
    parser.add_argument("--asset-dir", default=DEFAULT_ASSET_DIR, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        build_eaf(
            dex_path=args.dex,
            plugin_path=args.plugin_file,
            refmap_path=args.refmap,
            metainfo_path=args.metainfo,
            extra_source_dir=args.extra_source_dir,
            asset_dir=args.asset_dir,
            output_path=args.output,
        )
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
