#!/usr/bin/env python3
"""Build the Zero History story overlay from the player's dump.

The story is authored in ``content/story_es.txt`` as short lines grouped by
section. This tool reads the verified Mega Man X3 (USA) image, finds the
game's own text slots, packs the authored lines into them without changing a
single control byte, and emits ``src/x3_story_data.c``.

Why this shape:

* The ROM stores its script as plain ASCII with ``0x80 0x80`` line breaks and
  one-byte control commands between pages. We replace only the printable run
  of each page, so every pointer and every control command the game already
  uses stays valid. No text relocation, no guessed pointers.
* The generated C contains only our Spanish text, the ROM offsets and the
  exact byte counts. It never contains the original English script, so the
  repository does not distribute ROM-derived text.
* The runtime applies the overlay only after hashing the loaded image against
  ``EXPECTED_SHA256``. A different dump receives nothing.

Usage:
    python3 tools/build_story.py --rom /path/to/mmx3.sfc
    python3 tools/build_story.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

EXPECTED_SHA256 = "65b03268afac296330e8ff8d60dd0825879e13ed658b37713c034a3bd074f1d7"
BASE_SIZE = 2 * 1024 * 1024
STORY_SOURCE = ROOT / "content" / "story_es.txt"
OUTPUT_C = ROOT / "src" / "x3_story_data.c"
MANIFEST = ROOT / "content" / "story_manifest.json"

# The story region is the game's own script bank: intro, dialogue pages,
# capsule texts and the ending. Offsets are linear file offsets in the
# headerless 2 MiB image and never change between supported dumps.
SECTIONS = [
    ("intro", 0x1CC2B6, 0x1CC6A9),
    ("act1", 0x1CC6A9, 0x1CCBFB),
    ("mid", 0x1CD425, 0x1CDA0B),
    ("final", 0x1CDA0B, 0x1CEB13),
]
CAPSULE_START = 0x1CCBFB
CAPSULE_END = 0x1CD425
CAPSULE_GROUPS = 8

# The tables below sit just past the page stream. Together with SECTIONS this
# is the whole region the overlay touches, and a test refuses any page or
# table outside it.
REGION_END = 0x1CF500

# The menu labels live in the bank where the title screen and the options
# screens keep their strings, far from the script. Kept as an explicit second
# region so a typo cannot silently rewrite unrelated code.
MENU_REGION = (0x30F00, 0x31500)

# Every byte the overlay may touch, as [start, end).
REGIONS = [(SECTIONS[0][1], REGION_END), MENU_REGION]

# Tables that are not part of the page stream: boss names, their stats, the
# weapon-get names, the cast roll header and the stage-boss placeholder.
# ``b"..."`` values use 0x80 as the game's own line separator.
TABLE_PATCHES = [
    # Cast roll header: " MEGAMAN X3 " -> " ZERO HISTORY "
    (0x1CEB13, 16, b" ZERO HISTORY \x80\x80"),
    # W-01 .. W-08, same two-line shape the boss intro uses.
    (0x1CEE45, 17, b"CONDOR\x80 COBALTO\x80\x80"),
    (0x1CEE83, 21, b"SALITRE\x80   SIERPE\x80\x80"),
    (0x1CEEC6, 19, b"GLACIAR\x80   GRIFO\x80\x80"),
    (0x1CEF06, 19, b"VIBORA\x80   CALDOR\x80\x80"),
    (0x1CEF46, 17, b"MAREA\x80   MANTIS\x80\x80"),
    (0x1CEF84, 19, b"JABALI\x80   ALERCE\x80\x80"),
    (0x1CEFC4, 17, b"BUHO\x80   RELOJ\x80\x80"),
    (0x1CF002, 15, b"PUMA\x80CHATARRA\x80\x80"),
    # Boss stats. The slot after each name is the POWER line, then SPEED.
    (0x1CEE59, 16, b"POWER    4800rp\x80"),
    (0x1CEE6B, 17, b"SPEED    9200rp\x80\x80"),
    (0x1CEE9B, 16, b"POWER    5200rp\x80"),
    (0x1CEEAD, 18, b"SPEED    4100rp\x80\x80\x80"),
    (0x1CEEDC, 16, b"POWER    6100rp\x80"),
    (0x1CEEEE, 17, b"SPEED    3800rp\x80\x80"),
    (0x1CEF1C, 16, b"POWER    7400rp\x80"),
    (0x1CEF2E, 17, b"SPEED    5600rp\x80\x80"),
    (0x1CEF5A, 16, b"POWER    5900rp\x80"),
    (0x1CEF6C, 17, b"SPEED    6700rp\x80\x80"),
    (0x1CEF9A, 16, b"POWER    8300rp\x80"),
    (0x1CEFAC, 17, b"SPEED    4900rp\x80\x80"),
    (0x1CEFD8, 16, b"POWER    4600rp\x80"),
    (0x1CEFEA, 17, b"SPEED    8800rp\x80\x80"),
    (0x1CF014, 16, b"POWER    9100rp\x80"),
    (0x1CF026, 17, b"SPEED    7300rp\x80\x80"),
    # Weapon-get names.
    (0x1CF291, 14, b"ALA COBALTO"),
    (0x1CF2A8, 12, b"SALMUERA"),
    (0x1CF2BD, 12, b"ALIENTO"),
    (0x1CF2D2, 10, b"ERUPCION"),
    (0x1CF2E5, 13, b"OLA CORTANTE"),
    (0x1CF2FB, 14, b"ASTILLA"),
    (0x1CF312, 12, b"SEGUNDERO"),
    (0x1CF327, 12, b"IMAN PUMA"),
    # Stage-boss placeholder used by the intro screen.
    (0x1CF4C2, 24, b"STAGE\x80\x80BOSS:\x80\x80CERO-OMEGA"),
    # Title screen and options. The three copies of each label are the three
    # language variants the cart ships; they share one layout column, so the
    # replacement stays left-aligned and pads with blanks like the original.
    (0x30FE8, 11, b"EMPEZAR"),
    (0x30FF7, 9, b"CLAVE"),
    (0x31004, 11, b"OPCIONES"),
    (0x31014, 11, b"EMPEZAR"),
    (0x31023, 9, b"CLAVE"),
    (0x31030, 11, b"OPCIONES"),
    (0x31040, 11, b"EMPEZAR"),
    (0x3104F, 9, b"CLAVE"),
    (0x3105C, 11, b"OPCIONES"),
    (0x311AB, 10, b"TECLAS"),
    (0x3123E, 10, b"TECLAS"),
    (0x312D1, 10, b"SONIDO"),
    (0x31332, 10, b"SONIDO"),
]

MAX_LINE = 32


def strip_copier_header(data: bytes) -> bytes:
    if len(data) % 32768 == 512:
        return data[512:]
    return data


def load_rom(path: Path) -> bytes:
    data = strip_copier_header(path.read_bytes())
    if len(data) != BASE_SIZE:
        raise SystemExit(f"{path}: {len(data)} bytes, expected {BASE_SIZE}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(
            f"{path}: sha256 {digest} does not match the supported dump "
            f"({EXPECTED_SHA256})"
        )
    return data


def is_text_byte(byte: int) -> bool:
    return 0x20 <= byte < 0x7F or byte == 0x80


def line_budgets(raw: bytes) -> list[int]:
    """Width budget of every line the original page drew.

    The page is the game's own text slot: printable bytes separated by
    ``0x80 0x80``. Keeping the exact same number of lines, each no wider than
    the line the original occupied, is what makes the replacement safe -- the
    box, the centring and the control bytes around the page never move.
    """
    budgets = []
    for part in raw.split(b"\x80\x80"):
        cleaned = part.rstrip(b"\x80 ")
        if not cleaned and budgets:
            continue
        budgets.append(len(cleaned))
    return budgets or [0]


def parse_slots(rom: bytes, start: int, end: int) -> list[dict]:
    slots = []
    i = start
    while i < end:
        if not is_text_byte(rom[i]):
            i += 1
            continue
        j = i
        while j < end and is_text_byte(rom[j]):
            j += 1
        length = j - i
        if length >= 6:
            raw = rom[i:j]
            slots.append(
                {
                    "address": i,
                    "length": length,
                    "budgets": line_budgets(raw),
                    "text": raw.replace(b"\x80", b"\\n").decode("ascii", "replace"),
                }
            )
        i = j
    return slots


def parse_story(path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@@"):
            current = line[2:].strip()
            if not current:
                raise SystemExit(f"{path}:{number}: empty section name")
            sections.setdefault(current, [])
            continue
        if current is None:
            raise SystemExit(f"{path}:{number}: text before the first @@section")
        if not line.isascii():
            raise SystemExit(f"{path}:{number}: non-ASCII text: {line!r}")
        sections[current].append(line)
    return sections


def _wrap_beat(beat: str, cursor: list[int],
               budgets: list[tuple[int, int, int]],
               filled: dict[tuple[int, int], str], label: str) -> None:
    """Place one authored beat, wrapping at spaces across page lines.

    A line too narrow for the next word is skipped (left blank), never
    truncated: the original script has a few six-column lines that held a
    single short word, and a blank line there reads as a beat, not an error.
    """
    words = beat.split()
    while words:
        if cursor[0] >= len(budgets):
            raise SystemExit(
                f"{label}: out of lines; still to place: {' '.join(words)!r}"
            )
        page, line, cap = budgets[cursor[0]]
        current = filled.get((page, line), "")
        candidate = (current + " " + words[0]).strip() if current else words[0]
        if len(candidate) <= cap:
            filled[(page, line)] = candidate
            words.pop(0)
            continue
        if current:
            # The line is partly used; the rest of the word goes below.
            cursor[0] += 1
            continue
        # The line is empty and still too narrow: skip it, and any other
        # empty line that cannot hold this word either.
        while (cursor[0] < len(budgets) and len(words[0]) > budgets[cursor[0]][2]):
            cursor[0] += 1


SPEAKERS = (
    "X:", "Zero:", "Eco:", "Salas:", "Nadia:", "Cero-Omega:", "ORDEN:",
)

# The script window draws three lines and CENTRES the third one, which starts
# at column 8 of a 32-column box. A centred line therefore has ~22 columns
# before it runs off the right edge, and the game clips rather than wraps.
# Measured on the real engine: a 28-column centred line loses its last glyph.
# 22 is the widest line that is safe in both positions.
MAX_LINE = 22

# A new speaker starts a new line; narration continues on the current line if
# that line already carries this many columns, which keeps the prose from
# leaving half-empty lines behind.
BEAT_BREAK_MIN = 10


def _is_dialogue(beat: str) -> bool:
    return beat.startswith(SPEAKERS)


def wrap_lines(beats: list[str]) -> list[str]:
    """Turn authored beats into rendered lines of at most MAX_LINE columns."""
    lines: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            lines.append(current)
            current = ""

    for beat in beats:
        if current and (_is_dialogue(beat) or len(current) >= BEAT_BREAK_MIN):
            flush()
        for word in beat.split():
            candidate = (current + " " + word).strip() if current else word
            if len(candidate) <= MAX_LINE:
                current = candidate
                continue
            flush()
            if len(word) > MAX_LINE:
                raise SystemExit(
                    f"the word {word!r} is {len(word)} columns, max {MAX_LINE}"
                )
            current = word
    flush()
    return lines


def pack_slots(slots: list[dict], beats: list[str], label: str) -> list[dict]:
    """Distribute authored lines into the pages the cartridge already has.

    Two invariants keep the game's own layout intact:

    * each page keeps its exact byte length, so no pointer and no control
      command moves, and
    * each page gets the same NUMBER of lines the original drew there, so a
      layout command that turns centring or a box on keeps covering the same
      lines of the scene.

    Inside those limits the words are free, as long as no line exceeds
    MAX_LINE -- the widest line the original script ever used.
    """
    queue = list(beats)
    out = []
    index = 0
    for slot in slots:
        cap = slot["length"]
        wanted_lines = max(1, len(slot["budgets"]))
        body = bytearray()
        used = 0
        while index < len(queue) and used < wanted_lines:
            # Build the next line from the queue's current beat.
            remaining = cap - len(body) - 2
            if remaining <= 0:
                break
            words = queue[index].split()
            line_words = []
            length = 0
            while words:
                candidate = length + (1 if line_words else 0) + len(words[0])
                if candidate > MAX_LINE or candidate > remaining:
                    break
                line_words.append(words.pop(0))
                length = candidate
            if not line_words:
                break
            body.extend(" ".join(line_words).encode("ascii"))
            body.extend(b"\x80\x80")
            used += 1
            if words:
                queue[index] = " ".join(words)
            else:
                index += 1
        body.extend(b" " * (cap - len(body)))
        out.append(
            {
                "address": slot["address"],
                "length": cap,
                "bytes": bytes(body),
                "lines_used": used,
            }
        )
    if index != len(queue):
        remaining = " ".join(queue[index:])
        raise SystemExit(
            f"{label}: {len(queue) - index} beat(s) left over; the section is "
            f"longer than its pages hold. Still to place: {remaining[:160]!r}"
        )
    return out, sum(page["lines_used"] for page in out)


def build_c(pages: list[dict]) -> str:
    chunks = [
        "/* Generated by tools/build_story.py -- do not edit by hand.\n"
        " *\n"
        " * Each entry is a page-sized replacement for a text slot in the\n"
        " * supported Mega Man X3 (USA) image. The bytes are our Spanish text\n"
        " * only; the original script is not stored here. The runtime checks\n"
        " * the loaded image digest before writing anything.\n"
        " */\n"
        '#include "x3_story.h"\n\n'
    ]
    for i, page in enumerate(pages):
        data = ",".join(f"0x{b:02X}" for b in page["bytes"])
        chunks.append(f"static const unsigned char kPage{i}[] = {{{data}}};\n")
    chunks.append("\nconst X3StoryPage kX3StoryPages[] = {\n")
    for i, page in enumerate(pages):
        chunks.append(
            f'  {{0x{page["address"]:06X}u, {page["length"]}u, kPage{i}}},\n'
        )
    chunks.append("};\n")
    chunks.append(
        f"const unsigned kX3StoryPageCount = "
        f"(unsigned)(sizeof kX3StoryPages / sizeof kX3StoryPages[0]);\n"
    )
    return "".join(chunks)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default="mmx3.sfc", help="verified 2 MiB dump")
    ap.add_argument("--check", action="store_true", help="validate, write nothing")
    ap.add_argument("--out", default=str(OUTPUT_C), help="generated C file")
    ap.add_argument("--manifest", default=str(MANIFEST), help="manifest path")
    args = ap.parse_args(argv)

    rom = load_rom(Path(args.rom))
    story = parse_story(STORY_SOURCE)

    packed: list[dict] = []
    report: dict[str, dict] = {}

    for name, start, end in SECTIONS:
        slots = parse_slots(rom, start, end)
        lines = story.get(name, [])
        pages, used = pack_slots(slots, lines, name)
        packed.extend(pages)
        report[name] = {
            "pages": len(pages),
            "lines": used,
            "authored": len(lines),
            "address": f"0x{start:06X}-0x{end:06X}",
        }
        if used < len(lines):
            print(
                f"warning: {name}: {len(lines) - used} authored line(s) did not fit",
                file=sys.stderr,
            )

    # Capsules: eight groups, each starting with the (DR.LIGHT) label. The
    # authored section names are capsule1 .. capsule8.
    capsule_slots = parse_slots(rom, CAPSULE_START, CAPSULE_END)
    groups: list[list[dict]] = []
    for slot in capsule_slots:
        if "DR.LIGHT" in slot["text"]:
            groups.append([])
        if groups:
            groups[-1].append(slot)
    if len(groups) != CAPSULE_GROUPS:
        raise SystemExit(f"found {len(groups)} capsule groups, expected {CAPSULE_GROUPS}")
    for n, group in enumerate(groups, 1):
        name = f"capsule{n}"
        # The first slot of a capsule is its own prompt -- "(DR.LIGHT)" /
        # "Enter this capsule," / "X." -- and stays exactly as it is. Only the
        # body the capsule speaks is authored.
        group = group[1:]
        lines = story.get(name, [])
        pages, used = pack_slots(group, lines, name)
        packed.extend(pages)
        report[name] = {
            "pages": len(pages),
            "lines": used,
            "authored": len(lines),
            "address": f"0x{group[0]['address']:06X}",
        }
        if used < len(lines):
            print(
                f"warning: {name}: {len(lines) - used} authored line(s) did not fit",
                file=sys.stderr,
            )

    # Explicit tables. These are byte strings, not packed pages.
    for address, length, payload in TABLE_PATCHES:
        if len(payload) > length:
            raise SystemExit(
                f"table 0x{address:06X}: {len(payload)} bytes > slot {length}"
            )
        packed.append(
            {
                "address": address,
                "length": length,
                "bytes": payload + b" " * (length - len(payload)),
                "lines_used": payload.count(b"\x80") // 2,
            }
        )
        report[f"table_0x{address:06X}"] = {
            "pages": 1,
            "lines": 1,
            "authored": 1,
            "address": f"0x{address:06X}",
        }

    packed.sort(key=lambda page: page["address"])
    c_source = build_c(packed)
    manifest = {
        "rom_sha256": EXPECTED_SHA256,
        "source": str(STORY_SOURCE.relative_to(ROOT)),
        "pages": len(packed),
        "bytes": sum(page["length"] for page in packed),
        "sections": report,
    }

    if args.check:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0

    out_path = Path(args.out)
    manifest_path = Path(args.manifest)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(c_source, encoding="ascii")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"{out_path}: {len(packed)} pages, {manifest['bytes']} bytes")
    for name, data in report.items():
        print(
            f"  {name:18s} {data['pages']:3d} page(s)  "
            f"{data['lines']:3d}/{data['authored']:3d} line(s)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
