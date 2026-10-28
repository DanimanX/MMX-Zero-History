#!/usr/bin/env python3
"""Tests for the story overlay data and its authoring source.

The overlay writes into the player's cartridge image, so the properties worth
locking down are the ones whose failure is silent: a page that overlaps
another, a byte that is not text, a generated file that drifted from the
script, or text that the game's font cannot draw.

No dump is needed: the committed `src/x3_story_data.c` is the artifact under
test, and `--rom` adds the byte-exact regeneration check on machines that have
the dump.

    python3 tools/test_story_layout.py
    python3 tools/test_story_layout.py --rom mmx3.sfc
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_story as story  # noqa: E402

failures = 0


def check(condition: bool, message: str) -> None:
    global failures
    if not condition:
        print(f"FAIL {message}")
        failures += 1


PAGE_RE = re.compile(
    r"static const unsigned char kPage(\d+)\[\] = \{([^}]*)\};", re.S
)
TABLE_RE = re.compile(r"\{0x([0-9A-Fa-f]+)u, (\d+)u, kPage(\d+)\}", re.S)


def parse_generated() -> list[dict]:
    text = (ROOT / "src" / "x3_story_data.c").read_text(encoding="ascii")
    arrays = {
        int(index): bytes(int(value, 16) for value in body.split(","))
        for index, body in PAGE_RE.findall(text)
    }
    pages = []
    for address, length, index in TABLE_RE.findall(text):
        pages.append(
            {
                "address": int(address, 16),
                "length": int(length),
                "bytes": arrays[int(index)],
            }
        )
    return pages


def test_generated_pages_are_well_formed() -> None:
    pages = parse_generated()
    check(bool(pages), "el archivo generado no declara páginas")
    check(len(pages) == len({(p["address"], p["length"]) for p in pages}),
          "hay páginas duplicadas")

    ordered = sorted(pages, key=lambda p: p["address"])
    check([p["address"] for p in ordered] == [p["address"] for p in pages],
          "las páginas no están ordenadas por dirección")

    previous_end = -1
    for page in pages:
        check(len(page["bytes"]) == page["length"],
              f"0x{page['address']:06X}: {len(page['bytes'])} bytes, "
              f"slot de {page['length']}")
        check(page["address"] > previous_end,
              f"0x{page['address']:06X}: se solapa con la página anterior")
        previous_end = page["address"] + page["length"] - 1

    # Every page sits wholly inside one of the two regions the overlay owns.
    for page in pages:
        end = page["address"] + page["length"]
        inside = [
            name
            for name, (start, region_end) in {
                "guion": story.REGIONS[0],
                "menú": story.MENU_REGION,
            }.items()
            if start <= page["address"] and end <= region_end
        ]
        check(bool(inside),
              f"0x{page['address']:06X}: fuera de las regiones del overlay")


def test_generated_bytes_are_text() -> None:
    for page in parse_generated():
        for offset, value in enumerate(page["bytes"]):
            # Printable ASCII plus the game's own line break. Anything else
            # would overwrite a control command the page stream depends on.
            if not (0x20 <= value < 0x7F or value == 0x80):
                check(False,
                      f"0x{page['address'] + offset:06X}: byte 0x{value:02X} "
                      f"no es texto")
                break


def test_script_source_is_authorable() -> None:
    text = (ROOT / "content" / "story_es.txt").read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("@@"):
            continue
        check(stripped.isascii(), f"línea {number}: no es ASCII")
        # A beat may be longer than a rendered line -- it wraps at spaces --
        # but a single word that does not fit can never be placed.
        for word in stripped.split():
            check(len(word) <= story.MAX_LINE,
                  f"línea {number}: la palabra {word!r} mide {len(word)}, "
                  f"máx {story.MAX_LINE}")

    sections = story.parse_story(ROOT / "content" / "story_es.txt")
    for name, _, _ in story.SECTIONS:
        check(sections.get(name), f"falta la sección {name}")
    for number in range(1, story.CAPSULE_GROUPS + 1):
        check(sections.get(f"capsule{number}"), f"falta capsule{number}")
    check(not (set(sections) - {n for n, _, _ in story.SECTIONS}
               - {f"capsule{n}" for n in range(1, story.CAPSULE_GROUPS + 1)}),
          "hay secciones que el generador no empaqueta")


def test_generated_file_matches_the_script() -> None:
    """Editing content/story_es.txt without regenerating must fail here.

    Without a dump the generator cannot run, so the committed manifest is the
    bridge: it records how many authored lines each section consumed.
    """
    manifest_path = ROOT / "content" / "story_manifest.json"
    check(manifest_path.is_file(), "falta content/story_manifest.json")
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sections = story.parse_story(ROOT / "content" / "story_es.txt")

    for name, data in manifest["sections"].items():
        if not name.startswith(("capsule", "intro", "act1", "mid", "final")):
            continue
        authored = len(sections.get(name, []))
        check(authored == data["authored"],
              f"{name}: el guion tiene {authored} líneas y el manifiesto "
              f"{data['authored']}; corré tools/build_story.py")

    pages = parse_generated()
    check(len(pages) == manifest["pages"],
          f"el generado tiene {len(pages)} páginas y el manifiesto "
          f"{manifest['pages']}")
    check(sum(p["length"] for p in pages) == manifest["bytes"],
          "el total de bytes no coincide con el manifiesto")
    verify = (ROOT / "tools" / "verify_rom.py").read_text()
    check(f'EXPECTED_SHA256 = "{manifest["rom_sha256"]}"' in verify,
          "el manifiesto y tools/verify_rom.py no declaran el mismo digest")


def test_regeneration_is_byte_exact(rom_path: Path) -> None:
    """With the dump present, regenerating must reproduce the committed file."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "x3_story_data.c"
        manifest = Path(tmp) / "story_manifest.json"
        code = story.main([
            "--rom", str(rom_path),
            "--out", str(out),
            "--manifest", str(manifest),
        ])
        if code != 0:
            check(False, "build_story falló con el dump dado")
            return
        check(out.read_bytes() == (ROOT / "src" / "x3_story_data.c").read_bytes(),
              "el generado no se reproduce; corré tools/build_story.py --rom")
        check(manifest.read_bytes() ==
              (ROOT / "content" / "story_manifest.json").read_bytes(),
              "el manifiesto no se reproduce; corré tools/build_story.py --rom")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", help="dump verificado, para la prueba de bytes")
    args = ap.parse_args(argv)

    test_generated_pages_are_well_formed()
    test_generated_bytes_are_text()
    test_script_source_is_authorable()
    test_generated_file_matches_the_script()
    if args.rom:
        test_regeneration_is_byte_exact(Path(args.rom))

    if failures == 0:
        print("ok: overlay narrativo")
    return failures != 0


if __name__ == "__main__":
    raise SystemExit(main())
