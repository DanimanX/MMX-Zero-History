#!/usr/bin/env python3
"""Tests for the content-patch engine.

No Mega Man X3 dump is involved: the fixtures are synthetic 2 MiB images with
the LoROM header layout, so the properties that matter can be checked without
distributing ROM data.

    python3 tools/test_content_patch.py
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import x3_content_patch as patch  # noqa: E402

failures = 0


def check(condition: bool, message: str) -> None:
    global failures
    if not condition:
        print(f"FAIL {message}")
        failures += 1


def make_rom(name: bytes = b"MEGAMAN X3" + b" " * 11, fill: int = 0x5A) -> bytes:
    rom = bytearray([fill]) * patch.ROM_BYTES
    rom[patch.HEADER_OFFSET:patch.HEADER_OFFSET + patch.HEADER_NAME_LEN] = name
    rom[patch.CHECKSUM_COMPLEMENT_OFFSET:patch.CHECKSUM_COMPLEMENT_OFFSET + 2] = b"\xff\xff"
    rom[patch.CHECKSUM_OFFSET:patch.CHECKSUM_OFFSET + 2] = b"\x00\x00"
    value = sum(rom) & 0xFFFF
    complement = value ^ 0xFFFF
    rom[patch.CHECKSUM_OFFSET:patch.CHECKSUM_OFFSET + 2] = bytes([value & 0xFF, value >> 8])
    rom[patch.CHECKSUM_COMPLEMENT_OFFSET:patch.CHECKSUM_COMPLEMENT_OFFSET + 2] = bytes(
        [complement & 0xFF, complement >> 8])
    return bytes(rom)


def table_text(target_hex: str, source_hex: str | None = None) -> str:
    source = source_hex or (b"MEGAMAN X3" + b" " * 11).hex()
    return f"""
schema = 1
default_lang = "es"

[[rom_patch]]
address = 0x7FC0
source = "{source}"
target_es = "{target_hex}"
"""


def write_table(directory: Path, text: str) -> Path:
    path = directory / "table.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_shipped_table_parses() -> None:
    patches, meta = patch.load_table(ROOT / "content" / "zerohistory.toml")
    check(len(patches) == 1, f"la tabla del repo declara {len(patches)} parche(s) de ROM, no 1")
    p = patches[0]
    check(p.address == patch.HEADER_OFFSET, f"offset 0x{p.address:06X}, no 0x7FC0")
    check(len(p.source) == patch.HEADER_NAME_LEN,
          f"source mide {len(p.source)} bytes, no 21")
    check(len(p.target) == len(p.source), "source y target difieren de tamaño")
    check(p.target != p.source, "el parche no cambia nada")
    # Un nombre interno con relleno de espacios es lo que especifica el formato.
    check(p.target.rstrip() == b"MMX ZERO HISTORY",
          f"target no es 'MMX ZERO HISTORY': {p.target!r}")
    check(p.target.endswith(b" ") and p.target == p.target.ljust(21),
          "el target no está rellenado a 21 bytes con espacios")


def test_shipped_table_uses_the_runner_spelling() -> None:
    """`source = "..."` parses as text in the engine and the patch never fires.

    The engine keys patches by `source_hex` / `target_<lang>_hex`
    (snes_text_xlate.cpp: `key.substr(key.size() - 4) == "_hex"`). This test
    exists because the first version of the table got it wrong and the patch
    silently applied zero times on a real run.
    """
    text = (ROOT / "content" / "zerohistory.toml").read_text(encoding="utf-8")
    check("source_hex" in text, "la tabla no usa source_hex")
    check("\nes_hex = " in text, "la tabla no usa es_hex")
    for bad in ("\nsource = ", "\ntarget_es = ", "\ntarget_es_hex = "):
        check(bad not in text,
              f"la tabla usa {bad.strip()!r}: el motor lo lee como texto o como "
              f"un idioma llamado 'target_es', y el parche nunca se aplica")


def test_both_spellings_parse_alike() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        target = (b"MMX ZERO HISTORY" + b" " * 5).hex()
        modern = write_table(directory, f"""
