#!/usr/bin/env python3
"""Apply MMX Zero History's content table to a ROM copy on disk.

The game itself never writes the player's dump: it patches the in-memory image
after verifying identity (``snes_text_xlate``). This tool exists for the other
two jobs:

* ``--check``  say what the table would do to this file, without writing;
* ``--apply``  write a patched copy (default ``<rom>.zerohistory.sfc``) with a
               fresh SNES checksum, for use in emulators or for shipping a
               reviewed patch set.

Every patch in the table is content-guarded: the bytes at ``address`` must be
exactly ``source``. A file that is not the expected dump gets no patches and a
non-zero exit — the tool never half-applies a table.

    python3 tools/x3_content_patch.py --check mmx3.sfc
    python3 tools/x3_content_patch.py --apply mmx3.sfc
    python3 tools/x3_content_patch.py --apply mmx3.sfc -o dist/mmx3.zhl.sfc
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLE = ROOT / "content" / "zerohistory.toml"

ROM_BYTES = 2 * 1024 * 1024
COPIER_HEADER = 512
EXPECTED_SHA256 = "65b03268afac296330e8ff8d60dd0825879e13ed658b37713c034a3bd074f1d7"
EXPECTED_CRC32 = 0xFA0FE671

# LoROM header: 21 bytes of internal name, then map mode, cartridge type,
# ROM size, SRAM size, country, licence, version, checksum complement and
# checksum. Offsets are the specification, not a guess about this title.
HEADER_OFFSET = 0x7FC0
HEADER_NAME_LEN = 21
CHECKSUM_COMPLEMENT_OFFSET = 0x7FDC
CHECKSUM_OFFSET = 0x7FDE


@dataclass
class Patch:
    address: int
    source: bytes
    target: bytes
    targets: dict[str, bytes] = field(default_factory=dict)

    def describe(self) -> str:
        return (f"0x{self.address:06X} ({len(self.source)} bytes: "
                f"{self.source.hex()} -> {self.target.hex()})")


def _strip_comment(line: str) -> str:
    quoted = False
    escape = False
    for i, ch in enumerate(line):
        if escape:
            escape = False
            continue
        if quoted and ch == "\\":
            escape = True
            continue
        if ch == '"':
            quoted = not quoted
        if ch == "#" and not quoted:
            return line[:i]
    return line


def _hex(text: str) -> bytes:
    value = text.strip()
    if not (value.startswith('"') and value.endswith('"')):
        raise ValueError(f"hex value must be quoted: {text!r}")
    digits = re.sub(r"[\s_:-]", "", value[1:-1])
    if len(digits) % 2:
        raise ValueError(f"odd hex length: {text!r}")
    return bytes.fromhex(digits)


def load_table(path: Path, language: str = "es") -> tuple[list[Patch], dict]:
    """Parse the subset of the snes_text_xlate table this tool needs.

    Only ``[[rom_patch]]`` blocks are read: the disk tool writes bytes into a
    file, and RAM/VRAM patches only make sense inside a running guest.
    """
    meta: dict = {"language": language, "ram_patches": 0, "vram_patches": 0}
    patches: list[Patch] = []
    section = ""
    current: dict[str, str] | None = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = _strip_comment(raw).strip()
        if not line:
            continue
        if line.startswith("[[") and line.endswith("]]"):
            name = line[2:-2].strip()
            if current is not None and section == "rom_patch":
                patches.append(_finish_rom_patch(current, language))
            section = name
            current = {} if section == "rom_patch" else None
            if section in ("ram_patch", "entry", "glyph_label"):
                meta["ram_patches"] += 1
            elif section == "vram_patch":
                meta["vram_patches"] += 1
            continue
        if "=" not in line:
            raise ValueError(f"invalid table line: {raw!r}")
        key, value = line.split("=", 1)
        if section == "rom_patch" and current is not None:
            current[key.strip()] = value.strip()
    if current is not None and section == "rom_patch":
        patches.append(_finish_rom_patch(current, language))
    return patches, meta


SOURCE_KEYS = ("source_hex", "source", "src_hex")


def _finish_rom_patch(fields: dict[str, str], language: str) -> Patch:
    """Build a patch from either spelling the two parsers accept.

    The runner reads ``source_hex`` / ``target_<lang>_hex``; an earlier draft
    of this table used ``source`` / ``target_<lang>``, which the runner stores
    as *text* and therefore never applies. Accepting both here keeps this tool
    and the engine honest about the same file, and the tests pin the runner's
    spelling so the table cannot silently drift back.
    """
    source_key = next((k for k in SOURCE_KEYS if k in fields), None)
    if "address" not in fields or source_key is None:
        raise ValueError(f"rom_patch needs address and source_hex: {fields}")
    address = int(fields["address"], 0)
    source = _hex(fields[source_key])
    skip = set(SOURCE_KEYS) | {"address", "guard_hex", "guard_address"}
    targets = {}
    for key, value in fields.items():
        if key in skip:
            continue
        # Idioma: `<lang>_hex` es el formato documentado
        # (snesrecomp/docs/RUNTIME_LOCALIZATION.md). `target_<lang>[_hex]` se
        # acepta por compatibilidad, nunca se emite.
        lang = key[:-len("_hex")] if key.endswith("_hex") else key
        if lang.startswith("target_"):
            lang = lang[len("target_"):]
        if not lang or lang == "guard":
            continue
        targets[lang] = _hex(value)
    target = targets.get(language) or targets.get("en")
    if target is None:
        raise ValueError(f"rom_patch at 0x{address:06X} has no payload for '{language}'")
    if len(target) != len(source):
        raise ValueError(
            f"rom_patch at 0x{address:06X}: source is {len(source)} bytes, "
            f"target is {len(target)}; a ROM patch cannot change length")
    return Patch(address=address, source=source, target=target, targets=targets)


def read_rom(path: Path) -> tuple[bytes, bool]:
    data = path.read_bytes()
    if len(data) == ROM_BYTES + COPIER_HEADER:
        return data[COPIER_HEADER:], True
    return data, False


def checksum(rom: bytes) -> int:
    """SNES checksum: 16-bit sum of every byte with the four checksum bytes
    treated as zero. Its complement is that value XOR 0xFFFF, which is what
    emulators and ROM managers test.

    The four bytes are removed as *bytes*, not as little-endian words: the sum
    counts each byte once, so subtracting the words would be off by however
    many carries the pair happens to have.
    """
    excluded = sum(rom[CHECKSUM_COMPLEMENT_OFFSET:CHECKSUM_COMPLEMENT_OFFSET + 4])
    return (sum(rom) - excluded) & 0xFFFF


def apply_patches(rom: bytes, patches: list[Patch]) -> tuple[bytes, list[str], list[str]]:
    """Return (image, applied descriptions, skipped descriptions).

    Fail-closed per patch: one whose guard does not match is skipped, never
    written with guessed bytes. Callers decide whether a skip is fatal.
    """
    image = bytearray(rom)
    applied: list[str] = []
    skipped: list[str] = []
    for patch in patches:
        end = patch.address + len(patch.source)
        if end > len(image):
            skipped.append(f"0x{patch.address:06X}: past the end of the ROM")
            continue
        current = bytes(image[patch.address:end])
        if current == patch.target:
            applied.append(f"0x{patch.address:06X}: already applied")
            continue
        if current != patch.source:
            skipped.append(
                f"0x{patch.address:06X}: expected {patch.source.hex()}, "
                f"found {current.hex()}")
            continue
        image[patch.address:end] = patch.target
        applied.append(patch.describe())
    return bytes(image), applied, skipped


def fix_checksum(image: bytes) -> tuple[bytes, int]:
    """Rewrite the checksum pair for `image`.

    The sum treats the four checksum bytes as zero; the complement is stored
    as ``checksum ^ 0xFFFF`` so the pair always validates, whoever recomputes
    it with the same convention.
    """
    rom = bytearray(image)
    rom[CHECKSUM_COMPLEMENT_OFFSET:CHECKSUM_COMPLEMENT_OFFSET + 2] = b"\x00\x00"
    rom[CHECKSUM_OFFSET:CHECKSUM_OFFSET + 2] = b"\x00\x00"
    value = sum(rom) & 0xFFFF
    rom[CHECKSUM_OFFSET] = value & 0xFF
    rom[CHECKSUM_OFFSET + 1] = (value >> 8) & 0xFF
    complement = value ^ 0xFFFF
    rom[CHECKSUM_COMPLEMENT_OFFSET] = complement & 0xFF
    rom[CHECKSUM_COMPLEMENT_OFFSET + 1] = (complement >> 8) & 0xFF
    return bytes(rom), value


def verify_identity(rom: bytes) -> tuple[bool, str]:
    sha = hashlib.sha256(rom).hexdigest()
    crc = _crc32(rom)
    if sha != EXPECTED_SHA256 or crc != EXPECTED_CRC32:
        return False, (f"no es Mega Man X3 (USA): sha256={sha} crc32={crc:08X}")
    return True, "identidad verificada"


def _crc32(data: bytes) -> int:
    import zlib
    return zlib.crc32(data) & 0xFFFFFFFF


def header_name(rom: bytes) -> str:
    raw = rom[HEADER_OFFSET:HEADER_OFFSET + HEADER_NAME_LEN]
    return raw.decode("ascii", "replace").rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rom", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="informar sin escribir nada")
    group.add_argument("--apply", action="store_true",
                       help="escribir una copia parcheada")
    parser.add_argument("-o", "--output", type=Path,
                        help="destino de --apply (por defecto <rom>.zerohistory.sfc)")
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    parser.add_argument("--language", default="es")
    parser.add_argument("--allow-foreign", action="store_true",
                        help="no exigir la identidad del cartucho (sólo desarrollo)")
    parser.add_argument("--no-checksum", action="store_true",
                        help="no recalcular el checksum SNES")
    args = parser.parse_args(argv)

    rom, stripped = read_rom(args.rom)
    if len(rom) != ROM_BYTES:
        print(f"error: {args.rom} tiene {len(rom)} bytes; se esperan {ROM_BYTES}",
              file=sys.stderr)
        return 2

    ok, detail = verify_identity(rom)
    if not ok and not args.allow_foreign:
        print(f"error: {detail}", file=sys.stderr)
        return 2
    if stripped:
        print("aviso: se descartó una cabecera de copiador de 512 bytes")

    patches, meta = load_table(args.table, args.language)
    print(f"tabla {args.table}: {len(patches)} parche(s) de ROM, "
          f"{meta['ram_patches']} de RAM, {meta['vram_patches']} de VRAM")

    image, applied, skipped = apply_patches(rom, patches)
    for line in applied:
        print(f"  aplicado   {line}")
    for line in skipped:
        print(f"  omitido    {line}")

    if skipped:
        print("error: hay parches que no corresponden a este ROM; no se escribe nada",
              file=sys.stderr)
        return 1

    if not args.no_checksum:
        image, value = fix_checksum(image)
        if not args.check:
            print(f"  checksum   SNES 0x{value:04X}")

    if args.check:
        print(f"cabecera actual: {header_name(rom)!r}")
        print("--check: no se escribió nada")
        return 0

    output = args.output or args.rom.with_suffix(".zerohistory.sfc")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(image)
    sha = hashlib.sha256(image).hexdigest()
    print(f"escrito {output} ({len(image)} bytes, sha256 {sha[:16]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
