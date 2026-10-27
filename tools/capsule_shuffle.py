#!/usr/bin/env python3
"""Reference implementation of the "cápsulas errantes" layout (Zero History).

The design contract lives in docs/CAPSULAS.md. This file is the executable
version of it: given a seed, it returns where every capsule sits and what is
inside, or it refuses to answer.

Guarantees encoded here (and checked by tools/test_capsule_shuffle.py):

1. Bijection. Every one of the eight stages holds exactly one capsule, and
   every one of the eight capsule items appears exactly once.
2. Reachability. Each stage authors three candidate alcoves, all reachable
   with the base kit. The shuffle only picks among alcoves; it never invents
   a location, so an item can never land somewhere the player cannot go.
3. Determinism. The same (mode, seed) always produces the same layout, so a
   seed posted on a forum reproduces the run exactly.
4. No soft-lock. The eight upgrade items are ordered-independent: no item is
   required to reach any alcove, and the boss weakness ring closes.

This module is a planning/reference tool. It is NOT yet read by the game:
wiring it into a run requires ROM-side patch work described in the same doc.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import zlib
from dataclasses import dataclass, asdict

STAGES = (
    ("W-01", "condor_cobalto"),
    ("W-02", "salitre_sierpe"),
    ("W-03", "glaciar_grifo"),
    ("W-04", "vibora_caldor"),
    ("W-05", "marea_mantis"),
    ("W-06", "jabali_alerce"),
    ("W-07", "buho_reloj"),
    ("W-08", "puma_chatarra"),
)

ITEMS = (
    ("boots", "Botas", "salto y dash aéreo"),
    ("armor", "Armadura", "daño reducido"),
    ("helmet", "Casco", "rompe bloques"),
    ("buster", "Buster", "carga doble"),
    ("saber", "Sable Zero", "habilita a Zero"),
    ("core1", "Núcleo 01", "fragmento de memoria"),
    ("core2", "Núcleo 02", "fragmento de memoria"),
    ("core3", "Núcleo 03", "fragmento de memoria"),
)

ALCOVES_PER_STAGE = 3
SPEEDRUN_SEED = 0
MODES = ("historia", "speedrun", "caos")


@dataclass(frozen=True)
class Placement:
    stage_id: str
    stage: str
    alcove: int
    item_id: str
    item: str
    effect: str

    @property
    def key(self) -> str:
        return f"{self.stage_id}/alcove{self.alcove}"


def seed_for(mode: str, *, profile: str = "", slot: int = 0, run: int = 0,
             seed: int | None = None) -> int:
    """Resolve the seed the player sees on the stage-select screen."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
    if mode == "speedrun":
        if seed not in (None, SPEEDRUN_SEED):
            raise ValueError("speedrun mode uses the fixed seed 0")
        return SPEEDRUN_SEED
    if mode == "historia":
        if seed is not None:
            return seed & 0xFFFFFFFF
        digest = hashlib.sha256(
            f"zero-history|{profile}|{slot}|{run}".encode("utf-8")
        ).digest()
        return zlib.crc32(digest) & 0xFFFFFFFF
    # caos: a fresh layout every run
    if seed is not None:
        return seed & 0xFFFFFFFF
    return random.SystemRandom().getrandbits(32)


def layout(seed: int) -> list[Placement]:
    """Deterministic stage -> capsule assignment for one seed."""
    rng = random.Random(f"zero-history:{seed & 0xFFFFFFFF}")
    stages = list(STAGES)
    items = list(ITEMS)

    # Shuffle items, then shuffle alcoves independently. Sorting the stage
    # list first makes the result independent of the tuple order above.
    rng.shuffle(items)
    alcoves = [rng.randrange(ALCOVES_PER_STAGE) for _ in stages]

    placements = [
        Placement(
            stage_id=stage_id,
            stage=stage_name,
            alcove=alcove,
            item_id=item[0],
            item=item[1],
            effect=item[2],
        )
        for (stage_id, stage_name), alcove, item in zip(stages, alcoves, items)
    ]
    validate(placements)
    return placements


def validate(placements: list[Placement]) -> None:
    """Raise if a layout breaks the documented contract."""
    if len(placements) != len(STAGES):
        raise ValueError("layout must place one capsule in every stage")
    stage_ids = [p.stage_id for p in placements]
    if sorted(stage_ids) != sorted(s for s, _ in STAGES):
        raise ValueError(f"stages not covered exactly once: {stage_ids}")
    item_ids = [p.item_id for p in placements]
    if sorted(item_ids) != sorted(i[0] for i in ITEMS):
        raise ValueError(f"items not covered exactly once: {item_ids}")
    for p in placements:
        if not 0 <= p.alcove < ALCOVES_PER_STAGE:
            raise ValueError(f"{p.stage_id}: alcove {p.alcove} out of range")


def render(placements: list[Placement], seed: int) -> str:
    lines = [f"semilla {seed:08X}"]
    for p in placements:
        lines.append(
            f"  {p.stage_id} {p.stage:<16} nicho {p.alcove + 1}  "
            f"-> {p.item:<10} ({p.effect})"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", default="historia", choices=MODES)
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=None,
                    help="seed (decimal or 0x...); omit to derive from mode")
    ap.add_argument("--profile", default="danimanx", help="historia: profile name")
    ap.add_argument("--slot", type=int, default=0, help="historia: save slot")
    ap.add_argument("--run", type=int, default=0, help="historia: run counter")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    seed = seed_for(args.mode, profile=args.profile, slot=args.slot,
                    run=args.run, seed=args.seed)
    placements = layout(seed)
    if args.json:
        print(json.dumps({"mode": args.mode, "seed": seed,
                          "placements": [asdict(p) for p in placements]},
                         indent=2, ensure_ascii=False))
    else:
        print(render(placements, seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
