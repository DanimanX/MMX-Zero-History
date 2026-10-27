#!/usr/bin/env python3
"""Verify a Mega Man X3 (USA) dump against the digest this port was built for.

    python3 tools/verify_rom.py mmx3.sfc

A 512-byte SMC copier header is stripped before hashing, matching the
recompiler and the launcher. Exit code 0 means the file is the expected ROM.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zlib
from pathlib import Path

EXPECTED_SHA256 = "65b03268afac296330e8ff8d60dd0825879e13ed658b37713c034a3bd074f1d7"
EXPECTED_CRC32 = 0xFA0FE671
BASE_SIZE = 2 * 1024 * 1024


def strip_copier_header(data: bytes) -> bytes:
    if len(data) % 32768 == 512:
        return data[512:]
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rom", nargs="?", default="mmx3.sfc")
    args = ap.parse_args(argv)

    path = Path(args.rom)
    if not path.is_file():
        print(f"no existe: {path}", file=sys.stderr)
        return 2

    raw = path.read_bytes()
    data = strip_copier_header(raw)
    sha = hashlib.sha256(data).hexdigest()
    crc = zlib.crc32(data) & 0xFFFFFFFF

    print(f"archivo    {path} ({len(raw)} bytes)")
    print(f"cabecera   {'512 B de copiador, descartada' if len(raw) != len(data) else 'ninguna'}")
    print(f"tamano     {len(data)} bytes (esperado {BASE_SIZE})")
    print(f"sha256     {sha}")
    print(f"crc32      0x{crc:08X}")

    problems = []
    if len(data) != BASE_SIZE:
        problems.append("tamano distinto de 2 MiB")
    if sha != EXPECTED_SHA256:
        problems.append("sha256 no coincide")
    if crc != EXPECTED_CRC32:
        problems.append(f"crc32 distinto de 0x{EXPECTED_CRC32:08X}")
    if problems:
        for p in problems:
            print(f"FALLA: {p}", file=sys.stderr)
        return 1
    print("OK: es el ROM esperado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