schema = 1
default_lang = "es"
[[rom_patch]]
address = 0x7FC0
source_hex = "{(b'MEGAMAN X3' + b' ' * 11).hex()}"
es_hex = "{target}"
""")
        legacy = directory / "legacy.toml"
        legacy.write_text(table_text(target).replace('target_es_hex', 'target_es'),
                          encoding="utf-8")
        a, _ = patch.load_table(modern)
        b, _ = patch.load_table(legacy)
        check(a[0].source == b[0].source and a[0].target == b[0].target,
              "las dos grafías no producen el mismo parche")


def test_apply_replaces_header_and_fixes_checksum() -> None:
    rom = make_rom()
    patches, _ = patch.load_table(ROOT / "content" / "zerohistory.toml")
    image, applied, skipped = patch.apply_patches(rom, patches)
    check(not skipped, f"no debía omitir nada: {skipped}")
    check(applied, "no aplicó nada")
    check(patch.header_name(image) == "MMX ZERO HISTORY",
          f"cabecera quedó {patch.header_name(image)!r}")
    check(len(image) == len(rom), "el tamaño cambió")

    fixed, value = patch.fix_checksum(image)
    stored = fixed[patch.CHECKSUM_OFFSET] | (fixed[patch.CHECKSUM_OFFSET + 1] << 8)
    complement = (fixed[patch.CHECKSUM_COMPLEMENT_OFFSET]
                  | (fixed[patch.CHECKSUM_COMPLEMENT_OFFSET + 1] << 8))
    check(stored == value, f"checksum escrito 0x{stored:04X} != calculado 0x{value:04X}")
    check((stored ^ complement) == 0xFFFF,
          "complemento del checksum no es el XOR 0xFFFF")
    # El checksum debe cubrir el archivo entero, incluidos los bytes parcheados.
    check(patch.checksum(fixed) == stored, "el checksum no se revalida sobre la imagen final")


def test_idempotent() -> None:
    rom = make_rom()
    patches, _ = patch.load_table(ROOT / "content" / "zerohistory.toml")
    once, _, _ = patch.apply_patches(rom, patches)
    twice, applied, skipped = patch.apply_patches(once, patches)
    check(not skipped, f"la segunda pasada omitió parches: {skipped}")
    check(once == twice, "aplicar dos veces cambia la imagen")
    check(any("already applied" in line for line in applied),
          "la segunda pasada no reconoce el parche como aplicado")


def test_foreign_rom_is_untouched() -> None:
    rom = make_rom(name=b"OTHER GAME" + b" " * 11)
    patches, _ = patch.load_table(ROOT / "content" / "zerohistory.toml")
    image, applied, skipped = patch.apply_patches(rom, patches)
    check(image == rom, "modificó un ROM cuyo guard no coincidía")
    check(not applied, "dijo haber aplicado algo en un ROM ajeno")
    check(skipped, "no informó el parche omitido")


def test_partial_table_fails_closed() -> None:
    """Un parche bueno y uno imposible: no se escribe ninguna imagen."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        text = table_text((b"MMX ZERO HISTORY" + b" " * 5).hex())
        text += f"""
[[rom_patch]]
address = 0x100000
source = "deadbeefdeadbeef"
target_es = "cafebabecafebabe"
"""
        table = write_table(directory, text)
        rom_path = directory / "mmx3.sfc"
        rom_path.write_bytes(make_rom())
        code = patch.main([str(rom_path), "--check", "--table", str(table),
                           "--allow-foreign"])
        check(code == 1, f"--check con un parche imposible devolvió {code}, no 1")


def test_check_writes_nothing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        table = write_table(directory, table_text(
            (b"MMX ZERO HISTORY" + b" " * 5).hex()))
        rom_path = directory / "mmx3.sfc"
        rom = make_rom()
        rom_path.write_bytes(rom)
        before = hashlib.sha256(rom_path.read_bytes()).hexdigest()
        code = patch.main([str(rom_path), "--check", "--table", str(table),
                           "--allow-foreign"])
        after = hashlib.sha256(rom_path.read_bytes()).hexdigest()
        check(code == 0, f"--check devolvió {code}")
        check(before == after, "--check modificó el archivo")
        check(not list(directory.glob("*.sfc.zerohistory*")), "--check creó un archivo")


def test_apply_writes_copy_and_leaves_original() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        table = write_table(directory, table_text(
            (b"MMX ZERO HISTORY" + b" " * 5).hex()))
        rom_path = directory / "mmx3.sfc"
        rom = make_rom()
        rom_path.write_bytes(rom)
        output = directory / "out.sfc"
        code = patch.main([str(rom_path), "--apply", "-o", str(output),
                           "--table", str(table), "--allow-foreign"])
        check(code == 0, f"--apply devolvió {code}")
        check(rom_path.read_bytes() == rom, "--apply alteró el ROM original")
        check(output.is_file(), "no escribió la copia")
        image = output.read_bytes()
        check(patch.header_name(image) == "MMX ZERO HISTORY",
              f"la copia quedó con {patch.header_name(image)!r}")
        stored = image[patch.CHECKSUM_OFFSET] | (image[patch.CHECKSUM_OFFSET + 1] << 8)
        check(patch.checksum(image) == stored, "la copia no tiene checksum válido")


def test_mismatched_lengths_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        table = write_table(directory, table_text("4d4d"))
        try:
            patch.load_table(table)
            check(False, "aceptó un target de distinto tamaño que el source")
        except ValueError:
            pass


def test_copier_header_stripped() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        rom_path = directory / "mmx3.smc"
        rom_path.write_bytes(b"\x00" * patch.COPIER_HEADER + make_rom())
        rom, stripped = patch.read_rom(rom_path)
        check(stripped, "no detectó la cabecera de copiador")
        check(len(rom) == patch.ROM_BYTES, "no recortó los 512 bytes")


def test_wrong_size_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        rom_path = directory / "short.sfc"
        rom_path.write_bytes(b"\x00" * 1024)
        code = patch.main([str(rom_path), "--check"])
        check(code == 2, f"un ROM corto devolvió {code}, no 2")


def main() -> int:
    test_shipped_table_parses()
    test_shipped_table_uses_the_runner_spelling()
    test_both_spellings_parse_alike()
    test_apply_replaces_header_and_fixes_checksum()
    test_idempotent()
    test_foreign_rom_is_untouched()
    test_partial_table_fails_closed()
    test_check_writes_nothing()
    test_apply_writes_copy_and_leaves_original()
    test_mismatched_lengths_rejected()
    test_copier_header_stripped()
    test_wrong_size_rejected()
    if failures:
        print(f"\n{failures} check(s) fallaron")
        return 1
    print("content patch: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
