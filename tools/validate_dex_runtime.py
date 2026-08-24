#!/usr/bin/env python3
"""Validate that a DEX does not leak compile-only runtime dependencies."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

ALLOWED_EXTERNAL_PREFIXES = (
    "Landroid/",
    "Ldalvik/",
    "Ljava/",
    "Ljavax/",
    "Lj$/",
    "Lorg/telegram/",
    "Lcom/exteragram/",
    "Lde/robv/android/xposed/",
    "Lorg/json/",
    # RecyclerView is compileOnly because the host APK provides it.
    "Landroidx/recyclerview/",
)


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _read_uleb128(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise ValueError("truncated ULEB128")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
        if shift > 35:
            raise ValueError("invalid ULEB128")


def _read_dex_string(data: bytes, string_ids_off: int, index: int) -> str:
    item_off = _u32(data, string_ids_off + index * 4)
    _, payload_off = _read_uleb128(data, item_off)
    end = data.find(b"\0", payload_off)
    if end < 0:
        raise ValueError("unterminated DEX string")
    return data[payload_off:end].decode("utf-8", errors="strict")


def inspect_dex(path: Path) -> tuple[set[str], set[str]]:
    data = path.read_bytes()
    if len(data) < 0x70 or not data.startswith(b"dex\n"):
        raise ValueError(f"not a DEX file: {path}")

    string_ids_size = _u32(data, 0x38)
    string_ids_off = _u32(data, 0x3C)
    type_ids_size = _u32(data, 0x40)
    type_ids_off = _u32(data, 0x44)
    class_defs_size = _u32(data, 0x60)
    class_defs_off = _u32(data, 0x64)

    strings = [
        _read_dex_string(data, string_ids_off, i)
        for i in range(string_ids_size)
    ]
    types = [
        strings[_u32(data, type_ids_off + i * 4)]
        for i in range(type_ids_size)
    ]

    defined: set[str] = set()
    for i in range(class_defs_size):
        class_idx = _u32(data, class_defs_off + i * 32)
        defined.add(types[class_idx])

    external = {
        descriptor
        for descriptor in types
        if descriptor.startswith("L") and descriptor not in defined
    }
    return defined, external


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dex", type=Path)
    args = parser.parse_args()

    try:
        defined, external = inspect_dex(args.dex)
    except (OSError, UnicodeError, ValueError, struct.error) as exc:
        parser.error(str(exc))

    unexpected = sorted(
        descriptor
        for descriptor in external
        if not descriptor.startswith(ALLOWED_EXTERNAL_PREFIXES)
    )

    if unexpected:
        print("Unexpected external runtime types in DEX:")
        for descriptor in unexpected:
            print(f"  {descriptor}")
        return 1

    print(
        f"DEX runtime surface clean: {len(defined)} defined classes, "
        f"{len(external)} allowed external classes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
